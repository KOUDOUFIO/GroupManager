"""Commande d'envoi des rappels de cotisation mensuelle."""

from django.conf import settings
from django.core.mail import send_mail
from django.core.management import BaseCommand
from django.utils import dateformat, timezone

from core.models import Notification, NotificationPreference
from core.services.contribution_service import ContributionService
from core.services.notification_service import NotificationService


class Command(BaseCommand):
    """Relance par email (et notification in-app) les membres sans cotisation mensuelle ce mois-ci."""

    help = "Envoie un rappel aux membres n'ayant pas encore paye leur cotisation mensuelle du mois en cours."

    def add_arguments(self, parser):
        """Définit les arguments de la commande.

        Args:
            parser: Le parser d'arguments Django.
        """
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche les membres qui seraient relances, sans envoyer d'email ni de notification.",
        )

    def handle(self, *args, **options):
        """Exécute l'envoi des rappels de cotisation.

        Args:
            *args: Arguments positionnels non utilisés.
            **options: Options de la commande.
        """
        dry_run = options["dry_run"]
        today = timezone.localdate()
        month_label = dateformat.format(today, "F Y")

        reminder_count = 0
        for group in ContributionService.get_groups_with_monthly_dues():
            members = ContributionService.get_members_without_monthly_payment(group, today.year, today.month)
            for member in members:
                if dry_run:
                    self.stdout.write(f"[dry-run] {member.full_name} ({group.name})")
                    continue

                self._send_reminder(member, group, month_label)
                reminder_count += 1

        if dry_run:
            self.stdout.write(self.style.NOTICE(f"{reminder_count} rappels seraient envoyes (dry-run)."))
        else:
            self.stdout.write(self.style.SUCCESS(f"{reminder_count} rappels envoyes."))

    def _send_reminder(self, member, group, month_label):
        """Envoie l'email et la notification in-app pour un membre en retard.

        Args:
            member: Le membre a relancer
            group: Le groupe concerne
            month_label: Libelle du mois en cours (ex: "Mars 2026")
        """
        title = f"Cotisation {group.name} - {month_label}"
        message = (
            f"Bonjour {member.full_name},\n\n"
            f"Nous n'avons pas encore enregistre votre cotisation mensuelle pour {group.name} "
            f"({month_label}). Merci de la regler des que possible."
        )

        if member.email:
            email_enabled = True
            if member.user_id:
                preference = NotificationPreference.objects.filter(user_id=member.user_id).first()
                if preference and not preference.email_enabled:
                    email_enabled = False
            if email_enabled:
                send_mail(
                    subject=title,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[member.email],
                    fail_silently=True,
                )

        if member.user_id:
            NotificationService.create_notification(
                user_id=member.user_id,
                notification_type=Notification.TYPE_WARNING,
                category=Notification.CATEGORY_CONTRIBUTION,
                title=title,
                message=message,
            )
