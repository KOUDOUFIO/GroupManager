"""Cotisations et paiements des membres."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from .group import Group
from .member import Member
from django.utils.translation import gettext, gettext_lazy as _


class Contribution(models.Model):
    """Représente une cotisation ou un paiement d'un membre à un groupe.

    Peut être de différents types : mensuelle, spontanée, amende pour retard,
    amende pour absence, ou autre.
    """
    TYPE_MONTHLY = "monthly"
    TYPE_ANNUAL = "annual"
    TYPE_SPONTANEOUS = "spontaneous"
    TYPE_LATE_FINE = "late_fine"
    TYPE_ABSENCE_FINE = "absence_fine"
    TYPE_OTHER = "other"
    TYPE_CHOICES = [
        (TYPE_MONTHLY, _("Mensuelle")),
        (TYPE_ANNUAL, _("Annuelle")),
        (TYPE_SPONTANEOUS, _("Spontanée")),
        (TYPE_LATE_FINE, _("Amende retard")),
        (TYPE_ABSENCE_FINE, _("Amende absence")),
        (TYPE_OTHER, _("Autre")),
    ]

    METHOD_CASH = "cash"
    METHOD_BANK_TRANSFER = "bank_transfer"
    METHOD_MOBILE_MONEY = "mobile_money"
    METHOD_CARD = "card"
    METHOD_OTHER = "other"
    METHOD_CHOICES = [
        (METHOD_CASH, _("Espèces")),
        (METHOD_BANK_TRANSFER, _("Virement bancaire")),
        (METHOD_MOBILE_MONEY, _("Mobile Money")),
        (METHOD_CARD, _("Carte bancaire")),
        (METHOD_OTHER, _("Autre")),
    ]

    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, _("En attente")),
        (STATUS_CONFIRMED, _("Confirmée")),
        (STATUS_FAILED, _("Échouée")),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="contributions", verbose_name=_("Membre"))
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="contributions", verbose_name=_("Groupe"))
    contribution_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name=_("Type"))
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES, default=METHOD_OTHER, verbose_name=_("Moyen de paiement"))
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CONFIRMED, verbose_name=_("Statut"))
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))], verbose_name=_("Montant"))
    paid_at = models.DateField(verbose_name=_("Date de paiement"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    gateway_transaction_id = models.CharField(max_length=64, null=True, blank=True, unique=True, verbose_name=_("Identifiant de transaction"))

    class Meta:
        verbose_name = _("Cotisation")
        verbose_name_plural = _("Cotisations")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="contribution_amount_gt_zero",
            ),
        ]
        indexes = [
            models.Index(fields=["contribution_type"]),
            models.Index(fields=["paid_at"]),
            models.Index(fields=["payment_status"]),
        ]

    def clean(self):
        """Valide que le membre appartient au groupe de la cotisation."""
        if self.group_id and self.member_id and not self.member.groups.filter(pk=self.group_id).exists():
            raise ValidationError({"member": gettext("Le membre doit appartenir au groupe de la cotisation.")})

    def __str__(self) -> str:
        return f"{self.member.full_name} - {self.amount}"
