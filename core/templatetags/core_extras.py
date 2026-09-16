"""Filtres de template personnalisés pour l'application core.

Ce module fournit des filtres de template Django personnalisés
pour faciliter l'accès aux attributs d'objets dans les templates.
"""

from django import template

register = template.Library()


@register.filter
def get_attr(obj, attr_path):
    """Récupère un attribut d'un objet via un chemin en notation pointée.

    Ce filtre permet d'accéder à des attributs imbriqués en utilisant
    la notation pointée (ex: obj.group.name).

    Args:
        obj: L'objet dont on veut récupérer l'attribut.
        attr_path: Le chemin de l'attribut en notation pointée.

    Returns:
        La valeur de l'attribut ou une chaîne vide si non trouvé.
    """
    if obj is None or not attr_path:
        return ""
    value = obj
    for attr in attr_path.split("."):
        if value is None:
            return ""
        value = getattr(value, attr, "")
        if callable(value):
            value = value()
    return value
