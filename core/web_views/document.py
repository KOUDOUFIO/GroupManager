"""CRUD web pour les documents."""

from django.urls import reverse_lazy

from .. import models
from .mixins import BaseCreateView, BaseDeleteView, BaseUpdateView, SearchableListView


class DocumentListView(SearchableListView):
    """ListView pour les documents."""
    model = models.Document
    template_name = "core/crud_list.html"
    title = "Documents"
    create_url_name = "document_create"
    base_url_name = "document"
    hero_image = "core/img/modules/documents.jpg"
    list_columns = [
        {"label": "Titre", "accessor": "title"},
        {"label": "Type", "accessor": "document_type"},
        {"label": "Groupe", "accessor": "group.name"},
        {"label": "Upload", "accessor": "uploaded_at"},
    ]
    search_fields = ["title", "document_type", "group__name"]
    select_related_fields = ("group",)


class DocumentCreateView(BaseCreateView):
    """Vue de création pour les documents."""
    model = models.Document
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Ajouter un document"
    success_url = reverse_lazy("document_list")
    list_url_name = "document_list"
    base_url_name = "document"


class DocumentUpdateView(BaseUpdateView):
    """Vue de modification pour les documents."""
    model = models.Document
    fields = "__all__"
    template_name = "core/crud_form.html"
    title = "Modifier un document"
    success_url = reverse_lazy("document_list")
    list_url_name = "document_list"
    base_url_name = "document"


class DocumentDeleteView(BaseDeleteView):
    """Vue de suppression pour les documents."""
    model = models.Document
    template_name = "core/crud_confirm_delete.html"
    title = "Supprimer un document"
    success_url = reverse_lazy("document_list")
    list_url_name = "document_list"
    base_url_name = "document"
