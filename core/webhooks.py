"""Webhooks recus depuis des services externes (passerelles de paiement)."""

import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Contribution
from .services.cinetpay_service import CinetPayService
from .services.contribution_service import ContributionService

logger = logging.getLogger(__name__)

CINETPAY_METHOD_MAP = {
    "MOBILE_MONEY": Contribution.METHOD_MOBILE_MONEY,
    "CREDIT_CARD": Contribution.METHOD_CARD,
    "WALLET": Contribution.METHOD_MOBILE_MONEY,
}


@csrf_exempt
@require_POST
def cinetpay_notify(request):
    """Recoit la notification CinetPay et confirme le paiement via l'API de verification.

    Le corps du webhook n'est jamais une source de verite : seul l'appel a
    `CinetPayService.check_transaction_status` (avec nos propres identifiants)
    determine le statut reel d'une transaction.
    """
    transaction_id = request.POST.get("cpm_trans_id")
    if not transaction_id:
        logger.warning("Webhook CinetPay recu sans cpm_trans_id")
        return HttpResponse(status=200)

    contribution = Contribution.objects.filter(gateway_transaction_id=transaction_id).first()
    if contribution is None:
        logger.warning("Webhook CinetPay pour une transaction inconnue: %s", transaction_id)
        return HttpResponse(status=200)

    status_data = CinetPayService.check_transaction_status(transaction_id)
    if status_data is None:
        logger.error("Echec de verification CinetPay pour la transaction %s", transaction_id)
        return HttpResponse(status=502)

    gateway_status = status_data.get("status")
    if gateway_status == "ACCEPTED":
        new_status = Contribution.STATUS_CONFIRMED
    elif gateway_status == "REFUSED":
        new_status = Contribution.STATUS_FAILED
    else:
        # Statut transitoire (ex: WAITING_FOR_CUSTOMER) : rien a faire, on
        # attend une prochaine notification.
        return HttpResponse(status=200)

    payment_method = CINETPAY_METHOD_MAP.get(
        status_data.get("payment_method", ""), contribution.payment_method
    )

    ContributionService.update_contribution(
        contribution_id=contribution.id,
        payment_status=new_status,
        payment_method=payment_method,
        actor=None,
    )
    return HttpResponse(status=200)
