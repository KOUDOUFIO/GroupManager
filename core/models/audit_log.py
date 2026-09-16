"""Journal d'audit des modifications."""

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class AuditLog(models.Model):
    """Représente une entrée du journal d'audit.

    Enregistre automatiquement les créations, modifications et suppressions
    sur les modèles principaux avec l'acteur, les changements et le contexte.
    """
    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_DELETE = "delete"
    ACTION_CHOICES = [
        (ACTION_CREATE, "Creation"),
        (ACTION_UPDATE, "Modification"),
        (ACTION_DELETE, "Suppression"),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_pk = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=255)
    path = models.CharField(max_length=300, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    changes = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["model_name"]),
            models.Index(fields=["object_pk"]),
            models.Index(fields=["action"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_action_display()} {self.model_name}#{self.object_pk}"
