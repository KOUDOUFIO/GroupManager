
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Commande d'initialisation des rôles et permissions."""

    help = "Create default roles with permissions for core modules."

    def handle(self, *args, **options):
        """Exécute la création des rôles et permissions.

        Args:
            *args: Arguments positionnels non utilisés.
            **options: Options de la commande non utilisées.
        """
        core_perms = Permission.objects.filter(content_type__app_label="core")
        view_perms = core_perms.filter(codename__startswith="view_")
        manager_perms = core_perms.filter(
            codename__startswith=("add_", "change_", "view_")
        )

        roles = [
            ("Administrateur", core_perms),
            ("Gestionnaire", manager_perms),
            ("Lecteur", view_perms),
        ]

        for name, perms in roles:
            group, _ = Group.objects.get_or_create(name=name)
            group.permissions.set(perms)
            group.save()

        self.stdout.write(self.style.SUCCESS("Roles et permissions initialises."))
