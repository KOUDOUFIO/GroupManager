"""Notifications de l'utilisateur connecte (rappels, informations)."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import ListView

from .. import models


class NotificationListView(LoginRequiredMixin, ListView):
    """Liste des notifications ; POST marque tout comme lu."""
    template_name = "core/notifications.html"
    context_object_name = "notifications"
    paginate_by = 20

    def get_queryset(self):
        """Notifications de l'utilisateur, les plus recentes d'abord."""
        return models.Notification.objects.filter(user=self.request.user).order_by("-created_at")

    def post(self, request, *args, **kwargs):
        """Marque toutes les notifications comme lues."""
        models.Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return redirect("notifications")
