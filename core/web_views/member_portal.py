"""Portail membre self-service : consultation en lecture seule de ses propres données."""

from django.views.generic import ListView, TemplateView

from ..services.member_service import MemberService
from .mixins import MemberSelfRequiredMixin


class MemberPortalDashboardView(MemberSelfRequiredMixin, TemplateView):
    """Tableau de bord personnel du membre connecté."""
    template_name = "core/member_portal_dashboard.html"

    def get_context_data(self, **kwargs):
        """Fournit les statistiques et l'activité récente du membre connecté."""
        context = super().get_context_data(**kwargs)
        context.update(MemberService.get_member_statistics(self.member.id))
        context.update(
            {
                "recent_contributions": self.member.contributions.select_related("group").order_by("-paid_at")[:8],
                "recent_attendance": self.member.meeting_entries.select_related(
                    "meeting", "meeting__group"
                ).order_by("-meeting__scheduled_at")[:8],
                "member_groups": self.member.groups.all(),
            }
        )
        return context


class MemberContributionsListView(MemberSelfRequiredMixin, ListView):
    """Liste paginée des cotisations du membre connecté."""
    template_name = "core/member_portal_contributions.html"
    paginate_by = 10

    def get_queryset(self):
        """Cotisations du membre connecté uniquement."""
        return self.member.contributions.select_related("group").order_by("-paid_at")


class MemberAttendanceListView(MemberSelfRequiredMixin, ListView):
    """Liste paginée des présences aux rencontres du membre connecté."""
    template_name = "core/member_portal_attendance.html"
    paginate_by = 10

    def get_queryset(self):
        """Présences du membre connecté uniquement."""
        return self.member.meeting_entries.select_related("meeting", "meeting__group").order_by(
            "-meeting__scheduled_at"
        )
