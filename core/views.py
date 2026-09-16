"""ViewSets Django REST Framework pour l'API REST.

Ce module définit les ViewSets pour tous les modèles de l'application,
avec intégration du système d'audit pour tracer les actions des utilisateurs.
"""

from django.db.models import Sum
from django.utils import timezone
from rest_framework import filters, permissions, viewsets
from django.db import connection
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from . import models
from . import serializers
from .audit import set_actor_context
from .permissions import StrictDjangoModelPermissions


class AuditActorViewSetMixin:
    """Mixin pour capturer le contexte d'acteur dans les ViewSets.

    Ce mixin définit automatiquement le contexte d'acteur (utilisateur,
    chemin, adresse IP) avant chaque action de création, modification
    ou suppression dans l'API REST.
    """

    def _set_actor(self):
        """Définit le contexte d'acteur pour l'audit."""
        user = self.request.user if getattr(self.request, "user", None) and self.request.user.is_authenticated else None
        set_actor_context(
            user=user,
            path=getattr(self.request, "path", ""),
            ip_address=self.request.META.get("REMOTE_ADDR", ""),
        )

    def perform_create(self, serializer):
        """Capture l'acteur avant création."""
        self._set_actor()
        return super().perform_create(serializer)

    def perform_update(self, serializer):
        """Capture l'acteur avant modification."""
        self._set_actor()
        return super().perform_update(serializer)

    def perform_destroy(self, instance):
        """Capture l'acteur avant suppression."""
        self._set_actor()
        return super().perform_destroy(instance)


class GroupViewSet(AuditActorViewSetMixin, viewsets.ModelViewSet):
    """ViewSet pour les groupes."""
    queryset = models.Group.objects.select_related("responsible").order_by("-id")
    serializer_class = serializers.GroupSerializer
    permission_classes = [permissions.IsAuthenticated, StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "responsible__username"]
    ordering_fields = ["name", "created_at"]


class OrganViewSet(AuditActorViewSetMixin, viewsets.ModelViewSet):
    """ViewSet pour les organes."""
    queryset = models.Organ.objects.select_related("group").order_by("-id")
    serializer_class = serializers.OrganSerializer
    permission_classes = [permissions.IsAuthenticated, StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "group__name"]
    ordering_fields = ["name"]


class MemberViewSet(AuditActorViewSetMixin, viewsets.ModelViewSet):
    """ViewSet pour les membres."""
    queryset = models.Member.objects.prefetch_related("groups").order_by("-id")
    serializer_class = serializers.MemberSerializer
    permission_classes = [permissions.IsAuthenticated, StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["full_name", "email", "phone", "groups__name"]
    ordering_fields = ["full_name", "email"]


class PositionViewSet(AuditActorViewSetMixin, viewsets.ModelViewSet):
    """ViewSet pour les postes."""
    queryset = models.Position.objects.select_related("group", "organ", "member").order_by("-id")
    serializer_class = serializers.PositionSerializer
    permission_classes = [permissions.IsAuthenticated, StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "group__name", "organ__name", "member__full_name"]
    ordering_fields = ["name"]


class MeetingViewSet(AuditActorViewSetMixin, viewsets.ModelViewSet):
    """ViewSet pour les rencontres."""
    queryset = models.Meeting.objects.select_related("group").order_by("-id")
    serializer_class = serializers.MeetingSerializer
    permission_classes = [permissions.IsAuthenticated, StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "group__name"]
    ordering_fields = ["scheduled_at"]


class MeetingEntryViewSet(AuditActorViewSetMixin, viewsets.ModelViewSet):
    """ViewSet pour les présences aux rencontres."""
    queryset = models.MeetingEntry.objects.select_related("meeting", "meeting__group", "member").order_by("-id")
    serializer_class = serializers.MeetingEntrySerializer
    permission_classes = [permissions.IsAuthenticated, StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["member__full_name", "meeting__title", "status", "meeting__group__name"]
    ordering_fields = ["recorded_at"]


class ContributionViewSet(AuditActorViewSetMixin, viewsets.ModelViewSet):
    """ViewSet pour les cotisations."""
    queryset = models.Contribution.objects.select_related("member", "group").order_by("-id")
    serializer_class = serializers.ContributionSerializer
    permission_classes = [permissions.IsAuthenticated, StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["member__full_name", "group__name", "contribution_type"]
    ordering_fields = ["paid_at", "amount"]


class DocumentViewSet(AuditActorViewSetMixin, viewsets.ModelViewSet):
    """ViewSet pour les documents."""
    queryset = models.Document.objects.select_related("group").order_by("-id")
    serializer_class = serializers.DocumentSerializer
    permission_classes = [permissions.IsAuthenticated, StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "document_type", "group__name"]
    ordering_fields = ["uploaded_at", "title"]


class EventViewSet(AuditActorViewSetMixin, viewsets.ModelViewSet):
    """ViewSet pour les événements."""
    queryset = models.Event.objects.select_related("group").order_by("-id")
    serializer_class = serializers.EventSerializer
    permission_classes = [permissions.IsAuthenticated, StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "event_type", "group__name", "location"]
    ordering_fields = ["starts_at", "title"]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les logs d'audit (lecture seule)."""
    queryset = models.AuditLog.objects.select_related("actor").order_by("-created_at")
    serializer_class = serializers.AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["model_name", "object_pk", "object_repr", "actor__username", "path"]
    ordering_fields = ["created_at", "model_name", "action"]


def healthcheck(_request):
    """Endpoint de healthcheck pour vérifier l'état de l'application.

    Args:
        _request: La requête HTTP (non utilisée).

    Returns:
        JsonResponse: JSON avec le statut de l'application et de la base de données.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_status = "ok"
        status_code = 200
    except Exception:
        db_status = "error"
        status_code = 503
    return JsonResponse({"status": "ok" if db_status == "ok" else "degraded", "database": db_status}, status=status_code)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def dashboard_summary(_request):
    """Endpoint API fournissant un résumé des KPIs du tableau de bord.

    Args:
        _request: La requête HTTP (non utilisée).

    Returns:
        Response: JSON avec les statistiques principales de l'application.
    """
    today = timezone.localdate()
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

    return Response(
        {
            "group_count": models.Group.objects.count(),
            "member_count": models.Member.objects.count(),
            "meeting_count": models.Meeting.objects.count(),
            "event_count": models.Event.objects.count(),
            "total_contributions": total_contributions,
            "current_month_contributions": current_month_contributions,
            "attendance_rate": attendance_rate,
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_schema(_request):
    """Endpoint API fournissant le schéma des ressources disponibles.

    Args:
        _request: La requête HTTP (non utilisée).

    Returns:
        Response: JSON décrivant les endpoints API disponibles.
    """
    return Response(
        {
            "name": "GroupManager API",
            "version": "1.0.0",
            "resources": [
                {"path": "/api/groups/", "description": "CRUD groupes"},
                {"path": "/api/organs/", "description": "CRUD organes"},
                {"path": "/api/members/", "description": "CRUD membres"},
                {"path": "/api/positions/", "description": "CRUD postes"},
                {"path": "/api/meetings/", "description": "CRUD rencontres"},
                {"path": "/api/meeting-entries/", "description": "CRUD presences"},
                {"path": "/api/contributions/", "description": "CRUD cotisations"},
                {"path": "/api/documents/", "description": "CRUD documents"},
                {"path": "/api/events/", "description": "CRUD evenements"},
                {"path": "/api/audit-logs/", "description": "Historique d'audit (lecture seule)"},
                {"path": "/api/dashboard-summary/", "description": "KPI tableau de bord"},
            ],
        }
    )
