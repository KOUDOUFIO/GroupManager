"""Normalisation des numeros de telephone au format international (E.164)."""

import re

from django.conf import settings


def normalize_phone(raw: str) -> str:
    """Convertit un numero saisi librement en +<indicatif><numero>.

    "90 12 34 56" -> "+22890123456", "0022890123456" -> "+22890123456".

    Returns:
        str: le numero normalise, ou "" s'il est inexploitable.
    """
    if not raw:
        return ""
    digits = re.sub(r"\D", "", raw)
    country = settings.KOTIZA_DEFAULT_COUNTRY_CODE
    if digits.startswith("00"):
        digits = digits[2:]
    elif not raw.strip().startswith("+") and (len(digits) <= 8 or not digits.startswith(country)):
        # Numero local : on ajoute l'indicatif du pays.
        digits = country + digits.lstrip("0")
    if not 8 <= len(digits) <= 15:
        return ""
    return f"+{digits}"
