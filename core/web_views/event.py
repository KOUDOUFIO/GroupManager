"""CRUD web pour les événements."""

from django.urls import reverse_lazy

from .. import models
from .mixins import BaseCreateView, BaseDeleteView, BaseUpdateView, SearchableListView
from django.utils.translation import gettext_lazy as _


class EventListView(SearchableListView):
    """ListView pour les événements."""
    model = models.Event
    template_name = "core/crud_list.html"
    title = _("Événements")
    create_url_name = "event_create"
    base_url_name = "event"
    hero_image = "core/img/modules/evenements.jpg"
    list_columns = [
        {"label": _("Titre"), "accessor": "title"},
        {"label": _("Type"), "accessor": "event_type"},
        {"label": _("Date"), "accessor": "starts_at"},
        {"label": _("Lieu"), "accessor": "location"},
    ]
    search_fields = ["title", "event_type", "group__name", "location"]
    select_related_fields = ("group",)


class EventCreateView(BaseCreateView):
    """Vue de création pour les événements."""
    model = models.Event
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = _("Ajouter un événement")
    success_url = reverse_lazy("event_list")
    list_url_name = "event_list"
    base_url_name = "event"


class EventUpdateView(BaseUpdateView):
    """Vue de modification pour les événements."""
    model = models.Event
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = _("Modifier un événement")
    success_url = reverse_lazy("event_list")
    list_url_name = "event_list"
    base_url_name = "event"


class EventDeleteView(BaseDeleteView):
    """Vue de suppression pour les événements."""
    model = models.Event
    template_name = "core/crud_confirm_delete.html"
    title = _("Supprimer un événement")
    success_url = reverse_lazy("event_list")
    list_url_name = "event_list"
    base_url_name = "event"
