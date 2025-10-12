"""
Simple in-memory caching system for Fino application.
"""
from datetime import datetime, timedelta
from threading import Lock

class SimpleCache:
    """
    Thread-safe in-memory cache with TTL support.
    """
    
    def __init__(self, ttl_seconds=300):
        """
        Initialize cache.
        
        Args:
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.cache = {}
        self.ttl = timedelta(seconds=ttl_seconds)
        self.lock = Lock()
    
    def get(self, key):
        """
        Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found/expired
        """
        with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if datetime.now() - timestamp < self.ttl:
                    return value
                # Entry expired, remove it
                del self.cache[key]
            return None
    
    def set(self, key, value):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self.lock:
            self.cache[key] = (value, datetime.now())
    
    def invalidate(self, pattern=None):
        """
        Invalidate cache entries.
        
        Args:
            pattern: If provided, only invalidate keys containing this pattern.
                    If None, clear entire cache.
        """
        with self.lock:
            if pattern:
                keys_to_delete = [k for k in self.cache.keys() if pattern in k]
                for k in keys_to_delete:
                    del self.cache[k]
            else:
                self.cache.clear()
    
    def clear(self):
        """Clear entire cache."""
        self.invalidate()
    
    def size(self):
        """Get number of entries in cache."""
        with self.lock:
            return len(self.cache)
    
    def cleanup_expired(self):
        """Remove all expired entries from cache."""
        with self.lock:
            now = datetime.now()
            expired_keys = [
                key for key, (_, timestamp) in self.cache.items()
                if now - timestamp >= self.ttl
            ]
            for key in expired_keys:
                del self.cache[key]
            return len(expired_keys)