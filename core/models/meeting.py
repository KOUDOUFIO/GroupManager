"""Rencontres planifiées et présences des membres."""

from django.core.exceptions import ValidationError
from django.db import models

from .group import Group
from .member import Member
from django.utils.translation import gettext, gettext_lazy as _


class Meeting(models.Model):
    """Représente une rencontre planifiée pour un groupe."""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="meetings", verbose_name=_("Groupe"))
    scheduled_at = models.DateTimeField(verbose_name=_("Date et heure"))
    title = models.CharField(max_length=200, blank=True, verbose_name=_("Titre"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    class Meta:
        verbose_name = _("Rencontre")
        verbose_name_plural = _("Rencontres")
        indexes = [
            models.Index(fields=["scheduled_at"]),
            models.Index(fields=["title"]),
        ]

    def __str__(self) -> str:
        label = self.title or gettext("Rencontre")
        return f"{label} - {self.group.name}"


class MeetingEntry(models.Model):
    """Représente la présence d'un membre à une rencontre.

    Enregistre le statut de présence (présent, absent, retard, permission)
    avec un motif optionnel.
    """
    STATUS_PRESENT = "present"
    STATUS_ABSENT = "absent"
    STATUS_LATE = "late"
    STATUS_PERMISSION = "permission"
    STATUS_CHOICES = [
        (STATUS_PRESENT, _("Présent")),
        (STATUS_ABSENT, _("Absent")),
        (STATUS_LATE, _("En retard")),
        (STATUS_PERMISSION, _("Permission")),
    ]

    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name="entries", verbose_name=_("Rencontre"))
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="meeting_entries", verbose_name=_("Membre"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name=_("Statut"))
    reason = models.TextField(blank=True, verbose_name=_("Motif"))
    recorded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Enregistré le"))

    class Meta:
        verbose_name = _("Présence")
        verbose_name_plural = _("Présences")
        unique_together = ("meeting", "member")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["recorded_at"]),
        ]

    def clean(self):
        """Valide que le membre appartient au groupe de la rencontre."""
        if self.meeting_id and self.member_id and not self.member.groups.filter(pk=self.meeting.group_id).exists():
            raise ValidationError({"member": gettext("Le membre doit appartenir au groupe de la rencontre.")})

    def __str__(self) -> str:
        return f"{self.member.full_name} - {self.meeting}"
