"""Configuration de l'interface d'administration Django pour les modèles core.

Ce module définit les classes d'administration pour tous les modèles
de l'application core, avec des configurations optimisées pour la recherche,
le filtrage et l'affichage.
"""

from django.contrib import admin

from . import models


@admin.register(models.Group)
class GroupAdmin(admin.ModelAdmin):
    """Interface d'administration pour les groupes."""
    list_display = ("name", "responsible", "created_at")
    search_fields = ("name", "description", "responsible__username")
    list_filter = ("created_at",)


@admin.register(models.Organ)
class OrganAdmin(admin.ModelAdmin):
    """Interface d'administration pour les organes."""
    list_display = ("name", "group")
    search_fields = ("name", "description", "group__name")
    list_filter = ("group",)


@admin.register(models.Member)
class MemberAdmin(admin.ModelAdmin):
    """Interface d'administration pour les membres."""
    list_display = ("full_name", "email", "phone", "user")
    search_fields = ("full_name", "email", "phone")
    filter_horizontal = ("groups",)
    autocomplete_fields = ("user",)


@admin.register(models.Position)
class PositionAdmin(admin.ModelAdmin):
    """Interface d'administration pour les postes."""
    list_display = ("name", "group", "organ", "member")
    search_fields = ("name", "description", "group__name", "organ__name", "member__full_name")
    list_filter = ("group", "organ")


@admin.register(models.Meeting)
class MeetingAdmin(admin.ModelAdmin):
    """Interface d'administration pour les rencontres."""
    list_display = ("title", "group", "scheduled_at")
    search_fields = ("title", "group__name")
    list_filter = ("group", "scheduled_at")


@admin.register(models.MeetingEntry)
class MeetingEntryAdmin(admin.ModelAdmin):
    """Interface d'administration pour les présences aux rencontres."""
    list_display = ("meeting", "member", "status", "recorded_at")
    search_fields = ("meeting__title", "meeting__group__name", "member__full_name", "reason")
    list_filter = ("status", "meeting__group")


@admin.register(models.Contribution)
class ContributionAdmin(admin.ModelAdmin):
    """Interface d'administration pour les cotisations."""
    list_display = ("member", "group", "contribution_type", "payment_method", "payment_status", "amount", "paid_at")
    search_fields = ("member__full_name", "group__name")
    list_filter = ("contribution_type", "payment_method", "payment_status", "group", "paid_at")


@admin.register(models.Document)
class DocumentAdmin(admin.ModelAdmin):
    """Interface d'administration pour les documents."""
    list_display = ("title", "group", "document_type", "uploaded_at")
    search_fields = ("title", "group__name", "document_type")
    list_filter = ("group", "document_type", "uploaded_at")


@admin.register(models.Event)
class EventAdmin(admin.ModelAdmin):
    """Interface d'administration pour les événements."""
    list_display = ("title", "group", "event_type", "starts_at", "location")
    search_fields = ("title", "group__name", "event_type", "location")
    list_filter = ("group", "event_type", "starts_at")


@admin.register(models.ProposalRequest)
class ProposalRequestAdmin(admin.ModelAdmin):
    """Interface d'administration pour les demandes de devis."""
    list_display = ("name", "email", "company", "organization_type", "created_at")
    search_fields = ("name", "email", "company", "message")
    list_filter = ("organization_type", "created_at")
    readonly_fields = ("created_at",)


@admin.register(models.AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Interface d'administration pour les logs d'audit (lecture seule)."""
    list_display = ("created_at", "actor", "action", "model_name", "object_pk", "path")
    search_fields = ("actor__username", "model_name", "object_pk", "object_repr", "path")
    list_filter = ("action", "model_name", "created_at")
    readonly_fields = ("created_at", "actor", "action", "model_name", "object_pk", "object_repr", "path", "ip_address", "changes")

    def has_add_permission(self, request):
        """Empêche la création manuelle de logs d'audit."""
        return False

    def has_change_permission(self, request, obj=None):
        """Empêche la modification de logs d'audit."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Empêche la suppression de logs d'audit."""
        return False
