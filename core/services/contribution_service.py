"""Service Layer pour la gestion des cotisations.

Ce service encapsule toute la logique métier liée aux cotisations,
permettant une réutilisation entre les vues web et l'API REST.
"""

from typing import List, Optional, Dict, Any
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.core.exceptions import ValidationError
from django.utils import timezone

from ..models import Contribution, Member, Group
from ..audit import log_action


class ContributionService:
    """Service pour la gestion des cotisations."""
    
    @staticmethod
    def get_contribution_list(
        search_query: Optional[str] = None,
        group_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Contribution]:
        """Récupère la liste des cotisations avec filtres optionnels.
        
        Args:
            search_query: Recherche textuelle
            group_id: Filtre par groupe
            start_date: Date de début (format YYYY-MM-DD)
            end_date: Date de fin (format YYYY-MM-DD)
            
        Returns:
            Liste des cotisations filtrées
        """
        queryset = Contribution.objects.select_related('member', 'group')
        
        if search_query:
            queryset = queryset.filter(
                Q(member__full_name__icontains=search_query) |
                Q(group__name__icontains=search_query) |
                Q(contribution_type__icontains=search_query)
            )
        
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        
        if start_date:
            queryset = queryset.filter(paid_at__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(paid_at__lte=end_date)
            
        return queryset.order_by('-paid_at')
    
    @staticmethod
    def get_contribution_detail(contribution_id: int) -> Optional[Contribution]:
        """Récupère les détails d'une cotisation.
        
        Args:
            contribution_id: ID de la cotisation
            
        Returns:
            Instance de la cotisation ou None
        """
        try:
            return Contribution.objects.select_related('member', 'group').get(pk=contribution_id)
        except Contribution.DoesNotExist:
            return None
    
    @staticmethod
    @transaction.atomic
    def create_contribution(
        member_id: int,
        group_id: int,
        contribution_type: str,
        amount: str,
        paid_at: str,
        notes: str = "",
        payment_method: str = Contribution.METHOD_OTHER,
        payment_status: str = Contribution.STATUS_CONFIRMED,
        gateway_transaction_id: Optional[str] = None,
        actor=None
    ) -> Optional[Contribution]:
        """Crée une nouvelle cotisation avec validation et logging.

        Args:
            member_id: ID du membre
            group_id: ID du groupe
            contribution_type: Type de cotisation
            amount: Montant
            paid_at: Date de paiement
            notes: Notes optionnelles
            payment_method: Methode de paiement
            payment_status: Statut du paiement
            gateway_transaction_id: Identifiant de transaction de la passerelle de paiement
            actor: Utilisateur effectuant l'action

        Returns:
            Instance de la cotisation créée ou None si validation échoue
        """
        try:
            # Validation: le membre doit appartenir au groupe
            from .member_service import MemberService
            if not MemberService.validate_member_group_membership(member_id, group_id):
                raise ValidationError("Le membre doit appartenir au groupe de la cotisation.")
            
            # Validation: le montant doit être positif
            try:
                amount_float = float(amount)
                if amount_float <= 0:
                    raise ValidationError("Le montant doit être positif.")
            except ValueError:
                raise ValidationError("Le montant doit être un nombre valide.")
            
            contribution = Contribution.objects.create(
                member_id=member_id,
                group_id=group_id,
                contribution_type=contribution_type,
                amount=amount,
                paid_at=paid_at,
                notes=notes,
                payment_method=payment_method,
                payment_status=payment_status,
                gateway_transaction_id=gateway_transaction_id
            )
            
            if actor:
                log_action(actor, 'create', 'contribution', contribution.pk, str(contribution))
            
            return contribution
        except (Member.DoesNotExist, Group.DoesNotExist, ValidationError):
            return None
    
    @staticmethod
    @transaction.atomic
    def update_contribution(
        contribution_id: int,
        amount: Optional[str] = None,
        contribution_type: Optional[str] = None,
        paid_at: Optional[str] = None,
        notes: Optional[str] = None,
        payment_method: Optional[str] = None,
        payment_status: Optional[str] = None,
        actor=None
    ) -> Optional[Contribution]:
        """Met à jour une cotisation avec logging d'audit.

        Args:
            contribution_id: ID de la cotisation
            amount: Nouveau montant
            contribution_type: Nouveau type
            paid_at: Nouvelle date
            notes: Nouvelles notes
            payment_method: Nouvelle methode de paiement
            payment_status: Nouveau statut de paiement
            actor: Utilisateur effectuant l'action

        Returns:
            Instance de la cotisation mise à jour ou None
        """
        try:
            contribution = Contribution.objects.get(pk=contribution_id)
            
            changes = {}
            if amount is not None and amount != contribution.amount:
                # Validation du montant
                try:
                    amount_float = float(amount)
                    if amount_float <= 0:
                        raise ValidationError("Le montant doit être positif.")
                except ValueError:
                    raise ValidationError("Le montant doit être un nombre valide.")
                
                changes['amount'] = {'old': contribution.amount, 'new': amount}
                contribution.amount = amount
            
            if contribution_type and contribution_type != contribution.contribution_type:
                changes['contribution_type'] = {'old': contribution.contribution_type, 'new': contribution_type}
                contribution.contribution_type = contribution_type
            
            if paid_at and paid_at != str(contribution.paid_at):
                changes['paid_at'] = {'old': str(contribution.paid_at), 'new': paid_at}
                contribution.paid_at = paid_at
            
            if notes is not None and notes != contribution.notes:
                changes['notes'] = {'old': contribution.notes, 'new': notes}
                contribution.notes = notes

            if payment_method and payment_method != contribution.payment_method:
                changes['payment_method'] = {'old': contribution.payment_method, 'new': payment_method}
                contribution.payment_method = payment_method

            if payment_status and payment_status != contribution.payment_status:
                changes['payment_status'] = {'old': contribution.payment_status, 'new': payment_status}
                contribution.payment_status = payment_status

            if changes:
                contribution.save()
                # Journalise meme sans acteur (ex: webhook de paiement) : la
                # confirmation d'un paiement reel doit rester tracable meme
                # quand elle vient d'un systeme externe plutot que d'un
                # utilisateur connecte. log_action gere deja actor=None
                # (FK nullable sur AuditLog.actor).
                log_action(actor, 'update', 'contribution', contribution.pk, str(contribution), changes)

            return contribution
        except Contribution.DoesNotExist:
            return None
    
    @staticmethod
    @transaction.atomic
    def delete_contribution(contribution_id: int, actor=None) -> bool:
        """Supprime une cotisation avec logging d'audit.
        
        Args:
            contribution_id: ID de la cotisation
            actor: Utilisateur effectuant l'action
            
        Returns:
            True si supprimée, False sinon
        """
        try:
            contribution = Contribution.objects.get(pk=contribution_id)
            contribution_repr = str(contribution)
            contribution.delete()
            
            if actor:
                log_action(actor, 'delete', 'contribution', contribution_id, contribution_repr)
            
            return True
        except Contribution.DoesNotExist:
            return False
    
    @staticmethod
    def get_contribution_summary(group_id: Optional[int] = None) -> Dict[str, Any]:
        """Calcule un résumé des cotisations.
        
        Args:
            group_id: ID du groupe (optionnel)
            
        Returns:
            Dictionnaire avec le résumé des cotisations
        """
        queryset = Contribution.objects.all()

        if group_id:
            queryset = queryset.filter(group_id=group_id)

        total = queryset.filter(payment_status=Contribution.STATUS_CONFIRMED).aggregate(
            total_amount=Sum('amount'),
            count=Count('id')
        )
        
        # Par type de cotisation
        by_type = queryset.values('contribution_type').annotate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        return {
            'total_amount': total['total_amount'] or 0,
            'total_count': total['count'] or 0,
            'by_type': list(by_type),
        }
