"""Portail membre self-service : consultation en lecture seule de ses propres données,
et initiation de paiement en ligne via CinetPay."""

import uuid

from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import FormView, ListView, TemplateView

from .. import forms as core_forms
from ..models import Contribution
from ..services.contribution_service import ContributionService
from ..services.cinetpay_service import CinetPayService
from ..services.member_service import MemberService
from .mixins import MemberSelfRequiredMixin


class MemberPortalDashboardView(MemberSelfRequiredMixin, TemplateView):
    """Tableau de bord personnel du membre connecté."""
    template_name = "core/member_portal_dashboard.html"

    def get_context_data(self, **kwargs):
        """Fournit les statistiques et l'activité récente du membre connecté."""
        context = super().get_context_data(**kwargs)
        context.update(MemberService.get_member_statistics(self.member.id))
        context.update(
            {
                "recent_contributions": self.member.contributions.select_related("group").order_by("-paid_at")[:8],
                "recent_attendance": self.member.meeting_entries.select_related(
                    "meeting", "meeting__group"
                ).order_by("-meeting__scheduled_at")[:8],
                "member_groups": self.member.groups.all(),
                "cinetpay_enabled": settings.CINETPAY_ENABLED,
            }
        )
        return context


class MemberContributionsListView(MemberSelfRequiredMixin, ListView):
    """Liste paginée des cotisations du membre connecté."""
    template_name = "core/member_portal_contributions.html"
    paginate_by = 10

    def get_queryset(self):
        """Cotisations du membre connecté uniquement."""
        return self.member.contributions.select_related("group").order_by("-paid_at")


class MemberAttendanceListView(MemberSelfRequiredMixin, ListView):
    """Liste paginée des présences aux rencontres du membre connecté."""
    template_name = "core/member_portal_attendance.html"
    paginate_by = 10

    def get_queryset(self):
        """Présences du membre connecté uniquement."""
        return self.member.meeting_entries.select_related("meeting", "meeting__group").order_by(
            "-meeting__scheduled_at"
        )


class MemberPaymentInitiateView(MemberSelfRequiredMixin, FormView):
    """Initie un paiement en ligne (CinetPay) pour une cotisation du membre connecté."""
    template_name = "core/member_portal_payment_form.html"
    form_class = core_forms.MemberPaymentForm

    def get_form_kwargs(self):
        """Restreint le formulaire aux groupes du membre connecté."""
        kwargs = super().get_form_kwargs()
        kwargs["member"] = self.member
        return kwargs

    def get_context_data(self, **kwargs):
        """Fournit le contexte avec l'etat de la passerelle de paiement."""
        context = super().get_context_data(**kwargs)
        context["cinetpay_enabled"] = settings.CINETPAY_ENABLED
        return context

    def form_valid(self, form):
        """Cree une cotisation en attente et redirige vers la page de paiement CinetPay."""
        if not settings.CINETPAY_ENABLED:
            form.add_error(None, "Le paiement en ligne n'est pas disponible pour le moment.")
            return self.form_invalid(form)

        transaction_id = uuid.uuid4().hex
        group = form.cleaned_data["group"]
        contribution_type = form.cleaned_data["contribution_type"]
        amount = form.cleaned_data["amount"]

        contribution = ContributionService.create_contribution(
            member_id=self.member.id,
            group_id=group.id,
            contribution_type=contribution_type,
            amount=str(amount),
            paid_at=str(timezone.now().date()),
            notes="Paiement en ligne CinetPay",
            payment_method=Contribution.METHOD_MOBILE_MONEY,
            payment_status=Contribution.STATUS_PENDING,
            gateway_transaction_id=transaction_id,
            actor=self.request.user,
        )
        if contribution is None:
            form.add_error(None, "Impossible de creer la cotisation. Verifiez les informations saisies.")
            return self.form_invalid(form)

        payment_data = CinetPayService.initiate_payment(
            transaction_id=transaction_id,
            amount=int(amount),
            description=f"Cotisation {contribution.get_contribution_type_display()} - {group.name}",
            notify_url=self.request.build_absolute_uri(reverse("cinetpay_webhook")),
            return_url=self.request.build_absolute_uri(reverse("member_portal_contributions")) + "?paiement=en_attente",
        )
        if not payment_data or not payment_data.get("payment_url"):
            contribution.delete()
            form.add_error(None, "La passerelle de paiement n'a pas pu etre contactee. Reessayez plus tard.")
            return self.form_invalid(form)

        return HttpResponseRedirect(payment_data["payment_url"])
