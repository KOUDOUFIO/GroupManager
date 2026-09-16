"""Vues web Django pour l'interface utilisateur.

Ce module définit les vues web pour l'interface utilisateur de GroupManager,
incluant les pages d'accueil, les workspaces, les vues CRUD génériques,
les exports (CSV, Excel, PDF) et les tableaux de bord.
"""

import csv
from io import BytesIO
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView
from openpyxl import Workbook
from reportlab.pdfgen import canvas

from . import forms
from . import models
from .services import GroupService, MemberService, ContributionService, MeetingService


def company_page(request):
    """Page d'entreprise pour le branding premium."""
    company_values = [
        {
            "title": "Clarté opérationnelle",
            "description": "Nous aidons les organisations à mieux voir les priorités, les responsabilités et les réalités du terrain.",
        },
        {
            "title": "Sérénité administrative",
            "description": "Chaque action est suivie, chaque décision est traçable et chaque routine est sécurisée.",
        },
        {
            "title": "Croissance mesurée",
            "description": "Le système s'adapte à votre volume sans complexifier les usages ni ralentir les équipes.",
        },
    ]

    roadmap = [
        {"step": "01", "title": "Analyse", "description": "Nous identifions votre structure, vos groupes, vos rôles et vos points de friction."},
        {"step": "02", "title": "Configuration", "description": "Nous configurons les espaces, les permissions et les workflows adaptés à votre organisation."},
        {"step": "03", "title": "Adoption", "description": "Les équipes passent en production avec une logique de pilotage claire et un accompagnement précis."},
        {"step": "04", "title": "Optimisation", "description": "Vous mesurez les performances, ajustez les routines et améliorez la gouvernance au fil du temps."},
    ]

    faqs = [
        {
            "question": "Le système convient-il à des structures diverses ?",
            "answer": "Oui. GroupManager est conçu pour s’adapter à des entreprises, associations, clubs, institutions ou organisations multisites.",
        },
        {
            "question": "Peut-on personnaliser le niveau d’accès ?",
            "answer": "Oui. Les rôles et permissions sont pensés pour distinguer administrateurs, gestionnaires, responsables et utilisateurs.",
        },
        {
            "question": "Le déploiement est-il rapide ?",
            "answer": "La mise en service est rapide et l’accompagnement permet de démarrer sans friction sur les routines existantes.",
        },
    ]

    context = {"company_values": company_values, "roadmap": roadmap, "faqs": faqs}
    return render(request, "core/enterprise.html", context)


def platform_page(request):
    """Page de la plateforme d'entreprise : modules, roadmap et valeur commerciale."""
    platform_modules = [
        {
            "title": "CRM & relations",
            "description": "Centralisez les contacts, les prospects, les comptes et l’historique des échanges pour un meilleur suivi commercial.",
            "badge": "Sales",
        },
        {
            "title": "Devis & factures",
            "description": "Créez, suivez et finalisez vos propositions commerciales avec une gestion plus claire de la facturation.",
            "badge": "Billing",
        },
        {
            "title": "Tâches & workflow",
            "description": "Coordonnez les actions internes, les responsabilités et les priorités à travers des workflows simples et fiables.",
            "badge": "Ops",
        },
        {
            "title": "Reporting & KPI",
            "description": "Pilotez vos performances grâce à des tableaux de bord, des indicateurs, des tendances et des comparatifs.",
            "badge": "Analytics",
        },
        {
            "title": "Notifications",
            "description": "Rappelez les échéances, les réunions et les tâches grâce à des alertes utiles et personnalisables.",
            "badge": "Alerts",
        },
        {
            "title": "API & intégrations",
            "description": "Connectez votre système à d’autres outils pour automatiser la gestion de vos données et de vos process.",
            "badge": "Integrations",
        },
    ]

    roadmap = [
        {"phase": "Phase 1", "title": "Organisation interne", "description": "Groupes, membres, réunions, présences, cotisations et documents centralisés."},
        {"phase": "Phase 2", "title": "CRM & ventes", "description": "Contacts, prospection, pipeline, suivi des opportunités et gestion des comptes."},
        {"phase": "Phase 3", "title": "Finance & propositions", "description": "Devis, factures, suivi des paiements et reporting commercial."},
        {"phase": "Phase 4", "title": "Automatisation", "description": "Notifications, tâches, workflows, intégrations et analytics avancés."},
    ]

    comparison = [
        ["Gestion des groupes", "Oui", "Oui", "Oui"],
        ["CRM client/prospect", "À venir", "Oui", "Oui"],
        ["Devis / factures", "À venir", "Oui", "Oui"],
        ["Tableaux de bord", "Partiel", "Oui", "Oui"],
        ["API / intégrations", "Restreint", "Oui", "Oui"],
    ]

    context = {
        "platform_modules": platform_modules,
        "roadmap": roadmap,
        "comparison": comparison,
    }
    return render(request, "core/platform.html", context)


def proposal_page(request):
    """Page de proposition commerciale / devis premium."""
    pricing = [
        {
            "name": "Starter",
            "price": "€49",
            "subtitle": "Par mois",
            "description": "Idéal pour petites structures et équipes de démarrage.",
            "features": [
                "Jusqu’à 3 groupes",
                "Suivi des membres et réunions",
                "Dashboard actif",
                "Exports de base",
            ],
            "highlighted": False,
        },
        {
            "name": "Business",
            "price": "€99",
            "subtitle": "Par mois",
            "description": "Pour les organisations qui veulent un pilotage plus profond.",
            "features": [
                "Gestion multi-groupes",
                "Accès rôles et permissions",
                "Audit complet",
                "Support prioritaire",
            ],
            "highlighted": True,
        },
        {
            "name": "Enterprise",
            "price": "Sur devis",
            "subtitle": "Personnalisé",
            "description": "Pour les structures multi-sites avec besoin de conformité et d’intégration.",
            "features": [
                "Configuration sur mesure",
                "API et intégrations",
                "Support dédié",
                "Sécurité avancée",
            ],
            "highlighted": False,
        },
    ]

    benefits = [
        "Pilotage centralisé en temps réel",
        "Traçabilité des actions et décisions",
        "Réduction du travail manuel et des doublons",
        "Expérience claire pour les responsables et les équipes",
    ]

    contact_points = [
        {"label": "Déploiement", "value": "7 jours"},
        {"label": "Mise en service", "value": "Sans migration lourde"},
        {"label": "Support", "value": "Réponse sous 24h"},
    ]

    context = {
        "pricing": pricing,
        "benefits": benefits,
        "contact_points": contact_points,
    }
    return render(request, "core/proposal.html", context)


def home(request):
    """Vue de la page d'accueil avec les KPIs principaux.

    Args:
        request: L'objet HttpRequest Django.

    Returns:
        HttpResponse: La page d'accueil avec les statistiques.
    """
    today = timezone.localdate()
    group_count = models.Group.objects.count()
    member_count = models.Member.objects.count()
    meeting_count = models.Meeting.objects.count()
    event_count = models.Event.objects.count()
    total_contributions = models.Contribution.objects.aggregate(total=Sum("amount"))["total"] or 0
    current_month_contributions = (
        models.Contribution.objects.filter(paid_at__year=today.year, paid_at__month=today.month)
        .aggregate(total=Sum("amount"))["total"]
        or 0
    )
    entries_qs = models.MeetingEntry.objects.all()
    total_entries = entries_qs.count()
    attended_entries = entries_qs.filter(
        status__in=[
            models.MeetingEntry.STATUS_PRESENT,
            models.MeetingEntry.STATUS_LATE,
            models.MeetingEntry.STATUS_PERMISSION,
        ]
    ).count()
    attendance_rate = round((attended_entries / total_entries) * 100, 1) if total_entries else 0
    contribution_month_share = round((current_month_contributions / total_contributions) * 100, 1) if total_contributions else 0
    event_activity_rate = round((event_count / meeting_count) * 100, 1) if meeting_count else 0
    event_activity_rate = min(event_activity_rate, 100)

    industry_cards = [
        {
            "tag": "Associations",
            "title": "ONG, clubs et fondations",
            "description": "Organisez les adhésions, les rencontres, les cotisations et les décisions de manière transparente pour votre communauté.",
            "points": ["Membres et responsables", "Suivi des présences", "Gestion des documents"],
        },
        {
            "tag": "Education",
            "title": "Écoles et centres de formation",
            "description": "Pilotez la planification des cours, l'activité des groupes et le suivi des participants avec un tableau de bord clair.",
            "points": ["Planning des sessions", "Évaluations et présence", "Suivi des participants"],
        },
        {
            "tag": "Services",
            "title": "PME, cabinets et services",
            "description": "Un cadre de gestion opérationnelle pour coordonner les équipes, les projets et les engagements clients dans un seul espace.",
            "points": ["Equipes et rôles", "Suivi des activités", "Rapports dynamiques"],
        },
        {
            "tag": "Sport",
            "title": "Clubs sportifs et culturels",
            "description": "Gérez les effectifs, les événements, les paiements et les annonces avec une expérience pensée pour les bénévoles et les responsables.",
            "points": ["Effectifs et postes", "Événements publics", "Cotisations et remboursements"],
        },
        {
            "tag": "Santé",
            "title": "Structures communautaires",
            "description": "Trouvez un équilibre entre la coordination des membres, le suivi des activités et la communication interne dans un environnement structuré.",
            "points": ["Suivi des missions", "Communication interne", "Historique des actions"],
        },
        {
            "tag": "Public",
            "title": "Institutions et collectivités",
            "description": "Adaptez la plateforme à un environnement plus réglementé avec une gestion fiable des groupes, documents et opérations administratives.",
            "points": ["Traçabilité des actions", "Accès par rôle", "Pilotage centralisé"],
        },
    ]

    workflow_steps = [
        {
            "title": "Centraliser l'organisation",
            "description": "Créez vos groupes, organes, membres et postes dans un espace unique, sans friction ni doublons.",
        },
        {
            "title": "Suivre l'activité",
            "description": "Visualisez les réunions, présences, événements et cotisations pour mesurer le rythme réel de l'organisation.",
        },
        {
            "title": "Automatiser les routines",
            "description": "Utilisez des tableaux de bord et les flux de travail pour réduire les tâches manuelles et améliorer la fiabilité.",
        },
        {
            "title": "Piloter la décision",
            "description": "Analysez les performances, les taux de présence et les indicateurs de gestion pour agir avec précision.",
        },
    ]

    feature_highlights = [
        "Gestion multi-groupes",
        "Rôles et permissions",
        "Recherche globale",
        "Audit trail complet",
        "Documents et événements",
        "Exports CSV / Excel / PDF",
        "Dashboard d'activité",
        "API de données",
    ]

    solution_cards = [
        {
            "title": "Pilotage d'opérations",
            "description": "Suivez les réunions, les effectifs, les obligations et les engagements dans un tableau de bord centralisé.",
            "icon": "01",
        },
        {
            "title": "Coordination multisite",
            "description": "Gérez plusieurs structures, équipes ou territoires sans perdre la trace des responsabilités et des livrables.",
            "icon": "02",
        },
        {
            "title": "Présence & trésorerie",
            "description": "Analysez les taux de présence, les paiements et la santé financière globale de votre organisation.",
            "icon": "03",
        },
    ]

    testimonials = [
        {
            "quote": "La plateforme a transformé notre façon de gérer les groupes, les événements et les cotisations sans dépendre de plusieurs outils. ",
            "name": "Amina K.",
            "role": "Directrice d'association",
        },
        {
            "quote": "Nous avons gagné en visibilité opérationnelle et nos équipes adoptent beaucoup plus facilement les routines de suivi.",
            "name": "Thomas R.",
            "role": "Responsable administratif",
        },
        {
            "quote": "L'ergonomie est claire, la traçabilité est solide et le pilotage est devenu plus rapide pour toute l'entreprise.",
            "name": "Sofia M.",
            "role": "Chef de projet",
        },
    ]

    trust_metrics = [
        {"value": "24/7", "label": "Suivi opérationnel"},
        {"value": "360°", "label": "Vue d'ensemble"},
        {"value": "100%", "label": "Traçabilité"},
    ]

    context = {
        "group_count": group_count,
        "member_count": member_count,
        "meeting_count": meeting_count,
        "event_count": event_count,
        "total_contributions": total_contributions,
        "current_month_contributions": current_month_contributions,
        "attendance_rate": attendance_rate,
        "contribution_month_share": contribution_month_share,
        "event_activity_rate": event_activity_rate,
        "industry_cards": industry_cards,
        "workflow_steps": workflow_steps,
        "feature_highlights": feature_highlights,
        "solution_cards": solution_cards,
        "testimonials": testimonials,
        "trust_metrics": trust_metrics,
    }
    return render(request, "core/home.html", context)


class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin restreignant l'accès aux membres du staff."""
    raise_exception = True

    def test_func(self):
        """Vérifie que l'utilisateur est membre du staff."""
        return self.request.user.is_staff


class AdminWorkspaceView(LoginRequiredMixin, StaffRequiredMixin, TemplateView):
    """Vue du workspace administrateur avec statistiques globales."""
    template_name = "core/admin_workspace.html"

    def get_context_data(self, **kwargs):
        """Fournit le contexte avec les statistiques pour l'admin."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "group_count": models.Group.objects.count(),
                "member_count": models.Member.objects.count(),
                "meeting_count": models.Meeting.objects.count(),
                "contribution_count": models.Contribution.objects.count(),
                "audit_count": models.AuditLog.objects.count(),
                "recent_audits": models.AuditLog.objects.select_related("actor").order_by("-created_at")[:10],
            }
        )
        return context


class ManagerWorkspaceView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Vue du workspace gestionnaire avec statistiques opérationnelles."""
    template_name = "core/manager_workspace.html"
    raise_exception = True

    def test_func(self):
        """Vérifie que l'utilisateur est staff ou gestionnaire."""
        user = self.request.user
        return user.is_staff or user.groups.filter(name="Gestionnaire").exists()

    def get_context_data(self, **kwargs):
        """Fournit le contexte avec les données opérationnelles."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "group_count": models.Group.objects.count(),
                "member_count": models.Member.objects.count(),
                "meeting_count": models.Meeting.objects.count(),
                "event_count": models.Event.objects.count(),
                "latest_meetings": models.Meeting.objects.select_related("group").order_by("-scheduled_at")[:8],
                "latest_contributions": models.Contribution.objects.select_related("member", "group").order_by("-paid_at")[:8],
            }
        )
        return context


class GlobalSearchView(LoginRequiredMixin, TemplateView):
    """Vue de recherche globale sur toutes les entités."""
    template_name = "core/global_search.html"

    def get_context_data(self, **kwargs):
        """Fournit le contexte avec les résultats de recherche."""
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()
        context["query"] = query
        if not query:
            context["has_query"] = False
            return context

        context["has_query"] = True
        context["groups"] = models.Group.objects.filter(Q(name__icontains=query) | Q(description__icontains=query))[:6]
        context["members"] = models.Member.objects.filter(
            Q(full_name__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query)
        )[:6]
        context["meetings"] = models.Meeting.objects.select_related("group").filter(
            Q(title__icontains=query) | Q(group__name__icontains=query)
        )[:6]
        context["contributions"] = models.Contribution.objects.select_related("member", "group").filter(
            Q(member__full_name__icontains=query) | Q(group__name__icontains=query) | Q(contribution_type__icontains=query)
        )[:6]
        context["events"] = models.Event.objects.select_related("group").filter(
            Q(title__icontains=query) | Q(location__icontains=query) | Q(group__name__icontains=query)
        )[:6]
        return context


class GroupDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Vue du tableau de bord détaillé pour un groupe (Groupe 360)."""
    template_name = "core/group_dashboard.html"
    raise_exception = True

    def get_permission_required(self):
        """Retourne la permission requise pour voir un groupe."""
        return ("core.view_group",)

    def get_context_data(self, **kwargs):
        """Fournit le contexte avec les statistiques détaillées du groupe."""
        context = super().get_context_data(**kwargs)
        group = get_object_or_404(models.Group.objects.select_related("responsible"), pk=self.kwargs["pk"])

        total_contributions = group.contributions.aggregate(total=Sum("amount"))["total"] or 0
        meeting_entries = models.MeetingEntry.objects.filter(meeting__group=group)
        total_entries = meeting_entries.count()
        attended_entries = meeting_entries.filter(
            status__in=[
                models.MeetingEntry.STATUS_PRESENT,
                models.MeetingEntry.STATUS_LATE,
                models.MeetingEntry.STATUS_PERMISSION,
            ]
        ).count()
        attendance_rate = round((attended_entries / total_entries) * 100, 1) if total_entries else 0

        context.update(
            {
                "group": group,
                "member_count": group.members.count(),
                "meeting_count": group.meetings.count(),
                "event_count": group.events.count(),
                "position_count": group.positions.count(),
                "total_contributions": total_contributions,
                "attendance_rate": attendance_rate,
                "recent_contributions": group.contributions.select_related("member").order_by("-paid_at")[:8],
                "upcoming_events": group.events.filter(starts_at__gte=timezone.now()).order_by("starts_at")[:8],
                "recent_meetings": group.meetings.order_by("-scheduled_at")[:8],
            }
        )
        return context


class CrudContextMixin:
    """Mixin fournissant le contexte commun pour les vues CRUD."""
    title = ""
    create_url_name = ""
    list_url_name = ""
    base_url_name = ""
    list_columns = []
    show_actions = True

    def get_context_data(self, **kwargs):
        """Fournit le contexte avec les URLs et configuration CRUD."""
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        context["base_url_name"] = self.base_url_name
        if self.list_columns:
            context["list_columns"] = self.list_columns
        if self.create_url_name:
            context["create_url"] = reverse_lazy(self.create_url_name)
        if self.list_url_name:
            context["list_url"] = reverse_lazy(self.list_url_name)
        context["query"] = self.request.GET.get("q", "")
        context["show_actions"] = self.show_actions
        return context


class ModelPermissionMixin(PermissionRequiredMixin):
    """Mixin pour les permissions basées sur l'action et le modèle."""
    permission_action = "view"
    raise_exception = True

    def get_permission_required(self):
        """Génère la permission Django basée sur l'action et le modèle."""
        opts = self.model._meta
        return (f"{opts.app_label}.{self.permission_action}_{opts.model_name}",)


class SearchableListView(LoginRequiredMixin, ModelPermissionMixin, CrudContextMixin, ListView):
    """ListView générique avec recherche et pagination."""
    permission_action = "view"
    paginate_by = 10
    search_fields = []
    default_ordering = ("-pk",)
    select_related_fields = ()
    prefetch_related_fields = ()

    def get_queryset(self):
        """Filtre le queryset selon la recherche et l'ordre."""
        queryset = super().get_queryset()
        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)
        if self.prefetch_related_fields:
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)
        query = self.request.GET.get("q", "").strip()
        if query and self.search_fields:
            q_object = Q()
            for field in self.search_fields:
                q_object |= Q(**{f"{field}__icontains": query})
            queryset = queryset.filter(q_object).distinct()
        if not queryset.ordered:
            queryset = queryset.order_by(*self.default_ordering)
        return queryset


class BaseCreateView(LoginRequiredMixin, ModelPermissionMixin, CrudContextMixin, CreateView):
    """Vue de création de base avec permissions."""
    permission_action = "add"


class BaseUpdateView(LoginRequiredMixin, ModelPermissionMixin, CrudContextMixin, UpdateView):
    """Vue de modification de base avec permissions."""
    permission_action = "change"


class BaseDeleteView(LoginRequiredMixin, ModelPermissionMixin, CrudContextMixin, DeleteView):
    """Vue de suppression de base avec permissions."""
    permission_action = "delete"


class GroupListView(SearchableListView):
    """ListView pour les groupes."""
    model = models.Group
    template_name = "core/crud_list.html"
    title = "Groupes"
    create_url_name = "group_create"
    base_url_name = "group"
    list_columns = [
        {"label": "Nom", "accessor": "name"},
        {"label": "Responsable", "accessor": "responsible.get_username"},
        {"label": "Creation", "accessor": "created_at"},
    ]
    search_fields = ["name", "description"]
    select_related_fields = ("responsible",)


class GroupCreateView(BaseCreateView):
    """Vue de création pour les groupes."""
    model = models.Group
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Ajouter un groupe"
    success_url = reverse_lazy("group_list")
    list_url_name = "group_list"
    base_url_name = "group"


class GroupUpdateView(BaseUpdateView):
    """Vue de modification pour les groupes."""
    model = models.Group
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Modifier un groupe"
    success_url = reverse_lazy("group_list")
    list_url_name = "group_list"
    base_url_name = "group"


class GroupDeleteView(BaseDeleteView):
    """Vue de suppression pour les groupes."""
    model = models.Group
    template_name = "core/crud_confirm_delete.html"
    title = "Supprimer un groupe"
    success_url = reverse_lazy("group_list")
    list_url_name = "group_list"
    base_url_name = "group"


class OrganListView(SearchableListView):
    """ListView pour les organes."""
    model = models.Organ
    template_name = "core/crud_list.html"
    title = "Organes"
    create_url_name = "organ_create"
    base_url_name = "organ"
    list_columns = [
        {"label": "Nom", "accessor": "name"},
        {"label": "Groupe", "accessor": "group.name"},
        {"label": "Description", "accessor": "description"},
    ]
    search_fields = ["name", "description", "group__name"]
    select_related_fields = ("group",)


class OrganCreateView(BaseCreateView):
    """Vue de création pour les organes."""
    model = models.Organ
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Ajouter un organe"
    success_url = reverse_lazy("organ_list")
    list_url_name = "organ_list"
    base_url_name = "organ"


class OrganUpdateView(BaseUpdateView):
    """Vue de modification pour les organes."""
    model = models.Organ
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Modifier un organe"
    success_url = reverse_lazy("organ_list")
    list_url_name = "organ_list"
    base_url_name = "organ"


class OrganDeleteView(BaseDeleteView):
    """Vue de suppression pour les organes."""
    model = models.Organ
    template_name = "core/crud_confirm_delete.html"
    title = "Supprimer un organe"
    success_url = reverse_lazy("organ_list")
    list_url_name = "organ_list"
    base_url_name = "organ"


class MemberListView(SearchableListView):
    """ListView pour les membres."""
    model = models.Member
    template_name = "core/crud_list.html"
    title = "Membres"
    create_url_name = "member_create"
    base_url_name = "member"
    list_columns = [
        {"label": "Nom complet", "accessor": "full_name"},
        {"label": "Email", "accessor": "email"},
        {"label": "Telephone", "accessor": "phone"},
    ]
    search_fields = ["full_name", "email", "phone", "groups__name"]
    prefetch_related_fields = ("groups",)


class MemberCreateView(BaseCreateView):
    """Vue de création pour les membres."""
    model = models.Member
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Ajouter un membre"
    success_url = reverse_lazy("member_list")
    list_url_name = "member_list"
    base_url_name = "member"


class MemberUpdateView(BaseUpdateView):
    """Vue de modification pour les membres."""
    model = models.Member
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Modifier un membre"
    success_url = reverse_lazy("member_list")
    list_url_name = "member_list"
    base_url_name = "member"


class MemberDeleteView(BaseDeleteView):
    """Vue de suppression pour les membres."""
    model = models.Member
    template_name = "core/crud_confirm_delete.html"
    title = "Supprimer un membre"
    success_url = reverse_lazy("member_list")
    list_url_name = "member_list"
    base_url_name = "member"


class PositionListView(SearchableListView):
    """ListView pour les postes."""
    model = models.Position
    template_name = "core/crud_list.html"
    title = "Postes"
    create_url_name = "position_create"
    base_url_name = "position"
    list_columns = [
        {"label": "Nom", "accessor": "name"},
        {"label": "Groupe", "accessor": "group.name"},
        {"label": "Organe", "accessor": "organ.name"},
        {"label": "Membre", "accessor": "member.full_name"},
    ]
    search_fields = ["name", "description", "group__name", "organ__name", "member__full_name"]
    select_related_fields = ("group", "organ", "member")


class PositionCreateView(BaseCreateView):
    """Vue de création pour les postes."""
    model = models.Position
    form_class = forms.PositionForm
    template_name = "core/crud_form.html"
    title = "Ajouter un poste"
    success_url = reverse_lazy("position_list")
    list_url_name = "position_list"
    base_url_name = "position"


class PositionUpdateView(BaseUpdateView):
    """Vue de modification pour les postes."""
    model = models.Position
    form_class = forms.PositionForm
    template_name = "core/crud_form.html"
    title = "Modifier un poste"
    success_url = reverse_lazy("position_list")
    list_url_name = "position_list"
    base_url_name = "position"


