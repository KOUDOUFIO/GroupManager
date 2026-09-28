"""Commande d'envoi des rappels de cotisation mensuelle."""

from django.conf import settings
from django.core.mail import send_mail
from django.core.management import BaseCommand
from django.utils import dateformat, timezone

from core.models import Notification, NotificationPreference
from core.services.contribution_service import ContributionService
from core.services.messaging_service import MessagingService
from core.services.notification_service import NotificationService


class Command(BaseCommand):
    """Relance les membres sans cotisation mensuelle ce mois-ci.

    Canaux : email, notification in-app, puis WhatsApp (repli SMS si
    WhatsApp echoue) pour les membres ayant un numero de telephone.
    """

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
        self.phone_sent = 0
        for group in ContributionService.get_groups_with_monthly_dues():
            members = ContributionService.get_members_without_monthly_payment(group, today.year, today.month)
            for member in members:
                reminder_count += 1
                if dry_run:
                    self.stdout.write(f"[dry-run] {member.full_name} ({group.name})")
                    continue

                self._send_reminder(member, group, month_label)

        if dry_run:
            self.stdout.write(self.style.NOTICE(f"{reminder_count} rappels seraient envoyes (dry-run)."))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"{reminder_count} rappels envoyes, dont {self.phone_sent} par WhatsApp/SMS."
            ))

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

        if member.phone and self._send_to_phone(member, group, month_label):
            self.phone_sent += 1

        if member.user_id:
            NotificationService.create_notification(
                user_id=member.user_id,
                notification_type=Notification.TYPE_WARNING,
                category=Notification.CATEGORY_CONTRIBUTION,
                title=title,
                message=message,
            )

    def _send_to_phone(self, member, group, month_label):
        """Rappel court sur le telephone : WhatsApp d'abord, SMS en repli.

        Returns:
            bool: True si un message a ete accepte par le fournisseur.
        """
        body = (
            f"Kotiza - Bonjour {member.full_name}, votre cotisation {group.name} de {month_label} "
            f"n'est pas encore enregistree. Merci de la regler rapidement."
        )
        template_vars = {"1": member.full_name, "2": group.name, "3": month_label}

        for channel in MessagingService.enabled_channels():
            if MessagingService.send(channel, member.phone, body, template_vars=template_vars):
                return True
        return False
