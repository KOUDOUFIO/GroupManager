"""Mixins partagés par les vues web : permissions, contexte CRUD, listes cherchables."""

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView


class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin restreignant l'accès aux membres du staff."""
    raise_exception = True

    def test_func(self):
        """Vérifie que l'utilisateur est membre du staff."""
        return self.request.user.is_staff


class CrudContextMixin:
    """Mixin fournissant le contexte commun pour les vues CRUD."""
    title = ""
    create_url_name = ""
    list_url_name = ""
    base_url_name = ""
    list_columns = []
    show_actions = True
    hero_image = ""

    def get_context_data(self, **kwargs):
        """Fournit le contexte avec les URLs et configuration CRUD."""
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        context["base_url_name"] = self.base_url_name
        if self.hero_image:
            context["hero_image"] = self.hero_image
        if self.list_columns:
            context["list_columns"] = self.list_columns
        if self.create_url_name:
            context["create_url"] = reverse_lazy(self.create_url_name)
        if self.list_url_name:
            context["list_url"] = reverse_lazy(self.list_url_name)
        context["query"] = self.request.GET.get("q", "")
        context["show_actions"] = self.show_actions
        return context


class ModelPermissionMixin(PermissionRequiredMixin):
    """Mixin pour les permissions basées sur l'action et le modèle."""
    permission_action = "view"
    raise_exception = True

    def get_permission_required(self):
        """Génère la permission Django basée sur l'action et le modèle."""
        opts = self.model._meta
        return (f"{opts.app_label}.{self.permission_action}_{opts.model_name}",)


class SearchableListView(LoginRequiredMixin, ModelPermissionMixin, CrudContextMixin, ListView):
    """ListView générique avec recherche et pagination."""
    permission_action = "view"
    paginate_by = 10
    search_fields = []
    default_ordering = ("-pk",)
    select_related_fields = ()
    prefetch_related_fields = ()

    def get_queryset(self):
        """Filtre le queryset selon la recherche et l'ordre."""
        queryset = super().get_queryset()
        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)
        if self.prefetch_related_fields:
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)
        query = self.request.GET.get("q", "").strip()
        if query and self.search_fields:
            q_object = Q()
            for field in self.search_fields:
                q_object |= Q(**{f"{field}__icontains": query})
            queryset = queryset.filter(q_object).distinct()
        if not queryset.ordered:
            queryset = queryset.order_by(*self.default_ordering)
        return queryset


class BaseCreateView(LoginRequiredMixin, ModelPermissionMixin, CrudContextMixin, CreateView):
    """Vue de création de base avec permissions."""
    permission_action = "add"


class BaseUpdateView(LoginRequiredMixin, ModelPermissionMixin, CrudContextMixin, UpdateView):
    """Vue de modification de base avec permissions."""
    permission_action = "change"


class BaseDeleteView(LoginRequiredMixin, ModelPermissionMixin, CrudContextMixin, DeleteView):
    """Vue de suppression de base avec permissions."""
    permission_action = "delete"
