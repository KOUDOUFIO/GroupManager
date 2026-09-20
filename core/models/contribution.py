"""Cotisations et paiements des membres."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from .group import Group
from .member import Member


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
        (TYPE_MONTHLY, "Mensuelle"),
        (TYPE_ANNUAL, "Annuelle"),
        (TYPE_SPONTANEOUS, "Spontanee"),
        (TYPE_LATE_FINE, "Amende retard"),
        (TYPE_ABSENCE_FINE, "Amende absence"),
        (TYPE_OTHER, "Autre"),
    ]

    METHOD_CASH = "cash"
    METHOD_BANK_TRANSFER = "bank_transfer"
    METHOD_MOBILE_MONEY = "mobile_money"
    METHOD_CARD = "card"
    METHOD_OTHER = "other"
    METHOD_CHOICES = [
        (METHOD_CASH, "Especes"),
        (METHOD_BANK_TRANSFER, "Virement bancaire"),
        (METHOD_MOBILE_MONEY, "Mobile Money"),
        (METHOD_CARD, "Carte bancaire"),
        (METHOD_OTHER, "Autre"),
    ]

    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "En attente"),
        (STATUS_CONFIRMED, "Confirmee"),
        (STATUS_FAILED, "Echouee"),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="contributions")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="contributions")
    contribution_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES, default=METHOD_OTHER)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CONFIRMED)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    paid_at = models.DateField()
    notes = models.TextField(blank=True)
    gateway_transaction_id = models.CharField(max_length=64, null=True, blank=True, unique=True)

    class Meta:
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
            raise ValidationError({"member": "Le membre doit appartenir au groupe de la cotisation."})

    def __str__(self) -> str:
        return f"{self.member.full_name} - {self.amount}"
