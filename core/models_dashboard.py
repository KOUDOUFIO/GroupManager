"""Modèles pour les dashboards personnalisables.

Ce module définit les modèles pour les préférences de dashboard
permettant aux utilisateurs de personnaliser leur interface.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class DashboardPreference(models.Model):
    """Préférences de dashboard pour les utilisateurs."""
    
    # Widgets disponibles
    WIDGET_GROUP_STATS = 'group_stats'
    WIDGET_MEMBER_STATS = 'member_stats'
    WIDGET_MEETING_STATS = 'meeting_stats'
    WIDGET_CONTRIBUTION_STATS = 'contribution_stats'
    WIDGET_RECENT_ACTIVITY = 'recent_activity'
    WIDGET_UPCOMING_EVENTS = 'upcoming_events'
    WIDGET_QUICK_ACTIONS = 'quick_actions'
    WIDGET_ATTENDANCE_RATE = 'attendance_rate'
    
    WIDGET_CHOICES = [
        (WIDGET_GROUP_STATS, 'Statistiques Groupes'),
        (WIDGET_MEMBER_STATS, 'Statistiques Membres'),
        (WIDGET_MEETING_STATS, 'Statistiques Rencontres'),
        (WIDGET_CONTRIBUTION_STATS, 'Statistiques Cotisations'),
        (WIDGET_RECENT_ACTIVITY, 'Activité Récente'),
        (WIDGET_UPCOMING_EVENTS, 'Événements à Venir'),
        (WIDGET_QUICK_ACTIONS, 'Actions Rapides'),
        (WIDGET_ATTENDANCE_RATE, 'Taux de Présence'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='dashboard_preferences',
        verbose_name='Utilisateur'
    )
    
    # Widgets activés (stockés comme JSON)
    enabled_widgets = models.JSONField(
        default=list,
        verbose_name='Widgets activés'
    )
    
    # Ordre des widgets (liste des IDs dans l'ordre)
    widget_order = models.JSONField(
        default=list,
        verbose_name='Ordre des widgets'
    )
    
    # Layout preference (grid columns)
    layout_columns = models.IntegerField(
        default=3,
        choices=[(1, '1 colonne'), (2, '2 colonnes'), (3, '3 colonnes'), (4, '4 colonnes')],
        verbose_name='Nombre de colonnes'
    )
    
    # Theme preference
    theme = models.CharField(
        max_length=20,
        default='light',
        choices=[('light', 'Clair'), ('dark', 'Sombre'), ('auto', 'Auto')],
        verbose_name='Thème'
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
        verbose_name = 'Préférence de dashboard'
        verbose_name_plural = 'Préférences de dashboard'
    
    def __str__(self):
        return f"Dashboard de {self.user.username}"
    
    def clean(self):
        """Valide que les widgets activés sont valides."""
        valid_widgets = [choice[0] for choice in self.WIDGET_CHOICES]
        for widget in self.enabled_widgets:
            if widget not in valid_widgets:
                raise ValidationError({
                    'enabled_widgets': f'Widget "{widget}" non valide.'
                })
    
    def get_default_widgets(self):
        """Retourne les widgets par défaut pour un nouvel utilisateur."""
        return [
            self.WIDGET_GROUP_STATS,
            self.WIDGET_MEMBER_STATS,
            self.WIDGET_MEETING_STATS,
            self.WIDGET_CONTRIBUTION_STATS,
            self.WIDGET_RECENT_ACTIVITY,
            self.WIDGET_QUICK_ACTIONS,
        ]
    
    def save(self, *args, **kwargs):
        """Sauvegarde en initialisant les widgets par défaut si vide."""
        if not self.enabled_widgets:
            self.enabled_widgets = self.get_default_widgets()
        if not self.widget_order:
            self.widget_order = self.enabled_widgets.copy()
        super().save(*args, **kwargs)
    
    def add_widget(self, widget_id):
        """Ajoute un widget aux widgets activés."""
        if widget_id not in self.enabled_widgets:
            self.enabled_widgets.append(widget_id)
            self.widget_order.append(widget_id)
            self.save()
    
    def remove_widget(self, widget_id):
        """Retire un widget des widgets activés."""
        if widget_id in self.enabled_widgets:
            self.enabled_widgets.remove(widget_id)
            if widget_id in self.widget_order:
                self.widget_order.remove(widget_id)
            self.save()
    
    def reorder_widget(self, widget_id, new_position):
        """Réordonne un widget à une nouvelle position."""
        if widget_id in self.widget_order:
            self.widget_order.remove(widget_id)
            self.widget_order.insert(new_position, widget_id)
            self.save()
