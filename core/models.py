"""Modèles de données pour l'application core.

Ce module définit tous les modèles de données de l'application :
- Group: Groupes d'organisation
- Organ: Organes au sein des groupes
- Member: Membres des groupes
- Position: Postes occupés par les membres
- Meeting: Rencontres planifiées
- MeetingEntry: Présences aux rencontres
- Contribution: Cotisations et paiements
- Document: Documents partagés
- Event: Événements spéciaux
- AuditLog: Journal d'audit des modifications
- Notification: Notifications utilisateurs
- NotificationPreference: Préférences de notification
- DashboardPreference: Préférences de dashboard personnalisable
- TwoFactorPreference: Préférences 2FA
"""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice as BaseTOTPDevice


class Group(models.Model):
    """Représente un groupe d'organisation.

    Un groupe peut contenir des membres, des organes, des postes,
    des rencontres, des cotisations, des documents et des événements.
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_groups",
    )

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return self.name


class Organ(models.Model):
    """Représente un organe au sein d'un groupe.

    Un organe est une sous-structure d'un groupe (ex: comité, département).
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="organs")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.group.name})"


class Member(models.Model):
    """Représente un membre pouvant appartenir à plusieurs groupes.

    Un membre peut être associé à plusieurs groupes via une relation many-to-many.
    """
    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    groups = models.ManyToManyField(Group, related_name="members", blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["email"]),
            models.Index(fields=["phone"]),
        ]

    def __str__(self) -> str:
        return self.full_name


class Position(models.Model):
    """Représente un poste occupé par un membre dans un groupe.

    Un poste peut être rattaché à un organe spécifique ou directement au groupe.
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    organ = models.ForeignKey(Organ, on_delete=models.SET_NULL, null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="positions")
    member = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
        ]

    def clean(self):
        """Valide que l'organe appartient au même groupe."""
        if self.organ_id and self.group_id and self.organ.group_id != self.group_id:
            raise ValidationError({"organ": "L'organe selectionne doit appartenir au meme groupe."})

    def __str__(self) -> str:
        return f"{self.name} ({self.group.name})"


class Meeting(models.Model):
    """Représente une rencontre planifiée pour un groupe."""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="meetings")
    scheduled_at = models.DateTimeField()
    title = models.CharField(max_length=200, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["scheduled_at"]),
            models.Index(fields=["title"]),
        ]

    def __str__(self) -> str:
        label = self.title or "Rencontre"
        return f"{label} - {self.group.name}"


class MeetingEntry(models.Model):
    """Représente la présence d'un membre à une rencontre.

    Enregistre le statut de présence (présent, absent, retard, permission)
    avec un motif optionnel.
    """
    STATUS_PRESENT = "present"
    STATUS_ABSENT = "absent"
    STATUS_LATE = "late"
    STATUS_PERMISSION = "permission"
    STATUS_CHOICES = [
        (STATUS_PRESENT, "Present"),
        (STATUS_ABSENT, "Absent"),
        (STATUS_LATE, "Late"),
        (STATUS_PERMISSION, "Permission"),
    ]

    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name="entries")
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="meeting_entries")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    reason = models.TextField(blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("meeting", "member")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["recorded_at"]),
        ]

    def clean(self):
        """Valide que le membre appartient au groupe de la rencontre."""
        if self.meeting_id and self.member_id and not self.member.groups.filter(pk=self.meeting.group_id).exists():
            raise ValidationError({"member": "Le membre doit appartenir au groupe de la rencontre."})

    def __str__(self) -> str:
        return f"{self.member.full_name} - {self.meeting}"


