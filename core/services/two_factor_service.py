"""Service Layer pour l'authentification à deux facteurs (2FA).

Ce service encapsule la logique métier liée à la 2FA,
permettant de configurer et gérer l'authentification TOTP.
"""

from typing import Optional, Dict, Any
from django.db import transaction
from django.contrib.auth import get_user_model
import qrcode
from io import BytesIO
import base64

from ..models import TOTPDevice, TwoFactorPreference

User = get_user_model()


class TwoFactorService:
    """Service pour la gestion de l'authentification à deux facteurs."""
    
    @staticmethod
    def get_or_create_preferences(user_id: int) -> TwoFactorPreference:
        """Récupère ou crée les préférences 2FA d'un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            Instance des préférences 2FA
        """
        preference, created = TwoFactorPreference.objects.get_or_create(
            user_id=user_id
        )
        return preference
    
    @staticmethod
    @transaction.atomic
    def create_totp_device(user_id: int, name: str = "Default") -> TOTPDevice:
        """Crée un nouvel appareil TOTP pour un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            name: Nom de l'appareil
            
        Returns:
            Instance de l'appareil TOTP créé
        """
        device = TOTPDevice.objects.create(
            user_id=user_id,
            name=name,
            confirmed=False
        )
        return device
    
    @staticmethod
    def get_totp_device(user_id: int, device_id: Optional[int] = None) -> Optional[TOTPDevice]:
        """Récupère un appareil TOTP pour un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            device_id: ID de l'appareil (optionnel, retourne le premier si non spécifié)
            
        Returns:
            Instance de l'appareil TOTP ou None
        """
        queryset = TOTPDevice.objects.filter(user_id=user_id)
        if device_id:
            queryset = queryset.filter(id=device_id)
        return queryset.first()
    
    @staticmethod
    def generate_qr_code(device: TOTPDevice) -> str:
        """Génère un QR code pour la configuration TOTP.
        
        Args:
            device: Instance de l'appareil TOTP
            
        Returns:
            QR code encodé en base64
        """
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(device.config_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    
    @staticmethod
    @transaction.atomic
    def confirm_totp_device(device_id: int, token: str) -> bool:
        """Confirme un appareil TOTP en vérifiant le token.
        
        Args:
            device_id: ID de l'appareil
            token: Token TOTP à vérifier
            
        Returns:
            True si confirmé, False sinon
        """
        try:
            device = TOTPDevice.objects.get(id=device_id)
            if device.verify_token(token):
                device.confirmed = True
                device.save()
                
                # Activer le 2FA pour l'utilisateur
                preference, _ = TwoFactorPreference.objects.get_or_create(
                    user_id=device.user_id
                )
                preference.enabled = True
                preference.save()
                
                return True
            return False
        except TOTPDevice.DoesNotExist:
            return False
    
    @staticmethod
    @transaction.atomic
    def disable_two_factor(user_id: int) -> bool:
        """Désactive le 2FA pour un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            True si désactivé, False sinon
        """
        try:
            preference = TwoFactorPreference.objects.get(user_id=user_id)
            preference.enabled = False
            preference.save()
            
            # Supprimer tous les appareils TOTP
            TOTPDevice.objects.filter(user_id=user_id).delete()
            
            return True
        except TwoFactorPreference.DoesNotExist:
            return False
    
    @staticmethod
    def verify_totp_token(user_id: int, token: str) -> bool:
        """Vérifie un token TOTP pour un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            token: Token TOTP à vérifier
            
        Returns:
            True si valide, False sinon
        """
        device = TOTPDevice.objects.filter(
            user_id=user_id,
            confirmed=True
        ).first()
        
        if device:
            return device.verify_token(token)
        return False
    
    @staticmethod
    @transaction.atomic
    def generate_backup_codes(user_id: int, count: int = 10) -> list:
        """Génère des codes de secours pour un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            count: Nombre de codes à générer
            
        Returns:
            Liste des codes de secours générés
        """
        preference = TwoFactorService.get_or_create_preferences(user_id)
        return preference.generate_backup_codes(count)
    
    @staticmethod
    def use_backup_code(user_id: int, code: str) -> bool:
        """Utilise un code de secours.
        
        Args:
            user_id: ID de l'utilisateur
            code: Code de secours
            
        Returns:
            True si utilisé avec succès, False sinon
        """
        try:
            preference = TwoFactorPreference.objects.get(user_id=user_id)
            return preference.use_backup_code(code)
        except TwoFactorPreference.DoesNotExist:
            return False
    
    @staticmethod
    def get_remaining_backup_codes(user_id: int) -> int:
        """Retourne le nombre de codes de secours restants.
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            Nombre de codes restants
        """
        try:
            preference = TwoFactorPreference.objects.get(user_id=user_id)
            return preference.remaining_backup_codes()
        except TwoFactorPreference.DoesNotExist:
            return 0
    
    @staticmethod
    def is_two_factor_enabled(user_id: int) -> bool:
        """Vérifie si le 2FA est activé pour un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            True si activé, False sinon
        """
        try:
            preference = TwoFactorPreference.objects.get(user_id=user_id)
            return preference.enabled
        except TwoFactorPreference.DoesNotExist:
            return False
    
    @staticmethod
    def get_user_devices(user_id: int) -> list:
        """Récupère tous les appareils TOTP d'un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            Liste des appareils TOTP
        """
        return list(TOTPDevice.objects.filter(user_id=user_id))
