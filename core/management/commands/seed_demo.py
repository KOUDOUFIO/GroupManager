"""Commande de creation d'une organisation de demonstration (tontine a Lome)."""

import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction
from django.utils import timezone

from core.models import Contribution, Event, Group, Meeting, MeetingEntry, Member, Organ, Position

DEMO_SUFFIX = " (démo)"
DEMO_EMAIL_DOMAIN = "demo.kotiza.tg"
MONTHLY_DUE = Decimal("5000")

MEMBERS = [
    ("Ama Mensah", "90 11 22 33"), ("Kodjo Agbeko", "91 23 45 67"), ("Afi Dzifa", "92 34 56 78"),
    ("Yao Kpodar", "93 45 67 89"), ("Akossiwa Lawson", "96 56 78 90"), ("Komla Adjavon", "97 67 89 01"),
    ("Essi Amegah", "98 78 90 12"), ("Kossi Tchalla", "99 89 01 23"), ("Dédé Aziablé", "70 90 12 34"),
    ("Mawuli Gbeto", "79 01 23 45"), ("Abla Kouma", "90 12 34 56"), ("Sena Folly", "91 34 56 78"),
]


class Command(BaseCommand):
    """Remplit une tontine d'exemple pour les demonstrations commerciales."""

    help = (
        "Cree une organisation de demonstration (tontine, membres, cotisations, rencontres, evenements). "
        "Tout est marque \"(démo)\" et peut etre supprime avec --reset."
    )

    def add_arguments(self, parser):
        """Definit les arguments de la commande."""
        parser.add_argument("--reset", action="store_true", help="Supprimer les donnees de demonstration existantes.")
        parser.add_argument(
            "--password",
            help="Cree aussi les comptes demo-tresorier (gestionnaire) et demo-membre avec ce mot de passe.",
        )

    def handle(self, *args, **options):
        """Supprime puis recree les donnees de demonstration."""
        self._delete_demo()
        if options["reset"]:
            self.stdout.write(self.style.SUCCESS("Donnees de demonstration supprimees."))
            return
        if options["password"] and len(options["password"]) < 8:
            raise CommandError("Le mot de passe doit contenir au moins 8 caracteres.")

        with transaction.atomic():
            group, members = self._create_organisation()
            self._create_contributions(group, members)
            self._create_meetings(group, members)
            self._create_events(group)
            if options["password"]:
                self._create_accounts(members, options["password"])

        self.stdout.write(self.style.SUCCESS(
            f"Demonstration prete : {group.name}, {len(members)} membres. "
            "Supprimez-la avec : python manage.py seed_demo --reset"
        ))

    def _delete_demo(self):
        Group.objects.filter(name__endswith=DEMO_SUFFIX).delete()
        Member.objects.filter(email__endswith=f"@{DEMO_EMAIL_DOMAIN}").delete()
        get_user_model().objects.filter(username__in=["demo-tresorier", "demo-membre"]).delete()

    def _create_organisation(self):
        today = timezone.localdate()
        first_month = (today.replace(day=1) - timedelta(days=5 * 28)).replace(day=1)
        group = Group.objects.create(
            name=f"Tontine Espoir de Lomé{DEMO_SUFFIX}",
            description="Tontine mensuelle de 12 membres : 5 000 FCFA par mois, réunion le samedi.",
            monthly_due=MONTHLY_DUE,
            dues_start=first_month,
        )
        members = []
        for name, phone in MEMBERS:
            slug = name.lower().replace(" ", ".").replace("é", "e")
            member = Member.objects.create(
                full_name=name, phone=f"+228 {phone}", email=f"{slug}@{DEMO_EMAIL_DOMAIN}", address="Lomé",
            )
            member.groups.add(group)
            members.append(member)

        bureau = Organ.objects.create(group=group, name="Bureau exécutif", description="Direction de la tontine.")
        finances = Organ.objects.create(group=group, name="Commission des finances", description="Suivi de la caisse.")
        for title, organ, member in [
            ("Présidente", bureau, members[0]), ("Trésorier", finances, members[1]),
            ("Secrétaire", bureau, members[2]), ("Commissaire aux comptes", finances, members[3]),
        ]:
            Position.objects.create(group=group, organ=organ, name=title, member=member)
        return group, members

    def _create_contributions(self, group, members):
        rng = random.Random(2026)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        for months_ago in range(5, -1, -1):
            first_day = (month_start - timedelta(days=months_ago * 28)).replace(day=1)
            for member in members:
                # Ce mois-ci, un tiers des membres n'a pas encore paye (pour montrer les rappels).
                if months_ago == 0 and rng.random() < 0.35:
                    continue
                paid_day = min(first_day + timedelta(days=rng.randint(0, 12)), today)
                Contribution.objects.create(
                    member=member, group=group, contribution_type=Contribution.TYPE_MONTHLY,
                    amount=MONTHLY_DUE, paid_at=paid_day,
                    payment_method=rng.choice([Contribution.METHOD_MOBILE_MONEY] * 3 + [Contribution.METHOD_CASH]),
                )
        for member in rng.sample(members, 3):
            Contribution.objects.create(
                member=member, group=group, contribution_type=Contribution.TYPE_LATE_FINE,
                amount=Decimal("500"), paid_at=today - timedelta(days=rng.randint(0, 20)),
                payment_method=Contribution.METHOD_CASH, notes="Retard à la réunion",
            )

    def _create_meetings(self, group, members):
        rng = random.Random(7)
        today = timezone.localdate()
        last_saturday = today - timedelta(days=(today.weekday() - 5) % 7)
        statuses = [MeetingEntry.STATUS_PRESENT] * 7 + [
            MeetingEntry.STATUS_LATE, MeetingEntry.STATUS_ABSENT, MeetingEntry.STATUS_PERMISSION,
        ]
        for weeks_ago in range(8, -2, -1):
            day = last_saturday - timedelta(weeks=weeks_ago)
            meeting = Meeting.objects.create(
                group=group, title="Réunion de la tontine",
                scheduled_at=timezone.make_aware(datetime.combine(day, time(16, 0))),
                description="Collecte des cotisations et tour de la caisse.",
            )
            if day > today:
                continue
            for member in members:
                status = rng.choice(statuses)
                MeetingEntry.objects.create(
                    meeting=meeting, member=member, status=status,
                    reason="Voyage" if status == MeetingEntry.STATUS_PERMISSION else "",
                )

    def _create_events(self, group):
        today = timezone.localdate()
        for offset, kind, title, place in [
            (-20, "Assemblée", "Assemblée générale annuelle", "Salle paroissiale de Bè"),
            (2, "Social", "Remise de la caisse du mois", "Chez la présidente"),
            (15, "Formation", "Atelier : épargne et petits projets", "Maison des jeunes, Lomé"),
        ]:
            Event.objects.create(
                group=group, event_type=kind, title=title, location=place,
                starts_at=timezone.make_aware(datetime.combine(today + timedelta(days=offset), time(10, 0))),
            )

    def _create_accounts(self, members, password):
        User = get_user_model()
        call_command("seed_roles", verbosity=0)
        treasurer = User.objects.create_user("demo-tresorier", password=password)
        manager_role = AuthGroup.objects.get(name="Gestionnaire")
        treasurer.groups.add(manager_role)
        member_user = User.objects.create_user("demo-membre", password=password)
        members[0].user = member_user
        members[0].save(update_fields=["user"])
        self.stdout.write("Comptes crees : demo-tresorier (gestionnaire) et demo-membre (espace membre).")
