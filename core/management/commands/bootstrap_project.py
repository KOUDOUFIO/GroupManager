

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    """Commande d'initialisation du projet GroupManager."""

    help = "Initialise le projet: migrate, seed_roles, et creation optionnelle d'un superutilisateur."

    def add_arguments(self, parser):
        """Définit les arguments de la commande.

        Args:
            parser: Le parser d'arguments Django.
        """
        parser.add_argument("--with-superuser", action="store_true", help="Creer/mettre a jour un superutilisateur.")
        parser.add_argument("--username", default="admin", help="Nom d'utilisateur du superutilisateur.")
        parser.add_argument("--email", default="admin@example.com", help="Email du superutilisateur.")
        parser.add_argument("--password", default="Admin1234!", help="Mot de passe du superutilisateur.")
        parser.add_argument("--collectstatic", action="store_true", help="Executer collectstatic --noinput.")

    def handle(self, *args, **options):
        """Exécute la commande d'initialisation.

        Args:
            *args: Arguments positionnels non utilisés.
            **options: Options de la commande.
        """
        self.stdout.write(self.style.NOTICE("Application des migrations..."))
        call_command("migrate")

        self.stdout.write(self.style.NOTICE("Initialisation des roles..."))
        call_command("seed_roles")

        if options["with_superuser"]:
            self.stdout.write(self.style.NOTICE("Creation/mise a jour du superutilisateur..."))
            User = get_user_model()
            user, created = User.objects.get_or_create(
                username=options["username"],
                defaults={"email": options["email"], "is_staff": True, "is_superuser": True},
            )
            user.email = options["email"]
            user.is_staff = True
            user.is_superuser = True
            user.set_password(options["password"])
            user.save()
            msg = "Superutilisateur cree." if created else "Superutilisateur mis a jour."
            self.stdout.write(self.style.SUCCESS(msg))

        if options["collectstatic"]:
            self.stdout.write(self.style.NOTICE("Collecte des fichiers statiques..."))
            call_command("collectstatic", interactive=False, verbosity=0)
            self.stdout.write(self.style.SUCCESS("Collectstatic termine."))

        self.stdout.write(self.style.SUCCESS("Bootstrap termine avec succes."))
