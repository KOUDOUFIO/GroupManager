"""Formulaires Django pour l'application core.

Ce module définit les formulaires ModelForm avec validation personnalisée
pour assurer la cohérence des données entre les modèles liés.
"""

from django import forms

from . import models
from django.utils.translation import gettext, gettext_lazy as _


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
            self.add_error("organ", gettext("L'organe sélectionné doit appartenir au même groupe."))
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
            self.add_error("member", gettext("Le membre doit appartenir au groupe de la rencontre."))
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
            self.add_error("member", gettext("Le membre doit appartenir au groupe de la cotisation."))
        return cleaned_data


class ProposalRequestForm(forms.ModelForm):
    """Formulaire de demande de devis depuis la page vitrine."""

    class Meta:
        model = models.ProposalRequest
        fields = ["name", "email", "company", "organization_type", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Votre nom")}),
            "email": forms.EmailInput(attrs={"placeholder": _("nom@entreprise.com")}),
            "company": forms.TextInput(attrs={"placeholder": _("Nom de l'organisation")}),
            "message": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": _("Décrivez votre besoin, le nombre d'utilisateurs, les groupes et les priorités..."),
            }),
        }
        labels = {
            "name": _("Nom"),
            "email": _("Email"),
            "company": _("Entreprise"),
            "organization_type": _("Type d'organisation"),
            "message": _("Besoin principal"),
        }
