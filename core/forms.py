"""Formulaires Django pour l'application core.

Ce module définit les formulaires ModelForm avec validation personnalisée
pour assurer la cohérence des données entre les modèles liés.
"""

from django import forms

from . import models
from django.utils.translation import gettext, gettext_lazy as _


def polish_form(form):
    """Rend un formulaire de gestion agreable a utiliser.

    Calendrier pour les dates, cases a cocher pour les choix multiples et
    "Choisissez..." a la place de "---------" dans les listes.
    """
    for field in form.fields.values():
        if isinstance(field, forms.ModelMultipleChoiceField):
            field.widget = forms.CheckboxSelectMultiple(choices=field.widget.choices)
        elif isinstance(field, forms.ModelChoiceField):
            field.empty_label = _("Choisissez...")
        elif isinstance(field, forms.DateTimeField):
            field.widget = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")
            field.input_formats = ["%Y-%m-%dT%H:%M", *(field.input_formats or [])]
        elif isinstance(field, forms.DateField):
            field.widget = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
            field.input_formats = ["%Y-%m-%d", *(field.input_formats or [])]
        if isinstance(field, forms.TypedChoiceField) and field.choices and field.choices[0][0] == "":
            field.choices = [("", _("Choisissez..."))] + list(field.choices)[1:]
    return form


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
        exclude = ["gateway_transaction_id"]

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

    # Champ piege invisible : un robot le remplit, un humain ne le voit pas.
    website = forms.CharField(required=False, label="", widget=forms.TextInput(attrs={
        "autocomplete": "off", "tabindex": "-1",
    }))

    class Meta:
        model = models.ProposalRequest
        fields = ["name", "email", "phone", "company", "organization_type", "plan", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Votre nom"), "autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"placeholder": _("nom@entreprise.com"), "autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"placeholder": _("90 12 34 56"), "autocomplete": "tel", "inputmode": "tel"}),
            "company": forms.TextInput(attrs={"placeholder": _("Nom de l'organisation"), "autocomplete": "organization"}),
            "message": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": _("Décrivez votre besoin, le nombre d'utilisateurs, les groupes et les priorités..."),
            }),
        }
        labels = {
            "name": _("Nom"),
            "email": _("Email"),
            "phone": _("Téléphone / WhatsApp"),
            "company": _("Organisation"),
            "organization_type": _("Type d'organisation"),
            "plan": _("Formule souhaitée"),
            "message": _("Besoin principal"),
        }

    def __init__(self, *args, **kwargs):
        """Remplace les tirets des listes par un texte clair."""
        super().__init__(*args, **kwargs)
        self.fields["organization_type"].choices = [("", _("Choisissez..."))] + list(
            models.ProposalRequest.ORG_TYPE_CHOICES
        )
        self.fields["plan"].choices = [("", _("Je ne sais pas encore"))] + list(models.ProposalRequest.PLAN_CHOICES)

    def is_spam(self):
        """Vrai si le champ piege a ete rempli (robot)."""
        return bool(self.cleaned_data.get("website"))

    def clean_phone(self):
        """Normalise le numero s'il est renseigne (+228...)."""
        from .services.phone import normalize_phone

        raw = self.cleaned_data.get("phone", "").strip()
        if not raw:
            return ""
        phone = normalize_phone(raw)
        if not phone:
            raise forms.ValidationError(_("Numéro de téléphone invalide."))
        return phone

