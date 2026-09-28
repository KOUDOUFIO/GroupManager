"""Tests du paiement Mobile Money (PayGate), des rappels SMS/WhatsApp,
de la demonstration, des tarifs et des temoignages."""

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Contribution, Group, Member, Testimonial
from .services.messaging_service import CHANNEL_SMS, CHANNEL_WHATSAPP, MessagingService
from .services.paygate_service import PayGateService
from .services.phone import normalize_phone
from .templatetags.core_extras import money

PAYGATE = {"PAYGATE_AUTH_TOKEN": "test-token", "PAYGATE_ENABLED": True}
# Point de depart neutre : les tests ne dependent jamais des vraies cles du .env local.
NO_PROVIDERS = {
    "PAYGATE_AUTH_TOKEN": "", "PAYGATE_ENABLED": False, "ESMS_API_KEY": "",
    "TWILIO_ACCOUNT_SID": "", "TWILIO_AUTH_TOKEN": "", "TWILIO_SMS_FROM": "", "TWILIO_WHATSAPP_FROM": "",
}


def fake_response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


class PhoneAndMoneyTests(TestCase):
    def test_normalize_phone_adds_togo_country_code(self):
        self.assertEqual(normalize_phone("90 12 34 56"), "+22890123456")
        self.assertEqual(normalize_phone("+228 90 12 34 56"), "+22890123456")
        self.assertEqual(normalize_phone("0022890123456"), "+22890123456")
        self.assertEqual(normalize_phone("12"), "")

    def test_money_filter_uses_fcfa_and_thousands(self):
        self.assertIn("FCFA", money(Decimal("15000")))
        self.assertTrue(money(Decimal("15000")).replace(" ", " ").startswith("15"))
        self.assertNotIn(",00", money(Decimal("15000")))


@override_settings(**NO_PROVIDERS)
class MemberPaymentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="payer", password="password123")
        self.group = Group.objects.create(name="Tontine")
        self.member = Member.objects.create(full_name="Ama", phone="90 12 34 56", user=self.user)
        self.member.groups.add(self.group)
        self.client.force_login(self.user)

    def _post_payment(self):
        return self.client.post(reverse("member_portal_pay"), {
            "group": self.group.pk,
            "contribution_type": Contribution.TYPE_MONTHLY,
            "amount": "5000",
            "network": "TMONEY",
            "phone_number": "90 12 34 56",
        })

    def test_payment_page_hidden_without_paygate(self):
        self.assertEqual(self.client.get(reverse("member_portal_pay")).status_code, 404)

    @override_settings(**PAYGATE)
    @patch("core.services.paygate_service.requests.post")
    def test_payment_creates_pending_contribution_and_sends_request(self, post):
        post.return_value = fake_response({"tx_reference": "12345", "status": 0})
        response = self._post_payment()
        contribution = Contribution.objects.get()
        self.assertRedirects(response, reverse("member_portal_payment_status", args=[contribution.pk]))
        self.assertEqual(contribution.payment_status, Contribution.STATUS_PENDING)
        self.assertEqual(contribution.payer_phone, "+22890123456")
        self.assertEqual(contribution.gateway_reference, "12345")
        sent = post.call_args.kwargs["json"]
        self.assertEqual(sent["network"], "TMONEY")
        self.assertEqual(sent["amount"], 5000)
        self.assertEqual(sent["identifier"], contribution.gateway_transaction_id)

    @override_settings(**PAYGATE)
    @patch("core.services.paygate_service.requests.post")
    def test_refused_payment_leaves_no_contribution(self, post):
        post.return_value = fake_response({"status": 4})
        response = self._post_payment()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Contribution.objects.exists())

    @override_settings(**PAYGATE)
    def test_member_cannot_see_another_members_payment(self):
        other = Member.objects.create(full_name="Autre")
        other.groups.add(self.group)
        foreign = Contribution.objects.create(
            member=other, group=self.group, contribution_type=Contribution.TYPE_MONTHLY, amount=5000,
            paid_at=timezone.localdate(), payment_status=Contribution.STATUS_PENDING, gateway_transaction_id="KZX",
        )
        response = self.client.get(reverse("member_portal_payment_status", args=[foreign.pk]))
        self.assertEqual(response.status_code, 404)


