"""Notifications utilisateurs et préférences associées."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """Modèle pour les notifications utilisateurs."""

    # Types de notifications
    TYPE_INFO = 'info'
    TYPE_SUCCESS = 'success'
    TYPE_WARNING = 'warning'
    TYPE_ERROR = 'error'

    TYPE_CHOICES = [
        (TYPE_INFO, 'Information'),
        (TYPE_SUCCESS, 'Succès'),
        (TYPE_WARNING, 'Avertissement'),
        (TYPE_ERROR, 'Erreur'),
    ]

    # Catégories de notifications
    CATEGORY_GROUP = 'group'
    CATEGORY_MEMBER = 'member'
    CATEGORY_MEETING = 'meeting'
    CATEGORY_CONTRIBUTION = 'contribution'
    CATEGORY_SYSTEM = 'system'

    CATEGORY_CHOICES = [
        (CATEGORY_GROUP, 'Groupe'),
        (CATEGORY_MEMBER, 'Membre'),
        (CATEGORY_MEETING, 'Rencontre'),
        (CATEGORY_CONTRIBUTION, 'Cotisation'),
        (CATEGORY_SYSTEM, 'Système'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Utilisateur'
    )

    notification_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_INFO,
        verbose_name='Type'
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_SYSTEM,
        verbose_name='Catégorie'
    )

    title = models.CharField(
        max_length=200,
        verbose_name='Titre'
    )

    message = models.TextField(
        verbose_name='Message'
    )

    link = models.URLField(
        blank=True,
        null=True,
        verbose_name='Lien'
    )

    is_read = models.BooleanField(
        default=False,
        verbose_name='Lu'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Créé le'
    )

    read_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Lu le'
    )

    # Métadonnées pour les notifications liées à des objets
    related_model = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Modèle lié'
    )

    related_object_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='ID de l\'objet lié'
    )

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.title} - {self.user.username}"

    def mark_as_read(self):
        """Marque la notification comme lue."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def mark_as_unread(self):
        """Marque la notification comme non lue."""
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=['is_read', 'read_at'])


class NotificationPreference(models.Model):
    """Préférences de notification pour les utilisateurs."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name='Utilisateur'
    )

    # Préférences par canal
    email_enabled = models.BooleanField(
        default=True,
        verbose_name='Notifications par email'
    )

    in_app_enabled = models.BooleanField(
        default=True,
        verbose_name='Notifications in-app'
    )

    # Préférences par catégorie
    notify_groups = models.BooleanField(
        default=True,
        verbose_name='Notifications groupes'
    )

    notify_members = models.BooleanField(
        default=True,
        verbose_name='Notifications membres'
    )

    notify_meetings = models.BooleanField(
        default=True,
        verbose_name='Notifications rencontres'
    )

    notify_contributions = models.BooleanField(
        default=True,
        verbose_name='Notifications cotisations'
    )

    notify_system = models.BooleanField(
        default=True,
        verbose_name='Notifications système'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Créé le'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Mis à jour le'
    )

    class Meta:
        verbose_name = 'Préférence de notification'
        verbose_name_plural = 'Préférences de notification'

    def __str__(self):
        return f"Préférences de {self.user.username}"

    def should_notify(self, category):
        """Vérifie si l'utilisateur veut recevoir des notifications pour cette catégorie."""
        category_map = {
            Notification.CATEGORY_GROUP: self.notify_groups,
            Notification.CATEGORY_MEMBER: self.notify_members,
            Notification.CATEGORY_MEETING: self.notify_meetings,
            Notification.CATEGORY_CONTRIBUTION: self.notify_contributions,
            Notification.CATEGORY_SYSTEM: self.notify_system,
        }
        return category_map.get(category, True) and self.in_app_enabled
