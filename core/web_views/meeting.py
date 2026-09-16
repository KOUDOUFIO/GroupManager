"""CRUD web pour les rencontres et les présences (MeetingEntry)."""

from urllib.parse import urlencode

from django.urls import reverse_lazy
from django.utils.dateparse import parse_date

from .. import forms, models
from .mixins import BaseCreateView, BaseDeleteView, BaseUpdateView, SearchableListView


class MeetingListView(SearchableListView):
    """ListView pour les rencontres."""
    model = models.Meeting
    template_name = "core/crud_list.html"
    title = "Rencontres"
    create_url_name = "meeting_create"
    base_url_name = "meeting"
    list_columns = [
        {"label": "Titre", "accessor": "title"},
        {"label": "Groupe", "accessor": "group.name"},
        {"label": "Date", "accessor": "scheduled_at"},
    ]
    search_fields = ["title", "group__name"]
    select_related_fields = ("group",)


class MeetingCreateView(BaseCreateView):
    """Vue de création pour les rencontres."""
    model = models.Meeting
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Ajouter une rencontre"
    success_url = reverse_lazy("meeting_list")
    list_url_name = "meeting_list"
    base_url_name = "meeting"


class MeetingUpdateView(BaseUpdateView):
    """Vue de modification pour les rencontres."""
    model = models.Meeting
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Modifier une rencontre"
    success_url = reverse_lazy("meeting_list")
    list_url_name = "meeting_list"
    base_url_name = "meeting"


class MeetingDeleteView(BaseDeleteView):
    """Vue de suppression pour les rencontres."""
    model = models.Meeting
    template_name = "core/crud_confirm_delete.html"
    title = "Supprimer une rencontre"
    success_url = reverse_lazy("meeting_list")
    list_url_name = "meeting_list"
    base_url_name = "meeting"


class MeetingEntryListView(SearchableListView):
    """ListView pour les présences aux rencontres avec filtres avancés."""
    model = models.MeetingEntry
    template_name = "core/crud_list.html"
    title = "Presences"
    create_url_name = "meeting_entry_create"
    base_url_name = "meeting_entry"
    list_columns = [
        {"label": "Membre", "accessor": "member.full_name"},
        {"label": "Rencontre", "accessor": "meeting.title"},
        {"label": "Groupe", "accessor": "meeting.group.name"},
        {"label": "Statut", "accessor": "get_status_display"},
        {"label": "Date", "accessor": "recorded_at"},
    ]
    search_fields = ["member__full_name", "meeting__title", "status", "reason", "meeting__group__name"]
    select_related_fields = ("meeting", "meeting__group", "member")

    def get_queryset(self):
        """Filtre le queryset selon groupe et dates."""
        queryset = super().get_queryset()
        group_id = self.request.GET.get("group")
        start_date = parse_date(self.request.GET.get("start_date", ""))
        end_date = parse_date(self.request.GET.get("end_date", ""))
        if group_id:
            queryset = queryset.filter(meeting__group_id=group_id)
        if start_date:
            queryset = queryset.filter(recorded_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(recorded_at__date__lte=end_date)
        return queryset

    def get_context_data(self, **kwargs):
        """Fournit le contexte avec les filtres et paramètres d'export."""
        context = super().get_context_data(**kwargs)
        context["groups"] = models.Group.objects.order_by("name")
        context["selected_group"] = self.request.GET.get("group", "")
        context["start_date"] = self.request.GET.get("start_date", "")
        context["end_date"] = self.request.GET.get("end_date", "")
        context["export_query"] = urlencode(
            {
                "group": context["selected_group"],
                "start_date": context["start_date"],
                "end_date": context["end_date"],
            }
        )
        return context


class MeetingEntryCreateView(BaseCreateView):
    """Vue de création pour les présences."""
    model = models.MeetingEntry
    form_class = forms.MeetingEntryForm
    template_name = "core/crud_form.html"
    title = "Ajouter une presence"
    success_url = reverse_lazy("meeting_entry_list")
    list_url_name = "meeting_entry_list"
    base_url_name = "meeting_entry"


class MeetingEntryUpdateView(BaseUpdateView):
    """Vue de modification pour les présences."""
    model = models.MeetingEntry
    form_class = forms.MeetingEntryForm
    template_name = "core/crud_form.html"
    title = "Modifier une presence"
    success_url = reverse_lazy("meeting_entry_list")
    list_url_name = "meeting_entry_list"
    base_url_name = "meeting_entry"


class MeetingEntryDeleteView(BaseDeleteView):
    """Vue de suppression pour les présences."""
    model = models.MeetingEntry
    template_name = "core/crud_confirm_delete.html"
    title = "Supprimer une presence"
    success_url = reverse_lazy("meeting_entry_list")
    list_url_name = "meeting_entry_list"
    base_url_name = "meeting_entry"
