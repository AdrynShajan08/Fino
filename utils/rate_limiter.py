"""
Rate limiting utilities for Fino application.
"""
from datetime import datetime, timedelta
from functools import wraps
from flask import request, session, jsonify
from threading import Lock

class RateLimiter:
    """
    Simple rate limiter using sliding window algorithm.
    """
    
    def __init__(self, max_requests=60, window_seconds=60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self.requests = {}
        self.lock = Lock()
    
    def is_allowed(self, key):
        """
        Check if request is allowed for the given key.
        
        Args:
            key: Unique identifier for the requester
        
        Returns:
            bool: True if request is allowed, False otherwise
        """
        with self.lock:
            now = datetime.now()
            
            if key not in self.requests:
                self.requests[key] = []
            
            # Clean old requests outside the window
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if now - req_time < self.window
            ]
            
            # Check if limit exceeded
            if len(self.requests[key]) >= self.max_requests:
                return False
            
            # Add current request
            self.requests[key].append(now)
            return True
    
    def cleanup(self):
        """Remove expired entries to prevent memory leak."""
        with self.lock:
            now = datetime.now()
            keys_to_delete = []
            
            for key, timestamps in self.requests.items():
                # Remove expired timestamps
                self.requests[key] = [
                    ts for ts in timestamps if now - ts < self.window
                ]
                # If no timestamps left, mark key for deletion
                if not self.requests[key]:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self.requests[key]

def rate_limit(max_requests=60, window_seconds=60):
    """
    Decorator for rate limiting Flask routes.
    
    Args:
        max_requests: Maximum number of requests allowed
        window_seconds: Time window in seconds
    
    Returns:
        Decorated function
    """
    limiter = RateLimiter(max_requests, window_seconds)
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Create key from IP and user_id
            key = f"{request.remote_addr}:{session.get('user_id', 'anonymous')}"
            
            if not limiter.is_allowed(key):
                return jsonify({
                    'error': 'Rate limit exceeded. Please try again later.'
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator