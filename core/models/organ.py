"""Organe au sein d'un groupe."""

from django.db import models
from django.utils.translation import gettext_lazy as _

from .group import Group


class Organ(models.Model):
    """Représente un organe au sein d'un groupe.

    Un organe est une sous-structure d'un groupe (ex: comité, département).
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="organs", verbose_name=_("Groupe"))
    name = models.CharField(max_length=200, verbose_name=_("Nom"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    class Meta:
        verbose_name = _("Organe")
        verbose_name_plural = _("Organes")
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.group.name})"
