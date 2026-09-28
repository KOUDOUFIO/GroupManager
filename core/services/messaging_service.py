"""Envoi de SMS (eSMS Africa ou Twilio) et de messages WhatsApp (Twilio).

SMS : eSMS Africa si ESMS_API_KEY est defini, sinon Twilio (TWILIO_SMS_FROM).
WhatsApp : Twilio (TWILIO_WHATSAPP_FROM). Un canal non configure ne fait
que journaliser le message : aucun envoi, aucun cout.
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
        channels = []
        if cls.sender(CHANNEL_WHATSAPP):
            channels.append(CHANNEL_WHATSAPP)
        if settings.ESMS_API_KEY or cls.sender(CHANNEL_SMS):
            channels.append(CHANNEL_SMS)
        return channels

    @staticmethod
    def _send_esms(to: str, body: str) -> bool:
        """SMS via eSMS Africa (POST /messages/send, cle en Bearer)."""
        payload = {"to": to, "text": body}
        if settings.ESMS_SENDER_ID:
            payload["sender_id"] = settings.ESMS_SENDER_ID
        try:
            response = requests.post(
                f"{settings.ESMS_API_URL}/messages/send",
                json=payload,
                headers={"Authorization": f"Bearer {settings.ESMS_API_KEY}", "Accept": "application/json"},
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            detail = getattr(getattr(exc, "response", None), "text", "")[:300]
            logger.error("Envoi SMS eSMS vers %s en echec : %s %s", to, exc, detail)
            return False
        return True

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
        if channel == CHANNEL_SMS and settings.ESMS_API_KEY:
            return cls._send_esms(to, body)
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
