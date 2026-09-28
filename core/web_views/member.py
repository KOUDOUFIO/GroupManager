"""CRUD web pour les membres."""

from django.urls import reverse_lazy

from .. import models
from .mixins import BaseCreateView, BaseDeleteView, BaseUpdateView, SearchableListView
from django.utils.translation import gettext_lazy as _


class MemberListView(SearchableListView):
    """ListView pour les membres."""
    model = models.Member
    template_name = "core/crud_list.html"
    title = _("Membres")
    create_url_name = "member_create"
    base_url_name = "member"
    hero_image = "core/img/modules/membres.jpg"
    list_columns = [
        {"label": _("Nom complet"), "accessor": "full_name"},
        {"label": _("Email"), "accessor": "email"},
        {"label": _("Téléphone"), "accessor": "phone"},
    ]
    search_fields = ["full_name", "email", "phone", "groups__name"]
    prefetch_related_fields = ("groups",)


# Le compte de connexion se gere depuis la page "Acces" du membre, pas ici.
MEMBER_FORM_FIELDS = ["full_name", "email", "phone", "address", "groups"]


class MemberCreateView(BaseCreateView):
    """Vue de création pour les membres."""
    model = models.Member
    fields = MEMBER_FORM_FIELDS
    template_name = "core/crud_form.html"
    title = _("Ajouter un membre")
    success_url = reverse_lazy("member_list")
    list_url_name = "member_list"
    base_url_name = "member"


class MemberUpdateView(BaseUpdateView):
    """Vue de modification pour les membres."""
    model = models.Member
    fields = MEMBER_FORM_FIELDS
    template_name = "core/crud_form.html"
    title = _("Modifier un membre")
    success_url = reverse_lazy("member_list")
    list_url_name = "member_list"
    base_url_name = "member"


class MemberDeleteView(BaseDeleteView):
    """Vue de suppression pour les membres."""
    model = models.Member
    template_name = "core/crud_confirm_delete.html"
    title = _("Supprimer un membre")
    success_url = reverse_lazy("member_list")
    list_url_name = "member_list"
    base_url_name = "member"
