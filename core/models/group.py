"""Groupe d'organisation."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Group(models.Model):
    """Représente un groupe d'organisation.

    Un groupe peut contenir des membres, des organes, des postes,
    des rencontres, des cotisations, des documents et des événements.
    """
    name = models.CharField(max_length=200, verbose_name=_("Nom"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Créé le"))
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_groups", verbose_name=_("Responsable"))
    # Suivi des retards : montant attendu chaque mois par membre, a partir d'une date.
    monthly_due = models.DecimalField(
        _("Cotisation mensuelle attendue"), max_digits=10, decimal_places=2, null=True, blank=True,
        help_text=_("Montant que chaque membre doit verser par mois. Vide = pas de suivi des retards."),
    )
    dues_start = models.DateField(
        _("Début des cotisations"), null=True, blank=True,
        help_text=_("Premier mois dû. Vide = date de création du groupe."),
    )

    class Meta:
        verbose_name = _("Groupe")
        verbose_name_plural = _("Groupes")
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return self.name
