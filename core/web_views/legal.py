"""Pages legales : mentions legales et politique de confidentialite."""

from django.views.generic import TemplateView


class LegalNoticeView(TemplateView):
    """Mentions legales."""
    template_name = "core/legal_notice.html"


class PrivacyPolicyView(TemplateView):
    """Politique de confidentialite."""
    template_name = "core/privacy_policy.html"