class PositionDeleteView(BaseDeleteView):
    """Vue de suppression pour les postes."""
    model = models.Position
    template_name = "core/crud_confirm_delete.html"
    title = "Supprimer un poste"
    success_url = reverse_lazy("position_list")
    list_url_name = "position_list"
    base_url_name = "position"


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


class ContributionListView(SearchableListView):
    """ListView pour les cotisations avec filtres avancés."""
    model = models.Contribution
    template_name = "core/crud_list.html"
    title = "Cotisations"
    create_url_name = "contribution_create"
    base_url_name = "contribution"
    list_columns = [
        {"label": "Membre", "accessor": "member.full_name"},
        {"label": "Groupe", "accessor": "group.name"},
        {"label": "Type", "accessor": "get_contribution_type_display"},
        {"label": "Montant", "accessor": "amount"},
        {"label": "Date", "accessor": "paid_at"},
    ]
    search_fields = ["member__full_name", "group__name", "contribution_type"]
    select_related_fields = ("member", "group")

    def get_queryset(self):
        """Filtre le queryset selon groupe et dates."""
        queryset = super().get_queryset()
        group_id = self.request.GET.get("group")
        start_date = parse_date(self.request.GET.get("start_date", ""))
        end_date = parse_date(self.request.GET.get("end_date", ""))
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        if start_date:
            queryset = queryset.filter(paid_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(paid_at__lte=end_date)
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


class ContributionCreateView(BaseCreateView):
    """Vue de création pour les cotisations."""
    model = models.Contribution
    form_class = forms.ContributionForm
    template_name = "core/crud_form.html"
    title = "Ajouter une cotisation"
    success_url = reverse_lazy("contribution_list")
    list_url_name = "contribution_list"
    base_url_name = "contribution"


class ContributionUpdateView(BaseUpdateView):
    """Vue de modification pour les cotisations."""
    model = models.Contribution
    form_class = forms.ContributionForm
    template_name = "core/crud_form.html"
    title = "Modifier une cotisation"
    success_url = reverse_lazy("contribution_list")
    list_url_name = "contribution_list"
    base_url_name = "contribution"


class ContributionDeleteView(BaseDeleteView):
    """Vue de suppression pour les cotisations."""
    model = models.Contribution
    template_name = "core/crud_confirm_delete.html"
    title = "Supprimer une cotisation"
    success_url = reverse_lazy("contribution_list")
    list_url_name = "contribution_list"
    base_url_name = "contribution"


class DocumentListView(SearchableListView):
    """ListView pour les documents."""
    model = models.Document
    template_name = "core/crud_list.html"
    title = "Documents"
    create_url_name = "document_create"
    base_url_name = "document"
    list_columns = [
        {"label": "Titre", "accessor": "title"},
        {"label": "Type", "accessor": "document_type"},
        {"label": "Groupe", "accessor": "group.name"},
        {"label": "Upload", "accessor": "uploaded_at"},
    ]
    search_fields = ["title", "document_type", "group__name"]
    select_related_fields = ("group",)


class DocumentCreateView(BaseCreateView):
    """Vue de création pour les documents."""
    model = models.Document
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Ajouter un document"
    success_url = reverse_lazy("document_list")
    list_url_name = "document_list"
    base_url_name = "document"


class DocumentUpdateView(BaseUpdateView):
    """Vue de modification pour les documents."""
    model = models.Document
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Modifier un document"
    success_url = reverse_lazy("document_list")
    list_url_name = "document_list"
    base_url_name = "document"


class DocumentDeleteView(BaseDeleteView):
    """Vue de suppression pour les documents."""
    model = models.Document
    template_name = "core/crud_confirm_delete.html"
    title = "Supprimer un document"
    success_url = reverse_lazy("document_list")
    list_url_name = "document_list"
    base_url_name = "document"


class EventListView(SearchableListView):
    """ListView pour les événements."""
    model = models.Event
    template_name = "core/crud_list.html"
    title = "Evenements"
    create_url_name = "event_create"
    base_url_name = "event"
    list_columns = [
        {"label": "Titre", "accessor": "title"},
        {"label": "Type", "accessor": "event_type"},
        {"label": "Date", "accessor": "starts_at"},
        {"label": "Lieu", "accessor": "location"},
    ]
    search_fields = ["title", "event_type", "group__name", "location"]
    select_related_fields = ("group",)


class EventCreateView(BaseCreateView):
    """Vue de création pour les événements."""
    model = models.Event
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Ajouter un evenement"
    success_url = reverse_lazy("event_list")
    list_url_name = "event_list"
    base_url_name = "event"


class EventUpdateView(BaseUpdateView):
    """Vue de modification pour les événements."""
    model = models.Event
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Modifier un evenement"
    success_url = reverse_lazy("event_list")
    list_url_name = "event_list"
    base_url_name = "event"


class EventDeleteView(BaseDeleteView):
    """Vue de suppression pour les événements."""
    model = models.Event
    template_name = "core/crud_confirm_delete.html"
    title = "Supprimer un evenement"
    success_url = reverse_lazy("event_list")
    list_url_name = "event_list"
    base_url_name = "event"


class AuditLogListView(SearchableListView):
    """ListView pour les logs d'audit (lecture seule)."""
    model = models.AuditLog
    template_name = "core/crud_list.html"
    title = "Historique d'audit"
    base_url_name = "audit_log"
    list_columns = [
        {"label": "Date", "accessor": "created_at"},
        {"label": "Utilisateur", "accessor": "actor.get_username"},
        {"label": "Action", "accessor": "get_action_display"},
        {"label": "Modele", "accessor": "model_name"},
        {"label": "Objet", "accessor": "object_repr"},
        {"label": "Route", "accessor": "path"},
    ]
    search_fields = ["model_name", "object_pk", "object_repr", "actor__username", "path"]
    select_related_fields = ("actor",)
    default_ordering = ("-created_at",)
    show_actions = False


def _pdf_response(filename):
    """Crée une réponse HTTP pour un fichier PDF.

    Args:
        filename: Le nom du fichier à télécharger.

    Returns:
        HttpResponse: La réponse HTTP configurée pour PDF.
    """
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response


def _xlsx_response(filename):
    """Crée une réponse HTTP pour un fichier Excel XLSX.

    Args:
        filename: Le nom du fichier à télécharger.

    Returns:
        HttpResponse: La réponse HTTP configurée pour XLSX.
    """
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response


def _safe_spreadsheet_cell(value):
    """Échappe les valeurs dangereuses pour les cellules de feuille de calcul.

    Args:
        value: La valeur à échapper.

    Returns:
        La valeur échappée ou inchangée.
    """
    if isinstance(value, str) and value and value[0] in ("=", "+", "-", "@"):
        return f"'{value}"
    return value


def _parse_filters(request):
    """Parse les filtres de date et groupe depuis la requête.

    Args:
        request: L'objet HttpRequest Django.

    Returns:
        tuple: (group_id, start_date, end_date)
    """
    return (
        request.GET.get("group"),
        parse_date(request.GET.get("start_date", "")),
        parse_date(request.GET.get("end_date", "")),
    )


@login_required
@permission_required("core.view_contribution", raise_exception=True)
def export_contributions_csv(request):
    """Exporte les cotisations au format CSV.

    Args:
        request: L'objet HttpRequest Django.

    Returns:
        HttpResponse: Le fichier CSV des cotisations.
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=cotisations.csv"
    writer = csv.writer(response)
    writer.writerow(["Membre", "Groupe", "Type", "Montant", "Date"])
    queryset = models.Contribution.objects.select_related("member", "group").order_by("-paid_at")
    group_id, start_date, end_date = _parse_filters(request)
    if group_id:
        queryset = queryset.filter(group_id=group_id)
    if start_date:
        queryset = queryset.filter(paid_at__gte=start_date)
    if end_date:
        queryset = queryset.filter(paid_at__lte=end_date)
    for item in queryset:
        writer.writerow(
            [
                _safe_spreadsheet_cell(item.member.full_name),
                _safe_spreadsheet_cell(item.group.name),
                _safe_spreadsheet_cell(item.get_contribution_type_display()),
                item.amount,
                item.paid_at,
            ]
        )
    return response


@login_required
@permission_required("core.view_contribution", raise_exception=True)
def export_contributions_xlsx(request):
    """Exporte les cotisations au format Excel XLSX.

    Args:
        request: L'objet HttpRequest Django.

    Returns:
        HttpResponse: Le fichier XLSX des cotisations.
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Cotisations"
    sheet.append(["Membre", "Groupe", "Type", "Montant", "Date"])
    queryset = models.Contribution.objects.select_related("member", "group").order_by("-paid_at")
    group_id, start_date, end_date = _parse_filters(request)
    if group_id:
        queryset = queryset.filter(group_id=group_id)
    if start_date:
        queryset = queryset.filter(paid_at__gte=start_date)
    if end_date:
        queryset = queryset.filter(paid_at__lte=end_date)
    for item in queryset:
        sheet.append(
            [
                _safe_spreadsheet_cell(item.member.full_name),
                _safe_spreadsheet_cell(item.group.name),
                _safe_spreadsheet_cell(item.get_contribution_type_display()),
                float(item.amount),
                item.paid_at.strftime("%Y-%m-%d"),
            ]
        )
    response = _xlsx_response("cotisations.xlsx")
    output = BytesIO()
    workbook.save(output)
    response.write(output.getvalue())
    return response


@login_required
@permission_required("core.view_contribution", raise_exception=True)
def export_contributions_pdf(request):
    """Exporte les cotisations au format PDF.

    Args:
        request: L'objet HttpRequest Django.

    Returns:
        HttpResponse: Le fichier PDF des cotisations.
    """
    response = _pdf_response("cotisations.pdf")
    pdf = canvas.Canvas(response)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, 800, "Rapport des cotisations")
    pdf.setFont("Helvetica", 10)
    y = 770
    pdf.drawString(40, y, "Membre")
    pdf.drawString(200, y, "Groupe")
    pdf.drawString(320, y, "Type")
    pdf.drawString(420, y, "Montant")
    pdf.drawString(490, y, "Date")
    y -= 20
    queryset = models.Contribution.objects.select_related("member", "group").order_by("-paid_at")
    group_id, start_date, end_date = _parse_filters(request)
    if group_id:
        queryset = queryset.filter(group_id=group_id)
    if start_date:
        queryset = queryset.filter(paid_at__gte=start_date)
    if end_date:
        queryset = queryset.filter(paid_at__lte=end_date)
    for item in queryset:
        if y < 60:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = 800
        pdf.drawString(40, y, item.member.full_name)
        pdf.drawString(200, y, item.group.name)
        pdf.drawString(320, y, item.get_contribution_type_display())
        pdf.drawRightString(460, y, f"{item.amount}")
        pdf.drawString(480, y, item.paid_at.strftime("%Y-%m-%d"))
        y -= 18
    pdf.showPage()
    pdf.save()
    return response


