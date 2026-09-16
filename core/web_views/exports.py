"""Exports CSV, Excel (XLSX) et PDF pour les cotisations et les présences."""

import csv
from io import BytesIO

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from openpyxl import Workbook
from reportlab.pdfgen import canvas

from .. import models


def _pdf_response(filename):
    """Crée une réponse HTTP pour un fichier PDF.

    Args:
        filename: Le nom du fichier à télécharger.

    Returns:
        HttpResponse: La réponse HTTP configurée pour PDF.
    """
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response


def _xlsx_response(filename):
    """Crée une réponse HTTP pour un fichier Excel XLSX.

    Args:
        filename: Le nom du fichier à télécharger.

    Returns:
        HttpResponse: La réponse HTTP configurée pour XLSX.
    """
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response


def _safe_spreadsheet_cell(value):
    """Échappe les valeurs dangereuses pour les cellules de feuille de calcul.

    Args:
        value: La valeur à échapper.

    Returns:
        La valeur échappée ou inchangée.
    """
    if isinstance(value, str) and value and value[0] in ("=", "+", "-", "@"):
        return f"'{value}"
    return value


def _parse_filters(request):
    """Parse les filtres de date et groupe depuis la requête.

    Args:
        request: L'objet HttpRequest Django.

    Returns:
        tuple: (group_id, start_date, end_date)
    """
    return (
        request.GET.get("group"),
        parse_date(request.GET.get("start_date", "")),
        parse_date(request.GET.get("end_date", "")),
    )


@login_required
@permission_required("core.view_contribution", raise_exception=True)
def export_contributions_csv(request):
    """Exporte les cotisations au format CSV.

    Args:
        request: L'objet HttpRequest Django.

    Returns:
        HttpResponse: Le fichier CSV des cotisations.
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=cotisations.csv"
    writer = csv.writer(response)
    writer.writerow(["Membre", "Groupe", "Type", "Montant", "Date"])
    queryset = models.Contribution.objects.select_related("member", "group").order_by("-paid_at")
    group_id, start_date, end_date = _parse_filters(request)
    if group_id:
        queryset = queryset.filter(group_id=group_id)
    if start_date:
        queryset = queryset.filter(paid_at__gte=start_date)
    if end_date:
        queryset = queryset.filter(paid_at__lte=end_date)
    for item in queryset:
        writer.writerow(
            [
                _safe_spreadsheet_cell(item.member.full_name),
                _safe_spreadsheet_cell(item.group.name),
                _safe_spreadsheet_cell(item.get_contribution_type_display()),
                item.amount,
                item.paid_at,
            ]
        )
    return response


@login_required
@permission_required("core.view_contribution", raise_exception=True)
def export_contributions_xlsx(request):
    """Exporte les cotisations au format Excel XLSX.

    Args:
        request: L'objet HttpRequest Django.

    Returns:
        HttpResponse: Le fichier XLSX des cotisations.
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Cotisations"
    sheet.append(["Membre", "Groupe", "Type", "Montant", "Date"])
    queryset = models.Contribution.objects.select_related("member", "group").order_by("-paid_at")
    group_id, start_date, end_date = _parse_filters(request)
    if group_id:
        queryset = queryset.filter(group_id=group_id)
    if start_date:
        queryset = queryset.filter(paid_at__gte=start_date)
    if end_date:
        queryset = queryset.filter(paid_at__lte=end_date)
    for item in queryset:
        sheet.append(
            [
                _safe_spreadsheet_cell(item.member.full_name),
                _safe_spreadsheet_cell(item.group.name),
                _safe_spreadsheet_cell(item.get_contribution_type_display()),
                float(item.amount),
                item.paid_at.strftime("%Y-%m-%d"),
            ]
        )
    response = _xlsx_response("cotisations.xlsx")
    output = BytesIO()
    workbook.save(output)
    response.write(output.getvalue())
    return response


@login_required
@permission_required("core.view_contribution", raise_exception=True)
def export_contributions_pdf(request):
    """Exporte les cotisations au format PDF.

    Args:
        request: L'objet HttpRequest Django.

    Returns:
        HttpResponse: Le fichier PDF des cotisations.
    """
    response = _pdf_response("cotisations.pdf")
    pdf = canvas.Canvas(response)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, 800, "Rapport des cotisations")
    pdf.setFont("Helvetica", 10)
    y = 770
    pdf.drawString(40, y, "Membre")
    pdf.drawString(200, y, "Groupe")
    pdf.drawString(320, y, "Type")
    pdf.drawString(420, y, "Montant")
    pdf.drawString(490, y, "Date")
    y -= 20
    queryset = models.Contribution.objects.select_related("member", "group").order_by("-paid_at")
    group_id, start_date, end_date = _parse_filters(request)
    if group_id:
        queryset = queryset.filter(group_id=group_id)
    if start_date:
        queryset = queryset.filter(paid_at__gte=start_date)
    if end_date:
        queryset = queryset.filter(paid_at__lte=end_date)
    for item in queryset:
        if y < 60:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = 800
        pdf.drawString(40, y, item.member.full_name)
        pdf.drawString(200, y, item.group.name)
        pdf.drawString(320, y, item.get_contribution_type_display())
        pdf.drawRightString(460, y, f"{item.amount}")
        pdf.drawString(480, y, item.paid_at.strftime("%Y-%m-%d"))
        y -= 18
    pdf.showPage()
    pdf.save()
    return response


