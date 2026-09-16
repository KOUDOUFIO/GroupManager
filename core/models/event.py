"""Événements spéciaux organisés par un groupe."""

from django.db import models

from .group import Group


class Event(models.Model):
    """Représente un événement spécial organisé par un groupe.

    Les événements peuvent être des conférences, ateliers, célébrations, etc.
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    starts_at = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["starts_at"]),
            models.Index(fields=["title"]),
            models.Index(fields=["location"]),
        ]

    def __str__(self) -> str:
        return self.title
