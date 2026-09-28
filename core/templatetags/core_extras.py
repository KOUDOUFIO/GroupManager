"""Filtres de template personnalisés pour l'application core.

Ce module fournit des filtres de template Django personnalisés
pour faciliter l'accès aux attributs d'objets dans les templates.
"""

from django import template
from django.utils.safestring import mark_safe

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


@register.filter
def money(value):
    """Formate un montant avec separateur de milliers et la devise : 15 000 FCFA."""
    from decimal import Decimal, InvalidOperation

    from django.conf import settings
    from django.utils.formats import number_format

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return value
    decimals = 0 if amount == amount.to_integral_value() else 2
    return f"{number_format(amount, decimals, force_grouping=True)} {settings.KOTIZA_CURRENCY}"


@register.simple_tag
def currency():
    """Devise configuree (KOTIZA_CURRENCY)."""
    from django.conf import settings

    return settings.KOTIZA_CURRENCY


# Icones au trait (24x24), dessinees avec la couleur du texte courant.
ICONS = {
    "dashboard": '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>',
    "chart": '<path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "network": '<rect x="9" y="2" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="16" y="16" width="6" height="6" rx="1"/><path d="M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3"/><path d="M12 12V8"/>',
    "briefcase": '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/><path d="M2 13h20"/>',
    "id-card": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M15 9h2"/><path d="M15 13h2"/><path d="M6 16a3 3 0 0 1 6 0"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
    "check": '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="m9 14 2 2 4-4"/>',
    "wallet": '<path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1"/><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/>',
    "flag": '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><path d="M4 22v-7"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    "history": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "arrow-left": '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
    "arrow-right": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "plus": '<path d="M12 5v14"/><path d="M5 12h14"/>',
    "trending": '<path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
    "close": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
}


@register.simple_tag
def icon(name, size=20):
    """Rend une icone SVG en ligne (decorative, masquee aux lecteurs d'ecran)."""
    paths = ICONS.get(name, ICONS["grid"])
    return mark_safe(
        f'<svg class="icon" width="{int(size)}" height="{int(size)}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true" focusable="false">{paths}</svg>'
    )
