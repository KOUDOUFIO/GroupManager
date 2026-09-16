"""Gestion du contexte d'acteur pour l'audit.

Ce module fournit des fonctions pour stocker et récupérer le contexte
de l'acteur (utilisateur, chemin, adresse IP) dans un stockage local
au thread, utilisé par le système d'audit pour tracer les modifications.
"""

import threading

_audit_local = threading.local()


def set_actor_context(user=None, path="", ip_address=""):
    """Définit le contexte de l'acteur pour la requête courante.

    Args:
        user: L'utilisateur Django connecté ou None.
        path: Le chemin de la requête HTTP.
        ip_address: L'adresse IP de la requête.
    """
    _audit_local.user = user
    _audit_local.path = path
    _audit_local.ip_address = ip_address


def clear_actor_context():
    """Nettoie le contexte de l'acteur après traitement de la requête."""
    _audit_local.user = None
    _audit_local.path = ""
    _audit_local.ip_address = ""


def get_actor_context():
    """Récupère le contexte de l'acteur pour la requête courante.

    Returns:
        tuple: (user, path, ip_address)
    """
    return (
        getattr(_audit_local, "user", None),
        getattr(_audit_local, "path", ""),
        getattr(_audit_local, "ip_address", ""),
    )


def log_action(actor, action, model_name, object_pk, object_repr, changes=None):
    """Enregistre une action d'audit dans la base de données.
    
    Args:
        actor: L'utilisateur ayant effectué l'action.
        action: Le type d'action ('create', 'update', 'delete').
        model_name: Le nom du modèle affecté.
        object_pk: La clé primaire de l'objet.
        object_repr: La représentation textuelle de l'objet.
        changes: Un dictionnaire des changements (pour les mises à jour).
    """
    from .models import AuditLog
    
    user, path, ip_address = get_actor_context()
    
    AuditLog.objects.create(
        actor=actor or user,
        action=action,
        model_name=model_name,
        object_pk=str(object_pk),
        object_repr=object_repr[:255],
        path=path,
        ip_address=ip_address,
        changes=changes or {}
    )
