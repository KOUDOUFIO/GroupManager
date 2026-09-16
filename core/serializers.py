"""Sérialiseurs Django REST Framework pour l'application core.

Ce module définit les sérialiseurs pour tous les modèles de l'application,
avec validation personnalisée pour assurer la cohérence des données.
"""

from rest_framework import serializers

from . import models


class GroupSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les groupes."""

    class Meta:
        model = models.Group
        fields = "__all__"


class OrganSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les organes."""

    class Meta:
        model = models.Organ
        fields = "__all__"


class MemberSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les membres."""

    class Meta:
        model = models.Member
        fields = "__all__"


class PositionSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les postes avec validation de cohérence."""

    def validate(self, attrs):
        """Valide que l'organe appartient au même groupe."""
        group = attrs.get("group", getattr(self.instance, "group", None))
        organ = attrs.get("organ", getattr(self.instance, "organ", None))
        if organ and group and organ.group_id != group.id:
            raise serializers.ValidationError(
                {"organ": "L'organe selectionne doit appartenir au meme groupe."}
            )
        return attrs

    class Meta:
        model = models.Position
        fields = "__all__"


class MeetingSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les rencontres."""

    class Meta:
        model = models.Meeting
        fields = "__all__"


class MeetingEntrySerializer(serializers.ModelSerializer):
    """Sérialiseur pour les présences aux rencontres avec validation."""

    def validate(self, attrs):
        """Valide que le membre appartient au groupe de la rencontre."""
        meeting = attrs.get("meeting", getattr(self.instance, "meeting", None))
        member = attrs.get("member", getattr(self.instance, "member", None))
        if meeting and member and not member.groups.filter(pk=meeting.group_id).exists():
            raise serializers.ValidationError(
                {"member": "Le membre doit appartenir au groupe de la rencontre."}
            )
        return attrs

    class Meta:
        model = models.MeetingEntry
        fields = "__all__"


class ContributionSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les cotisations avec validation."""

    def validate(self, attrs):
        """Valide que le membre appartient au groupe de la cotisation."""
        group = attrs.get("group", getattr(self.instance, "group", None))
        member = attrs.get("member", getattr(self.instance, "member", None))
        if group and member and not member.groups.filter(pk=group.id).exists():
            raise serializers.ValidationError(
                {"member": "Le membre doit appartenir au groupe de la cotisation."}
            )
        return attrs

    class Meta:
        model = models.Contribution
        fields = "__all__"


class DocumentSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les documents."""

    class Meta:
        model = models.Document
        fields = "__all__"


class EventSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les événements."""

    class Meta:
        model = models.Event
        fields = "__all__"


class AuditLogSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les logs d'audit (lecture seule)."""
    actor_username = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = models.AuditLog
        fields = "__all__"
        read_only_fields = ["actor", "created_at", "changes"]
