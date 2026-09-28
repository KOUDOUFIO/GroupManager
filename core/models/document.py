"""Documents partagés au sein d'un groupe."""

from django.db import models
from django.utils.translation import gettext_lazy as _

from .group import Group


class Document(models.Model):
    """Représente un document partagé au sein d'un groupe.

    Les documents sont stockés dans le système de fichiers et associés à un groupe.
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="documents", verbose_name=_("Groupe"))
    document_type = models.CharField(max_length=200, verbose_name=_("Type de document"))
    title = models.CharField(max_length=200, verbose_name=_("Titre"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    file = models.FileField(upload_to="documents/", verbose_name=_("Fichier"))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Ajouté le"))

    class Meta:
        verbose_name = _("Document")
        verbose_name_plural = _("Documents")
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["uploaded_at"]),
        ]

    def __str__(self) -> str:
        return self.title
