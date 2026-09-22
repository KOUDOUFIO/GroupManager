"""Demandes de devis soumises depuis la page vitrine."""

from django.db import models


class ProposalRequest(models.Model):
    """Demande de devis envoyée via le formulaire de contact commercial."""

    ORG_TYPE_COMPANY = "company"
    ORG_TYPE_ASSOCIATION = "association"
    ORG_TYPE_LOCAL_AUTHORITY = "local_authority"
    ORG_TYPE_CLUB = "club"
    ORG_TYPE_CHOICES = [
        (ORG_TYPE_COMPANY, "Société"),
        (ORG_TYPE_ASSOCIATION, "Association"),
        (ORG_TYPE_LOCAL_AUTHORITY, "Collectivité"),
        (ORG_TYPE_CLUB, "Club / groupe"),
    ]

    name = models.CharField(max_length=150, verbose_name="Nom")
    email = models.EmailField(verbose_name="Email")
    company = models.CharField(max_length=150, blank=True, verbose_name="Entreprise")
    organization_type = models.CharField(
        max_length=20, choices=ORG_TYPE_CHOICES, verbose_name="Type d'organisation"
    )
    message = models.TextField(verbose_name="Besoin principal")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Reçu le")

    class Meta:
        verbose_name = "Demande de devis"
        verbose_name_plural = "Demandes de devis"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.email})"
