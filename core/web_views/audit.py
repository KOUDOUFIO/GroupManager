"""Consultation web du journal d'audit (lecture seule)."""

from .. import models
from .mixins import SearchableListView


class AuditLogListView(SearchableListView):
    """ListView pour les logs d'audit (lecture seule)."""
    model = models.AuditLog
    template_name = "core/crud_list.html"
    title = "Historique d'audit"
    base_url_name = "audit_log"
    list_columns = [
        {"label": "Date", "accessor": "created_at"},
        {"label": "Utilisateur", "accessor": "actor.get_username"},
        {"label": "Action", "accessor": "get_action_display"},
        {"label": "Modele", "accessor": "model_name"},
        {"label": "Objet", "accessor": "object_repr"},
        {"label": "Route", "accessor": "path"},
    ]
    search_fields = ["model_name", "object_pk", "object_repr", "actor__username", "path"]
    select_related_fields = ("actor",)
    default_ordering = ("-created_at",)
    show_actions = False
