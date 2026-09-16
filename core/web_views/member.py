"""CRUD web pour les membres."""

from django.urls import reverse_lazy

from .. import models
from .mixins import BaseCreateView, BaseDeleteView, BaseUpdateView, SearchableListView


class MemberListView(SearchableListView):
    """ListView pour les membres."""
    model = models.Member
    template_name = "core/crud_list.html"
    title = "Membres"
    create_url_name = "member_create"
    base_url_name = "member"
    list_columns = [
        {"label": "Nom complet", "accessor": "full_name"},
        {"label": "Email", "accessor": "email"},
        {"label": "Telephone", "accessor": "phone"},
    ]
    search_fields = ["full_name", "email", "phone", "groups__name"]
    prefetch_related_fields = ("groups",)


class MemberCreateView(BaseCreateView):
    """Vue de création pour les membres."""
    model = models.Member
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Ajouter un membre"
    success_url = reverse_lazy("member_list")
    list_url_name = "member_list"
    base_url_name = "member"


class MemberUpdateView(BaseUpdateView):
    """Vue de modification pour les membres."""
    model = models.Member
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Modifier un membre"
    success_url = reverse_lazy("member_list")
    list_url_name = "member_list"
    base_url_name = "member"


class MemberDeleteView(BaseDeleteView):
    """Vue de suppression pour les membres."""
    model = models.Member
    template_name = "core/crud_confirm_delete.html"
    title = "Supprimer un membre"
    success_url = reverse_lazy("member_list")
    list_url_name = "member_list"
    base_url_name = "member"
