"""Suivi des cotisations dues : qui doit combien, et depuis combien de mois.

Pour chaque groupe ayant un montant mensuel attendu, on compare ce que chaque
membre aurait du verser depuis le premier mois du avec ce qu'il a reellement
verse en cotisations mensuelles confirmees.
"""

import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from ..models import Contribution, Group


@dataclass
class MemberDues:
    """Situation d'un membre dans un groupe."""
    member: object
    group: Group
    months_due: int
    expected: Decimal
    paid: Decimal

    @property
    def remaining(self) -> Decimal:
        return max(self.expected - self.paid, Decimal("0"))

    @property
    def months_late(self) -> int:
        if not self.remaining or not self.group.monthly_due:
            return 0
        return math.ceil(self.remaining / self.group.monthly_due)

    @property
    def is_late(self) -> bool:
        return self.remaining > 0


def dues_start(group: Group) -> date:
    """Premier mois du du groupe (1er jour du mois)."""
    start = group.dues_start or timezone.localtime(group.created_at).date()
    return start.replace(day=1)


def months_between(start: date, today: date) -> int:
    """Nombre de mois dus, mois de debut et mois courant inclus."""
    if start > today:
        return 0
    return (today.year - start.year) * 12 + today.month - start.month + 1


class DuesService:
    """Calcul des sommes dues et des retards."""

    @staticmethod
    def tracked_groups():
        """Groupes ayant un montant mensuel attendu."""
        return Group.objects.filter(monthly_due__gt=0).order_by("name")

    @staticmethod
    def for_group(group: Group, today: date = None) -> list:
        """Situation de chaque membre du groupe, les plus en retard d'abord."""
        today = today or timezone.localdate()
        if not group.monthly_due:
            return []
        start = dues_start(group)
        months = months_between(start, today)
        expected = group.monthly_due * months
        paid_by_member = dict(
            Contribution.objects.filter(
                group=group,
                contribution_type=Contribution.TYPE_MONTHLY,
                payment_status=Contribution.STATUS_CONFIRMED,
                paid_at__gte=start,
            ).values_list("member_id").annotate(total=Sum("amount"))
        )
        rows = [
            MemberDues(member, group, months, expected, paid_by_member.get(member.id) or Decimal("0"))
            for member in group.members.order_by("full_name")
        ]
        rows.sort(key=lambda row: (-row.remaining, row.member.full_name))
        return rows

    @classmethod
    def for_member(cls, member, today: date = None) -> list:
        """Situation d'un membre dans chacun de ses groupes suivis."""
        today = today or timezone.localdate()
        rows = []
        for group in member.groups.filter(monthly_due__gt=0).order_by("name"):
            rows.extend(row for row in cls.for_group(group, today) if row.member.id == member.id)
        return rows

    @staticmethod
    def summary(rows: list) -> dict:
        """Totaux d'une liste de situations."""
        return {
            "expected": sum((row.expected for row in rows), Decimal("0")),
            "paid": sum((min(row.paid, row.expected) for row in rows), Decimal("0")),
            "remaining": sum((row.remaining for row in rows), Decimal("0")),
            "late_count": sum(1 for row in rows if row.is_late),
            "member_count": len(rows),
        }
