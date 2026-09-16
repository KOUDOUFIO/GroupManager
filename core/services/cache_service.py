"""Service Layer pour la gestion du cache Redis.

Ce service encapsule la logique de caching pour améliorer les performances
des requêtes fréquentes et réduire la charge sur la base de données.
"""

from typing import Any, Optional, Callable
from django.core.cache import cache
from django.conf import settings
from functools import wraps


class CacheService:
    """Service pour la gestion du cache Redis."""
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """Récupère une valeur du cache.
        
        Args:
            key: Clé de cache
            default: Valeur par défaut si non trouvée
            
        Returns:
            Valeur en cache ou valeur par défaut
        """
        return cache.get(key, default)
    
    @staticmethod
    def set(key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Définit une valeur dans le cache.
        
        Args:
            key: Clé de cache
            value: Valeur à stocker
            timeout: Temps d'expiration en secondes (optionnel)
            
        Returns:
            True si succès, False sinon
        """
        if timeout is None:
            timeout = settings.CACHES['default'].get('TIMEOUT', 300)
        return cache.set(key, value, timeout)
    
    @staticmethod
    def delete(key: str) -> bool:
        """Supprime une valeur du cache.
        
        Args:
            key: Clé de cache
            
        Returns:
            True si supprimé, False sinon
        """
        return cache.delete(key)
    
    @staticmethod
    def delete_pattern(pattern: str) -> int:
        """Supprime toutes les clés correspondant au pattern.
        
        Args:
            pattern: Pattern de clés (ex: "groups:*")
            
        Returns:
            Nombre de clés supprimées
        """
        from django_redis import get_redis_connection
        redis = get_redis_connection("default")
        count = 0
        for key in redis.keys(f"{settings.CACHES['default']['KEY_PREFIX']}:{pattern}"):
            redis.delete(key)
            count += 1
        return count
    
    @staticmethod
    def clear() -> bool:
        """Vide tout le cache.
        
        Returns:
            True si succès, False sinon
        """
        return cache.clear()
    
    @staticmethod
    def get_or_set(key: str, callable_func: Callable, timeout: Optional[int] = None) -> Any:
        """Récupère une valeur du cache ou la calcule et la stocke.
        
        Args:
            key: Clé de cache
            callable_func: Fonction à exécuter si non en cache
            timeout: Temps d'expiration en secondes (optionnel)
            
        Returns:
            Valeur en cache ou calculée
        """
        return cache.get_or_set(key, callable_func, timeout)
    
    @staticmethod
    def invalidate_group_cache(group_id: Optional[int] = None):
        """Invalide le cache lié aux groupes.
        
        Args:
            group_id: ID du groupe spécifique (optionnel)
        """
        if group_id:
            # Invalider le cache d'un groupe spécifique
            cache.delete(settings.CACHE_KEYS['group_detail'].format(id=group_id))
        else:
            # Invalider tout le cache des groupes
            cache.delete(settings.CACHE_KEYS['group_list'])
            cache.delete_pattern('groups:*')
    
    @staticmethod
    def invalidate_member_cache(member_id: Optional[int] = None):
        """Invalide le cache lié aux membres.
        
        Args:
            member_id: ID du membre spécifique (optionnel)
        """
        if member_id:
            # Invalider le cache d'un membre spécifique
            cache.delete(settings.CACHE_KEYS['member_detail'].format(id=member_id))
        else:
            # Invalider tout le cache des membres
            cache.delete(settings.CACHE_KEYS['member_list'])
            cache.delete_pattern('members:*')
    
    @staticmethod
    def invalidate_dashboard_cache(user_id: int):
        """Invalide le cache du dashboard d'un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
        """
        cache.delete(settings.CACHE_KEYS['dashboard_stats'].format(user_id=user_id))
    
    @staticmethod
    def invalidate_notification_cache(user_id: int):
        """Invalide le cache des notifications d'un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
        """
        cache.delete(settings.CACHE_KEYS['notification_count'].format(user_id=user_id))


def cache_result(key_template: str, timeout: Optional[int] = None):
    """Décorateur pour mettre en cache le résultat d'une fonction.
    
    Args:
        key_template: Template de clé de cache (ex: "groups:detail:{group_id}")
        timeout: Temps d'expiration en secondes (optionnel)
        
    Usage:
        @cache_result("groups:detail:{group_id}", timeout=600)
        def get_group_detail(group_id):
            # ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Construire la clé de cache
            key = key_template.format(**kwargs)
            
            # Essayer de récupérer du cache
            cached_value = CacheService.get(key)
            if cached_value is not None:
                return cached_value
            
            # Calculer et mettre en cache
            result = func(*args, **kwargs)
            CacheService.set(key, result, timeout)
            return result
        return wrapper
    return decorator


def cache_invalidate(*patterns):
    """Décorateur pour invalider le cache après l'exécution d'une fonction.
    
    Args:
        patterns: Patterns de clés à invalider
        
    Usage:
        @cache_invalidate("groups:*", "members:*")
        def update_group(group_id):
            # ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            for pattern in patterns:
                CacheService.delete_pattern(pattern)
            return result
        return wrapper
    return decorator
