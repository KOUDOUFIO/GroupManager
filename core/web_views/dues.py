"""Suivi des cotisations dues (retards par membre et par groupe)."""

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import TemplateView

from ..services.dues_service import DuesService


class DuesView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Qui doit combien : attendu, verse et reste a payer par membre."""
    template_name = "core/dues.html"
    permission_required = "core.view_contribution"
    raise_exception = True

    def get_context_data(self, **kwargs):
        """Situation des membres, filtrable par groupe et par statut."""
        context = super().get_context_data(**kwargs)
        groups = list(DuesService.tracked_groups())
        selected = self.request.GET.get("group", "")
        only_late = self.request.GET.get("statut") == "retard"

        rows = []
        for group in groups:
            if selected and str(group.pk) != selected:
                continue
            rows.extend(DuesService.for_group(group))
        summary = DuesService.summary(rows)
        if only_late:
            rows = [row for row in rows if row.is_late]
        rows.sort(key=lambda row: (-row.remaining, row.member.full_name))

        context.update({
            "groups": groups,
            "selected_group": selected,
            "only_late": only_late,
            "rows": rows,
            "summary": summary,
        })
        return context
