"""Service Layer pour la gestion des groupes.

Ce service encapsule toute la logique métier liée aux groupes,
permettant une réutilisation entre les vues web et l'API REST.
"""

from typing import List, Optional, Dict, Any
from django.db import transaction
from django.db.models import Q, Count, Sum
from django.utils import timezone

from ..models import Group, Member, Meeting, Contribution, Event
from ..audit import log_action


class GroupService:
    """Service pour la gestion des groupes."""
    
    @staticmethod
    def get_group_list(
        search_query: Optional[str] = None,
        responsible_id: Optional[int] = None
    ) -> List[Group]:
        """Récupère la liste des groupes avec filtres optionnels.
        
        Args:
            search_query: Recherche textuelle sur nom/description
            responsible_id: Filtre par responsable
            
        Returns:
            Liste des groupes filtrés
        """
        queryset = Group.objects.select_related('responsible').annotate(
            member_count=Count('members', distinct=True),
            meeting_count=Count('meetings', distinct=True),
            contribution_total=Sum('contributions__amount')
        )
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        
        if responsible_id:
            queryset = queryset.filter(responsible_id=responsible_id)
            
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_group_detail(group_id: int) -> Optional[Group]:
        """Récupère les détails d'un groupe avec ses relations.
        
        Args:
            group_id: ID du groupe
            
        Returns:
            Instance du groupe ou None
        """
        try:
            return Group.objects.select_related('responsible').prefetch_related(
                'members', 'positions', 'organs', 'meetings', 'events'
            ).get(pk=group_id)
        except Group.DoesNotExist:
            return None
    
    @staticmethod
    @transaction.atomic
    def create_group(
        name: str,
        description: str = "",
        responsible_id: Optional[int] = None,
        actor=None
    ) -> Group:
        """Crée un nouveau groupe avec logging d'audit.
        
        Args:
            name: Nom du groupe
            description: Description du groupe
            responsible_id: ID du responsable
            actor: Utilisateur effectuant l'action
            
        Returns:
            Instance du groupe créé
        """
        group = Group.objects.create(
            name=name,
            description=description,
            responsible_id=responsible_id
        )
        
        if actor:
            log_action(actor, 'create', 'group', group.pk, str(group))
        
        return group
    
    @staticmethod
    @transaction.atomic
    def update_group(
        group_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        responsible_id: Optional[int] = None,
        actor=None
    ) -> Optional[Group]:
        """Met à jour un groupe avec logging d'audit.
        
        Args:
            group_id: ID du groupe
            name: Nouveau nom
            description: Nouvelle description
            responsible_id: Nouveau responsable
            actor: Utilisateur effectuant l'action
            
        Returns:
            Instance du groupe mis à jour ou None
        """
        try:
            group = Group.objects.get(pk=group_id)
            
            changes = {}
            if name and name != group.name:
                changes['name'] = {'old': group.name, 'new': name}
                group.name = name
            if description is not None and description != group.description:
                changes['description'] = {'old': group.description, 'new': description}
                group.description = description
            if responsible_id is not None and responsible_id != group.responsible_id:
                changes['responsible'] = {'old': group.responsible_id, 'new': responsible_id}
                group.responsible_id = responsible_id
            
            if changes:
                group.save()
                if actor:
                    log_action(actor, 'update', 'group', group.pk, str(group), changes)
            
            return group
        except Group.DoesNotExist:
            return None
    
    @staticmethod
    @transaction.atomic
    def delete_group(group_id: int, actor=None) -> bool:
        """Supprime un groupe avec logging d'audit.
        
        Args:
            group_id: ID du groupe
            actor: Utilisateur effectuant l'action
            
        Returns:
            True si supprimé, False sinon
        """
        try:
            group = Group.objects.get(pk=group_id)
            group_repr = str(group)
            group.delete()
            
            if actor:
                log_action(actor, 'delete', 'group', group_id, group_repr)
            
            return True
        except Group.DoesNotExist:
            return False
    
    @staticmethod
    def get_group_statistics(group_id: int) -> Dict[str, Any]:
        """Calcule les statistiques pour un groupe.
        
        Args:
            group_id: ID du groupe
            
        Returns:
            Dictionnaire avec les statistiques
        """
        try:
            group = Group.objects.get(pk=group_id)
            
            total_contributions = group.contributions.aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            meeting_entries = group.meetings.values('meeting_entries__status').annotate(
                count=Count('meeting_entries__status')
            )
            
            attendance_data = {}
            total_attendance = 0
            for entry in meeting_entries:
                if entry['meeting_entries__status']:
                    attendance_data[entry['meeting_entries__status']] = entry['count']
                    total_attendance += entry['count']
            
            return {
                'group': group,
                'member_count': group.members.count(),
                'meeting_count': group.meetings.count(),
                'event_count': group.events.count(),
                'position_count': group.positions.count(),
                'organ_count': group.organs.count(),
                'total_contributions': total_contributions,
                'attendance_data': attendance_data,
                'total_attendance': total_attendance,
            }
        except Group.DoesNotExist:
            return {}
    
    @staticmethod
    def add_member_to_group(group_id: int, member_id: int, actor=None) -> bool:
        """Ajoute un membre à un groupe.
        
        Args:
            group_id: ID du groupe
            member_id: ID du membre
            actor: Utilisateur effectuant l'action
            
        Returns:
            True si ajouté, False sinon
        """
        try:
            group = Group.objects.get(pk=group_id)
            member = Member.objects.get(pk=member_id)
            
            group.members.add(member)
            
            if actor:
                log_action(actor, 'update', 'member', member_id, str(member), 
                         {'groups': {'added': group.name}})
            
            return True
        except (Group.DoesNotExist, Member.DoesNotExist):
            return False
    
    @staticmethod
    def remove_member_from_group(group_id: int, member_id: int, actor=None) -> bool:
        """Retire un membre d'un groupe.
        
        Args:
            group_id: ID du groupe
            member_id: ID du membre
            actor: Utilisateur effectuant l'action
            
        Returns:
            True si retiré, False sinon
        """
        try:
            group = Group.objects.get(pk=group_id)
            member = Member.objects.get(pk=member_id)
            
            group.members.remove(member)
            
            if actor:
                log_action(actor, 'update', 'member', member_id, str(member),
                         {'groups': {'removed': group.name}})
            
            return True
        except (Group.DoesNotExist, Member.DoesNotExist):
            return False
