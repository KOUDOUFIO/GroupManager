from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (
    AuditLog,
    Contribution,
    Group,
    Meeting,
    MeetingEntry,
    Member,
    Notification,
    NotificationPreference,
    Organ,
    Position,
)
from .services.member_service import MemberService
from .web_views import _safe_spreadsheet_cell


class HomeViewTests(TestCase):
    def test_home_view_status_ok(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_home_hides_platform_stats_from_anonymous_visitors(self):
        response = self.client.get(reverse("home"))
        self.assertFalse(response.context["show_platform_stats"])
        self.assertNotIn("total_contributions", response.context)
        self.assertNotContains(response, 'class="stats"')

    def test_home_hides_platform_stats_from_non_staff_users(self):
        user = get_user_model().objects.create_user(username="simple_user", password="password123")
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertNotIn("total_contributions", response.context)

    def test_home_shows_platform_stats_to_staff(self):
        staff = get_user_model().objects.create_user(
            username="staff_user", password="password123", is_staff=True
        )
        self.client.force_login(staff)
        response = self.client.get(reverse("home"))
        self.assertIn("total_contributions", response.context)
        self.assertIn("current_month_contributions", response.context)
        self.assertIn("attendance_rate", response.context)

    def test_proposal_page_status_ok(self):
        response = self.client.get(reverse("proposal_page"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Demander un devis")
        self.assertContains(response, "Business")

    def test_proposal_page_submission_creates_request_and_sends_notification(self):
        from .models import ProposalRequest

        response = self.client.post(
            reverse("proposal_page"),
            {
                "name": "Amina K.",
                "email": "amina@example.com",
                "company": "Association Test",
                "organization_type": ProposalRequest.ORG_TYPE_ASSOCIATION,
                "message": "Nous avons besoin d'un devis pour 50 membres.",
            },
        )
        self.assertRedirects(response, reverse("proposal_page") + "?envoye=1")
        self.assertTrue(ProposalRequest.objects.filter(email="amina@example.com").exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Amina K.", mail.outbox[0].subject)

    def test_proposal_page_submission_invalid_shows_errors(self):
        response = self.client.post(reverse("proposal_page"), {"name": "", "email": "pas-un-email"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error-messages")

    def test_company_page_status_ok(self):
        response = self.client.get(reverse("company_page"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Clarté opérationnelle")
        self.assertContains(response, "Notre approche")

    def test_platform_page_status_ok(self):
        response = self.client.get(reverse("platform_page"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CRM")
        self.assertContains(response, "Phase 1")

    def test_healthcheck_status_ok(self):
        response = self.client.get(reverse("healthcheck"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database"], "ok")

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
    def test_custom_404_page(self):
        response = self.client.get("/route-inexistante/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Page introuvable", status_code=404)


class ModelTests(TestCase):
    def test_group_and_member_creation(self):
        group = Group.objects.create(name="Chorale A", description="Test")
        member = Member.objects.create(full_name="Jean Test", email="jean@example.com")
        member.groups.add(group)
        self.assertEqual(group.members.count(), 1)

    def test_member_group_assignment_creates_audit_log(self):
        group = Group.objects.create(name="G-M2M")
        member = Member.objects.create(full_name="M2M User")
        member.groups.add(group)
        log = AuditLog.objects.filter(model_name="member", action=AuditLog.ACTION_UPDATE).first()
        self.assertIsNotNone(log)
        self.assertIn("groups", log.changes)

    def test_contribution_defaults_payment_method_and_status(self):
        group = Group.objects.create(name="G-Defaults")
        member = Member.objects.create(full_name="Defaults User")
        member.groups.add(group)
        contribution = Contribution.objects.create(
            member=member,
            group=group,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount="10.00",
            paid_at="2025-01-01",
        )
        self.assertEqual(contribution.payment_method, Contribution.METHOD_OTHER)
        self.assertEqual(contribution.payment_status, Contribution.STATUS_CONFIRMED)


class WebPermissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser",
            password="password123",
        )
        Group.objects.create(name="Groupe Test")

    def test_group_list_requires_login(self):
        response = self.client.get(reverse("group_list"))
        self.assertEqual(response.status_code, 403)

    def test_group_list_requires_permission(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("group_list"))
        self.assertEqual(response.status_code, 403)

    def test_group_list_with_permission(self):
        perm = Permission.objects.get(codename="view_group", content_type__app_label="core")
        self.user.user_permissions.add(perm)
        self.client.force_login(self.user)
        response = self.client.get(reverse("group_list"))
        self.assertEqual(response.status_code, 200)

    def test_member_list_search_does_not_duplicate_results(self):
        member_view_perm = Permission.objects.get(codename="view_member", content_type__app_label="core")
        self.user.user_permissions.add(member_view_perm)
        self.client.force_login(self.user)

        alpha = Group.objects.create(name="Alpha")
        beta = Group.objects.create(name="Beta")
        member = Member.objects.create(full_name="Alice Dupont", email="alice@example.com")
        member.groups.add(alpha, beta)

        response = self.client.get(reverse("member_list"), {"q": "a"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["paginator"].count, 1)

    def test_admin_workspace_requires_staff(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("admin_workspace"))
        self.assertEqual(response.status_code, 403)

    def test_admin_workspace_staff_access(self):
        self.user.is_staff = True
        self.user.save()
        self.client.force_login(self.user)
        response = self.client.get(reverse("admin_workspace"))
        self.assertEqual(response.status_code, 200)

    def test_manager_workspace_requires_manager_or_staff(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("manager_workspace"))
        self.assertEqual(response.status_code, 403)

        manager_group, _ = AuthGroup.objects.get_or_create(name="Gestionnaire")
        self.user.groups.add(manager_group)
        response = self.client.get(reverse("manager_workspace"))
        self.assertEqual(response.status_code, 200)

    def test_group_dashboard_requires_group_permission(self):
        group = Group.objects.create(name="Dashboard Group")
        self.client.force_login(self.user)
        response = self.client.get(reverse("group_dashboard", args=[group.id]))
        self.assertEqual(response.status_code, 403)

        perm = Permission.objects.get(codename="view_group", content_type__app_label="core")
        self.user.user_permissions.add(perm)
        response = self.client.get(reverse("group_dashboard", args=[group.id]))
        self.assertEqual(response.status_code, 200)

    def test_global_search_page(self):
        response = self.client.get(reverse("global_search"))
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.user)
        Group.objects.create(name="Chorale Recherche")
        response = self.client.get(reverse("global_search"), {"q": "Recherche"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chorale Recherche")

    def test_base_nav_displays_role_label(self):
        manager_group, _ = AuthGroup.objects.get_or_create(name="Gestionnaire")
        self.user.groups.add(manager_group)
        self.client.force_login(self.user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gestionnaire")


class ContributionAggregationTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="Groupe Agregation")
        self.member = Member.objects.create(full_name="Membre Agregation")
        self.member.groups.add(self.group)
        Contribution.objects.create(
            member=self.member,
            group=self.group,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount="20.00",
            paid_at=timezone.now().date(),
            payment_status=Contribution.STATUS_CONFIRMED,
        )
        Contribution.objects.create(
            member=self.member,
            group=self.group,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount="500.00",
            paid_at=timezone.now().date(),
            payment_status=Contribution.STATUS_PENDING,
        )

    def test_home_total_excludes_unconfirmed_contributions(self):
        staff = get_user_model().objects.create_user(
            username="agg_staff", password="password123", is_staff=True
        )
        self.client.force_login(staff)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_contributions"], 20)

    def test_group_dashboard_total_excludes_unconfirmed_contributions(self):
        user = get_user_model().objects.create_user(username="dash_user", password="password123")
        perm = Permission.objects.get(codename="view_group", content_type__app_label="core")
        user.user_permissions.add(perm)
        self.client.force_login(user)

        response = self.client.get(reverse("group_dashboard", args=[self.group.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_contributions"], 20)

    def test_member_statistics_exclude_unconfirmed_contributions(self):
        stats = MemberService.get_member_statistics(self.member.id)
        self.assertEqual(stats["contribution_total"], 20)
        self.assertEqual(stats["contribution_count"], 1)


class MemberPortalTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="Groupe Portail")
        self.user_a = get_user_model().objects.create_user(username="membre_a", password="password123")
        self.member_a = Member.objects.create(full_name="Membre A", user=self.user_a)
        self.member_a.groups.add(self.group)
        self.contribution_a = Contribution.objects.create(
            member=self.member_a,
            group=self.group,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount="10.00",
            paid_at=timezone.now().date(),
        )
        self.meeting = Meeting.objects.create(group=self.group, title="Reunion A", scheduled_at=timezone.now())
        self.entry_a = MeetingEntry.objects.create(
            meeting=self.meeting, member=self.member_a, status=MeetingEntry.STATUS_PRESENT
        )

        self.user_b = get_user_model().objects.create_user(username="membre_b", password="password123")
        self.member_b = Member.objects.create(full_name="Membre B", user=self.user_b)
        self.member_b.groups.add(self.group)
        self.contribution_b = Contribution.objects.create(
            member=self.member_b,
            group=self.group,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount="99.00",
            paid_at=timezone.now().date(),
        )
        MeetingEntry.objects.create(meeting=self.meeting, member=self.member_b, status=MeetingEntry.STATUS_ABSENT)

        self.user_no_member = get_user_model().objects.create_user(username="sans_membre", password="password123")

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("member_portal"))
        self.assertEqual(response.status_code, 403)

    def test_dashboard_requires_linked_member(self):
        self.client.force_login(self.user_no_member)
        response = self.client.get(reverse("member_portal"))
        self.assertEqual(response.status_code, 403)

    def test_dashboard_shows_own_statistics(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("member_portal"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["member"], self.member_a)
        self.assertEqual(response.context["contribution_count"], 1)
        self.assertNotContains(response, "99.00")

    def test_contributions_list_scoped_to_self(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("member_portal_contributions"))
        self.assertEqual(response.status_code, 200)
        object_list = list(response.context["object_list"])
        self.assertEqual(object_list, [self.contribution_a])
        self.assertNotContains(response, "99.00")

    def test_attendance_list_scoped_to_self(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("member_portal_attendance"))
        self.assertEqual(response.status_code, 200)
        object_list = list(response.context["object_list"])
        self.assertEqual(object_list, [self.entry_a])


@override_settings(KOTIZA_API_ENABLED=True)
class ApiPermissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="apiuser",
            password="password123",
        )
        self.client_api = APIClient()
        Group.objects.create(name="Groupe API")

    def test_api_requires_authentication(self):
        response = self.client_api.get("/api/groups/")
        self.assertIn(response.status_code, (401, 403))

    def test_api_requires_permission(self):
        self.client_api.force_authenticate(user=self.user)
        response = self.client_api.get("/api/groups/")
        self.assertEqual(response.status_code, 403)

    def test_dashboard_summary_requires_authentication(self):
        response = self.client_api.get("/api/dashboard-summary/")
        self.assertIn(response.status_code, (401, 403))

    def test_dashboard_summary_authenticated(self):
        self.client_api.force_authenticate(user=self.user)
        response = self.client_api.get("/api/dashboard-summary/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("group_count", response.data)
        self.assertIn("total_contributions", response.data)
        self.assertIn("attendance_rate", response.data)

    def test_api_schema_requires_authentication(self):
        response = self.client_api.get("/api/schema/")
        self.assertIn(response.status_code, (401, 403))

    def test_api_schema_authenticated(self):
        self.client_api.force_authenticate(user=self.user)
        response = self.client_api.get("/api/schema/")
        self.assertEqual(response.status_code, 200)

    def test_api_with_permission(self):
        perm = Permission.objects.get(codename="view_group", content_type__app_label="core")
        self.user.user_permissions.add(perm)
        self.client_api.force_authenticate(user=self.user)
        response = self.client_api.get("/api/groups/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)

    def test_api_contribution_rejects_invalid_payload(self):
        add_perm = Permission.objects.get(codename="add_contribution", content_type__app_label="core")
        self.user.user_permissions.add(add_perm)
        self.client_api.force_authenticate(user=self.user)

        g1 = Group.objects.create(name="API-G1")
        g2 = Group.objects.create(name="API-G2")
        member = Member.objects.create(full_name="API User")
        member.groups.add(g1)

        response = self.client_api.post(
            "/api/contributions/",
            data={
                "member": member.id,
                "group": g2.id,
                "contribution_type": Contribution.TYPE_MONTHLY,
                "amount": "10.00",
                "paid_at": "2025-01-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("member", response.data)

    def test_api_contribution_rejects_non_positive_amount(self):
        add_perm = Permission.objects.get(codename="add_contribution", content_type__app_label="core")
        self.user.user_permissions.add(add_perm)
        self.client_api.force_authenticate(user=self.user)

        g1 = Group.objects.create(name="API-G1")
        member = Member.objects.create(full_name="API User")
        member.groups.add(g1)

        response = self.client_api.post(
            "/api/contributions/",
            data={
                "member": member.id,
                "group": g1.id,
                "contribution_type": Contribution.TYPE_MONTHLY,
                "amount": "0.00",
                "paid_at": "2025-01-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("amount", response.data)


class ExportSecurityTests(TestCase):
    def test_safe_spreadsheet_cell_prefixes_formula_like_content(self):
        self.assertEqual(_safe_spreadsheet_cell("=2+2"), "'=2+2")
        self.assertEqual(_safe_spreadsheet_cell("+cmd"), "'+cmd")
        self.assertEqual(_safe_spreadsheet_cell("-10"), "'-10")
        self.assertEqual(_safe_spreadsheet_cell("@SUM(A1:A2)"), "'@SUM(A1:A2)")
        self.assertEqual(_safe_spreadsheet_cell("normal"), "normal")

    def test_contribution_csv_export_escapes_formula_like_values(self):
        user = get_user_model().objects.create_user(username="exporter", password="password123")
        permission = Permission.objects.get(codename="view_contribution", content_type__app_label="core")
        user.user_permissions.add(permission)
        self.client.force_login(user)

        group = Group.objects.create(name="=Group Name")
        member = Member.objects.create(full_name="+Alice", email="alice@example.com")
        Contribution.objects.create(
            member=member,
            group=group,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount="100.00",
            paid_at="2025-01-01",
        )

        response = self.client.get(reverse("contribution_export_csv"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("'+Alice", content)
        self.assertIn("'=Group Name", content)

    def test_contribution_csv_export_includes_payment_columns(self):
        user = get_user_model().objects.create_user(username="exporter_payment", password="password123")
        permission = Permission.objects.get(codename="view_contribution", content_type__app_label="core")
        user.user_permissions.add(permission)
        self.client.force_login(user)

        response = self.client.get(reverse("contribution_export_csv"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("Methode", content)
        self.assertIn("Statut", content)

    def test_contribution_csv_export_filters_by_group(self):
        user = get_user_model().objects.create_user(username="exporter_filter", password="password123")
        permission = Permission.objects.get(codename="view_contribution", content_type__app_label="core")
        user.user_permissions.add(permission)
        self.client.force_login(user)

        group_a = Group.objects.create(name="Group A")
        group_b = Group.objects.create(name="Group B")
        member = Member.objects.create(full_name="Alice Export", email="alice.export@example.com")
        member.groups.add(group_a, group_b)
        Contribution.objects.create(
            member=member,
            group=group_a,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount="10.00",
            paid_at="2025-01-01",
        )
        Contribution.objects.create(
            member=member,
            group=group_b,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount="20.00",
            paid_at="2025-01-02",
        )

        response = self.client.get(reverse("contribution_export_csv"), {"group": group_a.id})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("Group A", content)
        self.assertNotIn("Group B", content)


class BusinessValidationTests(TestCase):
    def test_position_rejects_organ_from_another_group(self):
        g1 = Group.objects.create(name="G1")
        g2 = Group.objects.create(name="G2")
        organ = Organ.objects.create(name="Organe G1", group=g1)
        position = Position(name="Tresorier", group=g2, organ=organ)

        with self.assertRaises(ValidationError):
            position.full_clean()

    def test_contribution_rejects_member_outside_group(self):
        g1 = Group.objects.create(name="G1")
        g2 = Group.objects.create(name="G2")
        member = Member.objects.create(full_name="Membre X")
        member.groups.add(g1)
        contribution = Contribution(
            member=member,
            group=g2,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount="20.00",
            paid_at="2025-01-10",
        )

        with self.assertRaises(ValidationError):
            contribution.full_clean()

    def test_meeting_entry_rejects_member_outside_meeting_group(self):
        g1 = Group.objects.create(name="G1")
        g2 = Group.objects.create(name="G2")
        member = Member.objects.create(full_name="Membre Y")
        member.groups.add(g1)
        meeting = Meeting.objects.create(group=g2, scheduled_at=timezone.now(), title="Reunion")
        entry = MeetingEntry(meeting=meeting, member=member, status=MeetingEntry.STATUS_PRESENT)

        with self.assertRaises(ValidationError):
            entry.full_clean()


class WebFormValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="webformuser", password="password123")
        needed = [
            "add_position",
            "add_contribution",
            "add_meetingentry",
        ]
        permissions = Permission.objects.filter(codename__in=needed, content_type__app_label="core")
        self.user.user_permissions.set(permissions)
        self.client.force_login(self.user)

    def test_position_form_shows_error_for_organ_mismatch(self):
        g1 = Group.objects.create(name="G1")
        g2 = Group.objects.create(name="G2")
        organ = Organ.objects.create(name="Organe G1", group=g1)

        response = self.client.post(
            reverse("position_create"),
            data={"name": "Secretaire", "description": "", "organ": organ.id, "group": g2.id, "member": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "L&#x27;organe selectionne doit appartenir au meme groupe.")

    def test_contribution_form_shows_error_for_member_outside_group(self):
        g1 = Group.objects.create(name="G1")
        g2 = Group.objects.create(name="G2")
        member = Member.objects.create(full_name="Membre Form")
        member.groups.add(g1)

        response = self.client.post(
            reverse("contribution_create"),
            data={
                "member": member.id,
                "group": g2.id,
                "contribution_type": Contribution.TYPE_MONTHLY,
                "amount": "100.00",
                "paid_at": "2025-01-01",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Le membre doit appartenir au groupe de la cotisation.")


@override_settings(KOTIZA_API_ENABLED=True)
class AuditLogTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="audituser", password="password123")
        self.client_api = APIClient()

    def test_web_create_group_creates_audit_log(self):
        add_perm = Permission.objects.get(codename="add_group", content_type__app_label="core")
        view_perm = Permission.objects.get(codename="view_group", content_type__app_label="core")
        self.user.user_permissions.add(add_perm, view_perm)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("group_create"),
            data={"name": "Groupe Audit", "description": "Trace", "responsible": ""},
        )
        self.assertEqual(response.status_code, 302)
        log = AuditLog.objects.filter(model_name="group", action=AuditLog.ACTION_CREATE).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.user)

    def test_api_update_group_creates_update_audit_log(self):
        view_group = Permission.objects.get(codename="view_group", content_type__app_label="core")
        change_group = Permission.objects.get(codename="change_group", content_type__app_label="core")
        self.user.user_permissions.add(view_group, change_group)
        group = Group.objects.create(name="Avant Update")
        self.client_api.login(username="audituser", password="password123")

        response = self.client_api.patch(f"/api/groups/{group.id}/", data={"description": "Maj audit"}, format="json")
        self.assertEqual(response.status_code, 200)
        log = AuditLog.objects.filter(model_name="group", action=AuditLog.ACTION_UPDATE, object_pk=str(group.id)).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.user)
        self.assertIn("description", log.changes)

    def test_api_delete_group_creates_delete_audit_log(self):
        view_group = Permission.objects.get(codename="view_group", content_type__app_label="core")
        delete_group = Permission.objects.get(codename="delete_group", content_type__app_label="core")
        self.user.user_permissions.add(view_group, delete_group)
        group = Group.objects.create(name="ToDelete")
        self.client_api.login(username="audituser", password="password123")

        response = self.client_api.delete(f"/api/groups/{group.id}/")
        self.assertEqual(response.status_code, 204)
        log = AuditLog.objects.filter(model_name="group", action=AuditLog.ACTION_DELETE).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.user)

    def test_audit_web_list_requires_permission(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("audit_log_list"))
        self.assertEqual(response.status_code, 403)

        view_audit = Permission.objects.get(codename="view_auditlog", content_type__app_label="core")
        self.user.user_permissions.add(view_audit)
        response = self.client.get(reverse("audit_log_list"))
        self.assertEqual(response.status_code, 200)

    def test_audit_api_requires_permission(self):
        self.client_api.login(username="audituser", password="password123")
        response = self.client_api.get("/api/audit-logs/")
        self.assertEqual(response.status_code, 403)

        view_audit = Permission.objects.get(codename="view_auditlog", content_type__app_label="core")
        self.user.user_permissions.add(view_audit)
        response = self.client_api.get("/api/audit-logs/")
        self.assertEqual(response.status_code, 200)


class BootstrapCommandTests(TestCase):
    def test_bootstrap_project_creates_superuser(self):
        call_command(
            "bootstrap_project",
            with_superuser=True,
            username="opsadmin",
            email="opsadmin@example.com",
            password="OpsAdmin123!",
        )
        user = get_user_model().objects.get(username="opsadmin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


class ContributionReminderCommandTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.group = Group.objects.create(name="Groupe Rappels")
        # Historique: le groupe utilise bien des cotisations mensuelles.
        historical_member = Member.objects.create(full_name="Historique", email="historique@example.com")
        historical_member.groups.add(self.group)
        Contribution.objects.create(
            member=historical_member,
            group=self.group,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount="10.00",
            paid_at=self.today - timedelta(days=365),
            payment_status=Contribution.STATUS_CONFIRMED,
        )
        # Egalement a jour ce mois-ci, pour ne pas etre relance et fausser
        # les assertions ciblant member_late.
        Contribution.objects.create(
            member=historical_member,
            group=self.group,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount="10.00",
            paid_at=self.today,
            payment_status=Contribution.STATUS_CONFIRMED,
        )

        self.user = get_user_model().objects.create_user(username="retardataire", password="password123")
        self.member_late = Member.objects.create(
            full_name="Membre Retard", email="retard@example.com", user=self.user
        )
        self.member_late.groups.add(self.group)

        self.member_paid = Member.objects.create(full_name="Membre Paye", email="paye@example.com")
        self.member_paid.groups.add(self.group)
        Contribution.objects.create(
            member=self.member_paid,
            group=self.group,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount="10.00",
            paid_at=self.today,
            payment_status=Contribution.STATUS_CONFIRMED,
        )

        self.member_pending = Member.objects.create(full_name="Membre En Attente", email="attente@example.com")
        self.member_pending.groups.add(self.group)
        Contribution.objects.create(
            member=self.member_pending,
            group=self.group,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount="10.00",
            paid_at=self.today,
            payment_status=Contribution.STATUS_PENDING,
        )

        self.event_group = Group.objects.create(name="Groupe Evenementiel")
        self.event_member = Member.objects.create(full_name="Membre Evenement", email="evenement@example.com")
        self.event_member.groups.add(self.event_group)

    def test_sends_email_and_notification_to_late_member(self):
        call_command("send_contribution_reminders")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["retard@example.com"])

        notification = Notification.objects.filter(user=self.user).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.category, Notification.CATEGORY_CONTRIBUTION)

    def test_paid_member_is_not_reminded(self):
        call_command("send_contribution_reminders")
        self.assertNotIn("paye@example.com", [m.to[0] for m in mail.outbox])

    def test_pending_payment_is_not_reminded(self):
        call_command("send_contribution_reminders")
        self.assertNotIn("attente@example.com", [m.to[0] for m in mail.outbox])

    def test_group_without_monthly_history_is_skipped(self):
        call_command("send_contribution_reminders")
        self.assertNotIn("evenement@example.com", [m.to[0] for m in mail.outbox])

    def test_dry_run_sends_nothing(self):
        call_command("send_contribution_reminders", dry_run=True)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(Notification.objects.count(), 0)

    def test_email_disabled_preference_skips_email_but_keeps_notification(self):
        NotificationPreference.objects.create(user=self.user, email_enabled=False)
        call_command("send_contribution_reminders")
        self.assertNotIn("retard@example.com", [m.to[0] for m in mail.outbox])
        self.assertTrue(Notification.objects.filter(user=self.user).exists())


@override_settings(
    KOTIZA_ACCESS_UNTIL=date(2026, 1, 31),
    KOTIZA_BILLING_CONTACT="+228 90 00 00 00",
    KOTIZA_API_ENABLED=True,
)
class SubscriptionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="sub_user", password="password123")
        self.staff = get_user_model().objects.create_user(
            username="sub_staff", password="password123", is_staff=True
        )
        self.operator = get_user_model().objects.create_superuser(
            username="sub_operator", password="password123", email="op@example.com"
        )

    def _on(self, day):
        return patch("core.subscription.timezone.localdate", return_value=day)

    def test_site_open_until_last_day_included(self):
        self.client.force_login(self.user)
        with self._on(date(2026, 1, 31)):
            response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_expired_blocks_users_and_shows_billing_contact(self):
        self.client.force_login(self.user)
        with self._on(date(2026, 2, 1)):
            response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 402)
        self.assertContains(response, "+228 90 00 00 00", status_code=402)

    def test_expired_blocks_anonymous_visitors(self):
        with self._on(date(2026, 2, 1)):
            response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 402)

    def test_expired_blocks_api_with_json(self):
        self.client.force_login(self.user)
        with self._on(date(2026, 2, 1)):
            response = self.client.get("/api/")
        self.assertEqual(response.status_code, 402)
        self.assertEqual(response.json()["detail"], "Abonnement expiré.")

    def test_expired_keeps_login_and_health_reachable(self):
        with self._on(date(2026, 2, 1)):
            self.assertEqual(self.client.get(reverse("login")).status_code, 200)
            self.assertEqual(self.client.get("/health/").status_code, 200)

    def test_expired_blocks_client_admin(self):
        self.client.force_login(self.staff)
        with self._on(date(2026, 2, 1)):
            response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 402)

    def test_expired_blocks_client_admin_from_django_admin(self):
        self.client.force_login(self.staff)
        with self._on(date(2026, 2, 1)):
            response = self.client.get("/admin/core/contribution/")
        self.assertEqual(response.status_code, 402)

    def test_expired_lets_operator_into_django_admin(self):
        self.client.force_login(self.operator)
        with self._on(date(2026, 2, 1)):
            response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)

    def test_expired_lets_operator_in_with_banner(self):
        self.client.force_login(self.operator)
        with self._on(date(2026, 2, 1)):
            response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Abonnement expiré depuis le 31/01/2026")

    def test_staff_sees_reminder_banner_before_expiry(self):
        self.client.force_login(self.staff)
        with self._on(date(2026, 1, 25)):
            response = self.client.get(reverse("home"))
        self.assertContains(response, "6 jours restants")

    def test_no_banner_long_before_expiry(self):
        self.client.force_login(self.staff)
        with self._on(date(2025, 12, 1)):
            response = self.client.get(reverse("home"))
        self.assertNotContains(response, "subscription-banner")

    @override_settings(KOTIZA_ACCESS_UNTIL=None)
    def test_no_end_date_means_no_limit(self):
        with self._on(date(2099, 1, 1)):
            response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)


class CreateClientAdminCommandTests(TestCase):
    def test_creates_staff_admin_without_superuser_rights(self):
        call_command("create_client_admin", username="bureau", email="b@example.com", password="Pass1234!x")
        user = get_user_model().objects.get(username="bureau")
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.groups.filter(name="Administrateur").exists())
        self.assertTrue(user.has_perm("core.delete_contribution"))
        self.assertTrue(user.check_password("Pass1234!x"))


class ApiToggleTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_superuser(
            username="api_admin", password="password123", email="api@example.com"
        )
        self.client.force_login(self.staff)

    @override_settings(KOTIZA_API_ENABLED=False)
    def test_api_and_docs_return_404_when_disabled(self):
        for path in ["/api/", "/api/contributions/", "/api/docs/", "/api/schema/"]:
            self.assertEqual(self.client.get(path).status_code, 404, path)

    @override_settings(KOTIZA_API_ENABLED=False)
    def test_basic_auth_cannot_reach_api_when_disabled(self):
        self.client.logout()
        import base64
        creds = base64.b64encode(b"api_admin:password123").decode()
        response = self.client.get("/api/contributions/", HTTP_AUTHORIZATION=f"Basic {creds}")
        self.assertEqual(response.status_code, 404)

    @override_settings(KOTIZA_API_ENABLED=True)
    def test_api_reachable_when_enabled(self):
        self.assertEqual(self.client.get("/api/contributions/").status_code, 200)


class LanguageTests(TestCase):
    def test_french_is_the_default(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, "Mot de passe oublié ?")
        self.assertContains(response, '<html lang="fr">')

    def test_english_from_browser_language(self):
        response = self.client.get(reverse("login"), HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9")
        self.assertContains(response, "Forgot your password?")
        self.assertContains(response, '<html lang="en">')

    def test_switcher_sets_language_and_redirects_back(self):
        response = self.client.post("/i18n/setlang/", {"language": "en", "next": "/plateforme/"})
        self.assertRedirects(response, "/plateforme/", fetch_redirect_response=False)
        page = self.client.get("/plateforme/")
        self.assertContains(page, "Coming soon")
        self.assertContains(page, "Yes")

    def test_switcher_back_to_french(self):
        self.client.post("/i18n/setlang/", {"language": "en", "next": "/"})
        self.client.post("/i18n/setlang/", {"language": "fr", "next": "/"})
        self.assertContains(self.client.get("/plateforme/"), "Bientôt")

    @override_settings(KOTIZA_ACCESS_UNTIL=date(2026, 1, 31), KOTIZA_BILLING_CONTACT="Mobile Money : 91 19 80 74")
    def test_expired_page_in_english_and_switcher_still_works(self):
        with patch("core.subscription.timezone.localdate", return_value=date(2026, 2, 1)):
            response = self.client.post("/i18n/setlang/", {"language": "en", "next": "/"})
            self.assertEqual(response.status_code, 302)
            page = self.client.get("/")
        self.assertContains(page, "Subscription expired", status_code=402)
        self.assertContains(page, "Mobile Money : 91 19 80 74", status_code=402)
