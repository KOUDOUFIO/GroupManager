"""CRUD web pour les organes."""

from django.urls import reverse_lazy

from .. import models
from .mixins import BaseCreateView, BaseDeleteView, BaseUpdateView, SearchableListView
from django.utils.translation import gettext_lazy as _


class OrganListView(SearchableListView):
    """ListView pour les organes."""
    model = models.Organ
    template_name = "core/crud_list.html"
    title = _("Organes")
    create_url_name = "organ_create"
    base_url_name = "organ"
    hero_image = "core/img/modules/organes.jpg"
    list_columns = [
        {"label": _("Nom"), "accessor": "name"},
        {"label": _("Groupe"), "accessor": "group.name"},
        {"label": _("Description"), "accessor": "description"},
    ]
    search_fields = ["name", "description", "group__name"]
    select_related_fields = ("group",)


class OrganCreateView(BaseCreateView):
    """Vue de création pour les organes."""
    model = models.Organ
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = _("Ajouter un organe")
    success_url = reverse_lazy("organ_list")
    list_url_name = "organ_list"
    base_url_name = "organ"


class OrganUpdateView(BaseUpdateView):
    """Vue de modification pour les organes."""
    model = models.Organ
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = _("Modifier un organe")
    success_url = reverse_lazy("organ_list")
    list_url_name = "organ_list"
    base_url_name = "organ"


class OrganDeleteView(BaseDeleteView):
    """Vue de suppression pour les organes."""
    model = models.Organ
    template_name = "core/crud_confirm_delete.html"
    title = _("Supprimer un organe")
    success_url = reverse_lazy("organ_list")
    list_url_name = "organ_list"
    base_url_name = "organ"