class Contribution(models.Model):
    """Représente une cotisation ou un paiement d'un membre à un groupe.

    Peut être de différents types : mensuelle, spontanée, amende pour retard,
    amende pour absence, ou autre.
    """
    TYPE_MONTHLY = "monthly"
    TYPE_SPONTANEOUS = "spontaneous"
    TYPE_LATE_FINE = "late_fine"
    TYPE_ABSENCE_FINE = "absence_fine"
    TYPE_OTHER = "other"
    TYPE_CHOICES = [
        (TYPE_MONTHLY, "Mensuelle"),
        (TYPE_SPONTANEOUS, "Spontanee"),
        (TYPE_LATE_FINE, "Amende retard"),
        (TYPE_ABSENCE_FINE, "Amende absence"),
        (TYPE_OTHER, "Autre"),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="contributions")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="contributions")
    contribution_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    paid_at = models.DateField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="contribution_amount_gt_zero",
            ),
        ]
        indexes = [
            models.Index(fields=["contribution_type"]),
            models.Index(fields=["paid_at"]),
        ]

    def clean(self):
        """Valide que le membre appartient au groupe de la cotisation."""
        if self.group_id and self.member_id and not self.member.groups.filter(pk=self.group_id).exists():
            raise ValidationError({"member": "Le membre doit appartenir au groupe de la cotisation."})

    def __str__(self) -> str:
        return f"{self.member.full_name} - {self.amount}"


class Document(models.Model):
    """Représente un document partagé au sein d'un groupe.

    Les documents sont stockés dans le système de fichiers et associés à un groupe.
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["uploaded_at"]),
        ]

    def __str__(self) -> str:
        return self.title


class Event(models.Model):
    """Représente un événement spécial organisé par un groupe.

    Les événements peuvent être des conférences, ateliers, célébrations, etc.
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    starts_at = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["starts_at"]),
            models.Index(fields=["title"]),
            models.Index(fields=["location"]),
        ]

    def __str__(self) -> str:
        return self.title


class AuditLog(models.Model):
    """Représente une entrée du journal d'audit.

    Enregistre automatiquement les créations, modifications et suppressions
    sur les modèles principaux avec l'acteur, les changements et le contexte.
    """
    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_DELETE = "delete"
    ACTION_CHOICES = [
        (ACTION_CREATE, "Creation"),
        (ACTION_UPDATE, "Modification"),
        (ACTION_DELETE, "Suppression"),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_pk = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=255)
    path = models.CharField(max_length=300, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["model_name"]),
            models.Index(fields=["object_pk"]),
            models.Index(fields=["action"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_action_display()} {self.model_name}#{self.object_pk}"


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
        settings.AUTH_USER_MODEL,
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


class TOTPDevice(BaseTOTPDevice):
    """Extension du modèle TOTPDevice pour les besoins spécifiques."""
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Créé le'
    )
    
    last_used_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Dernière utilisation'
    )
    
    class Meta:
        verbose_name = 'Appareil TOTP'
        verbose_name_plural = 'Appareils TOTP'
    
    def __str__(self):
        return f"TOTP Device - {self.user.username}"
    
    def verify_token(self, token):
        """Vérifie le token et met à jour la dernière utilisation."""
        if super().verify_token(token):
            self.last_used_at = timezone.now()
            self.save(update_fields=['last_used_at'])
            return True
        return False


class TwoFactorPreference(models.Model):
    """Préférences 2FA pour les utilisateurs."""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='two_factor_preferences',
        verbose_name='Utilisateur'
    )
    
    enabled = models.BooleanField(
        default=False,
        verbose_name='2FA activé'
    )
    
    backup_codes = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Codes de secours'
    )
    
    backup_codes_used = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Codes de secours utilisés'
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
        verbose_name = 'Préférence 2FA'
        verbose_name_plural = 'Préférences 2FA'
    
    def __str__(self):
        return f"2FA - {self.user.username}"
    
    def generate_backup_codes(self, count=10):
        """Génère des codes de secours."""
        import secrets
        codes = []
        for _ in range(count):
            code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
            codes.append(code)
        self.backup_codes = codes
        self.backup_codes_used = []
        self.save()
        return codes
    
    def use_backup_code(self, code):
        """Utilise un code de secours."""
        if code in self.backup_codes and code not in self.backup_codes_used:
            self.backup_codes_used.append(code)
            self.save()
            return True
        return False
    
    def remaining_backup_codes(self):
        """Retourne le nombre de codes de secours restants."""
        return len(self.backup_codes) - len(self.backup_codes_used)
