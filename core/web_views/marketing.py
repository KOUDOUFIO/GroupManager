"""Pages vitrine : accueil, entreprise, plateforme, devis."""

from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from .. import models


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
