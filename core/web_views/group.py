"""CRUD web pour les groupes."""

from django.urls import reverse_lazy

from .. import models
from .mixins import BaseCreateView, BaseDeleteView, BaseUpdateView, SearchableListView
from django.utils.translation import gettext_lazy as _


class GroupListView(SearchableListView):
    """ListView pour les groupes."""
    model = models.Group
    template_name = "core/crud_list.html"
    title = _("Groupes")
    create_url_name = "group_create"
    base_url_name = "group"
    hero_image = "core/img/modules/groupes.jpg"
    list_columns = [
        {"label": _("Nom"), "accessor": "name"},
        {"label": _("Responsable"), "accessor": "responsible.get_username"},
        {"label": _("Création"), "accessor": "created_at"},
    ]
    search_fields = ["name", "description"]
    select_related_fields = ("responsible",)


class GroupCreateView(BaseCreateView):
    """Vue de création pour les groupes."""
    model = models.Group
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = _("Ajouter un groupe")
    success_url = reverse_lazy("group_list")
    list_url_name = "group_list"
    base_url_name = "group"


class GroupUpdateView(BaseUpdateView):
    """Vue de modification pour les groupes."""
    model = models.Group
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = _("Modifier un groupe")
    success_url = reverse_lazy("group_list")
    list_url_name = "group_list"
    base_url_name = "group"


class GroupDeleteView(BaseDeleteView):
    """Vue de suppression pour les groupes."""
    model = models.Group
    template_name = "core/crud_confirm_delete.html"
    title = _("Supprimer un groupe")
    success_url = reverse_lazy("group_list")
    list_url_name = "group_list"
    base_url_name = "group"
