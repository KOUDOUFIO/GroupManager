"""Service Layer pour l'integration de la passerelle de paiement CinetPay.

Ce service encapsule les appels HTTP vers l'API Checkout de CinetPay
(initiation de paiement et verification de transaction). Ne fait jamais
confiance au statut transmis par le webhook : seule la reponse de l'appel
de verification (check_transaction_status) fait foi, conformement a la
documentation CinetPay.
"""

from typing import Any, Dict, Optional

import requests
from django.conf import settings


class CinetPayService:
    """Service pour l'integration avec l'API Checkout de CinetPay."""

    TIMEOUT = 15

    @staticmethod
    def initiate_payment(
        transaction_id: str,
        amount: int,
        description: str,
        notify_url: str,
        return_url: str,
    ) -> Optional[Dict[str, Any]]:
        """Initie un paiement aupres de CinetPay.

        Args:
            transaction_id: Identifiant unique de transaction genere par l'application
            amount: Montant entier (pas de decimales, contrainte CinetPay)
            description: Description de la transaction
            notify_url: URL du webhook de notification
            return_url: URL de retour apres paiement

        Returns:
            Le contenu de `data` de la reponse CinetPay (payment_url, payment_token)
            ou None si la passerelle est desactivee ou l'appel a echoue
        """
        if not settings.CINETPAY_ENABLED:
            return None

        payload = {
            "apikey": settings.CINETPAY_API_KEY,
            "site_id": settings.CINETPAY_SITE_ID,
            "transaction_id": transaction_id,
            "amount": amount,
            "currency": settings.CINETPAY_CURRENCY,
            "description": description,
            "notify_url": notify_url,
            "return_url": return_url,
            "channels": "ALL",
        }
        try:
            response = requests.post(
                f"{settings.CINETPAY_BASE_URL}/payment",
                json=payload,
                timeout=CinetPayService.TIMEOUT,
            )
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError):
            return None

        if body.get("code") != "201":
            return None
        return body.get("data")

    @staticmethod
    def check_transaction_status(transaction_id: str) -> Optional[Dict[str, Any]]:
        """Verifie le statut reel d'une transaction aupres de CinetPay.

        C'est la seule source de verite pour confirmer un paiement : le
        corps du webhook ne doit jamais etre utilise directement.

        Args:
            transaction_id: Identifiant de transaction a verifier

        Returns:
            Le contenu de `data` de la reponse CinetPay (status, payment_method)
            ou None si la passerelle est desactivee ou l'appel a echoue
        """
        if not settings.CINETPAY_ENABLED:
            return None

        payload = {
            "apikey": settings.CINETPAY_API_KEY,
            "site_id": settings.CINETPAY_SITE_ID,
            "transaction_id": transaction_id,
        }
        try:
            response = requests.post(
                f"{settings.CINETPAY_BASE_URL}/payment/check",
                json=payload,
                timeout=CinetPayService.TIMEOUT,
            )
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError):
            return None

        if body.get("code") != "00":
            return None
        return body.get("data")
