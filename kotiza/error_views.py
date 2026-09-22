"""Vues de gestion d'erreurs personnalisées pour le projet Kotiza.

Ce module fournit des vues pour les pages d'erreur HTTP personnalisées
(400, 403, 404, 500) avec des templates dédiés.
"""

from django.shortcuts import render


def bad_request(request, exception):
    """Vue pour l'erreur 400 Bad Request.

    Args:
        request: L'objet HttpRequest Django.
        exception: L'exception levée.

    Returns:
        HttpResponse: La page d'erreur 400.
    """
    return render(request, "errors/400.html", status=400)


def permission_denied(request, exception):
    """Vue pour l'erreur 403 Permission Denied.

    Args:
        request: L'objet HttpRequest Django.
        exception: L'exception levée.

    Returns:
        HttpResponse: La page d'erreur 403.
    """
    return render(request, "errors/403.html", status=403)


def page_not_found(request, exception):
    """Vue pour l'erreur 404 Not Found.

    Args:
        request: L'objet HttpRequest Django.
        exception: L'exception levée.

    Returns:
        HttpResponse: La page d'erreur 404.
    """
    return render(request, "errors/404.html", status=404)


def server_error(request):
    """Vue pour l'erreur 500 Internal Server Error.

    Args:
        request: L'objet HttpRequest Django.

    Returns:
        HttpResponse: La page d'erreur 500.
    """
    return render(request, "errors/500.html", status=500)
