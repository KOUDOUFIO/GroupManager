"""Context processors Django pour l'application core.

Ce module fournit des variables de contexte globales pour les templates,
notamment les informations de profil utilisateur pour l'adaptation de l'interface.
"""


def ui_profile(request):
    """Fournit le profil UI de l'utilisateur connecté.

    Args:
        request: L'objet HttpRequest Django.

    Returns:
        dict: Dictionnaire avec les clés ui_is_authenticated, ui_is_admin,
              ui_is_manager, ui_is_member, ui_role_label.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {
            "ui_is_authenticated": False,
            "ui_is_admin": False,
            "ui_is_manager": False,
            "ui_is_member": False,
            "ui_role_label": "Visiteur",
        }

    is_admin = user.is_staff
    is_manager = user.groups.filter(name="Gestionnaire").exists()
    is_member = hasattr(user, "member_profile")

    if is_admin:
        role_label = "Administrateur"
    elif is_manager:
        role_label = "Gestionnaire"
    else:
        role_label = "Utilisateur"

    return {
        "ui_is_authenticated": True,
        "ui_is_admin": is_admin,
        "ui_is_manager": is_manager,
        "ui_is_member": is_member,
        "ui_role_label": role_label,
    }
