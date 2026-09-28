"""Commande de verification des paiements Mobile Money restes en attente."""

from datetime import timedelta

from django.conf import settings
from django.core.management import BaseCommand
from django.utils import timezone

from core.models import Contribution
from core.services.paygate_service import PayGateService


class Command(BaseCommand):
    """Relit aupres de PayGate le statut des paiements en attente (filet de securite du webhook)."""

    help = "Verifie aupres de PayGate Global les paiements Mobile Money encore en attente."

    def add_arguments(self, parser):
        """Definit les arguments de la commande."""
        parser.add_argument("--days", type=int, default=7, help="Anciennete maximale des paiements a verifier (jours).")

    def handle(self, *args, **options):
        """Synchronise chaque cotisation en attente payee en ligne."""
        if not settings.PAYGATE_ENABLED:
            self.stdout.write(self.style.WARNING("PayGate n'est pas configure (PAYGATE_AUTH_TOKEN vide)."))
            return

        since = timezone.localdate() - timedelta(days=options["days"])
        pending = Contribution.objects.filter(
            payment_status=Contribution.STATUS_PENDING,
            payment_method=Contribution.METHOD_MOBILE_MONEY,
            paid_at__gte=since,
        ).exclude(gateway_transaction_id=None)

        counts = {Contribution.STATUS_CONFIRMED: 0, Contribution.STATUS_FAILED: 0, Contribution.STATUS_PENDING: 0}
        for contribution in pending:
            counts[PayGateService.sync_contribution(contribution)] += 1

        self.stdout.write(self.style.SUCCESS(
            f"{counts['confirmed']} confirme(s), {counts['failed']} echoue(s), {counts['pending']} toujours en attente."
        ))
