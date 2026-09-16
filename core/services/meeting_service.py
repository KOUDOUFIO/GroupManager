

from typing import List, Optional, Dict, Any
from django.db import transaction
from django.db.models import Q, Count
from django.core.exceptions import ValidationError
from django.utils import timezone

from ..models import Meeting, MeetingEntry, Member, Group
from ..audit import log_action


class MeetingService:
    """Service pour la gestion des rencontres et présences."""
    
    @staticmethod
    def get_meeting_list(
        search_query: Optional[str] = None,
        group_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Meeting]:
        """Récupère la liste des rencontres avec filtres optionnels.
        
        Args:
            search_query: Recherche textuelle
            group_id: Filtre par groupe
            start_date: Date de début
            end_date: Date de fin
            
        Returns:
            Liste des rencontres filtrées
        """
        queryset = Meeting.objects.select_related('group').annotate(
            entry_count=Count('entries')
        )
        
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(group__name__icontains=search_query)
            )
        
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        
        if start_date:
            queryset = queryset.filter(scheduled_at__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(scheduled_at__lte=end_date)
            
        return queryset.order_by('-scheduled_at')
    
    @staticmethod
    def get_meeting_detail(meeting_id: int) -> Optional[Meeting]:
        """Récupère les détails d'une rencontre avec ses entrées.
        
        Args:
            meeting_id: ID de la rencontre
            
        Returns:
            Instance de la rencontre ou None
        """
        try:
            return Meeting.objects.select_related('group').prefetch_related(
                'meeting_entries__member'
            ).get(pk=meeting_id)
        except Meeting.DoesNotExist:
            return None
    
    @staticmethod
    @transaction.atomic
    def create_meeting(
        group_id: int,
        title: str,
        scheduled_at: str,
        description: str = "",
        actor=None
    ) -> Optional[Meeting]:
        """Crée une nouvelle rencontre avec logging d'audit.
        
        Args:
            group_id: ID du groupe
            title: Titre de la rencontre
            scheduled_at: Date prévue
            description: Description
            actor: Utilisateur effectuant l'action
            
        Returns:
            Instance de la rencontre créée ou None
        """
        try:
            meeting = Meeting.objects.create(
                group_id=group_id,
                title=title,
                scheduled_at=scheduled_at,
                description=description
            )
            
            if actor:
                log_action(actor, 'create', 'meeting', meeting.pk, str(meeting))
            
            return meeting
        except Group.DoesNotExist:
            return None
    
    @staticmethod
    @transaction.atomic
    def update_meeting(
        meeting_id: int,
        title: Optional[str] = None,
        scheduled_at: Optional[str] = None,
        description: Optional[str] = None,
        actor=None
    ) -> Optional[Meeting]:
        """Met à jour une rencontre avec logging d'audit.
        
        Args:
            meeting_id: ID de la rencontre
            title: Nouveau titre
            scheduled_at: Nouvelle date
            description: Nouvelle description
            actor: Utilisateur effectuant l'action
            
        Returns:
            Instance de la rencontre mise à jour ou None
        """
        try:
            meeting = Meeting.objects.get(pk=meeting_id)
            
            changes = {}
            if title and title != meeting.title:
                changes['title'] = {'old': meeting.title, 'new': title}
                meeting.title = title
            if scheduled_at and scheduled_at != str(meeting.scheduled_at):
                changes['scheduled_at'] = {'old': str(meeting.scheduled_at), 'new': scheduled_at}
                meeting.scheduled_at = scheduled_at
            if description is not None and description != meeting.description:
                changes['description'] = {'old': meeting.description, 'new': description}
                meeting.description = description
            
            if changes:
                meeting.save()
                if actor:
                    log_action(actor, 'update', 'meeting', meeting.pk, str(meeting), changes)
            
            return meeting
        except Meeting.DoesNotExist:
            return None
    
    @staticmethod
    @transaction.atomic
    def delete_meeting(meeting_id: int, actor=None) -> bool:
        """Supprime une rencontre avec logging d'audit.
        
        Args:
            meeting_id: ID de la rencontre
            actor: Utilisateur effectuant l'action
            
        Returns:
            True si supprimée, False sinon
        """
        try:
            meeting = Meeting.objects.get(pk=meeting_id)
            meeting_repr = str(meeting)
            meeting.delete()
            
            if actor:
                log_action(actor, 'delete', 'meeting', meeting_id, meeting_repr)
            
            return True
        except Meeting.DoesNotExist:
            return False
    
    @staticmethod
    def get_meeting_entry_list(
        search_query: Optional[str] = None,
        group_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[MeetingEntry]:
        """Récupère la liste des présences avec filtres optionnels.
        
        Args:
            search_query: Recherche textuelle
            group_id: Filtre par groupe
            status: Filtre par statut
            
        Returns:
            Liste des présences filtrées
        """
        queryset = MeetingEntry.objects.select_related(
            'member', 'meeting', 'meeting__group'
        )
        
        if search_query:
            queryset = queryset.filter(
                Q(member__full_name__icontains=search_query) |
                Q(meeting__title__icontains=search_query) |
                Q(status__icontains=search_query)
            )
        
        if group_id:
            queryset = queryset.filter(meeting__group_id=group_id)
        
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset.order_by('-recorded_at')
    
    @staticmethod
    @transaction.atomic
    def create_meeting_entry(
        meeting_id: int,
        member_id: int,
        status: str,
        reason: str = "",
        actor=None
    ) -> Optional[MeetingEntry]:
        """Crée une nouvelle présence avec validation.
        
        Args:
            meeting_id: ID de la rencontre
            member_id: ID du membre
            status: Statut de présence
            reason: Motif (optionnel)
            actor: Utilisateur effectuant l'action
            
        Returns:
            Instance de la présence créée ou None si validation échoue
        """
        try:
            # Validation: le membre doit appartenir au groupe de la rencontre
            from .member_service import MemberService
            meeting = Meeting.objects.get(pk=meeting_id)
            if not MemberService.validate_member_group_membership(member_id, meeting.group_id):
                raise ValidationError("Le membre doit appartenir au groupe de la rencontre.")
            
            entry = MeetingEntry.objects.create(
                meeting_id=meeting_id,
                member_id=member_id,
                status=status,
                reason=reason
            )
            
            if actor:
                log_action(actor, 'create', 'meeting_entry', entry.pk, str(entry))
            
            return entry
        except (Meeting.DoesNotExist, Member.DoesNotExist, ValidationError):
            return None
    
    @staticmethod
    @transaction.atomic
    def update_meeting_entry(
        entry_id: int,
        status: Optional[str] = None,
        reason: Optional[str] = None,
        actor=None
    ) -> Optional[MeetingEntry]:
        """Met à jour une présence avec logging d'audit.
        
        Args:
            entry_id: ID de la présence
            status: Nouveau statut
            reason: Nouveau motif
            actor: Utilisateur effectuant l'action
            
        Returns:
            Instance de la présence mise à jour ou None
        """
        try:
            entry = MeetingEntry.objects.get(pk=entry_id)
            
            changes = {}
            if status and status != entry.status:
                changes['status'] = {'old': entry.status, 'new': status}
                entry.status = status
            if reason is not None and reason != entry.reason:
                changes['reason'] = {'old': entry.reason, 'new': reason}
                entry.reason = reason
            
            if changes:
                entry.save()
                if actor:
                    log_action(actor, 'update', 'meeting_entry', entry.pk, str(entry), changes)
            
            return entry
        except MeetingEntry.DoesNotExist:
            return None
    
    @staticmethod
    @transaction.atomic
    def delete_meeting_entry(entry_id: int, actor=None) -> bool:
        """Supprime une présence avec logging d'audit.
        
        Args:
            entry_id: ID de la présence
            actor: Utilisateur effectuant l'action
            
        Returns:
            True si supprimée, False sinon
        """
        try:
            entry = MeetingEntry.objects.get(pk=entry_id)
            entry_repr = str(entry)
            entry.delete()
            
            if actor:
                log_action(actor, 'delete', 'meeting_entry', entry_id, entry_repr)
            
            return True
        except MeetingEntry.DoesNotExist:
            return False
    
    @staticmethod
    def get_attendance_statistics(group_id: Optional[int] = None) -> Dict[str, Any]:
        """Calcule les statistiques de présence.
        
        Args:
            group_id: ID du groupe (optionnel)
            
        Returns:
            Dictionnaire avec les statistiques de présence
        """
        queryset = MeetingEntry.objects.all()
        
        if group_id:
            queryset = queryset.filter(meeting__group_id=group_id)
        
        total = queryset.count()
        
        status_counts = queryset.values('status').annotate(
            count=Count('id')
        )
        
        status_dict = {item['status']: item['count'] for item in status_counts}
        
        present_count = (
            status_dict.get('present', 0) + 
            status_dict.get('late', 0) + 
            status_dict.get('permission', 0)
        )
        
        attendance_rate = (present_count / total * 100) if total > 0 else 0
        
        return {
            'total_entries': total,
            'present_count': present_count,
            'absent_count': status_dict.get('absent', 0),
            'late_count': status_dict.get('late', 0),
            'permission_count': status_dict.get('permission', 0),
            'attendance_rate': round(attendance_rate, 1),
            'status_breakdown': status_dict,
        }
