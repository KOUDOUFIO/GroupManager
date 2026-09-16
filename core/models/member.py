"""Membre pouvant appartenir à plusieurs groupes."""

from django.db import models

from .group import Group


class Member(models.Model):
    """Représente un membre pouvant appartenir à plusieurs groupes.

    Un membre peut être associé à plusieurs groupes via une relation many-to-many.
    """
    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    groups = models.ManyToManyField(Group, related_name="members", blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["email"]),
            models.Index(fields=["phone"]),
        ]

    def __str__(self) -> str:
        return self.full_name
