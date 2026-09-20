"""Service Layer pour la gestion des membres.

Ce service encapsule toute la logique métier liée aux membres,
permettant une réutilisation entre les vues web et l'API REST.
"""

from typing import List, Optional, Dict, Any
from django.db import transaction
from django.db.models import Q, Count, Sum
from django.core.exceptions import ValidationError

from ..models import Member, Group, Contribution, MeetingEntry
from ..audit import log_action


class MemberService:
    """Service pour la gestion des membres."""
    
    @staticmethod
    def get_member_list(
        search_query: Optional[str] = None,
        group_id: Optional[int] = None
    ) -> List[Member]:
        """Récupère la liste des membres avec filtres optionnels.
        
        Args:
            search_query: Recherche textuelle sur nom/email/téléphone
            group_id: Filtre par groupe
            
        Returns:
            Liste des membres filtrés
        """
        queryset = Member.objects.prefetch_related('groups').annotate(
            group_count=Count('groups', distinct=True),
            contribution_total=Sum(
                'contributions__amount',
                filter=Q(contributions__payment_status=Contribution.STATUS_CONFIRMED)
            )
        )
        
        if search_query:
            queryset = queryset.filter(
                Q(full_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query)
            )
        
        if group_id:
            queryset = queryset.filter(groups__id=group_id)
            
        return queryset.distinct().order_by('full_name')
    
    @staticmethod
    def get_member_detail(member_id: int) -> Optional[Member]:
        """Récupère les détails d'un membre avec ses relations.
        
        Args:
            member_id: ID du membre
            
        Returns:
            Instance du membre ou None
        """
        try:
            return Member.objects.prefetch_related(
                'groups', 'positions', 'contributions__group', 
                'meeting_entries__meeting__group'
            ).get(pk=member_id)
        except Member.DoesNotExist:
            return None
    
    @staticmethod
    @transaction.atomic
    def create_member(
        full_name: str,
        email: str = "",
        phone: str = "",
        address: str = "",
        actor=None
    ) -> Member:
        """Crée un nouveau membre avec logging d'audit.
        
        Args:
            full_name: Nom complet du membre
            email: Email du membre
            phone: Téléphone du membre
            address: Adresse du membre
            actor: Utilisateur effectuant l'action
            
        Returns:
            Instance du membre créé
        """
        member = Member.objects.create(
            full_name=full_name,
            email=email,
            phone=phone,
            address=address
        )
        
        if actor:
            log_action(actor, 'create', 'member', member.pk, str(member))
        
        return member
    
    @staticmethod
    @transaction.atomic
    def update_member(
        member_id: int,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        actor=None
    ) -> Optional[Member]:
        """Met à jour un membre avec logging d'audit.
        
        Args:
            member_id: ID du membre
            full_name: Nouveau nom complet
            email: Nouvel email
            phone: Nouveau téléphone
            address: Nouvelle adresse
            actor: Utilisateur effectuant l'action
            
        Returns:
            Instance du membre mis à jour ou None
        """
        try:
            member = Member.objects.get(pk=member_id)
            
            changes = {}
            if full_name and full_name != member.full_name:
                changes['full_name'] = {'old': member.full_name, 'new': full_name}
                member.full_name = full_name
            if email is not None and email != member.email:
                changes['email'] = {'old': member.email, 'new': email}
                member.email = email
            if phone is not None and phone != member.phone:
                changes['phone'] = {'old': member.phone, 'new': phone}
                member.phone = phone
            if address is not None and address != member.address:
                changes['address'] = {'old': member.address, 'new': address}
                member.address = address
            
            if changes:
                member.save()
                if actor:
                    log_action(actor, 'update', 'member', member.pk, str(member), changes)
            
            return member
        except Member.DoesNotExist:
            return None
    
    @staticmethod
    @transaction.atomic
    def delete_member(member_id: int, actor=None) -> bool:
        """Supprime un membre avec logging d'audit.
        
        Args:
            member_id: ID du membre
            actor: Utilisateur effectuant l'action
            
        Returns:
            True si supprimé, False sinon
        """
        try:
            member = Member.objects.get(pk=member_id)
            member_repr = str(member)
            member.delete()
            
            if actor:
                log_action(actor, 'delete', 'member', member_id, member_repr)
            
            return True
        except Member.DoesNotExist:
            return False
    
    @staticmethod
    def get_member_statistics(member_id: int) -> Dict[str, Any]:
        """Calcule les statistiques pour un membre.
        
        Args:
            member_id: ID du membre
            
        Returns:
            Dictionnaire avec les statistiques
        """
        try:
            member = Member.objects.get(pk=member_id)
            
            total_contributions = member.contributions.filter(
                payment_status=Contribution.STATUS_CONFIRMED
            ).aggregate(
                total=Sum('amount'),
                count=Count('id')
            )
            
            meeting_entries = member.meeting_entries.all()
            total_meetings = meeting_entries.count()
            present_count = meeting_entries.filter(
                status__in=['present', 'late', 'permission']
            ).count()
            
            attendance_rate = (present_count / total_meetings * 100) if total_meetings > 0 else 0
            
            return {
                'member': member,
                'group_count': member.groups.count(),
                'position_count': member.positions.count(),
                'contribution_total': total_contributions['total'] or 0,
                'contribution_count': total_contributions['count'] or 0,
                'meeting_count': total_meetings,
                'attendance_rate': round(attendance_rate, 1),
            }
        except Member.DoesNotExist:
            return {}
    
    @staticmethod
    def validate_member_group_membership(member_id: int, group_id: int) -> bool:
        """Valide qu'un membre appartient bien à un groupe.
        
        Args:
            member_id: ID du membre
            group_id: ID du groupe
            
        Returns:
            True si le membre appartient au groupe, False sinon
        """
        try:
            member = Member.objects.get(pk=member_id)
            return member.groups.filter(id=group_id).exists()
        except Member.DoesNotExist:
            return False
