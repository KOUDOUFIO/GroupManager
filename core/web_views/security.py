"""Securite du compte : connexion a deux etapes (code a 6 chiffres, TOTP)."""

import secrets
from base64 import b32encode

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views import View
from django_otp import login as otp_login
from django_otp import match_token
from django_otp import user_has_device
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

DEVICE_NAME = "Kotiza"
BACKUP_NAME = "Codes de secours"
BACKUP_COUNT = 8


def _new_backup_codes(user) -> list:
    """Remplace les codes de secours de l'utilisateur ; renvoie les nouveaux (affiches une seule fois)."""
    StaticDevice.objects.filter(user=user).delete()
    device = StaticDevice.objects.create(user=user, name=BACKUP_NAME, confirmed=True)
    codes = []
    while len(codes) < BACKUP_COUNT:
        code = f"{secrets.randbelow(10**8):08d}"
        if code not in codes:
            codes.append(code)
            StaticToken.objects.create(device=device, token=code)
    return codes


def _remaining_backup_codes(user) -> int:
    return StaticToken.objects.filter(device__user=user).count()


class CodeForm(forms.Form):
    """Code a 6 chiffres de l'application, ou code de secours a 8 chiffres."""
    code = forms.RegexField(
        label=gettext_lazy("Code à 6 chiffres"), regex=r"^(\d{6}|\d{8})$", max_length=8,
        error_messages={"invalid": gettext_lazy("Le code contient 6 chiffres (ou 8 pour un code de secours).")},
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "one-time-code", "autofocus": True}),
    )


def _qr_svg(data: str) -> str:
    """QR code en SVG (sans dependance image)."""
    import qrcode
    import qrcode.image.svg

    image = qrcode.make(data, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=2)
    return image.to_string(encoding="unicode")


def _confirmed_device(user):
    return TOTPDevice.objects.filter(user=user, confirmed=True).first()


class SecurityView(LoginRequiredMixin, View):
    """Activation et desactivation de la connexion a deux etapes."""
    template_name = "core/security.html"

    def _render(self, request, **extra):
        device = _confirmed_device(request.user)
        return render(request, self.template_name, {
            "enabled": device is not None,
            "backup_remaining": _remaining_backup_codes(request.user) if device else 0,
            **extra,
        })

    def get(self, request):
        """Etat actuel."""
        return self._render(request)

    def post(self, request):
        """Etapes : start (QR code), confirm (premier code), disable (code actuel)."""
        action = request.POST.get("action")
        user = request.user

        if action == "start":
            TOTPDevice.objects.filter(user=user, confirmed=False).delete()
            device = TOTPDevice.objects.create(user=user, name=DEVICE_NAME, confirmed=False)
            return self._setup(request, device, CodeForm())

        if action == "confirm":
            device = TOTPDevice.objects.filter(user=user, confirmed=False).order_by("-id").first()
            if device is None:
                return redirect("security")
            form = CodeForm(request.POST)
            if form.is_valid() and device.verify_token(form.cleaned_data["code"]):
                device.confirmed = True
                device.save(update_fields=["confirmed"])
                otp_login(request, device)
                messages.success(request, _("Connexion à deux étapes activée. Le code vous sera demandé à chaque connexion."))
                return self._render(request, backup_codes=_new_backup_codes(user))
            if form.is_valid():
                form.add_error("code", _("Code incorrect. Vérifiez l'heure du téléphone et réessayez."))
            return self._setup(request, device, form)

        if action == "disable":
            form = CodeForm(request.POST)
            device = _confirmed_device(user)
            if device and form.is_valid() and device.verify_token(form.cleaned_data["code"]):
                TOTPDevice.objects.filter(user=user).delete()
                StaticDevice.objects.filter(user=user).delete()
                messages.success(request, _("Connexion à deux étapes désactivée."))
                return redirect("security")
            if form.is_valid():
                form.add_error("code", _("Code incorrect."))
            return self._render(request, disable_form=form)

        if action == "backup" and _confirmed_device(user):
            return self._render(request, backup_codes=_new_backup_codes(user))

        return redirect("security")

    def _setup(self, request, device, form):
        return self._render(
            request,
            setup=True,
            form=form,
            qr_svg=mark_safe(_qr_svg(device.config_url)),
            secret=b32encode(device.bin_key).decode(),
        )


class TwoFactorVerifyView(LoginRequiredMixin, View):
    """Demande le code apres le mot de passe, pour les comptes proteges."""
    template_name = "core/two_factor_verify.html"

    def _next(self, request):
        target = request.POST.get("next") or request.GET.get("next") or "/"
        if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            return "/"
        return target

    def get(self, request):
        """Formulaire du code (inutile si deja verifie ou sans protection)."""
        if request.user.is_verified() or not user_has_device(request.user, confirmed=True):
            return redirect(self._next(request))
        return render(request, self.template_name, {"form": CodeForm(), "next": self._next(request)})

    def post(self, request):
        """Verifie le code et termine la connexion."""
        form = CodeForm(request.POST)
        if form.is_valid():
            device = match_token(request.user, form.cleaned_data["code"])
            if device is not None:
                otp_login(request, device)
                return redirect(self._next(request))
            form.add_error("code", _("Code incorrect ou expiré. Utilisez le code affiché en ce moment."))
        return render(request, self.template_name, {"form": form, "next": self._next(request)})
