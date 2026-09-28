"""Commande d'envoi des rappels de cotisation."""

from django.conf import settings
from django.core.mail import send_mail
from django.core.management import BaseCommand
from django.utils import dateformat, timezone

from core.models import Notification, NotificationPreference
from core.services.contribution_service import ContributionService
from core.services.dues_service import DuesService
from core.services.messaging_service import MessagingService
from core.services.notification_service import NotificationService
from core.templatetags.core_extras import money


def _plain(text: str) -> str:
    """Espaces insecables -> espaces simples (SMS et emails texte)."""
    return text.replace(" ", " ").replace(" ", " ")


class Command(BaseCommand):
    """Relance les membres en retard de cotisation.

    - Groupes avec une cotisation mensuelle attendue : les membres dont le
      "reste a payer" est positif, avec le montant et le nombre de mois.
    - Autres groupes : les membres sans cotisation mensuelle ce mois-ci.

    Canaux : email, notification in-app, puis WhatsApp (repli SMS si
    WhatsApp echoue) pour les membres ayant un numero de telephone.
    """

    help = "Envoie un rappel aux membres en retard de cotisation."

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

        reminders = []
        tracked = list(DuesService.tracked_groups())
        for group in tracked:
            for row in DuesService.for_group(group, today):
                if row.is_late:
                    reminders.append((row.member, group, row))
        tracked_ids = {group.pk for group in tracked}
        for group in ContributionService.get_groups_with_monthly_dues():
            if group.pk in tracked_ids:
                continue
            for member in ContributionService.get_members_without_monthly_payment(group, today.year, today.month):
                reminders.append((member, group, None))

        self.phone_sent = 0
        for member, group, dues in reminders:
            if dry_run:
                detail = f" - reste {_plain(money(dues.remaining))}" if dues else ""
                self.stdout.write(f"[dry-run] {member.full_name} ({group.name}){detail}")
                continue
            self._send_reminder(member, group, month_label, dues)

        if dry_run:
            self.stdout.write(self.style.NOTICE(f"{len(reminders)} rappels seraient envoyes (dry-run)."))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"{len(reminders)} rappels envoyes, dont {self.phone_sent} par WhatsApp/SMS."
            ))

    def _texts(self, member, group, month_label, dues):
        """Titre, message complet et message court (telephone)."""
        if dues:
            amount = _plain(money(dues.remaining))
            months = dues.months_late
            title = f"Cotisation {group.name} - reste {amount}"
            message = (
                f"Bonjour {member.full_name},\n\n"
                f"D'apres nos registres, il vous reste {amount} a regler pour {group.name} "
                f"({months} mois de cotisation). Merci de regulariser des que possible.\n\n"
                f"Si vous avez deja paye, signalez-le au tresorier."
            )
            short = (
                f"Kotiza - Bonjour {member.full_name}, il vous reste {amount} a regler "
                f"pour {group.name} ({months} mois). Merci de regulariser."
            )
        else:
            title = f"Cotisation {group.name} - {month_label}"
            message = (
                f"Bonjour {member.full_name},\n\n"
                f"Nous n'avons pas encore enregistre votre cotisation mensuelle pour {group.name} "
                f"({month_label}). Merci de la regler des que possible."
            )
            short = (
                f"Kotiza - Bonjour {member.full_name}, votre cotisation {group.name} de {month_label} "
                f"n'est pas encore enregistree. Merci de la regler rapidement."
            )
        return title, message, short

    def _send_reminder(self, member, group, month_label, dues=None):
        """Envoie l'email, le message telephone et la notification in-app."""
        title, message, short = self._texts(member, group, month_label, dues)

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

        if member.phone and self._send_to_phone(member, group, month_label, short):
            self.phone_sent += 1

        if member.user_id:
            NotificationService.create_notification(
                user_id=member.user_id,
                notification_type=Notification.TYPE_WARNING,
                category=Notification.CATEGORY_CONTRIBUTION,
                title=title,
                message=message,
            )

    def _send_to_phone(self, member, group, month_label, body):
        """Rappel court sur le telephone : WhatsApp d'abord, SMS en repli.

        Returns:
            bool: True si un message a ete accepte par le fournisseur.
        """
        template_vars = {"1": member.full_name, "2": group.name, "3": month_label}
        for channel in MessagingService.enabled_channels():
            if MessagingService.send(channel, member.phone, body, template_vars=template_vars):
                return True
        return False
