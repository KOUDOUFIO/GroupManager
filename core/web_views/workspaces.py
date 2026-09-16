"""Workspaces (admin/gestionnaire), recherche globale et dashboard groupe."""

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView

from .. import models
from .mixins import StaffRequiredMixin


class AdminWorkspaceView(LoginRequiredMixin, StaffRequiredMixin, TemplateView):
    """Vue du workspace administrateur avec statistiques globales."""
    template_name = "core/admin_workspace.html"

    def get_context_data(self, **kwargs):
        """Fournit le contexte avec les statistiques pour l'admin."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "group_count": models.Group.objects.count(),
                "member_count": models.Member.objects.count(),
                "meeting_count": models.Meeting.objects.count(),
                "contribution_count": models.Contribution.objects.count(),
                "audit_count": models.AuditLog.objects.count(),
                "recent_audits": models.AuditLog.objects.select_related("actor").order_by("-created_at")[:10],
            }
        )
        return context


class ManagerWorkspaceView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Vue du workspace gestionnaire avec statistiques opérationnelles."""
    template_name = "core/manager_workspace.html"
    raise_exception = True

    def test_func(self):
        """Vérifie que l'utilisateur est staff ou gestionnaire."""
        user = self.request.user
        return user.is_staff or user.groups.filter(name="Gestionnaire").exists()

    def get_context_data(self, **kwargs):
        """Fournit le contexte avec les données opérationnelles."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "group_count": models.Group.objects.count(),
                "member_count": models.Member.objects.count(),
                "meeting_count": models.Meeting.objects.count(),
                "event_count": models.Event.objects.count(),
                "latest_meetings": models.Meeting.objects.select_related("group").order_by("-scheduled_at")[:8],
                "latest_contributions": models.Contribution.objects.select_related("member", "group").order_by("-paid_at")[:8],
            }
        )
        return context


class GlobalSearchView(LoginRequiredMixin, TemplateView):
    """Vue de recherche globale sur toutes les entités."""
    template_name = "core/global_search.html"

    def get_context_data(self, **kwargs):
        """Fournit le contexte avec les résultats de recherche."""
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()
        context["query"] = query
        if not query:
            context["has_query"] = False
            return context

        context["has_query"] = True
        context["groups"] = models.Group.objects.filter(Q(name__icontains=query) | Q(description__icontains=query))[:6]
        context["members"] = models.Member.objects.filter(
            Q(full_name__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query)
        )[:6]
        context["meetings"] = models.Meeting.objects.select_related("group").filter(
            Q(title__icontains=query) | Q(group__name__icontains=query)
        )[:6]
        context["contributions"] = models.Contribution.objects.select_related("member", "group").filter(
            Q(member__full_name__icontains=query) | Q(group__name__icontains=query) | Q(contribution_type__icontains=query)
        )[:6]
        context["events"] = models.Event.objects.select_related("group").filter(
            Q(title__icontains=query) | Q(location__icontains=query) | Q(group__name__icontains=query)
        )[:6]
        return context


class GroupDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Vue du tableau de bord détaillé pour un groupe (Groupe 360)."""
    template_name = "core/group_dashboard.html"
    raise_exception = True

    def get_permission_required(self):
        """Retourne la permission requise pour voir un groupe."""
        return ("core.view_group",)

    def get_context_data(self, **kwargs):
        """Fournit le contexte avec les statistiques détaillées du groupe."""
        context = super().get_context_data(**kwargs)
        group = get_object_or_404(models.Group.objects.select_related("responsible"), pk=self.kwargs["pk"])

        total_contributions = group.contributions.aggregate(total=Sum("amount"))["total"] or 0
        meeting_entries = models.MeetingEntry.objects.filter(meeting__group=group)
        total_entries = meeting_entries.count()
        attended_entries = meeting_entries.filter(
            status__in=[
                models.MeetingEntry.STATUS_PRESENT,
                models.MeetingEntry.STATUS_LATE,
                models.MeetingEntry.STATUS_PERMISSION,
            ]
        ).count()
        attendance_rate = round((attended_entries / total_entries) * 100, 1) if total_entries else 0

        context.update(
            {
                "group": group,
                "member_count": group.members.count(),
                "meeting_count": group.meetings.count(),
                "event_count": group.events.count(),
                "position_count": group.positions.count(),
                "total_contributions": total_contributions,
                "attendance_rate": attendance_rate,
                "recent_contributions": group.contributions.select_related("member").order_by("-paid_at")[:8],
                "upcoming_events": group.events.filter(starts_at__gte=timezone.now()).order_by("starts_at")[:8],
                "recent_meetings": group.meetings.order_by("-scheduled_at")[:8],
            }
        )
        return context
