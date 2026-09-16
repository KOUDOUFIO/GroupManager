"""Modèles pour l'authentification à deux facteurs (2FA).

Ce module définit les modèles pour la gestion de l'authentification
à deux facteurs utilisant django-otp.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django_otp.models import Device as BaseDevice
from django_otp.plugins.otp_totp.models import TOTPDevice as BaseTOTPDevice

User = get_user_model()


class TOTPDevice(BaseTOTPDevice):
    """Extension du modèle TOTPDevice pour les besoins spécifiques."""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='totp_devices',
        verbose_name='Utilisateur'
    )
    
    confirmed = models.BooleanField(
        default=False,
        verbose_name='Confirmé'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Créé le'
    )
    
    last_used_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Dernière utilisation'
    )
    
    class Meta:
        verbose_name = 'Appareil TOTP'
        verbose_name_plural = 'Appareils TOTP'
    
    def __str__(self):
        return f"TOTP Device - {self.user.username}"
    
    def verify_token(self, token):
        """Vérifie le token et met à jour la dernière utilisation."""
        if super().verify_token(token):
            from django.utils import timezone
            self.last_used_at = timezone.now()
            self.save(update_fields=['last_used_at'])
            return True
        return False


class TwoFactorPreference(models.Model):
    """Préférences 2FA pour les utilisateurs."""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='two_factor_preferences',
        verbose_name='Utilisateur'
    )
    
    enabled = models.BooleanField(
        default=False,
        verbose_name='2FA activé'
    )
    
    backup_codes = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Codes de secours'
    )
    
    backup_codes_used = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Codes de secours utilisés'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Créé le'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Mis à jour le'
    )
    
    class Meta:
        verbose_name = 'Préférence 2FA'
        verbose_name_plural = 'Préférences 2FA'
    
    def __str__(self):
        return f"2FA - {self.user.username}"
    
    def generate_backup_codes(self, count=10):
        """Génère des codes de secours."""
        import secrets
        codes = []
        for _ in range(count):
            code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
            codes.append(code)
        self.backup_codes = codes
        self.backup_codes_used = []
        self.save()
        return codes
    
    def use_backup_code(self, code):
        """Utilise un code de secours."""
        if code in self.backup_codes and code not in self.backup_codes_used:
            self.backup_codes_used.append(code)
            self.save()
            return True
        return False
    
    def remaining_backup_codes(self):
        """Retourne le nombre de codes de secours restants."""
        return len(self.backup_codes) - len(self.backup_codes_used)