@login_required
@permission_required("core.view_meetingentry", raise_exception=True)
def export_meeting_entries_csv(request):
    """Exporte les présences aux rencontres au format CSV.

    Args:
        request: L'objet HttpRequest Django.

    Returns:
        HttpResponse: Le fichier CSV des présences.
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=presences.csv"
    writer = csv.writer(response)
    writer.writerow(["Rencontre", "Groupe", "Membre", "Statut", "Motif", "Date"])
    queryset = models.MeetingEntry.objects.select_related("meeting", "meeting__group", "member").order_by(
        "-recorded_at"
    )
    group_id, start_date, end_date = _parse_filters(request)
    if group_id:
        queryset = queryset.filter(meeting__group_id=group_id)
    if start_date:
        queryset = queryset.filter(recorded_at__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(recorded_at__date__lte=end_date)
    for item in queryset:
        writer.writerow(
            [
                _safe_spreadsheet_cell(item.meeting.title or "Rencontre"),
                _safe_spreadsheet_cell(item.meeting.group.name),
                _safe_spreadsheet_cell(item.member.full_name),
                _safe_spreadsheet_cell(item.get_status_display()),
                _safe_spreadsheet_cell(item.reason),
                item.recorded_at.date(),
            ]
        )
    return response


@login_required
@permission_required("core.view_meetingentry", raise_exception=True)
def export_meeting_entries_xlsx(request):
    """Exporte les présences aux rencontres au format Excel XLSX.

    Args:
        request: L'objet HttpRequest Django.

    Returns:
        HttpResponse: Le fichier XLSX des présences.
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Presences"
    sheet.append(["Rencontre", "Groupe", "Membre", "Statut", "Motif", "Date"])
    queryset = models.MeetingEntry.objects.select_related("meeting", "meeting__group", "member").order_by(
        "-recorded_at"
    )
    group_id, start_date, end_date = _parse_filters(request)
    if group_id:
        queryset = queryset.filter(meeting__group_id=group_id)
    if start_date:
        queryset = queryset.filter(recorded_at__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(recorded_at__date__lte=end_date)
    for item in queryset:
        sheet.append(
            [
                _safe_spreadsheet_cell(item.meeting.title or "Rencontre"),
                _safe_spreadsheet_cell(item.meeting.group.name),
                _safe_spreadsheet_cell(item.member.full_name),
                _safe_spreadsheet_cell(item.get_status_display()),
                _safe_spreadsheet_cell(item.reason),
                item.recorded_at.strftime("%Y-%m-%d"),
            ]
        )
    response = _xlsx_response("presences.xlsx")
    output = BytesIO()
    workbook.save(output)
    response.write(output.getvalue())
    return response


@login_required
@permission_required("core.view_meetingentry", raise_exception=True)
def export_meeting_entries_pdf(request):
    """Exporte les présences aux rencontres au format PDF.

    Args:
        request: L'objet HttpRequest Django.

    Returns:
        HttpResponse: Le fichier PDF des présences.
    """
    response = _pdf_response("presences.pdf")
    pdf = canvas.Canvas(response)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, 800, "Rapport des presences")
    pdf.setFont("Helvetica", 10)
    y = 770
    pdf.drawString(40, y, "Rencontre")
    pdf.drawString(170, y, "Groupe")
    pdf.drawString(280, y, "Membre")
    pdf.drawString(410, y, "Statut")
    pdf.drawString(470, y, "Date")
    y -= 20
    queryset = models.MeetingEntry.objects.select_related("meeting", "meeting__group", "member").order_by(
        "-recorded_at"
    )
    group_id, start_date, end_date = _parse_filters(request)
    if group_id:
        queryset = queryset.filter(meeting__group_id=group_id)
    if start_date:
        queryset = queryset.filter(recorded_at__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(recorded_at__date__lte=end_date)
    for item in queryset:
        if y < 60:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = 800
        pdf.drawString(40, y, item.meeting.title or "Rencontre")
        pdf.drawString(170, y, item.meeting.group.name)
        pdf.drawString(280, y, item.member.full_name)
        pdf.drawString(410, y, item.get_status_display())
        pdf.drawString(470, y, item.recorded_at.strftime("%Y-%m-%d"))
        y -= 18
    pdf.showPage()
    pdf.save()
    return response
