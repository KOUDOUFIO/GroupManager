"""Abonnement du client pour une installation Kotiza (une installation par client).

La date de fin est fixee par `KOTIZA_ACCESS_UNTIL` dans le `.env` du client.
Une fois cette date passee, le site affiche une page "abonnement expire" a
tout le monde, y compris a l'administrateur du client. Seuls les
superutilisateurs (l'operateur Kotiza) gardent l'acces, par exemple pour
exporter les donnees a la demande du client. Rien n'est jamais supprime.
"""

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext as _

# Nombre de jours avant l'expiration a partir duquel les administrateurs du
# client voient un bandeau de rappel.
REMINDER_DAYS = 14

# Chemins toujours accessibles : connexion, supervision, pages legales et
# fichiers statiques. /admin/ n'en fait PAS partie : l'administrateur du
# client (is_staff) pourrait sinon continuer a tout gerer via l'admin Django.
EXEMPT_PATH_PREFIXES = (
    "/accounts/",
    "/i18n/",
    "/health/",
    "/robots.txt",
    "/static/",
    "/mentions-legales/",
    "/confidentialite/",
)


def days_left(today=None):
    """Jours restants avant la fin de l'abonnement (0 le dernier jour).

    Returns:
        int | None: Negatif si expire, None si aucune date n'est configuree.
    """
    access_until = settings.KOTIZA_ACCESS_UNTIL
    if access_until is None:
        return None
    today = today or timezone.localdate()
    return (access_until - today).days


def is_expired(today=None):
    """Indique si l'abonnement est expire (la date de fin est incluse)."""
    remaining = days_left(today)
    return remaining is not None and remaining < 0


class SubscriptionMiddleware:
    """Bloque le site a tous sauf aux superutilisateurs une fois l'abonnement expire."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not is_expired() or request.path.startswith(EXEMPT_PATH_PREFIXES):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.is_superuser:
            return self.get_response(request)

        if request.path.startswith("/api/"):
            return JsonResponse({"detail": _("Abonnement expiré.")}, status=402)
        return render(
            request,
            "errors/subscription_expired.html",
            {"billing_contact": settings.KOTIZA_BILLING_CONTACT},
            status=402,
        )


def subscription_status(request):
    """Context processor : bandeau de rappel d'abonnement pour les administrateurs."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated or not user.is_staff:
        return {}
    remaining = days_left()
    if remaining is None or remaining > REMINDER_DAYS:
        return {}
    return {
        "subscription_days_left": remaining,
        "subscription_expired": remaining < 0,
        "subscription_access_until": settings.KOTIZA_ACCESS_UNTIL,
        "subscription_billing_contact": settings.KOTIZA_BILLING_CONTACT,
    }
