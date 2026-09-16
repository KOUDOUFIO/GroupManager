"""Tests pour les Services Layer - GroupManager

Ce module contient les tests unitaires pour les services métier,
assurant que la logique business fonctionne correctement.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import AuditLog, Group, Member, Meeting, Contribution, MeetingEntry
from .services import GroupService, MemberService, ContributionService, MeetingService

User = get_user_model()


class GroupServiceTests(TestCase):
    """Tests pour GroupService."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.group = Group.objects.create(name='Test Group', description='Test Description')
    
    def test_get_group_list_basic(self):
        """Test récupération basique de la liste des groupes."""
        groups = GroupService.get_group_list()
        self.assertEqual(groups.count(), 1)
        self.assertEqual(groups.first().name, 'Test Group')
    
    def test_get_group_list_with_search(self):
        """Test recherche dans la liste des groupes."""
        Group.objects.create(name='Another Group')
        groups = GroupService.get_group_list(search_query='Test')
        self.assertEqual(groups.count(), 1)
        
        groups = GroupService.get_group_list(search_query='Another')
        self.assertEqual(groups.count(), 1)
    
    def test_get_group_detail(self):
        """Test récupération des détails d'un groupe."""
        group = GroupService.get_group_detail(self.group.id)
        self.assertIsNotNone(group)
        self.assertEqual(group.name, 'Test Group')
    
    def test_get_group_detail_not_found(self):
        """Test récupération d'un groupe inexistant."""
        group = GroupService.get_group_detail(99999)
        self.assertIsNone(group)
    
    def test_create_group(self):
        """Test création d'un groupe."""
        group = GroupService.create_group(
            name='New Group',
            description='New Description',
            actor=self.user
        )
        self.assertIsNotNone(group)
        self.assertEqual(group.name, 'New Group')
        
        # Vérifier l'audit log
        log = AuditLog.objects.filter(
            model_name='group',
            action=AuditLog.ACTION_CREATE
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.user)
    
    def test_update_group(self):
        """Test mise à jour d'un groupe."""
        updated = GroupService.update_group(
            self.group.id,
            name='Updated Group',
            actor=self.user
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.name, 'Updated Group')
        
        # Vérifier l'audit log
        log = AuditLog.objects.filter(
            model_name='group',
            action=AuditLog.ACTION_UPDATE
        ).first()
        self.assertIsNotNone(log)
        self.assertIn('name', log.changes)
    
    def test_delete_group(self):
        """Test suppression d'un groupe."""
        result = GroupService.delete_group(self.group.id, actor=self.user)
        self.assertTrue(result)
        
        # Vérifier que le groupe est supprimé
        self.assertFalse(Group.objects.filter(id=self.group.id).exists())
        
        # Vérifier l'audit log
        log = AuditLog.objects.filter(
            model_name='group',
            action=AuditLog.ACTION_DELETE
        ).first()
        self.assertIsNotNone(log)
    
    def test_get_group_statistics(self):
        """Test calcul des statistiques d'un groupe."""
        member = Member.objects.create(full_name='Test Member')
        self.group.members.add(member)
        
        stats = GroupService.get_group_statistics(self.group.id)
        self.assertIsNotNone(stats)
        self.assertEqual(stats['member_count'], 1)
        self.assertIn('group', stats)
    
    def test_add_member_to_group(self):
        """Test ajout d'un membre à un groupe."""
        member = Member.objects.create(full_name='Test Member')
        result = GroupService.add_member_to_group(self.group.id, member.id, actor=self.user)
        self.assertTrue(result)
        self.assertTrue(self.group.members.filter(id=member.id).exists())
    
    def test_remove_member_from_group(self):
        """Test retrait d'un membre d'un groupe."""
        member = Member.objects.create(full_name='Test Member')
        self.group.members.add(member)
        
        result = GroupService.remove_member_from_group(self.group.id, member.id, actor=self.user)
        self.assertTrue(result)
        self.assertFalse(self.group.members.filter(id=member.id).exists())


