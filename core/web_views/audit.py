"""Consultation web du journal d'audit (lecture seule)."""

from .. import models
from .mixins import SearchableListView
from django.utils.translation import gettext_lazy as _


class AuditLogListView(SearchableListView):
    """ListView pour les logs d'audit (lecture seule)."""
    model = models.AuditLog
    template_name = "core/crud_list.html"
    title = _("Historique d'audit")
    base_url_name = "audit_log"
    hero_image = "core/img/modules/audit.jpg"
    list_columns = [
        {"label": _("Date"), "accessor": "created_at"},
        {"label": _("Utilisateur"), "accessor": "actor.get_username"},
        {"label": _("Action"), "accessor": "get_action_display"},
        {"label": _("Élément"), "accessor": "model_name", "format": "model"},
        {"label": _("Objet"), "accessor": "object_repr"},
    ]
    search_fields = ["model_name", "object_pk", "object_repr", "actor__username", "path"]
    select_related_fields = ("actor",)
    default_ordering = ("-created_at",)
    show_actions = False
