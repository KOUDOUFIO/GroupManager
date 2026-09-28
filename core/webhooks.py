"""Webhooks recus depuis des services externes (passerelles de paiement)."""

import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Contribution
from .services.paygate_service import PayGateService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def paygate_notify(request):
    """Recoit la notification PayGate Global et verifie le paiement aupres de PayGate.

    Le corps de la notification sert seulement a retrouver la cotisation : le
    statut est toujours relu via l'API PayGate avec notre propre cle.
    """
    try:
        payload = json.loads(request.body or b"{}")
    except ValueError:
        payload = request.POST
    identifier = str(payload.get("identifier") or "")
    if not identifier:
        logger.warning("Webhook PayGate recu sans identifier")
        return HttpResponse(status=200)

    contribution = Contribution.objects.filter(gateway_transaction_id=identifier).first()
    if contribution is None:
        logger.warning("Webhook PayGate pour une transaction inconnue : %s", identifier)
        return HttpResponse(status=200)

    PayGateService.sync_contribution(contribution)
    return HttpResponse(status=200)
