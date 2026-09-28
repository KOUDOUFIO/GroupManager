"""Poste occupé par un membre dans un groupe."""

from django.core.exceptions import ValidationError
from django.db import models

from .group import Group
from .member import Member
from .organ import Organ
from django.utils.translation import gettext


class Position(models.Model):
    """Représente un poste occupé par un membre dans un groupe.

    Un poste peut être rattaché à un organe spécifique ou directement au groupe.
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    organ = models.ForeignKey(Organ, on_delete=models.SET_NULL, null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="positions")
    member = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True, related_name="positions")

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
        ]

    def clean(self):
        """Valide que l'organe appartient au même groupe."""
        if self.organ_id and self.group_id and self.organ.group_id != self.group_id:
            raise ValidationError({"organ": gettext("L'organe sélectionné doit appartenir au même groupe.")})

    def __str__(self) -> str:
        return f"{self.name} ({self.group.name})"
