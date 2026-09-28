"""Tests : acces des membres, suivi des cotisations dues, recus PDF,
notifications et connexion a deux etapes."""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from .models import Contribution, Group, Member, Notification
from .services.dues_service import DuesService, months_between


def make_manager(username="gestion"):
    from django.core.management import call_command

    call_command("seed_roles", verbosity=0, stdout=open("/dev/null", "w"))
    user = get_user_model().objects.create_user(username=username, password="password123")
    user.groups.add(AuthGroup.objects.get(name="Gestionnaire"))
    return user


class RolePermissionTests(TestCase):
    def test_manager_role_can_use_modules_but_not_delete(self):
        manager = make_manager("role")
        self.client.force_login(manager)
        for name in ("member_list", "contribution_list", "meeting_list", "dues"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertTrue(manager.has_perm("core.add_contribution"))
        self.assertFalse(manager.has_perm("core.delete_contribution"))


class MemberAccessTests(TestCase):
    def setUp(self):
        self.manager = make_manager()
        self.client.force_login(self.manager)

    def test_grant_access_by_email_sends_set_password_link(self):
        member = Member.objects.create(full_name="Ama Mensah", email="ama@example.com")
        response = self.client.post(reverse("member_access", args=[member.pk]), {"username": "ama.mensah"})
        self.assertEqual(response.status_code, 200)
        member.refresh_from_db()
        self.assertEqual(member.user.username, "ama.mensah")
        self.assertFalse(member.user.has_usable_password())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/reset/", mail.outbox[0].body)

    def test_grant_access_without_email_shows_temporary_password(self):
        member = Member.objects.create(full_name="Kofi Agbo", phone="90000000")
        response = self.client.post(reverse("member_access", args=[member.pk]), {"username": "kofi"})
        password = response.context["temporary_password"]
        self.assertEqual(len(password), 10)
        member.refresh_from_db()
        self.assertTrue(member.user.check_password(password))
        # Le membre peut ensuite ouvrir son espace.
        self.client.logout()
        self.assertTrue(self.client.login(username="kofi", password=password))
        self.assertEqual(self.client.get(reverse("member_portal")).status_code, 200)

    def test_suggested_username_avoids_duplicates(self):
        get_user_model().objects.create_user(username="afi.dzifa")
        member = Member.objects.create(full_name="Afi Dzifa")
        response = self.client.get(reverse("member_access", args=[member.pk]))
        self.assertEqual(response.context["form"].initial["username"], "afi.dzifa2")

    def test_revoke_deactivates_member_account_but_never_a_team_account(self):
        member = Member.objects.create(full_name="Membre")
        member.user = get_user_model().objects.create_user(username="membre")
        member.save()
        self.client.post(reverse("member_access", args=[member.pk]), {"action": "revoke"})
        member.refresh_from_db()
        self.assertIsNone(member.user_id)
        self.assertFalse(get_user_model().objects.get(username="membre").is_active)

        chief = Member.objects.create(full_name="Chef", user=make_manager("chef"))
        self.client.post(reverse("member_access", args=[chief.pk]), {"action": "revoke"})
        self.assertTrue(get_user_model().objects.get(username="chef").is_active)

    def test_simple_member_cannot_manage_access(self):
        plain = get_user_model().objects.create_user(username="simple")
        self.client.force_login(plain)
        member = Member.objects.create(full_name="X")
        self.assertEqual(self.client.get(reverse("member_access", args=[member.pk])).status_code, 403)


class DuesTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="Tontine", monthly_due=Decimal("5000"), dues_start=date(2026, 7, 1))
        self.paid = Member.objects.create(full_name="A jour")
        self.late = Member.objects.create(full_name="En retard")
        for m in (self.paid, self.late):
            m.groups.add(self.group)
        for month in (7, 8, 9):
            Contribution.objects.create(member=self.paid, group=self.group, contribution_type=Contribution.TYPE_MONTHLY,
                                        amount=5000, paid_at=date(2026, month, 5))
        Contribution.objects.create(member=self.late, group=self.group, contribution_type=Contribution.TYPE_MONTHLY,
                                    amount=5000, paid_at=date(2026, 7, 5))
        # Une cotisation en attente ne compte pas comme versee.
        Contribution.objects.create(member=self.late, group=self.group, contribution_type=Contribution.TYPE_MONTHLY,
                                    amount=5000, paid_at=date(2026, 8, 5), payment_status=Contribution.STATUS_PENDING)

    def test_months_between_includes_start_and_current_month(self):
        self.assertEqual(months_between(date(2026, 7, 1), date(2026, 9, 28)), 3)
        self.assertEqual(months_between(date(2026, 10, 1), date(2026, 9, 28)), 0)

    def test_balances_per_member(self):
        rows = {row.member.full_name: row for row in DuesService.for_group(self.group, date(2026, 9, 28))}
        self.assertEqual(rows["A jour"].remaining, 0)
        self.assertFalse(rows["A jour"].is_late)
        self.assertEqual(rows["En retard"].expected, Decimal("15000"))
        self.assertEqual(rows["En retard"].remaining, Decimal("10000"))
        self.assertEqual(rows["En retard"].months_late, 2)

    def test_dues_page_and_member_portal(self):
        staff = get_user_model().objects.create_superuser("root", "r@example.com", "password123")
        self.client.force_login(staff)
        response = self.client.get(reverse("dues") + "?statut=retard")
        self.assertContains(response, "En retard")
        self.assertNotContains(response, ">A jour<")

        member_user = get_user_model().objects.create_user(username="late")
        self.late.user = member_user
        self.late.save()
        self.client.force_login(member_user)
        response = self.client.get(reverse("member_portal"))
        self.assertContains(response, "Reste à payer")


class ReceiptTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="Tontine")
        self.member = Member.objects.create(full_name="Ama", user=get_user_model().objects.create_user("ama"))
        self.other = Member.objects.create(full_name="Autre", user=get_user_model().objects.create_user("autre"))
        for m in (self.member, self.other):
            m.groups.add(self.group)
        self.confirmed = Contribution.objects.create(member=self.member, group=self.group, amount=5000,
                                                     contribution_type=Contribution.TYPE_MONTHLY, paid_at=date(2026, 9, 1))
        self.pending = Contribution.objects.create(member=self.member, group=self.group, amount=5000,
                                                   contribution_type=Contribution.TYPE_MONTHLY, paid_at=date(2026, 9, 2),
                                                   payment_status=Contribution.STATUS_PENDING)

    def test_member_downloads_own_receipt(self):
        self.client.force_login(self.member.user)
        response = self.client.get(reverse("contribution_receipt", args=[self.confirmed.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertIn(f"R-2026-{self.confirmed.pk:05d}", response["Content-Disposition"])

    def test_no_receipt_for_someone_else_or_unconfirmed(self):
        self.client.force_login(self.other.user)
        self.assertEqual(self.client.get(reverse("contribution_receipt", args=[self.confirmed.pk])).status_code, 403)
        self.client.force_login(self.member.user)
        self.assertEqual(self.client.get(reverse("contribution_receipt", args=[self.pending.pk])).status_code, 404)


class NotificationTests(TestCase):
    def test_bell_count_list_and_mark_all_read(self):
        user = get_user_model().objects.create_user("notif")
        Notification.objects.create(user=user, title="Rappel", message="Cotisation de septembre")
        self.client.force_login(user)
        response = self.client.get(reverse("notifications"))
        self.assertContains(response, "Cotisation de septembre")
        self.assertContains(response, 'class="bell-count"')
        self.client.post(reverse("notifications"))
        self.assertFalse(Notification.objects.filter(user=user, is_read=False).exists())


class TwoFactorTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("secure", password="password123")

    def _code(self, device, ahead=0):
        # ahead=1 : code de la periode suivante (un meme code ne sert qu'une fois).
        t0 = device.t0 - ahead * device.step
        return f"{totp(device.bin_key, device.step, t0, device.digits, device.drift):06d}"

    def test_enable_then_code_required_at_next_login(self):
        self.client.login(username="secure", password="password123")
        self.client.post(reverse("security"), {"action": "start"})
        device = TOTPDevice.objects.get(user=self.user, confirmed=False)
        self.client.post(reverse("security"), {"action": "confirm", "code": self._code(device)})
        device.refresh_from_db()
        self.assertTrue(device.confirmed)

        # Nouvelle session : le mot de passe ne suffit plus.
        self.client.logout()
        self.client.login(username="secure", password="password123")
        response = self.client.get(reverse("member_list"))
        self.assertRedirects(response, "/securite/verification/?next=/membres/", fetch_redirect_response=False)

        bad = self.client.post(reverse("two_factor_verify"), {"code": "000000", "next": "/"})
        self.assertContains(bad, "Code incorrect")
        device.refresh_from_db()
        device.throttle_reset()
        ok = self.client.post(reverse("two_factor_verify"), {"code": self._code(device, ahead=1), "next": "/"})
        self.assertRedirects(ok, "/", fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)

    def test_accounts_without_2fa_are_not_affected(self):
        self.client.login(username="secure", password="password123")
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)

    def test_verify_page_refuses_external_next(self):
        TOTPDevice.objects.create(user=self.user, name="Kotiza", confirmed=True)
        self.client.login(username="secure", password="password123")
        response = self.client.post(reverse("two_factor_verify"), {"code": "000000", "next": "https://evil.example/"})
        self.assertEqual(response.context["next"], "/")
