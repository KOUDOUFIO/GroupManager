"""Service Layer pour la passerelle Mobile Money PayGate Global (T-Money, Flooz).

Flux : le membre choisit son reseau et son numero, PayGate envoie une demande
de confirmation sur son telephone, puis notifie notre webhook. Le corps du
webhook n'est jamais une source de verite : seul l'appel de verification
(`get_status`, avec notre propre cle) determine le statut reel.
"""

import logging
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ..models import Contribution

logger = logging.getLogger(__name__)

NETWORK_TMONEY = "TMONEY"
NETWORK_FLOOZ = "FLOOZ"

# Codes renvoyes par POST /v1/pay
INIT_OK = 0
# Codes renvoyes par POST /v2/status
STATUS_SUCCESS = 0
STATUS_PENDING = 2
STATUS_EXPIRED = 4
STATUS_CANCELLED = 6

TIMEOUT_SECONDS = 20


class PayGateError(Exception):
    """La passerelle n'a pas pu enregistrer la demande de paiement."""


class PayGateService:
    """Appels a l'API PayGate Global et mise a jour des cotisations."""

    @staticmethod
    def new_identifier() -> str:
        """Identifiant unique de transaction, cote Kotiza (stocke sur la cotisation)."""
        return f"KZ{uuid.uuid4().hex[:24].upper()}"

    @staticmethod
    def _post(path: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = {"auth_token": settings.PAYGATE_AUTH_TOKEN, **payload}
        try:
            response = requests.post(f"{settings.PAYGATE_API_URL}{path}", json=data, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError):
            logger.exception("Appel PayGate %s en echec", path)
            return None

    @classmethod
    def request_payment(cls, *, identifier: str, amount: Decimal, phone_number: str, network: str, description: str) -> str:
        """Envoie la demande de paiement sur le telephone du membre.

        Returns:
            str: la reference de transaction PayGate (tx_reference).

        Raises:
            PayGateError: si PayGate refuse ou ne repond pas.
        """
        result = cls._post(
            "/v1/pay",
            {
                "phone_number": phone_number,
                "amount": int(amount),
                "description": description[:100],
                "identifier": identifier,
                "network": network,
            },
        )
        if not result or result.get("status") != INIT_OK or not result.get("tx_reference"):
            logger.warning("PayGate a refuse la demande %s : %s", identifier, result)
            raise PayGateError(result.get("status") if result else None)
        return str(result["tx_reference"])

    @classmethod
    def get_status(cls, identifier: str) -> Optional[Dict[str, Any]]:
        """Statut reel d'une transaction, interroge par notre identifiant."""
        return cls._post("/v2/status", {"identifier": identifier})

    @classmethod
    @transaction.atomic
    def sync_contribution(cls, contribution: Contribution) -> str:
        """Met a jour une cotisation en attente d'apres le statut PayGate.

        Returns:
            str: le statut de la cotisation apres synchronisation.
        """
        contribution = Contribution.objects.select_for_update().get(pk=contribution.pk)
        if contribution.payment_status != Contribution.STATUS_PENDING or not contribution.gateway_transaction_id:
            return contribution.payment_status

        data = cls.get_status(contribution.gateway_transaction_id)
        if data is None:
            return contribution.payment_status

        status = data.get("status")
        if status == STATUS_SUCCESS:
            paid = Decimal(str(data.get("amount", contribution.amount)))
            if paid < contribution.amount:
                # Montant inferieur a celui demande : on ne confirme pas.
                logger.error(
                    "PayGate %s : montant paye %s < montant attendu %s",
                    contribution.gateway_transaction_id, paid, contribution.amount,
                )
                return contribution.payment_status
            contribution.payment_status = Contribution.STATUS_CONFIRMED
            contribution.paid_at = timezone.localdate()
            reference = data.get("payment_reference") or data.get("tx_reference")
            if reference:
                contribution.gateway_reference = str(reference)[:64]
        elif status in (STATUS_EXPIRED, STATUS_CANCELLED):
            contribution.payment_status = Contribution.STATUS_FAILED
        else:
            return contribution.payment_status

        # Le signal d'audit trace automatiquement ce changement de statut.
        contribution.save(update_fields=["payment_status", "paid_at", "gateway_reference"])
        return contribution.payment_status
