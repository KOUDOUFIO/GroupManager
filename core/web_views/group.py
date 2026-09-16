"""CRUD web pour les groupes."""

from django.urls import reverse_lazy

from .. import models
from .mixins import BaseCreateView, BaseDeleteView, BaseUpdateView, SearchableListView


class GroupListView(SearchableListView):
    """ListView pour les groupes."""
    model = models.Group
    template_name = "core/crud_list.html"
    title = "Groupes"
    create_url_name = "group_create"
    base_url_name = "group"
    hero_image = "core/img/modules/groupes.jpg"
    list_columns = [
        {"label": "Nom", "accessor": "name"},
        {"label": "Responsable", "accessor": "responsible.get_username"},
        {"label": "Creation", "accessor": "created_at"},
    ]
    search_fields = ["name", "description"]
    select_related_fields = ("responsible",)


class GroupCreateView(BaseCreateView):
    """Vue de création pour les groupes."""
    model = models.Group
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Ajouter un groupe"
    success_url = reverse_lazy("group_list")
    list_url_name = "group_list"
    base_url_name = "group"


class GroupUpdateView(BaseUpdateView):
    """Vue de modification pour les groupes."""
    model = models.Group
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Modifier un groupe"
    success_url = reverse_lazy("group_list")
    list_url_name = "group_list"
    base_url_name = "group"


class GroupDeleteView(BaseDeleteView):
    """Vue de suppression pour les groupes."""
    model = models.Group
    template_name = "core/crud_confirm_delete.html"
    title = "Supprimer un groupe"
    success_url = reverse_lazy("group_list")
    list_url_name = "group_list"
    base_url_name = "group"
