"""CRUD web pour les cotisations."""

from urllib.parse import urlencode

from django.urls import reverse_lazy
from django.utils.dateparse import parse_date

from .. import forms, models
from .mixins import BaseCreateView, BaseDeleteView, BaseUpdateView, SearchableListView
from django.utils.translation import gettext_lazy as _


class ContributionListView(SearchableListView):
    """ListView pour les cotisations avec filtres avancés."""
    model = models.Contribution
    template_name = "core/crud_list.html"
    title = _("Cotisations")
    create_url_name = "contribution_create"
    base_url_name = "contribution"
    hero_image = "core/img/modules/cotisations.jpg"
    list_columns = [
        {"label": _("Membre"), "accessor": "member.full_name"},
        {"label": _("Groupe"), "accessor": "group.name"},
        {"label": _("Type"), "accessor": "get_contribution_type_display"},
        {"label": _("Méthode"), "accessor": "get_payment_method_display"},
        {"label": _("Statut"), "accessor": "get_payment_status_display"},
        {"label": _("Montant"), "accessor": "amount"},
        {"label": _("Date"), "accessor": "paid_at"},
    ]
    search_fields = ["member__full_name", "group__name", "contribution_type", "payment_method", "payment_status"]
    select_related_fields = ("member", "group")

    def get_queryset(self):
        """Filtre le queryset selon groupe et dates."""
        queryset = super().get_queryset()
        group_id = self.request.GET.get("group")
        start_date = parse_date(self.request.GET.get("start_date", ""))
        end_date = parse_date(self.request.GET.get("end_date", ""))
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        if start_date:
            queryset = queryset.filter(paid_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(paid_at__lte=end_date)
        return queryset

    def get_context_data(self, **kwargs):
        """Fournit le contexte avec les filtres et paramètres d'export."""
        context = super().get_context_data(**kwargs)
        context["groups"] = models.Group.objects.order_by("name")
        context["selected_group"] = self.request.GET.get("group", "")
        context["start_date"] = self.request.GET.get("start_date", "")
        context["end_date"] = self.request.GET.get("end_date", "")
        context["export_query"] = urlencode(
            {
                "group": context["selected_group"],
                "start_date": context["start_date"],
                "end_date": context["end_date"],
            }
        )
        return context


class ContributionCreateView(BaseCreateView):
    """Vue de création pour les cotisations."""
    model = models.Contribution
    form_class = forms.ContributionForm
    template_name = "core/crud_form.html"
    title = _("Ajouter une cotisation")
    success_url = reverse_lazy("contribution_list")
    list_url_name = "contribution_list"
    base_url_name = "contribution"


class ContributionUpdateView(BaseUpdateView):
    """Vue de modification pour les cotisations."""
    model = models.Contribution
    form_class = forms.ContributionForm
    template_name = "core/crud_form.html"
    title = _("Modifier une cotisation")
    success_url = reverse_lazy("contribution_list")
    list_url_name = "contribution_list"
    base_url_name = "contribution"


class ContributionDeleteView(BaseDeleteView):
    """Vue de suppression pour les cotisations."""
    model = models.Contribution
    template_name = "core/crud_confirm_delete.html"
    title = _("Supprimer une cotisation")
    success_url = reverse_lazy("contribution_list")
    list_url_name = "contribution_list"
    base_url_name = "contribution"
