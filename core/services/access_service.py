"""Acces des membres a leur espace : creation du compte, invitation, retrait."""

import re
import secrets
import unicodedata

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext as _

# Mot de passe provisoire lisible (sans 0/O ni 1/l) a dicter ou envoyer par SMS.
_TEMP_ALPHABET = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def suggest_username(member) -> str:
    """Identifiant libre derive du nom : "Ama Mensah" -> "ama.mensah" (ou "ama.mensah2")."""
    ascii_name = unicodedata.normalize("NFKD", member.full_name).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", ".", ascii_name.lower()).strip(".")[:28] or "membre"
    User = get_user_model()
    username, suffix = base, 2
    while User.objects.filter(username=username).exists():
        username, suffix = f"{base}{suffix}", suffix + 1
    return username


class AccessService:
    """Donne ou retire l'acces d'un membre a "Mon espace"."""

    @staticmethod
    @transaction.atomic
    def grant(member, username: str, request):
        """Cree le compte du membre et le previent.

        Returns:
            tuple: (user, email_sent, temporary_password). Le mot de passe
            provisoire n'est renvoye que si le membre n'a pas d'email.
        """
        User = get_user_model()
        user = User.objects.create_user(username=username, email=member.email or "")
        temporary_password = ""
        if member.email:
            user.set_unusable_password()
        else:
            temporary_password = "".join(secrets.choice(_TEMP_ALPHABET) for _ in range(10))
            user.set_password(temporary_password)
        user.save()
        member.user = user
        member.save(update_fields=["user"])

        email_sent = False
        if member.email:
            link = request.build_absolute_uri(reverse("password_reset_confirm", kwargs={
                "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": default_token_generator.make_token(user),
            }))
            body = _(
                "Bonjour %(name)s,\n\n"
                "Votre espace Kotiza est prêt : vous pouvez y suivre vos cotisations et vos présences.\n\n"
                "Votre identifiant : %(username)s\n"
                "Choisissez votre mot de passe en ouvrant ce lien :\n%(link)s\n\n"
                "L'équipe Kotiza"
            ) % {"name": member.full_name, "username": username, "link": link}
            email_sent = send_mail(
                _("Votre accès à Kotiza"), body, settings.DEFAULT_FROM_EMAIL, [member.email], fail_silently=True,
            ) > 0
        return user, email_sent, temporary_password

    @staticmethod
    @transaction.atomic
    def revoke(member):
        """Desactive le compte du membre (l'historique est conserve)."""
        user = member.user
        if user is None:
            return
        # Un compte d'equipe (admin, gestionnaire) est seulement detache, jamais desactive.
        if not (user.is_staff or user.is_superuser or user.groups.exists()):
            user.is_active = False
            user.save(update_fields=["is_active"])
        member.user = None
        member.save(update_fields=["user"])
