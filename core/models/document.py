"""Documents partagés au sein d'un groupe."""

from django.db import models

from .group import Group


class Document(models.Model):
    """Représente un document partagé au sein d'un groupe.

    Les documents sont stockés dans le système de fichiers et associés à un groupe.
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["uploaded_at"]),
        ]

    def __str__(self) -> str:
        return self.title
