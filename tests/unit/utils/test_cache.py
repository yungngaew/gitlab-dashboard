"""Unit tests for cache functionality."""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta
from src.utils.cache import FileCache, CachedAnalytics
from unittest.mock import Mock


class TestFileCache:
    """Test file-based cache."""
    
    def test_cache_init(self, temp_dir):
        """Test cache initialization."""
        cache_dir = temp_dir / 'test_cache'
        cache = FileCache(str(cache_dir))
        
        assert cache_dir.exists()
        assert cache.default_ttl == 900
    
    def test_cache_set_get(self, temp_dir):
        """Test setting and getting cached values."""
        cache = FileCache(str(temp_dir / 'cache'))
        
        # Set a value
        test_data = {'key': 'value', 'number': 42}
        cache.set('test_key', test_data)
        
        # Get the value
        result = cache.get('test_key')
        assert result == test_data
    
    def test_cache_expiry(self, temp_dir):
        """Test cache expiration."""
        cache = FileCache(str(temp_dir / 'cache'))
        
        # Set with short TTL
        cache.set('expire_key', 'value', ttl=1)
        
        # Should exist immediately
        assert cache.get('expire_key') == 'value'
        
        # Mock time passing by modifying the cache file
        cache_file = cache.cache_dir / cache._get_cache_key('expire_key')
        with open(cache_file, 'r') as f:
            data = json.load(f)
        
        # Set expiry to past
        data['expiry'] = (datetime.now() - timedelta(seconds=1)).isoformat()
        with open(cache_file, 'w') as f:
            json.dump(data, f)
        
        # Should be expired now
        assert cache.get('expire_key') is None
        assert not cache_file.exists()  # Should be deleted
    
    def test_cache_delete(self, temp_dir):
        """Test deleting cache entries."""
        cache = FileCache(str(temp_dir / 'cache'))
        
        cache.set('delete_key', 'value')
        assert cache.get('delete_key') == 'value'
        
        cache.delete('delete_key')
        assert cache.get('delete_key') is None
    
    def test_cache_clear(self, temp_dir):
        """Test clearing all cache."""
        cache = FileCache(str(temp_dir / 'cache'))
        
        # Set multiple values
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        cache.set('key3', 'value3')
        
        # Clear cache
        cache.clear()
        
        # All should be gone
        assert cache.get('key1') is None
        assert cache.get('key2') is None
        assert cache.get('key3') is None
    
    def test_cache_stats(self, temp_dir):
        """Test cache statistics."""
        cache = FileCache(str(temp_dir / 'cache'))
        
        # Set some values
        cache.set('key1', 'value1')
        cache.set('key2', {'data': 'more complex'})
        
        stats = cache.get_stats()
        
        assert stats['total_entries'] == 2
        assert stats['total_size_bytes'] > 0
        assert stats['expired_entries'] == 0
        assert str(temp_dir / 'cache') in stats['cache_directory']
    
    def test_cache_cleanup_on_init(self, temp_dir):
        """Test that expired entries are cleaned up on init."""
        cache_dir = temp_dir / 'cache'
        cache = FileCache(str(cache_dir))
        
        # Create an expired cache file manually
        expired_data = {
            'key': 'expired_key',
            'value': 'expired_value',
            'expiry': (datetime.now() - timedelta(hours=1)).isoformat(),
            'created': datetime.now().isoformat()
        }
        
        expired_file = cache_dir / 'expired.json'
        with open(expired_file, 'w') as f:
            json.dump(expired_data, f)
        
        # Create new cache instance - should clean up expired file
        cache2 = FileCache(str(cache_dir))
        
        assert not expired_file.exists()


class TestCachedAnalytics:
    """Test cached analytics wrapper."""
    
    def test_cached_get_project_metrics(self, temp_dir, mock_gitlab_client):
        """Test cached project metrics retrieval."""
        # Create mock analytics service
        mock_analytics = Mock()
        mock_analytics.get_project_metrics.return_value = {
            'project': {'name': 'test'},
            'commits': {'total': 100}
        }
        
        # Create cache
        cache = FileCache(str(temp_dir / 'cache'))
        cached_analytics = CachedAnalytics(mock_analytics, cache)
        
        # First call should hit the service
        result1 = cached_analytics.get_project_metrics(1)
        assert mock_analytics.get_project_metrics.call_count == 1
        assert result1['commits']['total'] == 100
        
        # Second call should use cache
        result2 = cached_analytics.get_project_metrics(1)
        assert mock_analytics.get_project_metrics.call_count == 1  # No additional call
        assert result2['commits']['total'] == 100
        
        # Force refresh should hit service again
        result3 = cached_analytics.get_project_metrics(1, force_refresh=True)
        assert mock_analytics.get_project_metrics.call_count == 2
    
    def test_cached_get_project_trends(self, temp_dir):
        """Test cached project trends retrieval."""
        # Create mock analytics service
        mock_analytics = Mock()
        mock_analytics.get_project_trends.return_value = {
            'health_score': {'score': 85, 'grade': 'B'},
            'metrics': {}
        }
        
        # Create cache
        cache = FileCache(str(temp_dir / 'cache'))
        cached_analytics = CachedAnalytics(mock_analytics, cache)
        
        # Test caching with different parameters
        result1 = cached_analytics.get_project_trends(1, days=30)
        result2 = cached_analytics.get_project_trends(1, days=30)
        result3 = cached_analytics.get_project_trends(1, days=60)  # Different params
        
        # Same params should use cache
        assert mock_analytics.get_project_trends.call_count == 2  # Once for 30 days, once for 60
        assert result1 == result2
        assert result1 != result3  # Different params should have different cache key