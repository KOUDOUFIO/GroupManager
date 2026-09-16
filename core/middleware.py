"""Middleware Django pour l'application core.

Ce module fournit le middleware de capture du contexte d'acteur pour l'audit,
enregistrant automatiquement l'utilisateur, le chemin et l'adresse IP pour chaque requête.
"""

from .audit import clear_actor_context, set_actor_context


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
