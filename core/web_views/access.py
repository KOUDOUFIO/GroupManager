"""Page "Acces a Mon espace" d'un membre (gestionnaires et administrateurs)."""

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views import View

from .. import models
from ..services.access_service import AccessService, suggest_username


class AccessForm(forms.Form):
    """Identifiant du futur compte du membre."""
    username = forms.RegexField(
        label=gettext_lazy("Identifiant de connexion"), max_length=150, regex=r"^[\w.@+-]+$",
        error_messages={"invalid": gettext_lazy("Lettres, chiffres et . @ + - _ seulement, sans espace.")},
    )

    def clean_username(self):
        """Refuse un identifiant deja utilise."""
        username = self.cleaned_data["username"]
        if get_user_model().objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(_("Cet identifiant est déjà utilisé."))
        return username


class MemberAccessView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Donne ou retire l'acces d'un membre a son espace."""
    template_name = "core/member_access.html"
    raise_exception = True

    def test_func(self):
        """Administrateurs et gestionnaires ayant le droit de modifier les membres."""
        user = self.request.user
        is_manager = user.is_staff or user.groups.filter(name__in=["Gestionnaire", "Administrateur"]).exists()
        return is_manager and user.has_perm("core.change_member")

    def _render(self, request, member, form=None, **extra):
        return render(request, self.template_name, {
            "member": member,
            "form": form or AccessForm(initial={"username": suggest_username(member)}),
            **extra,
        })

    def get(self, request, pk):
        """Affiche l'etat de l'acces du membre."""
        return self._render(request, get_object_or_404(models.Member, pk=pk))

    def post(self, request, pk):
        """Cree ou retire l'acces."""
        member = get_object_or_404(models.Member, pk=pk)
        if request.POST.get("action") == "revoke":
            AccessService.revoke(member)
            messages.success(request, _("L'accès de %(name)s est retiré. Son historique est conservé.") % {"name": member.full_name})
            return redirect("member_access", pk=member.pk)

        if member.user_id:
            return redirect("member_access", pk=member.pk)
        form = AccessForm(request.POST)
        if not form.is_valid():
            return self._render(request, member, form)
        user, email_sent, temporary_password = AccessService.grant(member, form.cleaned_data["username"], request)
        return self._render(request, member, granted=True, username=user.username,
                            email_sent=email_sent, temporary_password=temporary_password)