class MemberServiceTests(TestCase):
    """Tests pour MemberService."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.member = Member.objects.create(
            full_name='Test Member',
            email='test@example.com',
            phone='1234567890'
        )
        self.group = Group.objects.create(name='Test Group')
    
    def test_get_member_list_basic(self):
        """Test récupération basique de la liste des membres."""
        members = MemberService.get_member_list()
        self.assertEqual(members.count(), 1)
        self.assertEqual(members.first().full_name, 'Test Member')
    
    def test_get_member_list_with_search(self):
        """Test recherche dans la liste des membres."""
        Member.objects.create(full_name='Another Member')
        members = MemberService.get_member_list(search_query='Test')
        self.assertEqual(members.count(), 1)
    
    def test_get_member_detail(self):
        """Test récupération des détails d'un membre."""
        member = MemberService.get_member_detail(self.member.id)
        self.assertIsNotNone(member)
        self.assertEqual(member.full_name, 'Test Member')
    
    def test_create_member(self):
        """Test création d'un membre."""
        member = MemberService.create_member(
            full_name='New Member',
            email='new@example.com',
            actor=self.user
        )
        self.assertIsNotNone(member)
        self.assertEqual(member.full_name, 'New Member')
        
        # Vérifier l'audit log
        log = AuditLog.objects.filter(
            model_name='member',
            action=AuditLog.ACTION_CREATE
        ).first()
        self.assertIsNotNone(log)
    
    def test_update_member(self):
        """Test mise à jour d'un membre."""
        updated = MemberService.update_member(
            self.member.id,
            full_name='Updated Member',
            actor=self.user
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.full_name, 'Updated Member')
    
    def test_delete_member(self):
        """Test suppression d'un membre."""
        result = MemberService.delete_member(self.member.id, actor=self.user)
        self.assertTrue(result)
        self.assertFalse(Member.objects.filter(id=self.member.id).exists())
    
    def test_get_member_statistics(self):
        """Test calcul des statistiques d'un membre."""
        self.member.groups.add(self.group)
        
        stats = MemberService.get_member_statistics(self.member.id)
        self.assertIsNotNone(stats)
        self.assertEqual(stats['group_count'], 1)
        self.assertIn('member', stats)
    
    def test_validate_member_group_membership(self):
        """Test validation de l'appartenance à un groupe."""
        self.member.groups.add(self.group)
        
        result = MemberService.validate_member_group_membership(
            self.member.id, self.group.id
        )
        self.assertTrue(result)
        
        # Test avec un groupe différent
        other_group = Group.objects.create(name='Other Group')
        result = MemberService.validate_member_group_membership(
            self.member.id, other_group.id
        )
        self.assertFalse(result)


class ContributionServiceTests(TestCase):
    """Tests pour ContributionService."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.group = Group.objects.create(name='Test Group')
        self.member = Member.objects.create(full_name='Test Member')
        self.member.groups.add(self.group)
    
    def test_get_contribution_list_basic(self):
        """Test récupération basique de la liste des cotisations."""
        contribution = Contribution.objects.create(
            member=self.member,
            group=self.group,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount='100.00',
            paid_at='2025-01-01'
        )
        
        contributions = ContributionService.get_contribution_list()
        self.assertEqual(contributions.count(), 1)
    
    def test_create_contribution(self):
        """Test création d'une cotisation."""
        contribution = ContributionService.create_contribution(
            member_id=self.member.id,
            group_id=self.group.id,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount='50.00',
            paid_at='2025-01-15',
            actor=self.user
        )
        self.assertIsNotNone(contribution)
        self.assertEqual(float(contribution.amount), 50.00)
    
    def test_create_contribution_invalid_member_not_in_group(self):
        """Test création avec membre hors du groupe (doit échouer)."""
        other_group = Group.objects.create(name='Other Group')
        other_member = Member.objects.create(full_name='Other Member')
        other_member.groups.add(other_group)
        
        contribution = ContributionService.create_contribution(
            member_id=other_member.id,
            group_id=self.group.id,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount='50.00',
            paid_at='2025-01-15'
        )
        self.assertIsNone(contribution)
    
    def test_create_contribution_invalid_amount(self):
        """Test création avec montant négatif (doit échouer)."""
        contribution = ContributionService.create_contribution(
            member_id=self.member.id,
            group_id=self.group.id,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount='-50.00',
            paid_at='2025-01-15'
        )
        self.assertIsNone(contribution)
    
    def test_update_contribution(self):
        """Test mise à jour d'une cotisation."""
        contribution = Contribution.objects.create(
            member=self.member,
            group=self.group,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount='100.00',
            paid_at='2025-01-01'
        )
        
        updated = ContributionService.update_contribution(
            contribution.id,
            amount='150.00',
            actor=self.user
        )
        self.assertIsNotNone(updated)
        self.assertEqual(float(updated.amount), 150.00)
    
    def test_delete_contribution(self):
        """Test suppression d'une cotisation."""
        contribution = Contribution.objects.create(
            member=self.member,
            group=self.group,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount='100.00',
            paid_at='2025-01-01'
        )
        
        result = ContributionService.delete_contribution(contribution.id, actor=self.user)
        self.assertTrue(result)
        self.assertFalse(Contribution.objects.filter(id=contribution.id).exists())
    
    def test_get_contribution_summary(self):
        """Test calcul du résumé des cotisations."""
        Contribution.objects.create(
            member=self.member,
            group=self.group,
            contribution_type=Contribution.TYPE_MONTHLY,
            amount='100.00',
            paid_at='2025-01-01'
        )
        Contribution.objects.create(
            member=self.member,
            group=self.group,
            contribution_type=Contribution.TYPE_ANNUAL,
            amount='200.00',
            paid_at='2025-01-15'
        )
        
        summary = ContributionService.get_contribution_summary()
        self.assertEqual(summary['total_amount'], 300.00)
        self.assertEqual(summary['total_count'], 2)


