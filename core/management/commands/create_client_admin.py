from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Cree (ou met a jour) le compte administrateur d'une organisation cliente.

    Contrairement a un superutilisateur, ce compte tient ses droits du role
    "Administrateur" : il perd l'acces au site quand l'abonnement expire.
    """

    help = "Create or update the client's administrator account (role Administrateur, not superuser)."

    def add_arguments(self, parser):
        """Declare les arguments de la commande."""
        parser.add_argument("--username", required=True, help="Nom d'utilisateur.")
        parser.add_argument("--email", required=True, help="Email de l'administrateur.")
        parser.add_argument("--password", required=True, help="Mot de passe initial.")

    def handle(self, *args, **options):
        """Cree le compte et l'ajoute au role Administrateur."""
        call_command("seed_roles", verbosity=0)
        user, created = get_user_model().objects.get_or_create(username=options["username"])
        user.email = options["email"]
        user.is_staff = True
        user.is_superuser = False
        user.set_password(options["password"])
        user.save()
        user.groups.add(Group.objects.get(name="Administrateur"))
        msg = "Administrateur client cree." if created else "Administrateur client mis a jour."
        self.stdout.write(self.style.SUCCESS(msg))
