"""Middleware Django pour l'application core.

Ce module fournit le middleware de capture du contexte d'acteur pour l'audit,
enregistrant automatiquement l'utilisateur, le chemin et l'adresse IP pour chaque requête.
"""

from urllib.parse import quote

from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect
from django_otp import user_has_device

from .audit import clear_actor_context, set_actor_context


class TwoFactorMiddleware:
    """Demande le code a 6 chiffres aux comptes qui ont active la connexion a deux etapes.

    Tant que le code n'est pas saisi, seules la page de verification, la
    deconnexion et les fichiers statiques restent accessibles.
    """

    ALLOWED_PREFIXES = ("/securite/verification/", "/accounts/logout/", "/static/", "/i18n/", "/health/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and not request.path.startswith(self.ALLOWED_PREFIXES)
            and not user.is_verified()
            and user_has_device(user, confirmed=True)
        ):
            return redirect(f"/securite/verification/?next={quote(request.get_full_path())}")
        return self.get_response(request)


class AuditActorMiddleware:
    """Middleware qui capture le contexte de l'acteur pour l'audit.

    Ce middleware enregistre l'utilisateur connecté, le chemin de la requête
    et l'adresse IP avant chaque traitement de requête, et nettoie le contexte
    après le traitement. Ces informations sont utilisées par le système d'audit
    pour tracer qui a effectué quelles modifications.
    """

    def __init__(self, get_response):
        """Initialise le middleware.

        Args:
            get_response: La fonction de traitement de la requête suivante.
        """
        self.get_response = get_response

    def __call__(self, request):
        """Traite la requête avec capture du contexte d'acteur.

        Args:
            request: L'objet HttpRequest Django.

        Returns:
            HttpResponse: La réponse de la vue.
        """
        user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
        set_actor_context(user=user, path=request.path, ip_address=request.META.get("REMOTE_ADDR", ""))
        try:
            return self.get_response(request)
        finally:
            clear_actor_context()


class ApiToggleMiddleware:
    """Repond 404 sur /api/ (API et documentation) si KOTIZA_API_ENABLED est faux."""

    def __init__(self, get_response):
        """Initialise le middleware.

        Args:
            get_response: La fonction de traitement de la requête suivante.
        """
        self.get_response = get_response

    def __call__(self, request):
        """Bloque l'API quand elle est desactivee.

        Args:
            request: L'objet HttpRequest Django.

        Returns:
            HttpResponse: La réponse de la vue, ou une 404 si l'API est coupee.
        """
        if not settings.KOTIZA_API_ENABLED and request.path.startswith("/api/"):
            raise Http404("API desactivee.")
        return self.get_response(request)
