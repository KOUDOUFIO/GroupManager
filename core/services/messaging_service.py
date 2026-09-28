"""Envoi de SMS et de messages WhatsApp (Twilio).

Un canal est actif des que son numero d'expedition est configure
(TWILIO_SMS_FROM, TWILIO_WHATSAPP_FROM). Sinon le message est seulement
journalise : aucun envoi, aucun cout.
"""

import json
import logging

import requests
from django.conf import settings

from .phone import normalize_phone

logger = logging.getLogger(__name__)

CHANNEL_SMS = "sms"
CHANNEL_WHATSAPP = "whatsapp"

TWILIO_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
TIMEOUT_SECONDS = 15


class MessagingService:
    """Envoi de messages courts vers le telephone des membres."""

    @staticmethod
    def sender(channel: str) -> str:
        """Numero d'expedition configure pour le canal ("" si inactif)."""
        if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN):
            return ""
        if channel == CHANNEL_WHATSAPP:
            return settings.TWILIO_WHATSAPP_FROM
        return settings.TWILIO_SMS_FROM

    @classmethod
    def enabled_channels(cls) -> list:
        """Canaux reellement configures, dans l'ordre d'envoi."""
        return [channel for channel in (CHANNEL_WHATSAPP, CHANNEL_SMS) if cls.sender(channel)]

    @classmethod
    def send(cls, channel: str, phone: str, body: str, template_vars: dict = None) -> bool:
        """Envoie un message ; renvoie True si le fournisseur l'a accepte.

        Sur WhatsApp, un message a l'initiative de l'organisation doit utiliser
        un modele valide par Meta : si TWILIO_WHATSAPP_TEMPLATE_SID est defini,
        il est envoye avec `template_vars` ({"1": ..., "2": ...}) a la place de `body`.
        """
        to = normalize_phone(phone)
        if not to:
            return False
        sender = cls.sender(channel)
        if not sender:
            logger.info("[%s non configure] message pour %s : %s", channel, to, body)
            return False
        if channel == CHANNEL_WHATSAPP:
            to = f"whatsapp:{to}"
            if not sender.startswith("whatsapp:"):
                sender = f"whatsapp:{sender}"
        data = {"From": sender, "To": to, "Body": body}
        if channel == CHANNEL_WHATSAPP and settings.TWILIO_WHATSAPP_TEMPLATE_SID and template_vars:
            data = {
                "From": sender,
                "To": to,
                "ContentSid": settings.TWILIO_WHATSAPP_TEMPLATE_SID,
                "ContentVariables": json.dumps(template_vars),
            }
        try:
            response = requests.post(
                TWILIO_URL.format(sid=settings.TWILIO_ACCOUNT_SID),
                data=data,
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException:
            logger.exception("Envoi %s vers %s en echec", channel, to)
            return False
        return True
