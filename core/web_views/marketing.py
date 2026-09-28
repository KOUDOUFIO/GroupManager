"""Pages vitrine : accueil, entreprise, plateforme, devis."""

from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Count, Sum
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format, number_format
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy

from .. import forms as core_forms
from .. import models


def company_page(request):
    """Page d'entreprise pour le branding premium."""
    company_values = [
        {
            "title": _("Clarté opérationnelle"),
            "description": _("Nous aidons les organisations à mieux voir les priorités, les responsabilités et les réalités du terrain."),
        },
        {
            "title": _("Sérénité administrative"),
            "description": _("Chaque action est suivie, chaque décision est traçable et chaque routine est sécurisée."),
        },
        {
            "title": _("Croissance mesurée"),
            "description": _("Le système s'adapte à votre volume sans complexifier les usages ni ralentir les équipes."),
        },
    ]

    roadmap = [
        {"step": "01", "title": _("Analyse"), "description": _("Nous identifions votre structure, vos groupes, vos rôles et vos points de friction.")},
        {"step": "02", "title": _("Configuration"), "description": _("Nous configurons les espaces, les permissions et les workflows adaptés à votre organisation.")},
        {"step": "03", "title": _("Adoption"), "description": _("Les équipes passent en production avec une logique de pilotage claire et un accompagnement précis.")},
        {"step": "04", "title": _("Optimisation"), "description": _("Vous mesurez les performances, ajustez les routines et améliorez la gouvernance au fil du temps.")},
    ]

    faqs = [
        {
            "question": _("Le système convient-il à des structures diverses ?"),
            "answer": _("Oui. Kotiza est conçu pour s’adapter à des entreprises, associations, clubs, institutions ou organisations multisites."),
        },
        {
            "question": _("Peut-on personnaliser le niveau d’accès ?"),
            "answer": _("Oui. Les rôles et permissions sont pensés pour distinguer administrateurs, gestionnaires, responsables et utilisateurs."),
        },
        {
            "question": _("Le déploiement est-il rapide ?"),
            "answer": _("La mise en service est rapide et l’accompagnement permet de démarrer sans friction sur les routines existantes."),
        },
    ]

    context = {"company_values": company_values, "roadmap": roadmap, "faqs": faqs}
    return render(request, "core/enterprise.html", context)


def platform_page(request):
    """Page de la plateforme d'entreprise : modules, roadmap et valeur commerciale."""
    platform_modules = [
        {
            "title": _("CRM & relations"),
            "description": _("Centralisez les contacts, les prospects, les comptes et l’historique des échanges pour un meilleur suivi commercial."),
            "badge": _("Sales"),
            "soon": True,
        },
        {
            "title": _("Devis & factures"),
            "description": _("Créez, suivez et finalisez vos propositions commerciales avec une gestion plus claire de la facturation."),
            "badge": _("Billing"),
            "soon": True,
        },
        {
            "title": _("Tâches & workflow"),
            "description": _("Coordonnez les actions internes, les responsabilités et les priorités à travers des workflows simples et fiables."),
            "badge": _("Ops"),
            "soon": True,
        },
        {
            "title": _("Reporting & KPI"),
            "description": _("Pilotez vos performances grâce à des tableaux de bord, des indicateurs, des tendances et des comparatifs."),
            "badge": _("Analytics"),
        },
        {
            "title": _("Notifications"),
            "description": _("Rappelez les échéances, les réunions et les tâches grâce à des alertes utiles et personnalisables."),
            "badge": _("Alerts"),
        },
        {
            "title": _("API & intégrations"),
            "description": _("Connectez votre système à d’autres outils pour automatiser la gestion de vos données et de vos process."),
            "badge": _("Integrations"),
        },
    ]

    roadmap = [
        {"phase": _("Phase 1"), "title": _("Organisation interne"), "description": _("Groupes, membres, réunions, présences, cotisations et documents centralisés.")},
        {"phase": _("Phase 2"), "title": _("CRM & ventes"), "description": _("Contacts, prospection, pipeline, suivi des opportunités et gestion des comptes.")},
        {"phase": _("Phase 3"), "title": _("Finance & propositions"), "description": _("Devis, factures, suivi des paiements et reporting commercial.")},
        {"phase": _("Phase 4"), "title": _("Automatisation"), "description": _("Notifications, tâches, workflows, intégrations et analytics avancés.")},
    ]

    comparison = [
        [_("Gestion des groupes"), _("Oui"), _("Oui"), _("Oui")],
        [_("CRM client/prospect"), _("Bientôt"), _("Bientôt"), _("Bientôt")],
        [_("Devis / factures"), _("Bientôt"), _("Bientôt"), _("Bientôt")],
        [_("Tableaux de bord"), _("Partiel"), _("Oui"), _("Oui")],
        [_("API / intégrations"), _("Non"), _("Sur demande"), _("Oui")],
    ]

    context = {
        "platform_modules": platform_modules,
        "roadmap": roadmap,
        "comparison": comparison,
    }
    return render(request, "core/platform.html", context)


