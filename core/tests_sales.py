"""Tests des rappels SMS/WhatsApp, de la demonstration, des tarifs et des temoignages."""

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
from .services.phone import normalize_phone
from .templatetags.core_extras import money

# Point de depart neutre : les tests ne dependent jamais des vraies cles du .env local.
NO_PROVIDERS = {
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
