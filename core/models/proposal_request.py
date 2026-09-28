"""Demandes de devis soumises depuis la page vitrine."""

from django.db import models
from django.utils.translation import gettext_lazy as _


class ProposalRequest(models.Model):
    """Demande de devis envoyée via le formulaire de contact commercial."""

    ORG_TYPE_COMPANY = "company"
    ORG_TYPE_ASSOCIATION = "association"
    ORG_TYPE_LOCAL_AUTHORITY = "local_authority"
    ORG_TYPE_CLUB = "club"
    ORG_TYPE_CHOICES = [
        (ORG_TYPE_COMPANY, _("Société")),
        (ORG_TYPE_ASSOCIATION, _("Association")),
        (ORG_TYPE_LOCAL_AUTHORITY, _("Collectivité")),
        (ORG_TYPE_CLUB, _("Club / groupe")),
    ]

    PLAN_STARTER = "starter"
    PLAN_BUSINESS = "business"
    PLAN_ENTERPRISE = "enterprise"
    PLAN_CHOICES = [
        (PLAN_STARTER, _("Starter")),
        (PLAN_BUSINESS, _("Business")),
        (PLAN_ENTERPRISE, _("Enterprise")),
    ]

    name = models.CharField(max_length=150, verbose_name=_("Nom"))
    email = models.EmailField(verbose_name=_("Email"))
    phone = models.CharField(max_length=32, blank=True, verbose_name=_("Téléphone / WhatsApp"))
    company = models.CharField(max_length=150, blank=True, verbose_name=_("Entreprise"))
    organization_type = models.CharField(
        max_length=20, choices=ORG_TYPE_CHOICES, verbose_name=_("Type d'organisation")
    )
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, blank=True, verbose_name=_("Formule souhaitée"))
    message = models.TextField(verbose_name=_("Besoin principal"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Reçu le"))

    class Meta:
        verbose_name = _("Demande de devis")
        verbose_name_plural = _("Demandes de devis")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.email})"
