"""Membre pouvant appartenir à plusieurs groupes."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .group import Group


class Member(models.Model):
    """Représente un membre pouvant appartenir à plusieurs groupes.

    Un membre peut être associé à plusieurs groupes via une relation many-to-many.
    """
    full_name = models.CharField(max_length=200, verbose_name=_("Nom complet"))
    email = models.EmailField(blank=True, verbose_name=_("Email"))
    phone = models.CharField(max_length=50, blank=True, verbose_name=_("Téléphone"))
    address = models.CharField(max_length=255, blank=True, verbose_name=_("Adresse"))
    groups = models.ManyToManyField(Group, related_name="members", blank=True, verbose_name=_("Groupes"))
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="member_profile", verbose_name=_("Compte utilisateur"))

    class Meta:
        verbose_name = _("Membre")
        verbose_name_plural = _("Membres")
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["email"]),
            models.Index(fields=["phone"]),
        ]

    def __str__(self) -> str:
        return self.full_name