def _notify_sales(proposal_request):
    """Previent l'equipe commerciale d'une nouvelle demande de devis (repondre = ecrire au prospect)."""
    recipient = settings.KOTIZA_SALES_EMAIL or settings.DEFAULT_FROM_EMAIL
    body = (
        f"Nom : {proposal_request.name}\n"
        f"Email : {proposal_request.email}\n"
        f"Téléphone / WhatsApp : {proposal_request.phone or '-'}\n"
        f"Organisation : {proposal_request.company or '-'}\n"
        f"Type d'organisation : {proposal_request.get_organization_type_display()}\n"
        f"Formule souhaitée : {proposal_request.get_plan_display() or '-'}\n\n"
        f"{proposal_request.message}"
    )
    EmailMessage(
        subject=f"Nouvelle demande de devis - {proposal_request.name}",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
        reply_to=[proposal_request.email],
    ).send(fail_silently=True)


def _published_testimonials():
    """Temoignages publies (avec accord du client), les plus mis en avant d'abord."""
    return list(models.Testimonial.objects.filter(is_published=True, consent_given=True)[:6])


def _price(amount):
    """Prix mensuel lisible : 15 000 FCFA."""
    return f"{number_format(amount, 0, force_grouping=True)} {settings.KOTIZA_CURRENCY}"


def proposal_page(request):
    """Page de proposition commerciale / devis premium."""
    pricing = [
        {
            "key": "starter",
            "name": _("Starter"),
            "price": _price(settings.KOTIZA_PRICE_STARTER),
            "subtitle": _("Par mois"),
            "description": _("Idéal pour petites structures et équipes de démarrage."),
            "features": [
                _("Jusqu’à 3 groupes"),
                _("Suivi des membres et réunions"),
                _("Paiement Mobile Money (T-Money, Flooz)"),
                _("Dashboard actif"),
                _("Exports de base"),
            ],
            "highlighted": False,
        },
        {
            "key": "business",
            "name": _("Business"),
            "price": _price(settings.KOTIZA_PRICE_BUSINESS),
            "subtitle": _("Par mois"),
            "description": _("Pour les organisations qui veulent un pilotage plus profond."),
            "features": [
                _("Gestion multi-groupes"),
                _("Rappels automatiques SMS / WhatsApp"),
                _("Accès rôles et permissions"),
                _("Audit complet"),
                _("Support prioritaire"),
            ],
            "highlighted": True,
        },
        {
            "key": "enterprise",
            "name": _("Enterprise"),
            "price": _("Sur devis"),
            "subtitle": _("Personnalisé"),
            "description": _("Pour les structures multi-sites avec besoin de conformité et d’intégration."),
            "features": [
                _("Configuration sur mesure"),
                _("API et intégrations"),
                _("Support dédié"),
                _("Sécurité avancée"),
            ],
            "highlighted": False,
        },
    ]

    benefits = [
        _("Pilotage centralisé en temps réel"),
        _("Traçabilité des actions et décisions"),
        _("Réduction du travail manuel et des doublons"),
        _("Expérience claire pour les responsables et les équipes"),
    ]

    contact_points = [
        {"label": _("Démarrage"), "value": _("Accompagné")},
        {"label": _("Mise en service"), "value": _("Sans migration lourde")},
        {"label": _("Support"), "value": _("Par email")},
    ]

    submitted = request.GET.get("envoye") == "1"
    if request.method == "POST":
        form = core_forms.ProposalRequestForm(request.POST)
        if form.is_valid():
            # Robot detecte : on fait comme si tout allait bien, sans rien enregistrer.
            if not form.is_spam():
                _notify_sales(form.save())
            return redirect(f"{reverse('proposal_page')}?envoye=1#contact")
    else:
        plan = request.GET.get("formule", "")
        valid_plans = {key for key, _label in models.ProposalRequest.PLAN_CHOICES}
        form = core_forms.ProposalRequestForm(initial={"plan": plan if plan in valid_plans else ""})

    context = {
        "pricing": pricing,
        "benefits": benefits,
        "contact_points": contact_points,
        "form": form,
        "submitted": submitted,
        "trial_days": settings.KOTIZA_TRIAL_DAYS,
        "testimonials": _published_testimonials(),
    }
    return render(request, "core/proposal.html", context)


