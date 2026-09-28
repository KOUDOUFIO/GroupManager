"""Portail membre self-service : consultation de ses propres données et
paiement de ses cotisations par Mobile Money (PayGate Global)."""

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.generic import DetailView, FormView, ListView, TemplateView

from .. import forms as core_forms
from ..models import Contribution
from ..services.member_service import MemberService
from ..services.paygate_service import PayGateError, PayGateService
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
                "paygate_enabled": settings.PAYGATE_ENABLED,
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


class MemberPaymentView(MemberSelfRequiredMixin, FormView):
    """Demande de paiement Mobile Money (T-Money / Flooz) d'une cotisation."""
    template_name = "core/member_portal_payment_form.html"
    form_class = core_forms.MemberPaymentForm

    def dispatch(self, request, *args, **kwargs):
        """Page indisponible tant que PayGate n'est pas configure."""
        if not settings.PAYGATE_ENABLED:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Restreint le formulaire aux groupes du membre connecte."""
        kwargs = super().get_form_kwargs()
        kwargs["member"] = self.member
        return kwargs

    def form_valid(self, form):
        """Cree la cotisation en attente puis envoie la demande sur le telephone."""
        data = form.cleaned_data
        contribution = Contribution(
            member=self.member,
            group=data["group"],
            contribution_type=data["contribution_type"],
            amount=data["amount"],
            paid_at=timezone.localdate(),
            payment_method=Contribution.METHOD_MOBILE_MONEY,
            payment_status=Contribution.STATUS_PENDING,
            gateway_transaction_id=PayGateService.new_identifier(),
            payer_phone=data["phone_number"],
            notes=f"Mobile Money {data['network']}",
        )
        contribution.save()
        try:
            contribution.gateway_reference = PayGateService.request_payment(
                identifier=contribution.gateway_transaction_id,
                amount=contribution.amount,
                phone_number=contribution.payer_phone,
                network=data["network"],
                description=f"{contribution.get_contribution_type_display()} - {contribution.group.name}",
            )
        except PayGateError:
            contribution.delete()
            form.add_error(None, _("Le paiement n'a pas pu être lancé. Vérifiez le numéro et réessayez dans quelques instants."))
            return self.form_invalid(form)
        contribution.save(update_fields=["gateway_reference"])
        return redirect("member_portal_payment_status", pk=contribution.pk)


class MemberPaymentStatusView(MemberSelfRequiredMixin, DetailView):
    """Suivi d'un paiement Mobile Money : attente de confirmation sur le telephone."""
    template_name = "core/member_portal_payment_status.html"
    context_object_name = "contribution"

    def get_queryset(self):
        """Uniquement les paiements en ligne du membre connecte."""
        return self.member.contributions.select_related("group").exclude(gateway_transaction_id=None)

    def post(self, request, *args, **kwargs):
        """Bouton "Verifier" : interroge PayGate pour mettre a jour le statut."""
        contribution = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        status = PayGateService.sync_contribution(contribution) if settings.PAYGATE_ENABLED else contribution.payment_status
        if status == Contribution.STATUS_PENDING:
            messages.info(request, _("Paiement toujours en attente. Confirmez-le sur votre téléphone avec votre code secret."))
        return redirect("member_portal_payment_status", pk=contribution.pk)
