"""Organe au sein d'un groupe."""

from django.db import models

from .group import Group


class Organ(models.Model):
    """Représente un organe au sein d'un groupe.

    Un organe est une sous-structure d'un groupe (ex: comité, département).
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="organs")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.group.name})"
