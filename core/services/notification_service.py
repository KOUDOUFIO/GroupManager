"""Service Layer pour le système de notifications.

Ce service encapsule la logique métier liée aux notifications,
permettant de créer et gérer les notifications utilisateurs.
"""

from typing import List, Optional, Dict, Any
from django.db import transaction
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from django.utils import timezone

from ..models import Notification, NotificationPreference

User = get_user_model()


class NotificationService:
    """Service pour la gestion des notifications."""
    
    @staticmethod
    def get_notification_list(
        user_id: int,
        unread_only: bool = False,
        category: Optional[str] = None
    ) -> List[Notification]:
        """Récupère la liste des notifications d'un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            unread_only: Ne récupérer que les non lues
            category: Filtrer par catégorie
            
        Returns:
            Liste des notifications
        """
        queryset = Notification.objects.filter(user_id=user_id)
        
        if unread_only:
            queryset = queryset.filter(is_read=False)
        
        if category:
            queryset = queryset.filter(category=category)
            
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_notification_count(user_id: int, unread_only: bool = True) -> int:
        """Compte les notifications d'un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            unread_only: Ne compter que les non lues
            
        Returns:
            Nombre de notifications
        """
        queryset = Notification.objects.filter(user_id=user_id)
        
        if unread_only:
            queryset = queryset.filter(is_read=False)
            
        return queryset.count()
    
    @staticmethod
    @transaction.atomic
    def create_notification(
        user_id: int,
        notification_type: str,
        category: str,
        title: str,
        message: str,
        link: Optional[str] = None,
        related_model: Optional[str] = None,
        related_object_id: Optional[int] = None
    ) -> Optional[Notification]:
        """Crée une nouvelle notification pour un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            notification_type: Type de notification
            category: Catégorie de notification
            title: Titre de la notification
            message: Message de la notification
            link: Lien optionnel
            related_model: Modèle lié optionnel
            related_object_id: ID de l'objet lié optionnel
            
        Returns:
            Instance de la notification créée ou None
        """
        try:
            # Vérifier les préférences de l'utilisateur
            preference = NotificationPreference.objects.get(user_id=user_id)
            if not preference.should_notify(category):
                return None
        except NotificationPreference.DoesNotExist:
            # Créer les préférences par défaut si elles n'existent pas
            NotificationPreference.objects.create(user_id=user_id)
        
        try:
            notification = Notification.objects.create(
                user_id=user_id,
                notification_type=notification_type,
                category=category,
                title=title,
                message=message,
                link=link,
                related_model=related_model,
                related_object_id=related_object_id
            )
            return notification
        except User.DoesNotExist:
            return None
    
    @staticmethod
    @transaction.atomic
    def mark_as_read(notification_id: int, user_id: int) -> bool:
        """Marque une notification comme lue.
        
        Args:
            notification_id: ID de la notification
            user_id: ID de l'utilisateur (pour vérification)
            
        Returns:
            True si marquée comme lue, False sinon
        """
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user_id=user_id
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False
    
    @staticmethod
    @transaction.atomic
    def mark_all_as_read(user_id: int) -> int:
        """Marque toutes les notifications d'un utilisateur comme lues.
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            Nombre de notifications marquées
        """
        count = Notification.objects.filter(
            user_id=user_id,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return count
    
    @staticmethod
    @transaction.atomic
    def delete_notification(notification_id: int, user_id: int) -> bool:
        """Supprime une notification.
        
        Args:
            notification_id: ID de la notification
            user_id: ID de l'utilisateur (pour vérification)
            
        Returns:
            True si supprimée, False sinon
        """
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user_id=user_id
            )
            notification.delete()
            return True
        except Notification.DoesNotExist:
            return False
    
    @staticmethod
    def get_or_create_preferences(user_id: int) -> NotificationPreference:
        """Récupère ou crée les préférences de notification d'un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            Instance des préférences
        """
        preference, created = NotificationPreference.objects.get_or_create(
            user_id=user_id
        )
        return preference
    
    @staticmethod
    @transaction.atomic
    def update_preferences(
        user_id: int,
        email_enabled: Optional[bool] = None,
        in_app_enabled: Optional[bool] = None,
        notify_groups: Optional[bool] = None,
        notify_members: Optional[bool] = None,
        notify_meetings: Optional[bool] = None,
        notify_contributions: Optional[bool] = None,
        notify_system: Optional[bool] = None
    ) -> Optional[NotificationPreference]:
        """Met à jour les préférences de notification d'un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            email_enabled: Notifications par email
            in_app_enabled: Notifications in-app
            notify_groups: Notifications groupes
            notify_members: Notifications membres
            notify_meetings: Notifications rencontres
            notify_contributions: Notifications cotisations
            notify_system: Notifications système
            
        Returns:
            Instance des préférences mises à jour ou None
        """
        try:
            preference = NotificationPreference.objects.get(user_id=user_id)
            
            if email_enabled is not None:
                preference.email_enabled = email_enabled
            if in_app_enabled is not None:
                preference.in_app_enabled = in_app_enabled
            if notify_groups is not None:
                preference.notify_groups = notify_groups
            if notify_members is not None:
                preference.notify_members = notify_members
            if notify_meetings is not None:
                preference.notify_meetings = notify_meetings
            if notify_contributions is not None:
                preference.notify_contributions = notify_contributions
            if notify_system is not None:
                preference.notify_system = notify_system
            
            preference.save()
            return preference
        except NotificationPreference.DoesNotExist:
            return None
    
    @staticmethod
    def notify_group_members(
        group_id: int,
        notification_type: str,
        title: str,
        message: str,
        link: Optional[str] = None
    ) -> int:
        """Notifie tous les membres d'un groupe.
        
        Args:
            group_id: ID du groupe
            notification_type: Type de notification
            title: Titre de la notification
            message: Message de la notification
            link: Lien optionnel
            
        Returns:
            Nombre de notifications créées
        """
        from ..models import Group, Member
        
        try:
            group = Group.objects.get(id=group_id)
            members = group.members.all()
            
            count = 0
            for member in members:
                # Trouver l'utilisateur associé au membre (si applicable)
                # Pour l'instant, on suppose que les membres sont des utilisateurs
                # Dans un système réel, il faudrait une relation Member <-> User
                notification = NotificationService.create_notification(
                    user_id=member.id,  # Simplification - adapter selon votre modèle
                    notification_type=notification_type,
                    category=Notification.CATEGORY_GROUP,
                    title=title,
                    message=message,
                    link=link,
                    related_model='Group',
                    related_object_id=group_id
                )
                if notification:
                    count += 1
            
            return count
        except Group.DoesNotExist:
            return 0