@override_settings(**{**NO_PROVIDERS, **PAYGATE})
class PayGateWebhookTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="Tontine")
        self.member = Member.objects.create(full_name="Ama")
        self.member.groups.add(self.group)
        self.contribution = Contribution.objects.create(
            member=self.member, group=self.group, contribution_type=Contribution.TYPE_MONTHLY,
            amount=Decimal("5000"), paid_at=timezone.localdate(), payment_method=Contribution.METHOD_MOBILE_MONEY,
            payment_status=Contribution.STATUS_PENDING, gateway_transaction_id="KZ123",
        )

    def _notify(self):
        return self.client.post(
            reverse("paygate_webhook"),
            data=json.dumps({"identifier": "KZ123", "tx_reference": "999", "amount": 5000}),
            content_type="application/json",
        )

    @patch("core.services.paygate_service.requests.post")
    def test_webhook_confirms_after_verification(self, post):
        post.return_value = fake_response({"status": 0, "amount": 5000, "payment_reference": "TM-777"})
        self.assertEqual(self._notify().status_code, 200)
        self.contribution.refresh_from_db()
        self.assertEqual(self.contribution.payment_status, Contribution.STATUS_CONFIRMED)
        self.assertEqual(self.contribution.gateway_reference, "TM-777")
        # Le statut est relu chez PayGate par notre identifiant, jamais pris du webhook.
        self.assertTrue(post.call_args.args[0].endswith("/v2/status"))

    @patch("core.services.paygate_service.requests.post")
    def test_webhook_rejects_underpaid_amount(self, post):
        post.return_value = fake_response({"status": 0, "amount": 100})
        self._notify()
        self.contribution.refresh_from_db()
        self.assertEqual(self.contribution.payment_status, Contribution.STATUS_PENDING)

    @patch("core.services.paygate_service.requests.post")
    def test_expired_payment_is_marked_failed(self, post):
        post.return_value = fake_response({"status": 4})
        self._notify()
        self.contribution.refresh_from_db()
        self.assertEqual(self.contribution.payment_status, Contribution.STATUS_FAILED)

    @patch("core.services.paygate_service.requests.post")
    def test_unknown_transaction_is_ignored(self, post):
        response = self.client.post(
            reverse("paygate_webhook"), data=json.dumps({"identifier": "NOPE"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        post.assert_not_called()

    @patch("core.services.paygate_service.requests.post")
    def test_check_pending_payments_command(self, post):
        post.return_value = fake_response({"status": 0, "amount": 5000})
        call_command("check_pending_payments", stdout=MagicMock())
        self.contribution.refresh_from_db()
        self.assertEqual(self.contribution.payment_status, Contribution.STATUS_CONFIRMED)


@override_settings(**NO_PROVIDERS)
class MessagingTests(TestCase):
    @patch("core.services.messaging_service.requests.post")
    def test_nothing_sent_without_configuration(self, post):
        self.assertEqual(MessagingService.enabled_channels(), [])
        self.assertFalse(MessagingService.send(CHANNEL_SMS, "90123456", "Bonjour"))
        post.assert_not_called()

    @override_settings(TWILIO_ACCOUNT_SID="AC1", TWILIO_AUTH_TOKEN="tok", TWILIO_SMS_FROM="+15550001111",
                       TWILIO_WHATSAPP_FROM="+15550002222", TWILIO_WHATSAPP_TEMPLATE_SID="HX1")
    @patch("core.services.messaging_service.requests.post")
    def test_whatsapp_uses_approved_template(self, post):
        post.return_value = fake_response({})
        self.assertTrue(MessagingService.send(CHANNEL_WHATSAPP, "90 12 34 56", "texte", template_vars={"1": "Ama"}))
        data = post.call_args.kwargs["data"]
        self.assertEqual(data["To"], "whatsapp:+22890123456")
        self.assertEqual(data["From"], "whatsapp:+15550002222")
        self.assertEqual(data["ContentSid"], "HX1")

    @override_settings(TWILIO_ACCOUNT_SID="AC1", TWILIO_AUTH_TOKEN="tok", TWILIO_SMS_FROM="+15550001111")
    @patch("core.services.messaging_service.requests.post")
    def test_reminders_are_sent_by_sms(self, post):
        post.return_value = fake_response({})
        group = Group.objects.create(name="Tontine")
        paid = Member.objects.create(full_name="A jour", phone="90000001")
        late = Member.objects.create(full_name="En retard", phone="90000002")
        for m in (paid, late):
            m.groups.add(group)
        Contribution.objects.create(
            member=paid, group=group, contribution_type=Contribution.TYPE_MONTHLY, amount=5000,
            paid_at=timezone.localdate(),
        )
        call_command("send_contribution_reminders", stdout=MagicMock())
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.kwargs["data"]["To"], "+22890000002")


@override_settings(**NO_PROVIDERS)
class EsmsAfricaTests(TestCase):
    @override_settings(ESMS_API_KEY="esms_test_abc", ESMS_SENDER_ID="KOTIZA",
                       TWILIO_ACCOUNT_SID="", TWILIO_AUTH_TOKEN="")
    @patch("core.services.messaging_service.requests.post")
    def test_sms_goes_through_esms_africa(self, post):
        post.return_value = fake_response({"id": "m1", "status": "submitted"})
        self.assertEqual(MessagingService.enabled_channels(), [CHANNEL_SMS])
        self.assertTrue(MessagingService.send(CHANNEL_SMS, "90 12 34 56", "Bonjour"))
        self.assertTrue(post.call_args.args[0].endswith("/messages/send"))
        self.assertEqual(post.call_args.kwargs["json"], {"to": "+22890123456", "text": "Bonjour", "sender_id": "KOTIZA"})
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer esms_test_abc")

    @override_settings(ESMS_API_KEY="esms_test_abc")
    @patch("core.services.messaging_service.requests.post")
    def test_esms_failure_returns_false(self, post):
        import requests as real_requests

        post.side_effect = real_requests.ConnectionError("hors ligne")
        self.assertFalse(MessagingService.send(CHANNEL_SMS, "90 12 34 56", "Bonjour"))


@override_settings(**NO_PROVIDERS)
class DemoAndMarketingTests(TestCase):
    def test_seed_demo_is_repeatable_and_removable(self):
        call_command("seed_demo", password="DemoPass123", stdout=MagicMock())
        call_command("seed_demo", password="DemoPass123", stdout=MagicMock())
        self.assertEqual(Group.objects.filter(name__endswith="(démo)").count(), 1)
        self.assertEqual(Member.objects.filter(email__endswith="@demo.kotiza.tg").count(), 12)
        self.assertTrue(get_user_model().objects.filter(username="demo-tresorier").exists())
        call_command("seed_demo", reset=True, stdout=MagicMock())
        self.assertFalse(Group.objects.filter(name__endswith="(démo)").exists())
        self.assertFalse(Member.objects.filter(email__endswith="@demo.kotiza.tg").exists())

    def test_pricing_in_fcfa_with_free_trial(self):
        response = self.client.get(reverse("proposal_page"))
        self.assertContains(response, "FCFA")
        self.assertNotContains(response, "€")
        self.assertContains(response, "essai gratuit")

    def test_only_consented_published_testimonials_are_shown(self):
        Testimonial.objects.create(author_name="Brouillon", quote="Pas encore publié")
        Testimonial.objects.create(author_name="Kafui", quote="Très pratique", consent_given=True, is_published=True)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Très pratique")
        self.assertNotContains(response, "Pas encore publié")

    def test_testimonial_cannot_be_published_without_consent(self):
        with self.assertRaises(ValidationError):
            Testimonial(author_name="X", quote="Y", is_published=True).full_clean()
