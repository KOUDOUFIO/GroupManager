"""Recu PDF d'une cotisation confirmee."""

from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext as _
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A5
from reportlab.pdfgen import canvas

from .. import models
from ..templatetags.core_extras import money

GREEN = HexColor("#0b3d1f")
GOLD = HexColor("#c7851a")
GREY = HexColor("#64748b")
LINE = HexColor("#e2e8f0")


def receipt_number(contribution) -> str:
    """Numero de recu stable : R-2026-00042."""
    return f"R-{contribution.paid_at.year}-{contribution.pk:05d}"


def _can_see(user, contribution) -> bool:
    if user.has_perm("core.view_contribution"):
        return True
    member = getattr(user, "member_profile", None)
    return member is not None and contribution.member_id == member.id


@login_required
def contribution_receipt(request, pk):
    """Telecharge le recu PDF d'une cotisation confirmee."""
    contribution = get_object_or_404(models.Contribution.objects.select_related("member", "group"), pk=pk)
    if not _can_see(request.user, contribution):
        raise PermissionDenied
    if contribution.payment_status != models.Contribution.STATUS_CONFIRMED:
        raise Http404(_("Seule une cotisation confirmée donne droit à un reçu."))

    number = receipt_number(contribution)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="recu-{number}.pdf"'
    width, height = A5
    pdf = canvas.Canvas(response, pagesize=A5)
    pdf.setTitle(f"{_('Reçu de cotisation')} {number}")

    # Bandeau vert avec le logo et le nom du groupe emetteur.
    pdf.setFillColor(GREEN)
    pdf.rect(0, height - 90, width, 90, stroke=0, fill=1)
    logo = finders.find("core/img/logo-192.png")
    if logo:
        try:
            pdf.drawImage(logo, 28, height - 72, width=48, height=48, mask="auto")
        except Exception:  # pragma: no cover - image illisible : le recu reste valable sans logo
            pass
    pdf.setFillColor(HexColor("#ffffff"))
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(88, height - 46, contribution.group.name[:40])
    pdf.setFont("Helvetica", 9)
    pdf.drawString(88, height - 62, _("Reçu établi avec Kotiza"))

    # Titre et numero.
    y = height - 128
    pdf.setFillColor(GREEN)
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawString(28, y, _("Reçu de cotisation"))
    pdf.setFillColor(GOLD)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawRightString(width - 28, y, number)

    # Lignes de detail.
    rows = [
        (_("Membre"), contribution.member.full_name),
        (_("Groupe"), contribution.group.name),
        (_("Type"), contribution.get_contribution_type_display()),
        (_("Moyen de paiement"), contribution.get_payment_method_display()),
        (_("Date de paiement"), date_format(contribution.paid_at, "j F Y")),
    ]
    y -= 30
    for label, value in rows:
        pdf.setFillColor(GREY)
        pdf.setFont("Helvetica", 9)
        pdf.drawString(28, y, label)
        pdf.setFillColor(HexColor("#0f172a"))
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawRightString(width - 28, y, str(value)[:48])
        pdf.setStrokeColor(LINE)
        pdf.line(28, y - 8, width - 28, y - 8)
        y -= 26

    # Montant mis en valeur.
    y -= 14
    pdf.setFillColor(HexColor("#f0fdf4"))
    pdf.roundRect(28, y - 34, width - 56, 52, 10, stroke=0, fill=1)
    pdf.setFillColor(GREY)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(42, y, _("Montant reçu"))
    pdf.setFillColor(GREEN)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(42, y - 24, money(contribution.amount).replace(" ", " ").replace(" ", " "))

    # Pied.
    pdf.setFillColor(GREY)
    pdf.setFont("Helvetica", 8)
    generated = date_format(timezone.localtime(), "j F Y, H:i")
    pdf.drawString(28, 40, _("Document généré le %(date)s. Conservez-le comme preuve de paiement.") % {"date": generated})
    pdf.drawString(28, 28, _("Vérifiable auprès du trésorier avec le numéro %(number)s.") % {"number": number})

    pdf.showPage()
    pdf.save()
    return response
