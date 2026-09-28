"""Témoignages de clients affichés sur les pages publiques."""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class Testimonial(models.Model):
    """Avis d'un vrai client, publié seulement avec son accord.

    Rien n'est affiché tant qu'aucun témoignage n'est publié.
    """
    author_name = models.CharField(_("Nom"), max_length=120)
    author_role = models.CharField(_("Fonction"), max_length=120, blank=True, help_text=_("Ex. Trésorière"))
    organization = models.CharField(_("Organisation"), max_length=160, blank=True)
    quote = models.TextField(_("Témoignage"), max_length=600)
    consent_given = models.BooleanField(
        _("Accord écrit du client"), default=False,
        help_text=_("Obligatoire pour publier : le client a accepté que son avis et son nom soient affichés."),
    )
    is_published = models.BooleanField(_("Publié"), default=False)
    sort_order = models.PositiveSmallIntegerField(_("Ordre"), default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        verbose_name = _("Témoignage")
        verbose_name_plural = _("Témoignages")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(is_published=False) | models.Q(consent_given=True),
                name="testimonial_published_requires_consent",
            ),
        ]

    def clean(self):
        """Refuse la publication sans l'accord du client."""
        if self.is_published and not self.consent_given:
            raise ValidationError({"is_published": _("Impossible de publier sans l'accord écrit du client.")})

    def __str__(self) -> str:
        return f"{self.author_name} - {self.organization}"
