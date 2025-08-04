"""Simple file-based cache for analytics data."""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


class FileCache:
    """Simple file-based cache with TTL support."""
    
    def __init__(self, cache_dir: str = ".cache", default_ttl: int = 900):
        """Initialize cache.
        
        Args:
            cache_dir: Directory to store cache files
            default_ttl: Default TTL in seconds (15 minutes)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.default_ttl = default_ttl
        
        # Clean up old cache files on init
        self._cleanup_expired()
    
    def _get_cache_key(self, key: str) -> str:
        """Generate cache filename from key."""
        # Use hash to avoid filesystem issues with special characters
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return f"{key_hash}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        cache_file = self.cache_dir / self._get_cache_key(key)
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # Check expiry
            expiry = datetime.fromisoformat(data['expiry'])
            if datetime.now() > expiry:
                cache_file.unlink()
                return None
            
            logger.debug(f"Cache hit for key: {key}")
            return data['value']
            
        except Exception as e:
            logger.warning(f"Failed to read cache for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (uses default if not specified)
        """
        if ttl is None:
            ttl = self.default_ttl
        
        cache_file = self.cache_dir / self._get_cache_key(key)
        expiry = datetime.now() + timedelta(seconds=ttl)
        
        try:
            data = {
                'key': key,
                'value': value,
                'expiry': expiry.isoformat(),
                'created': datetime.now().isoformat()
            }
            
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug(f"Cached key: {key} (TTL: {ttl}s)")
            
        except Exception as e:
            logger.warning(f"Failed to cache key {key}: {e}")
    
    def delete(self, key: str) -> None:
        """Delete a key from cache.
        
        Args:
            key: Cache key
        """
        cache_file = self.cache_dir / self._get_cache_key(key)
        if cache_file.exists():
            cache_file.unlink()
            logger.debug(f"Deleted cache key: {key}")
    
    def clear(self) -> None:
        """Clear all cache files."""
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete cache file {cache_file}: {e}")
        
        logger.info("Cache cleared")
    
    def _cleanup_expired(self) -> None:
        """Remove expired cache files."""
        now = datetime.now()
        expired_count = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                expiry = datetime.fromisoformat(data['expiry'])
                if now > expiry:
                    cache_file.unlink()
                    expired_count += 1
                    
            except Exception as e:
                # If we can't read it, delete it
                logger.debug(f"Removing invalid cache file {cache_file}: {e}")
                try:
                    cache_file.unlink()
                    expired_count += 1
                except:
                    pass
        
        if expired_count > 0:
            logger.debug(f"Cleaned up {expired_count} expired cache files")
    
    def get_stats(self) -> dict:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total_files = 0
        total_size = 0
        expired = 0
        
        now = datetime.now()
        
        for cache_file in self.cache_dir.glob("*.json"):
            total_files += 1
            total_size += cache_file.stat().st_size
            
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                expiry = datetime.fromisoformat(data['expiry'])
                if now > expiry:
                    expired += 1
                    
            except:
                expired += 1
        
        return {
            'total_entries': total_files,
            'total_size_bytes': total_size,
            'expired_entries': expired,
            'cache_directory': str(self.cache_dir)
        }


class CachedAnalytics:
    """Wrapper for analytics with caching support."""
    
    def __init__(self, analytics_service: Any, cache: Optional[FileCache] = None):
        """Initialize cached analytics.
        
        Args:
            analytics_service: The analytics service to wrap
            cache: Cache instance (creates default if not provided)
        """
        self.analytics = analytics_service
        self.cache = cache or FileCache()
    
    def get_project_metrics(self, project_id: Union[int, str], force_refresh: bool = False) -> dict:
        """Get project metrics with caching.
        
        Args:
            project_id: Project ID
            force_refresh: Force refresh from API
            
        Returns:
            Project metrics
        """
        cache_key = f"project_metrics:{project_id}"
        
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        
        # Fetch fresh data
        metrics = self.analytics.get_project_metrics(project_id)
        
        # Cache for 15 minutes
        self.cache.set(cache_key, metrics, ttl=900)
        
        return metrics
    
    def get_project_trends(
        self, 
        project_id: int, 
        days: int = 90,
        force_refresh: bool = False
    ) -> dict:
        """Get project trends with caching.
        
        Args:
            project_id: Project ID
            days: Number of days
            force_refresh: Force refresh from API
            
        Returns:
            Project trends
        """
        cache_key = f"project_trends:{project_id}:{days}"
        
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        
        # Fetch fresh data
        trends = self.analytics.get_project_trends(project_id, days)
        
        # Cache for 30 minutes for trends
        self.cache.set(cache_key, trends, ttl=1800)
        
        return trends