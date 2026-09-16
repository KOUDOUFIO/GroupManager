"""CRUD web pour les postes."""

from django.urls import reverse_lazy

from .. import forms, models
from .mixins import BaseCreateView, BaseDeleteView, BaseUpdateView, SearchableListView


class PositionListView(SearchableListView):
    """ListView pour les postes."""
    model = models.Position
    template_name = "core/crud_list.html"
    title = "Postes"
    create_url_name = "position_create"
    base_url_name = "position"
    list_columns = [
        {"label": "Nom", "accessor": "name"},
        {"label": "Groupe", "accessor": "group.name"},
        {"label": "Organe", "accessor": "organ.name"},
        {"label": "Membre", "accessor": "member.full_name"},
    ]
    search_fields = ["name", "description", "group__name", "organ__name", "member__full_name"]
    select_related_fields = ("group", "organ", "member")


class PositionCreateView(BaseCreateView):
    """Vue de création pour les postes."""
    model = models.Position
    form_class = forms.PositionForm
    template_name = "core/crud_form.html"
    title = "Ajouter un poste"
    success_url = reverse_lazy("position_list")
    list_url_name = "position_list"
    base_url_name = "position"


class PositionUpdateView(BaseUpdateView):
    """Vue de modification pour les postes."""
    model = models.Position
    form_class = forms.PositionForm
    template_name = "core/crud_form.html"
    title = "Modifier un poste"
    success_url = reverse_lazy("position_list")
    list_url_name = "position_list"
    base_url_name = "position"


class PositionDeleteView(BaseDeleteView):
    """Vue de suppression pour les postes."""
    model = models.Position
    template_name = "core/crud_confirm_delete.html"
    title = "Supprimer un poste"
    success_url = reverse_lazy("position_list")
    list_url_name = "position_list"
    base_url_name = "position"
