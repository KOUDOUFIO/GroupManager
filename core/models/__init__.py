"""Modèles de données pour l'application core, organisés par domaine :

- group / organ / member / position : structure organisationnelle
- meeting : rencontres planifiées et présences (MeetingEntry)
- contribution : cotisations et paiements
- document : documents partagés
- event : événements spéciaux
- audit_log : journal d'audit des modifications
- notification : notifications utilisateurs et préférences
- dashboard : préférences de dashboard personnalisable
- two_factor : authentification à deux facteurs (2FA)
"""

from .group import Group
from .organ import Organ
from .member import Member
from .position import Position
from .meeting import Meeting, MeetingEntry
from .contribution import Contribution
from .document import Document
from .event import Event
from .audit_log import AuditLog
from .notification import Notification, NotificationPreference
from .dashboard import DashboardPreference
from .two_factor import TOTPDevice, TwoFactorPreference

__all__ = [
    "Group",
    "Organ",
    "Member",
    "Position",
    "Meeting",
    "MeetingEntry",
    "Contribution",
    "Document",
    "Event",
    "AuditLog",
    "Notification",
    "NotificationPreference",
    "DashboardPreference",
    "TOTPDevice",
    "TwoFactorPreference",
]
