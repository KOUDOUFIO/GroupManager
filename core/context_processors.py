"""Context processors Django pour l'application core.

Ce module fournit des variables de contexte globales pour les templates,
notamment les informations de profil utilisateur pour l'adaptation de l'interface.
"""

from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy


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
            "ui_role_label": _("Visiteur"),
        }

    is_admin = user.is_staff
    is_manager = user.groups.filter(name="Gestionnaire").exists()
    is_member = hasattr(user, "member_profile")

    if is_admin:
        role_label = _("Administrateur")
    elif is_manager:
        role_label = _("Gestionnaire")
    else:
        role_label = _("Utilisateur")

    return {
        "ui_is_authenticated": True,
        "ui_is_admin": is_admin,
        "ui_is_manager": is_manager,
        "ui_is_member": is_member,
        "ui_role_label": role_label,
    }


# Catalogue des modules affiches dans le bouton "Modules" et les tableaux de bord.
# access : "all", "admin", "manager" (gestionnaire ou admin), "member" (fiche liee)
# ou une permission Django ("core.view_group").
MODULE_SECTIONS = (
    (gettext_lazy("Espaces"), (
        ("dashboard", gettext_lazy("Tableau de bord"), gettext_lazy("Vue d'ensemble de votre activité"), "/", "dashboard", "green", "all"),
        ("admin", gettext_lazy("Espace admin"), gettext_lazy("Gouvernance, audit et contrôle global"), "/admin-workspace/", "shield", "petrol", "admin"),
        ("manager", gettext_lazy("Espace manager"), gettext_lazy("Pilotage opérationnel au quotidien"), "/manager-workspace/", "chart", "sky", "manager"),
        ("member", gettext_lazy("Mon espace"), gettext_lazy("Vos cotisations et vos présences"), "/mon-espace/", "user", "olive", "member"),
    )),
    (gettext_lazy("Organisation"), (
        ("groups", gettext_lazy("Groupes"), gettext_lazy("Structures, responsables et membres"), "/groupes/", "users", "teal", "core.view_group"),
        ("organs", gettext_lazy("Organes"), gettext_lazy("Bureaux, comités et commissions"), "/organes/", "network", "petrol", "core.view_organ"),
        ("positions", gettext_lazy("Postes"), gettext_lazy("Rôles et responsabilités"), "/postes/", "briefcase", "sky", "core.view_position"),
    )),
    (gettext_lazy("Personnes"), (
        ("members", gettext_lazy("Membres"), gettext_lazy("Fiches et coordonnées des membres"), "/membres/", "id-card", "olive", "core.view_member"),
        ("meetings", gettext_lazy("Rencontres"), gettext_lazy("Réunions planifiées et passées"), "/rencontres/", "calendar", "amber", "core.view_meeting"),
        ("attendance", gettext_lazy("Présences"), gettext_lazy("Présents, absents, retards et permissions"), "/presences/", "check", "emerald", "core.view_meetingentry"),
    )),
    (gettext_lazy("Finance"), (
        ("contributions", gettext_lazy("Cotisations"), gettext_lazy("Paiements, reçus PDF et exports"), "/cotisations/", "wallet", "gold", "core.view_contribution"),
        ("dues", gettext_lazy("Suivi des cotisations"), gettext_lazy("Qui est à jour, qui est en retard"), "/suivi-cotisations/", "trending", "orange", "core.view_contribution"),
    )),
    (gettext_lazy("Activités"), (
        ("events", gettext_lazy("Événements"), gettext_lazy("Agenda des événements à venir"), "/evenements/", "flag", "orange", "core.view_event"),
        ("documents", gettext_lazy("Documents"), gettext_lazy("Statuts, comptes rendus et fichiers"), "/documents/", "file", "sky", "core.view_document"),
        ("audit", gettext_lazy("Audit"), gettext_lazy("Historique de toutes les actions"), "/audit-logs/", "history", "slate", "core.view_auditlog"),
    )),
    (gettext_lazy("Outils"), (
        ("search", gettext_lazy("Recherche"), gettext_lazy("Retrouvez tout en un seul champ"), "/recherche/", "search", "teal", "all"),
        ("notifications", gettext_lazy("Notifications"), gettext_lazy("Rappels et informations reçus"), "/notifications/", "bell", "sky", "all"),
        ("security", gettext_lazy("Sécurité du compte"), gettext_lazy("Mot de passe et connexion à deux étapes"), "/securite/", "lock", "slate", "all"),
    )),
)


def _can_access(user, access, flags):
    if access == "all":
        return True
    if access == "admin":
        return flags["ui_is_admin"]
    if access == "manager":
        return flags["ui_is_admin"] or flags["ui_is_manager"]
    if access == "member":
        return flags["ui_is_member"]
    return user.has_perm(access)


def ui_modules(request):
    """Fournit les modules accessibles a l'utilisateur, regroupes par section.

    Returns:
        dict: ui_module_sections, liste de {"label", "modules"} ou chaque module
              est un dict (key, label, description, url, icon, tone, active).
    """
    flags = ui_profile(request)
    if not flags["ui_is_authenticated"]:
        return {"ui_module_sections": []}

    user = request.user
    path = request.path
    sections = []
    for section_label, modules in MODULE_SECTIONS:
        items = [
            {
                "key": key,
                "label": label,
                "description": description,
                "url": url,
                "icon": icon,
                "tone": tone,
                "active": path == url if url == "/" else path.startswith(url),
            }
            for key, label, description, url, icon, tone, access in modules
            if _can_access(user, access, flags)
        ]
        if items:
            sections.append({"label": section_label, "modules": items})
    return {"ui_module_sections": sections}


def ui_notifications(request):
    """Nombre de notifications non lues (cloche de l'en-tete)."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"ui_unread_notifications": 0}
    from .models import Notification

    return {"ui_unread_notifications": Notification.objects.filter(user=user, is_read=False).count()}
