"""CRUD web pour les organes."""

from django.urls import reverse_lazy

from .. import models
from .mixins import BaseCreateView, BaseDeleteView, BaseUpdateView, SearchableListView


class OrganListView(SearchableListView):
    """ListView pour les organes."""
    model = models.Organ
    template_name = "core/crud_list.html"
    title = "Organes"
    create_url_name = "organ_create"
    base_url_name = "organ"
    hero_image = "core/img/modules/organes.jpg"
    list_columns = [
        {"label": "Nom", "accessor": "name"},
        {"label": "Groupe", "accessor": "group.name"},
        {"label": "Description", "accessor": "description"},
    ]
    search_fields = ["name", "description", "group__name"]
    select_related_fields = ("group",)


class OrganCreateView(BaseCreateView):
    """Vue de création pour les organes."""
    model = models.Organ
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Ajouter un organe"
    success_url = reverse_lazy("organ_list")
    list_url_name = "organ_list"
    base_url_name = "organ"


class OrganUpdateView(BaseUpdateView):
    """Vue de modification pour les organes."""
    model = models.Organ
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Modifier un organe"
    success_url = reverse_lazy("organ_list")
    list_url_name = "organ_list"
    base_url_name = "organ"


class OrganDeleteView(BaseDeleteView):
    """Vue de suppression pour les organes."""
    model = models.Organ
    template_name = "core/crud_confirm_delete.html"
    title = "Supprimer un organe"
    success_url = reverse_lazy("organ_list")
    list_url_name = "organ_list"
    base_url_name = "organ"
