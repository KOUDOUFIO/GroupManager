"""Permissions personnalisées pour Django REST Framework.

Ce module fournit des classes de permissions strictes pour l'API REST,
assurant un contrôle d'accès granulaire basé sur les permissions Django.
"""

from rest_framework.permissions import DjangoModelPermissions


class StrictDjangoModelPermissions(DjangoModelPermissions):
    """Classe de permissions Django ModelPermissions stricte.

    Cette classe étend DjangoModelPermissions pour mapper explicitement
    chaque méthode HTTP à la permission Django correspondante, garantissant
    un contrôle d'accès précis et prévisible.
    """
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }
