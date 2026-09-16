"""Signaux Django pour l'audit automatique des modèles.

Ce module définit les handlers de signaux Django qui capturent automatiquement
les créations, modifications et suppressions sur les modèles principaux
pour les enregistrer dans le journal d'audit.
"""

from datetime import date, datetime
from decimal import Decimal

from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver

from .audit import get_actor_context
from .models import AuditLog, Contribution, Document, Event, Group, Meeting, MeetingEntry, Member, Organ, Position

AUDITED_MODELS = [Group, Organ, Member, Position, Meeting, MeetingEntry, Contribution, Document, Event]


def _serialize_value(value):
    """Sérialise une valeur pour stockage JSON.

    Args:
        value: La valeur à sérialiser.

    Returns:
        La valeur sérialisée (string pour dates/decimals).
    """
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _snapshot(instance):
    """Crée un instantané de tous les champs d'une instance.

    Args:
        instance: L'instance de modèle à snapshoter.

    Returns:
        dict: Dictionnaire des champs avec leurs valeurs sérialisées.
    """
    snapshot = {}
    for field in instance._meta.concrete_fields:
        snapshot[field.name] = _serialize_value(getattr(instance, field.attname))
    return snapshot


def _create_audit_log(action, instance, changes=None):
    """Crée une entrée de log d'audit.

    Args:
        action: L'action effectuée (create/update/delete).
        instance: L'instance de modèle concernée.
        changes: Dictionnaire des changements (optionnel).
    """
    actor, path, ip_address = get_actor_context()
    AuditLog.objects.create(
        actor=actor,
        action=action,
        model_name=instance._meta.model_name,
        object_pk=str(instance.pk),
        object_repr=str(instance)[:255],
        path=path[:300] if path else "",
        ip_address=ip_address or None,
        changes=changes or {},
    )


@receiver(pre_save)
def capture_before_update(sender, instance, **kwargs):
    """Capture l'état avant modification pour le diff.

    Args:
        sender: La classe du modèle.
        instance: L'instance de modèle.
        **kwargs: Arguments supplémentaires du signal.
    """
    if sender not in AUDITED_MODELS:
        return
    if not instance.pk:
        instance._audit_before = None
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._audit_before = None
        return
    instance._audit_before = _snapshot(previous)


@receiver(post_save)
def create_audit_on_save(sender, instance, created, **kwargs):
    """Crée un log d'audit lors de la création ou modification.

    Args:
        sender: La classe du modèle.
        instance: L'instance de modèle.
        created: True si c'est une création, False si modification.
        **kwargs: Arguments supplémentaires du signal.
    """
    if sender not in AUDITED_MODELS:
        return

    if created:
        after = _snapshot(instance)
        changes = {field_name: {"old": None, "new": value} for field_name, value in after.items()}
        _create_audit_log(AuditLog.ACTION_CREATE, instance, changes=changes)
        return

    before = getattr(instance, "_audit_before", None)
    after = _snapshot(instance)
    if before is None:
        changes = {}
    else:
        changes = {}
        for field_name, new_value in after.items():
            old_value = before.get(field_name)
            if old_value != new_value:
                changes[field_name] = {"old": old_value, "new": new_value}

    if changes:
        _create_audit_log(AuditLog.ACTION_UPDATE, instance, changes=changes)


@receiver(post_delete)
def create_audit_on_delete(sender, instance, **kwargs):
    """Crée un log d'audit lors de la suppression.

    Args:
        sender: La classe du modèle.
        instance: L'instance de modèle.
        **kwargs: Arguments supplémentaires du signal.
    """
    if sender not in AUDITED_MODELS:
        return
    _create_audit_log(AuditLog.ACTION_DELETE, instance, changes={})


@receiver(m2m_changed, sender=Member.groups.through)
def create_audit_on_member_groups_changed(sender, instance, action, pk_set, **kwargs):
    """Crée un log d'audit lors des modifications de groupes d'un membre.

    Args:
        sender: La classe du modèle through.
        instance: L'instance de Member.
        action: L'action M2M (post_add, post_remove, post_clear).
        pk_set: L'ensemble des PKs affectés.
        **kwargs: Arguments supplémentaires du signal.
    """
    tracked_actions = {"post_add", "post_remove", "post_clear"}
    if action not in tracked_actions:
        return

    if action == "post_clear":
        payload = {"relation": "groups", "m2m_action": action}
    else:
        payload = {"relation": "groups", "m2m_action": action, "group_ids": sorted(list(pk_set))}

    _create_audit_log(
        AuditLog.ACTION_UPDATE,
        instance,
        changes={"groups": {"old": "many-to-many", "new": payload}},
    )
