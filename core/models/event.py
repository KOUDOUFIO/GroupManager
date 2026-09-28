"""Événements spéciaux organisés par un groupe."""

from django.db import models
from django.utils.translation import gettext_lazy as _

from .group import Group


class Event(models.Model):
    """Représente un événement spécial organisé par un groupe.

    Les événements peuvent être des conférences, ateliers, célébrations, etc.
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="events", verbose_name=_("Groupe"))
    event_type = models.CharField(max_length=200, verbose_name=_("Type d'événement"))
    title = models.CharField(max_length=200, verbose_name=_("Titre"))
    starts_at = models.DateTimeField(verbose_name=_("Date et heure"))
    location = models.CharField(max_length=200, blank=True, verbose_name=_("Lieu"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    class Meta:
        verbose_name = _("Événement")
        verbose_name_plural = _("Événements")
        indexes = [
            models.Index(fields=["starts_at"]),
            models.Index(fields=["title"]),
            models.Index(fields=["location"]),
        ]

    def __str__(self) -> str:
        return self.title