class MeetingServiceTests(TestCase):
    """Tests pour MeetingService."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.group = Group.objects.create(name='Test Group')
        self.member = Member.objects.create(full_name='Test Member')
        self.member.groups.add(self.group)
    
    def test_get_meeting_list_basic(self):
        """Test récupération basique de la liste des rencontres."""
        meeting = Meeting.objects.create(
            group=self.group,
            title='Test Meeting',
            scheduled_at='2025-01-01'
        )
        
        meetings = MeetingService.get_meeting_list()
        self.assertEqual(meetings.count(), 1)
    
    def test_create_meeting(self):
        """Test création d'une rencontre."""
        meeting = MeetingService.create_meeting(
            group_id=self.group.id,
            title='New Meeting',
            scheduled_at='2025-02-01',
            actor=self.user
        )
        self.assertIsNotNone(meeting)
        self.assertEqual(meeting.title, 'New Meeting')
    
    def test_update_meeting(self):
        """Test mise à jour d'une rencontre."""
        meeting = Meeting.objects.create(
            group=self.group,
            title='Test Meeting',
            scheduled_at='2025-01-01'
        )
        
        updated = MeetingService.update_meeting(
            meeting.id,
            title='Updated Meeting',
            actor=self.user
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.title, 'Updated Meeting')
    
    def test_delete_meeting(self):
        """Test suppression d'une rencontre."""
        meeting = Meeting.objects.create(
            group=self.group,
            title='Test Meeting',
            scheduled_at='2025-01-01'
        )
        
        result = MeetingService.delete_meeting(meeting.id, actor=self.user)
        self.assertTrue(result)
        self.assertFalse(Meeting.objects.filter(id=meeting.id).exists())
    
    def test_create_meeting_entry(self):
        """Test création d'une présence."""
        meeting = Meeting.objects.create(
            group=self.group,
            title='Test Meeting',
            scheduled_at='2025-01-01'
        )
        
        entry = MeetingService.create_meeting_entry(
            meeting_id=meeting.id,
            member_id=self.member.id,
            status=MeetingEntry.STATUS_PRESENT,
            actor=self.user
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry.status, MeetingEntry.STATUS_PRESENT)
    
    def test_create_meeting_entry_invalid_member_not_in_group(self):
        """Test création avec membre hors du groupe (doit échouer)."""
        other_group = Group.objects.create(name='Other Group')
        other_member = Member.objects.create(full_name='Other Member')
        other_member.groups.add(other_group)
        
        meeting = Meeting.objects.create(
            group=self.group,
            title='Test Meeting',
            scheduled_at='2025-01-01'
        )
        
        entry = MeetingService.create_meeting_entry(
            meeting_id=meeting.id,
            member_id=other_member.id,
            status=MeetingEntry.STATUS_PRESENT
        )
        self.assertIsNone(entry)
    
    def test_update_meeting_entry(self):
        """Test mise à jour d'une présence."""
        meeting = Meeting.objects.create(
            group=self.group,
            title='Test Meeting',
            scheduled_at='2025-01-01'
        )
        entry = MeetingEntry.objects.create(
            meeting=meeting,
            member=self.member,
            status=MeetingEntry.STATUS_PRESENT
        )
        
        updated = MeetingService.update_meeting_entry(
            entry.id,
            status=MeetingEntry.STATUS_LATE,
            actor=self.user
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, MeetingEntry.STATUS_LATE)
    
    def test_delete_meeting_entry(self):
        """Test suppression d'une présence."""
        meeting = Meeting.objects.create(
            group=self.group,
            title='Test Meeting',
            scheduled_at='2025-01-01'
        )
        entry = MeetingEntry.objects.create(
            meeting=meeting,
            member=self.member,
            status=MeetingEntry.STATUS_PRESENT
        )
        
        result = MeetingService.delete_meeting_entry(entry.id, actor=self.user)
        self.assertTrue(result)
        self.assertFalse(MeetingEntry.objects.filter(id=entry.id).exists())
    
    def test_get_attendance_statistics(self):
        """Test calcul des statistiques de présence."""
        meeting = Meeting.objects.create(
            group=self.group,
            title='Test Meeting',
            scheduled_at='2025-01-01'
        )
        
        MeetingEntry.objects.create(
            meeting=meeting,
            member=self.member,
            status=MeetingEntry.STATUS_PRESENT
        )
        
        stats = MeetingService.get_attendance_statistics()
        self.assertEqual(stats['total_entries'], 1)
        self.assertEqual(stats['present_count'], 1)
        self.assertEqual(stats['attendance_rate'], 100.0)
