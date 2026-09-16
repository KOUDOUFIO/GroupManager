"""Groupe d'organisation."""

from django.conf import settings
from django.db import models


class Group(models.Model):
    """Représente un groupe d'organisation.

    Un groupe peut contenir des membres, des organes, des postes,
    des rencontres, des cotisations, des documents et des événements.
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_groups",
    )

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return self.name
