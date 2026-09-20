"""Formulaires Django pour l'application core.

Ce module définit les formulaires ModelForm avec validation personnalisée
pour assurer la cohérence des données entre les modèles liés.
"""

from django import forms

from . import models


class PositionForm(forms.ModelForm):
    """Formulaire pour les postes avec validation de cohérence groupe/organe."""

    class Meta:
        model = models.Position
        fields = "__all__"

    def clean(self):
        """Valide que l'organe sélectionné appartient au même groupe."""
        cleaned_data = super().clean()
        group = cleaned_data.get("group")
        organ = cleaned_data.get("organ")
        if organ and group and organ.group_id != group.id:
            self.add_error("organ", "L'organe selectionne doit appartenir au meme groupe.")
        return cleaned_data


class MeetingEntryForm(forms.ModelForm):
    """Formulaire pour les présences aux rencontres avec validation d'appartenance."""

    class Meta:
        model = models.MeetingEntry
        fields = "__all__"

    def clean(self):
        """Valide que le membre appartient au groupe de la rencontre."""
        cleaned_data = super().clean()
        meeting = cleaned_data.get("meeting")
        member = cleaned_data.get("member")
        if meeting and member and not member.groups.filter(pk=meeting.group_id).exists():
            self.add_error("member", "Le membre doit appartenir au groupe de la rencontre.")
        return cleaned_data


class ContributionForm(forms.ModelForm):
    """Formulaire pour les cotisations avec validation d'appartenance."""

    class Meta:
        model = models.Contribution
        fields = "__all__"

    def clean(self):
        """Valide que le membre appartient au groupe de la cotisation."""
        cleaned_data = super().clean()
        group = cleaned_data.get("group")
        member = cleaned_data.get("member")
        if group and member and not member.groups.filter(pk=group.id).exists():
            self.add_error("member", "Le membre doit appartenir au groupe de la cotisation.")
        return cleaned_data


class MemberPaymentForm(forms.Form):
    """Formulaire d'initiation d'un paiement en ligne depuis le portail membre."""

    group = forms.ModelChoiceField(queryset=models.Group.objects.none(), label="Groupe")
    contribution_type = forms.ChoiceField(choices=models.Contribution.TYPE_CHOICES, label="Type")
    amount = forms.DecimalField(min_value=0.01, max_digits=10, decimal_places=2, label="Montant")

    def __init__(self, *args, member=None, **kwargs):
        """Restreint le choix de groupe aux groupes du membre connecté."""
        super().__init__(*args, **kwargs)
        if member is not None:
            self.fields["group"].queryset = member.groups.all()
