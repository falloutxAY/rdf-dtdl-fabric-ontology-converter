"""
Token Bucket Rate Limiter

This module provides thread-safe rate limiting functionality
for controlling API request rates to Microsoft Fabric APIs.

Microsoft Fabric throttles API requests and returns HTTP 429 with
a Retry-After header when limits are exceeded. This rate limiter
provides proactive client-side throttling to minimize 429 responses.

Reference: https://learn.microsoft.com/en-us/rest/api/fabric/articles/throttling
"""

import time
import threading
import logging
from typing import Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class RateLimiter(Protocol):
    """Protocol for rate limiters."""
    
    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """Block until tokens are available."""
        ...
    
    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without blocking."""
        ...
    
    def get_available_tokens(self) -> float:
        """Get current number of available tokens."""
        ...
    
    def reset(self) -> None:
        """Reset the rate limiter."""
        ...


class TokenBucketRateLimiter:
    """
    Thread-safe token bucket rate limiter for Microsoft Fabric API calls.
    
    The token bucket algorithm allows for controlled bursting while
    enforcing a long-term rate limit. Tokens are added to the bucket
    at a steady rate, and each request consumes one or more tokens.
    
    Microsoft Fabric does not publish specific rate limits - they vary
    by user and API endpoint. Use conservative defaults and adjust based
    on observed 429 responses.
    
    Example:
        # Allow 10 requests per minute with burst of 15
        limiter = TokenBucketRateLimiter(rate=10, per=60, burst=15)
        
        # Before each API call:
        limiter.acquire()  # Blocks until token available
        make_api_call()
        
        # Or non-blocking:
        if limiter.try_acquire():
            make_api_call()
        else:
            handle_rate_limit()
    """
    
    def __init__(
        self, 
        rate: int = 10, 
        per: int = 60,
        burst: Optional[int] = None
    ):
        """
        Initialize the rate limiter.
        
        Args:
            rate: Number of requests allowed per time period
            per: Time period in seconds
            burst: Maximum burst size (defaults to rate if not specified)
        """
        if rate <= 0:
            raise ValueError("rate must be positive")
        if per <= 0:
            raise ValueError("per must be positive")
        
        self.rate = rate
        self.per = per
        self.capacity = burst if burst is not None else rate
        
        if self.capacity <= 0:
            raise ValueError("burst capacity must be positive")
        
        self.tokens = float(self.capacity)  # Start with full bucket
        self.last_refill = time.time()
        self.lock = threading.Lock()
        
        # Statistics tracking
        self._total_requests = 0
        self._total_wait_time = 0.0
        self._times_waited = 0
    
    @property
    def tokens_per_second(self) -> float:
        """Calculate token generation rate per second."""
        return self.rate / self.per
    
    def _refill(self) -> None:
        """Refill tokens based on time elapsed (must be called with lock held)."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time
        new_tokens = elapsed * self.tokens_per_second
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now
    
    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Block until tokens are available, then consume them.
        
        Args:
            tokens: Number of tokens to acquire (default: 1)
            timeout: Maximum time to wait in seconds (None = wait forever)
            
        Returns:
            True if tokens were acquired, False if timeout occurred
            
        Raises:
            ValueError: If tokens requested exceeds capacity
        """
        if tokens > self.capacity:
            raise ValueError(
                f"Cannot acquire {tokens} tokens; capacity is {self.capacity}"
            )
        
        start_time = time.time()
        
        with self.lock:
            self._total_requests += 1
            
            while True:
                self._refill()
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
                
                # Calculate wait time
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.tokens_per_second
                
                # Check timeout
                if timeout is not None:
                    elapsed = time.time() - start_time
                    remaining = timeout - elapsed
                    if remaining <= 0:
                        logger.debug(f"Rate limit acquire timed out after {elapsed:.2f}s")
                        return False
                    wait_time = min(wait_time, remaining)
                
                logger.debug(f"Rate limit: waiting {wait_time:.2f}s for {tokens_needed:.2f} tokens")
                self._times_waited += 1
                
                # Release lock while sleeping
                self.lock.release()
                try:
                    time.sleep(wait_time)
                    self._total_wait_time += wait_time
                finally:
                    self.lock.acquire()
    
    def try_acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without blocking.
        
        Args:
            tokens: Number of tokens to acquire (default: 1)
            
        Returns:
            True if tokens were acquired, False if not enough tokens available
        """
        with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                self._total_requests += 1
                return True
            
            return False
    
    def get_available_tokens(self) -> float:
        """Get current number of available tokens."""
        with self.lock:
            self._refill()
            return self.tokens
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get estimated wait time for acquiring tokens.
        
        Args:
            tokens: Number of tokens to check (default: 1)
            
        Returns:
            Estimated wait time in seconds (0 if tokens available immediately)
        """
        with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                return 0.0
            
            tokens_needed = tokens - self.tokens
            return tokens_needed / self.tokens_per_second
    
    def reset(self) -> None:
        """Reset the rate limiter to full capacity."""
        with self.lock:
            self.tokens = float(self.capacity)
            self.last_refill = time.time()
    
    def get_statistics(self) -> dict:
        """
        Get rate limiter statistics.
        
        Returns:
            Dictionary with statistics about rate limiter usage
        """
        with self.lock:
            self._refill()
            return {
                'rate': self.rate,
                'per_seconds': self.per,
                'burst_capacity': self.capacity,
                'current_tokens': self.tokens,
                'total_requests': self._total_requests,
                'times_waited': self._times_waited,
                'total_wait_time_seconds': self._total_wait_time,
                'average_wait_time_seconds': (
                    self._total_wait_time / self._times_waited 
                    if self._times_waited > 0 else 0.0
                ),
            }
    
    def __repr__(self) -> str:
        return (
            f"TokenBucketRateLimiter(rate={self.rate}, per={self.per}, "
            f"burst={self.capacity}, tokens={self.tokens:.2f})"
        )


class NoOpRateLimiter:
    """
    A no-op rate limiter that doesn't actually limit anything.
    
    Useful for testing or when rate limiting should be disabled.
    """
    
    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """Always returns True immediately."""
        return True
    
    def try_acquire(self, tokens: int = 1) -> bool:
        """Always returns True."""
        return True
    
    def get_available_tokens(self) -> float:
        """Always returns infinity."""
        return float('inf')
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """Always returns 0."""
        return 0.0
    
    def reset(self) -> None:
        """No-op."""
        pass
    
    def get_statistics(self) -> dict:
        """Returns empty statistics."""
        return {
            'rate': 'unlimited',
            'per_seconds': 0,
            'burst_capacity': 'unlimited',
            'current_tokens': float('inf'),
            'total_requests': 0,
            'times_waited': 0,
            'total_wait_time_seconds': 0.0,
            'average_wait_time_seconds': 0.0,
        }
    
    def __repr__(self) -> str:
        return "NoOpRateLimiter()"