def _platform_stats():
    """Calcule les KPIs globaux de la plateforme (tous groupes confondus).

    Returns:
        dict: Les statistiques a injecter dans le contexte de la page d'accueil.
    """
    today = timezone.localdate()
    group_count = models.Group.objects.count()
    member_count = models.Member.objects.count()
    meeting_count = models.Meeting.objects.count()
    event_count = models.Event.objects.count()
    confirmed_contributions = models.Contribution.objects.filter(
        payment_status=models.Contribution.STATUS_CONFIRMED
    )
    total_contributions = confirmed_contributions.aggregate(total=Sum("amount"))["total"] or 0
    current_month_contributions = (
        confirmed_contributions.filter(paid_at__year=today.year, paid_at__month=today.month)
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

    return {
        "group_count": group_count,
        "member_count": member_count,
        "meeting_count": meeting_count,
        "event_count": event_count,
        "total_contributions": total_contributions,
        "current_month_contributions": current_month_contributions,
        "attendance_rate": attendance_rate,
        "contribution_month_share": contribution_month_share,
        "event_activity_rate": event_activity_rate,
    }


# Actions rapides du tableau de bord : (libelle, url, icone, couleur, permission).
QUICK_ACTIONS = (
    (_lazy("Ajouter un membre"), "/membres/nouveau/", "id-card", "olive", "core.add_member"),
    (_lazy("Enregistrer une cotisation"), "/cotisations/nouveau/", "wallet", "gold", "core.add_contribution"),
    (_lazy("Planifier une rencontre"), "/rencontres/nouveau/", "calendar", "amber", "core.add_meeting"),
    (_lazy("Créer un événement"), "/evenements/nouveau/", "flag", "orange", "core.add_event"),
    (_lazy("Créer un groupe"), "/groupes/nouveau/", "users", "teal", "core.add_group"),
)


# Series du graphique hebdomadaire : ordre fixe des couleurs (slots 1 a 3 valides).
WEEK_SERIES = (
    ("contributions", _lazy("Cotisations"), "#2a78d6"),
    ("meetings", _lazy("Rencontres"), "#eb6834"),
    ("events", _lazy("Événements"), "#1baf7a"),
)


def _week_activity():
    """Compte l'activite de la semaine en cours, du lundi au dimanche.

    Returns:
        dict: days (7 jours avec segments empiles en % de la plus haute barre),
              series (totaux par type, avec arcs du donut) et total.
    """
    today = timezone.localdate()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    per_day = {
        "contributions": dict(
            models.Contribution.objects.filter(paid_at__range=(monday, sunday))
            .values_list("paid_at")
            .annotate(n=Count("id"))
        ),
        "meetings": dict(
            models.Meeting.objects.filter(scheduled_at__date__range=(monday, sunday))
            .values_list("scheduled_at__date")
            .annotate(n=Count("id"))
        ),
        "events": dict(
            models.Event.objects.filter(starts_at__date__range=(monday, sunday))
            .values_list("starts_at__date")
            .annotate(n=Count("id"))
        ),
    }

    days = []
    for offset in range(7):
        day = monday + timedelta(days=offset)
        counts = [(key, label, color, per_day[key].get(day, 0)) for key, label, color in WEEK_SERIES]
        days.append({
            "date": day,
            "short": date_format(day, "D"),
            "long": date_format(day, "l j F"),
            "is_today": day == today,
            "total": sum(c[3] for c in counts),
            "rows": [{"label": lbl, "color": col, "count": n} for _k, lbl, col, n in counts],
            "segments": [{"key": k, "label": lbl, "color": col, "count": n} for k, lbl, col, n in counts if n],
        })

    peak = max((d["total"] for d in days), default=0)
    for d in days:
        d["height"] = round(d["total"] / peak * 100, 1) if peak else 0
        for seg in d["segments"]:
            seg["share"] = round(seg["count"] / d["total"] * 100, 2)

    total = sum(d["total"] for d in days)
    series, start = [], 0.0
    for key, label, color in WEEK_SERIES:
        count = sum(per_day[key].get(monday + timedelta(days=i), 0) for i in range(7))
        pct = count / total * 100 if total else 0
        # pathLength=100 : un arc = son pourcentage, moins 1 point d'espace entre parts.
        gap = 1 if pct and pct < 100 else 0
        series.append({
            "key": key,
            "label": label,
            "color": color,
            "count": count,
            "pct": round(pct),
            "dash": round(max(pct - gap, 0), 2),
            "offset": round(-start, 2),
        })
        start += pct

    return {
        "week_days": days,
        "week_series": series,
        "week_total": total,
        "week_peak": peak,
        "week_start": monday,
        "week_end": sunday,
    }


def _dashboard(request):
    """Tableau de bord des utilisateurs connectes (modules, actions, KPIs admin)."""
    user = request.user
    # Les totaux (dont la tresorerie) couvrent tous les groupes : on ne les
    # montre qu'aux administrateurs.
    show_platform_stats = user.is_staff
    quick_actions = [
        {"label": label, "url": url, "icon": icon, "tone": tone}
        for label, url, icon, tone, perm in QUICK_ACTIONS
        if user.has_perm(perm)
    ]
    context = {
        "show_platform_stats": show_platform_stats,
        **(_platform_stats() if show_platform_stats else {}),
        **(_week_activity() if show_platform_stats else {}),
        "quick_actions": quick_actions,
    }
    return render(request, "core/dashboard.html", context)


def home(request):
    """Vue de la page d'accueil avec les KPIs principaux.

    Args:
        request: L'objet HttpRequest Django.

    Returns:
        HttpResponse: La page d'accueil avec les statistiques.
    """
    if request.user.is_authenticated:
        return _dashboard(request)

    industry_cards = [
        {
            "tag": _("Associations"),
            "title": _("ONG, clubs et fondations"),
            "description": _("Organisez les adhésions, les rencontres, les cotisations et les décisions de manière transparente pour votre communauté."),
            "points": [_("Membres et responsables"), _("Suivi des présences"), _("Gestion des documents")],
        },
        {
            "tag": _("Education"),
            "title": _("Écoles et centres de formation"),
            "description": _("Pilotez la planification des cours, l'activité des groupes et le suivi des participants avec un tableau de bord clair."),
            "points": [_("Planning des sessions"), _("Évaluations et présence"), _("Suivi des participants")],
        },
        {
            "tag": _("Services"),
            "title": _("PME, cabinets et services"),
            "description": _("Un cadre de gestion opérationnelle pour coordonner les équipes, les projets et les engagements clients dans un seul espace."),
            "points": [_("Equipes et rôles"), _("Suivi des activités"), _("Rapports dynamiques")],
        },
        {
            "tag": _("Sport"),
            "title": _("Clubs sportifs et culturels"),
            "description": _("Gérez les effectifs, les événements, les paiements et les annonces avec une expérience pensée pour les bénévoles et les responsables."),
            "points": [_("Effectifs et postes"), _("Événements publics"), _("Cotisations et remboursements")],
        },
        {
            "tag": _("Santé"),
            "title": _("Structures communautaires"),
            "description": _("Trouvez un équilibre entre la coordination des membres, le suivi des activités et la communication interne dans un environnement structuré."),
            "points": [_("Suivi des missions"), _("Communication interne"), _("Historique des actions")],
        },
        {
            "tag": _("Public"),
            "title": _("Institutions et collectivités"),
            "description": _("Adaptez la plateforme à un environnement plus réglementé avec une gestion fiable des groupes, documents et opérations administratives."),
            "points": [_("Traçabilité des actions"), _("Accès par rôle"), _("Pilotage centralisé")],
        },
    ]

    workflow_steps = [
        {
            "title": _("Centraliser l'organisation"),
            "description": _("Créez vos groupes, organes, membres et postes dans un espace unique, sans friction ni doublons."),
        },
        {
            "title": _("Suivre l'activité"),
            "description": _("Visualisez les réunions, présences, événements et cotisations pour mesurer le rythme réel de l'organisation."),
        },
        {
            "title": _("Automatiser les routines"),
            "description": _("Utilisez des tableaux de bord et les flux de travail pour réduire les tâches manuelles et améliorer la fiabilité."),
        },
        {
            "title": _("Piloter la décision"),
            "description": _("Analysez les performances, les taux de présence et les indicateurs de gestion pour agir avec précision."),
        },
    ]

    feature_highlights = [
        _("Gestion multi-groupes"),
        _("Rôles et permissions"),
        _("Recherche globale"),
        _("Audit trail complet"),
        _("Documents et événements"),
        _("Exports CSV / Excel / PDF"),
        _("Dashboard d'activité"),
    ]

    solution_cards = [
        {
            "title": _("Pilotage d'opérations"),
            "description": _("Suivez les réunions, les effectifs, les obligations et les engagements dans un tableau de bord centralisé."),
            "icon": "01",
        },
        {
            "title": _("Coordination multisite"),
            "description": _("Gérez plusieurs structures, équipes ou territoires sans perdre la trace des responsabilités et des livrables."),
            "icon": "02",
        },
        {
            "title": _("Présence & trésorerie"),
            "description": _("Analysez les taux de présence, les paiements et la santé financière globale de votre organisation."),
            "icon": "03",
        },
    ]

    trust_metrics = [
        {"value": _("2FA"), "label": _("Connexion sécurisée")},
        {"value": _("360°"), "label": _("Vue d'ensemble")},
        {"value": _("100%"), "label": _("Traçabilité")},
    ]

    # Page vitrine des visiteurs : jamais de chiffres de la plateforme.
    context = {
        "show_platform_stats": False,
        "testimonials": _published_testimonials(),
        "industry_cards": industry_cards,
        "workflow_steps": workflow_steps,
        "feature_highlights": feature_highlights,
        "solution_cards": solution_cards,
        "trust_metrics": trust_metrics,
    }
    return render(request, "core/home.html", context)
