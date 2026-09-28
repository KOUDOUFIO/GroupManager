"""Vues web Django pour l'interface utilisateur.

Ce package regroupe les vues web pour l'interface utilisateur de Kotiza,
organisées par domaine :

- marketing : pages vitrine (accueil, entreprise, plateforme, devis)
- workspaces : workspaces admin/gestionnaire, recherche globale, dashboard groupe
- mixins : briques communes aux vues CRUD (permissions, recherche, pagination)
- group / organ / member / position / meeting / contribution / document / event / audit :
  CRUD web par domaine
- exports : exports CSV, Excel et PDF (cotisations, présences)
"""

from .marketing import company_page, home, platform_page, proposal_page
from .legal import LegalNoticeView, PrivacyPolicyView
from .workspaces import AdminWorkspaceView, GlobalSearchView, GroupDashboardView, ManagerWorkspaceView
from .mixins import (
    BaseCreateView,
    BaseDeleteView,
    BaseUpdateView,
    CrudContextMixin,
    MemberSelfRequiredMixin,
    ModelPermissionMixin,
    SearchableListView,
    StaffRequiredMixin,
)
from .member_portal import (
    MemberAttendanceListView,
    MemberContributionsListView,
    MemberPortalDashboardView,
)
from .group import GroupCreateView, GroupDeleteView, GroupListView, GroupUpdateView
from .organ import OrganCreateView, OrganDeleteView, OrganListView, OrganUpdateView
from .member import MemberCreateView, MemberDeleteView, MemberListView, MemberUpdateView
from .position import PositionCreateView, PositionDeleteView, PositionListView, PositionUpdateView
from .meeting import (
    MeetingCreateView,
    MeetingDeleteView,
    MeetingEntryCreateView,
    MeetingEntryDeleteView,
    MeetingEntryListView,
    MeetingEntryUpdateView,
    MeetingListView,
    MeetingUpdateView,
)
from .contribution import ContributionCreateView, ContributionDeleteView, ContributionListView, ContributionUpdateView
from .document import DocumentCreateView, DocumentDeleteView, DocumentListView, DocumentUpdateView
from .event import EventCreateView, EventDeleteView, EventListView, EventUpdateView
from .audit import AuditLogListView
from .exports import (
    _parse_filters,
    _pdf_response,
    _safe_spreadsheet_cell,
    _xlsx_response,
    export_contributions_csv,
    export_contributions_pdf,
    export_contributions_xlsx,
    export_meeting_entries_csv,
    export_meeting_entries_pdf,
    export_meeting_entries_xlsx,
)

__all__ = [
    "company_page",
    "home",
    "platform_page",
    "proposal_page",
    "LegalNoticeView",
    "PrivacyPolicyView",
    "AdminWorkspaceView",
    "GlobalSearchView",
    "GroupDashboardView",
    "ManagerWorkspaceView",
    "BaseCreateView",
    "BaseDeleteView",
    "BaseUpdateView",
    "CrudContextMixin",
    "MemberSelfRequiredMixin",
    "ModelPermissionMixin",
    "SearchableListView",
    "StaffRequiredMixin",
    "MemberAttendanceListView",
    "MemberContributionsListView",
    "MemberPortalDashboardView",
    "GroupCreateView",
    "GroupDeleteView",
    "GroupListView",
    "GroupUpdateView",
    "OrganCreateView",
    "OrganDeleteView",
    "OrganListView",
    "OrganUpdateView",
    "MemberCreateView",
    "MemberDeleteView",
    "MemberListView",
    "MemberUpdateView",
    "PositionCreateView",
    "PositionDeleteView",
    "PositionListView",
    "PositionUpdateView",
    "MeetingCreateView",
    "MeetingDeleteView",
    "MeetingEntryCreateView",
    "MeetingEntryDeleteView",
    "MeetingEntryListView",
    "MeetingEntryUpdateView",
    "MeetingListView",
    "MeetingUpdateView",
    "ContributionCreateView",
    "ContributionDeleteView",
    "ContributionListView",
    "ContributionUpdateView",
    "DocumentCreateView",
    "DocumentDeleteView",
    "DocumentListView",
    "DocumentUpdateView",
    "EventCreateView",
    "EventDeleteView",
    "EventListView",
    "EventUpdateView",
    "AuditLogListView",
    "export_contributions_csv",
    "export_contributions_pdf",
    "export_contributions_xlsx",
    "export_meeting_entries_csv",
    "export_meeting_entries_pdf",
    "export_meeting_entries_xlsx",
]