@login_required
@permission_required("core.view_meetingentry", raise_exception=True)
def export_meeting_entries_csv(request):
    """Exporte les présences aux rencontres au format CSV.

    Args:
        request: L'objet HttpRequest Django.

    Returns:
        HttpResponse: Le fichier CSV des présences.
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=presences.csv"
    writer = csv.writer(response)
    writer.writerow(["Rencontre", "Groupe", "Membre", "Statut", "Motif", "Date"])
    queryset = models.MeetingEntry.objects.select_related("meeting", "meeting__group", "member").order_by(
        "-recorded_at"
    )
    group_id, start_date, end_date = _parse_filters(request)
    if group_id:
        queryset = queryset.filter(meeting__group_id=group_id)
    if start_date:
        queryset = queryset.filter(recorded_at__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(recorded_at__date__lte=end_date)
    for item in queryset:
        writer.writerow(
            [
                _safe_spreadsheet_cell(item.meeting.title or "Rencontre"),
                _safe_spreadsheet_cell(item.meeting.group.name),
                _safe_spreadsheet_cell(item.member.full_name),
                _safe_spreadsheet_cell(item.get_status_display()),
                _safe_spreadsheet_cell(item.reason),
                item.recorded_at.date(),
            ]
        )
    return response


@login_required
@permission_required("core.view_meetingentry", raise_exception=True)
def export_meeting_entries_xlsx(request):
    """Exporte les présences aux rencontres au format Excel XLSX.

    Args:
        request: L'objet HttpRequest Django.

    Returns:
        HttpResponse: Le fichier XLSX des présences.
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Presences"
    sheet.append(["Rencontre", "Groupe", "Membre", "Statut", "Motif", "Date"])
    queryset = models.MeetingEntry.objects.select_related("meeting", "meeting__group", "member").order_by(
        "-recorded_at"
    )
    group_id, start_date, end_date = _parse_filters(request)
    if group_id:
        queryset = queryset.filter(meeting__group_id=group_id)
    if start_date:
        queryset = queryset.filter(recorded_at__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(recorded_at__date__lte=end_date)
    for item in queryset:
        sheet.append(
            [
                _safe_spreadsheet_cell(item.meeting.title or "Rencontre"),
                _safe_spreadsheet_cell(item.meeting.group.name),
                _safe_spreadsheet_cell(item.member.full_name),
                _safe_spreadsheet_cell(item.get_status_display()),
                _safe_spreadsheet_cell(item.reason),
                item.recorded_at.strftime("%Y-%m-%d"),
            ]
        )
    response = _xlsx_response("presences.xlsx")
    output = BytesIO()
    workbook.save(output)
    response.write(output.getvalue())
    return response


@login_required
@permission_required("core.view_meetingentry", raise_exception=True)
def export_meeting_entries_pdf(request):
    """Exporte les présences aux rencontres au format PDF.

    Args:
        request: L'objet HttpRequest Django.

    Returns:
        HttpResponse: Le fichier PDF des présences.
    """
    response = _pdf_response("presences.pdf")
    pdf = canvas.Canvas(response)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, 800, "Rapport des presences")
    pdf.setFont("Helvetica", 10)
    y = 770
    pdf.drawString(40, y, "Rencontre")
    pdf.drawString(170, y, "Groupe")
    pdf.drawString(280, y, "Membre")
    pdf.drawString(410, y, "Statut")
    pdf.drawString(470, y, "Date")
    y -= 20
    queryset = models.MeetingEntry.objects.select_related("meeting", "meeting__group", "member").order_by(
        "-recorded_at"
    )
    group_id, start_date, end_date = _parse_filters(request)
    if group_id:
        queryset = queryset.filter(meeting__group_id=group_id)
    if start_date:
        queryset = queryset.filter(recorded_at__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(recorded_at__date__lte=end_date)
    for item in queryset:
        if y < 60:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = 800
        pdf.drawString(40, y, item.meeting.title or "Rencontre")
        pdf.drawString(170, y, item.meeting.group.name)
        pdf.drawString(280, y, item.member.full_name)
        pdf.drawString(410, y, item.get_status_display())
        pdf.drawString(470, y, item.recorded_at.strftime("%Y-%m-%d"))
        y -= 18
    pdf.showPage()
    pdf.save()
    return response
