"""
Tests for TokenBucketRateLimiter and rate limiting functionality.
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from rate_limiter import TokenBucketRateLimiter, NoOpRateLimiter


class TestTokenBucketRateLimiter:
    """Tests for TokenBucketRateLimiter class."""
    
    def test_init_default_values(self):
        """Test default initialization."""
        limiter = TokenBucketRateLimiter()
        assert limiter.rate == 10
        assert limiter.per == 60
        assert limiter.capacity == 10  # burst defaults to rate
        assert limiter.tokens == 10.0  # starts full
    
    def test_init_custom_values(self):
        """Test initialization with custom values."""
        limiter = TokenBucketRateLimiter(rate=5, per=30, burst=10)
        assert limiter.rate == 5
        assert limiter.per == 30
        assert limiter.capacity == 10
        assert limiter.tokens == 10.0
    
    def test_init_invalid_rate(self):
        """Test initialization with invalid rate."""
        with pytest.raises(ValueError, match="rate must be positive"):
            TokenBucketRateLimiter(rate=0)
        with pytest.raises(ValueError, match="rate must be positive"):
            TokenBucketRateLimiter(rate=-1)
    
    def test_init_invalid_per(self):
        """Test initialization with invalid per."""
        with pytest.raises(ValueError, match="per must be positive"):
            TokenBucketRateLimiter(per=0)
    
    def test_init_invalid_burst(self):
        """Test initialization with invalid burst."""
        with pytest.raises(ValueError, match="burst capacity must be positive"):
            TokenBucketRateLimiter(burst=0)
    
    def test_tokens_per_second(self):
        """Test tokens per second calculation."""
        limiter = TokenBucketRateLimiter(rate=60, per=60)
        assert limiter.tokens_per_second == 1.0
        
        limiter2 = TokenBucketRateLimiter(rate=10, per=60)
        assert abs(limiter2.tokens_per_second - 0.1667) < 0.01
    
    def test_acquire_immediate(self):
        """Test immediate token acquisition."""
        limiter = TokenBucketRateLimiter(rate=10, per=60, burst=10)
        
        # Should succeed immediately (tokens available)
        start = time.time()
        result = limiter.acquire()
        elapsed = time.time() - start
        
        assert result is True
        assert elapsed < 0.1  # Should be near-instant
        assert limiter.tokens == 9.0  # One token consumed
    
    def test_acquire_multiple_immediate(self):
        """Test multiple immediate acquisitions."""
        limiter = TokenBucketRateLimiter(rate=10, per=60, burst=5)
        
        # Consume all 5 tokens
        for i in range(5):
            assert limiter.acquire() is True
            # Use approximate comparison due to time-based refill
            assert limiter.tokens <= 5 - i
            assert limiter.tokens >= 4 - i - 0.1  # Allow small refill margin
    
    def test_acquire_exceeds_capacity(self):
        """Test acquiring more tokens than capacity."""
        limiter = TokenBucketRateLimiter(rate=5, per=60, burst=5)
        
        with pytest.raises(ValueError, match="Cannot acquire 10 tokens"):
            limiter.acquire(tokens=10)
    
    def test_acquire_with_timeout_success(self):
        """Test acquire with timeout that succeeds."""
        limiter = TokenBucketRateLimiter(rate=10, per=60, burst=10)
        
        result = limiter.acquire(timeout=1.0)
        assert result is True
    
    def test_acquire_with_timeout_failure(self):
        """Test acquire with timeout that fails."""
        limiter = TokenBucketRateLimiter(rate=1, per=60, burst=1)
        
        # Consume the only token
        limiter.acquire()
        
        # Try to acquire another with short timeout
        start = time.time()
        result = limiter.acquire(timeout=0.1)
        elapsed = time.time() - start
        
        assert result is False
        assert elapsed >= 0.1  # Should have waited the full timeout
        assert elapsed < 0.3  # But not too long
    
    def test_try_acquire_success(self):
        """Test try_acquire when tokens available."""
        limiter = TokenBucketRateLimiter(rate=10, per=60, burst=10)
        
        assert limiter.try_acquire() is True
        assert limiter.tokens == 9.0
    
    def test_try_acquire_failure(self):
        """Test try_acquire when no tokens available."""
        limiter = TokenBucketRateLimiter(rate=10, per=60, burst=1)
        
        # Consume the only token
        assert limiter.try_acquire() is True
        
        # Should fail immediately without waiting
        start = time.time()
        assert limiter.try_acquire() is False
        elapsed = time.time() - start
        
        assert elapsed < 0.01  # Should be instant
    
    def test_token_refill(self):
        """Test token refill over time."""
        limiter = TokenBucketRateLimiter(rate=10, per=1, burst=10)  # 10 tokens/second
        
        # Consume all tokens
        for _ in range(10):
            limiter.acquire()
        
        assert limiter.tokens < 1
        
        # Wait for refill
        time.sleep(0.2)  # Should add ~2 tokens
        
        available = limiter.get_available_tokens()
        assert available >= 1.5  # At least 1.5 tokens should be refilled
        assert available <= 3.0  # But not more than ~3
    
    def test_get_available_tokens(self):
        """Test getting available tokens."""
        limiter = TokenBucketRateLimiter(rate=10, per=60, burst=10)
        
        # Use approximate comparison due to time-based refill
        assert abs(limiter.get_available_tokens() - 10.0) < 0.01
        
        limiter.acquire()
        # After acquiring one token, should have ~9 (allow small refill)
        available = limiter.get_available_tokens()
        assert available >= 8.9
        assert available <= 9.1
    
    def test_get_wait_time_no_wait(self):
        """Test get_wait_time when tokens available."""
        limiter = TokenBucketRateLimiter(rate=10, per=60, burst=10)
        
        assert limiter.get_wait_time() == 0.0
    
    def test_get_wait_time_with_wait(self):
        """Test get_wait_time when waiting required."""
        limiter = TokenBucketRateLimiter(rate=10, per=60, burst=1)
        
        # Consume the only token
        limiter.acquire()
        
        # Should need to wait ~6 seconds for 1 token at 10/minute rate
        wait_time = limiter.get_wait_time()
        assert wait_time > 5.0
        assert wait_time < 7.0
    
    def test_reset(self):
        """Test resetting the rate limiter."""
        limiter = TokenBucketRateLimiter(rate=10, per=60, burst=10)
        
        # Consume all tokens
        for _ in range(10):
            limiter.acquire()
        
        assert limiter.tokens < 1
        
        # Reset
        limiter.reset()
        
        assert limiter.tokens == 10.0
    
    def test_get_statistics(self):
        """Test getting rate limiter statistics."""
        limiter = TokenBucketRateLimiter(rate=10, per=60, burst=15)
        
        # Make some requests
        for _ in range(5):
            limiter.acquire()
        
        stats = limiter.get_statistics()
        
        assert stats['rate'] == 10
        assert stats['per_seconds'] == 60
        assert stats['burst_capacity'] == 15
        assert stats['total_requests'] == 5
        assert 'current_tokens' in stats
        assert 'times_waited' in stats
        assert 'total_wait_time_seconds' in stats
        assert 'average_wait_time_seconds' in stats
    
    def test_repr(self):
        """Test string representation."""
        limiter = TokenBucketRateLimiter(rate=10, per=60, burst=15)
        repr_str = repr(limiter)
        
        assert 'TokenBucketRateLimiter' in repr_str
        assert 'rate=10' in repr_str
        assert 'per=60' in repr_str
        assert 'burst=15' in repr_str


class TestTokenBucketRateLimiterThreadSafety:
    """Thread safety tests for TokenBucketRateLimiter."""
    
    def test_concurrent_acquire(self):
        """Test concurrent token acquisition from multiple threads."""
        limiter = TokenBucketRateLimiter(rate=100, per=1, burst=100)  # High rate for testing
        
        acquired_count = [0]
        lock = threading.Lock()
        
        def acquire_tokens():
            for _ in range(10):
                if limiter.try_acquire():
                    with lock:
                        acquired_count[0] += 1
        
        threads = [threading.Thread(target=acquire_tokens) for _ in range(10)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have acquired exactly 100 tokens (initial capacity)
        assert acquired_count[0] == 100
    
    def test_concurrent_refill_and_acquire(self):
        """Test concurrent refill and acquire operations."""
        limiter = TokenBucketRateLimiter(rate=100, per=1, burst=10)  # Fast refill
        
        errors = []
        
        def acquire_repeatedly():
            try:
                for _ in range(20):
                    limiter.acquire(timeout=1.0)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=acquire_repeatedly) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Errors occurred: {errors}"


class TestNoOpRateLimiter:
    """Tests for NoOpRateLimiter class."""
    
    def test_acquire_always_succeeds(self):
        """Test that acquire always returns True."""
        limiter = NoOpRateLimiter()
        
        for _ in range(1000):
            assert limiter.acquire() is True
    
    def test_try_acquire_always_succeeds(self):
        """Test that try_acquire always returns True."""
        limiter = NoOpRateLimiter()
        
        for _ in range(1000):
            assert limiter.try_acquire() is True
    
    def test_get_available_tokens_infinite(self):
        """Test that available tokens is infinite."""
        limiter = NoOpRateLimiter()
        
        assert limiter.get_available_tokens() == float('inf')
    
    def test_get_wait_time_zero(self):
        """Test that wait time is always zero."""
        limiter = NoOpRateLimiter()
        
        assert limiter.get_wait_time() == 0.0
        assert limiter.get_wait_time(100) == 0.0
    
    def test_reset_noop(self):
        """Test that reset does nothing."""
        limiter = NoOpRateLimiter()
        limiter.reset()  # Should not raise
    
    def test_get_statistics(self):
        """Test statistics for NoOpRateLimiter."""
        limiter = NoOpRateLimiter()
        stats = limiter.get_statistics()
        
        assert stats['rate'] == 'unlimited'
        assert stats['current_tokens'] == float('inf')
    
    def test_repr(self):
        """Test string representation."""
        limiter = NoOpRateLimiter()
        assert repr(limiter) == "NoOpRateLimiter()"


class TestRateLimitConfigIntegration:
    """Integration tests for rate limiting with FabricConfig."""
    
    def test_rate_limit_config_from_dict_default(self):
        """Test RateLimitConfig default values."""
        from fabric_client import RateLimitConfig
        
        config = RateLimitConfig.from_dict(None)
        
        assert config.enabled is True
        assert config.requests_per_minute == 10
        assert config.burst is None
    
    def test_rate_limit_config_from_dict_custom(self):
        """Test RateLimitConfig with custom values."""
        from fabric_client import RateLimitConfig
        
        config = RateLimitConfig.from_dict({
            'enabled': False,
            'requests_per_minute': 20,
            'burst': 30
        })
        
        assert config.enabled is False
        assert config.requests_per_minute == 20
        assert config.burst == 30
    
    def test_fabric_config_includes_rate_limit(self):
        """Test that FabricConfig includes rate limit settings."""
        from fabric_client import FabricConfig
        
        config = FabricConfig.from_dict({
            'fabric': {
                'workspace_id': 'test-workspace',
                'rate_limit': {
                    'enabled': True,
                    'requests_per_minute': 15,
                    'burst': 25
                }
            }
        })
        
        assert config.rate_limit.enabled is True
        assert config.rate_limit.requests_per_minute == 15
        assert config.rate_limit.burst == 25
    
    def test_fabric_config_default_rate_limit(self):
        """Test FabricConfig with default rate limit."""
        from fabric_client import FabricConfig
        
        config = FabricConfig.from_dict({
            'fabric': {
                'workspace_id': 'test-workspace'
            }
        })
        
        assert config.rate_limit.enabled is True
        assert config.rate_limit.requests_per_minute == 10
    
    def test_client_creates_rate_limiter_enabled(self):
        """Test client creates rate limiter when enabled."""
        from fabric_client import FabricConfig, FabricOntologyClient
        
        config = FabricConfig(
            workspace_id='12345678-1234-1234-1234-123456789012'
        )
        
        # Mock the credential to avoid authentication
        with patch.object(FabricOntologyClient, '_get_credential'):
            client = FabricOntologyClient(config)
        
        assert isinstance(client.rate_limiter, TokenBucketRateLimiter)
        assert client.rate_limiter.rate == 10
        assert client.rate_limiter.capacity == 10
    
    def test_client_creates_noop_limiter_disabled(self):
        """Test client creates NoOpRateLimiter when disabled."""
        from fabric_client import FabricConfig, FabricOntologyClient, RateLimitConfig
        
        config = FabricConfig(
            workspace_id='12345678-1234-1234-1234-123456789012',
            rate_limit=RateLimitConfig(enabled=False)
        )
        
        # Mock the credential to avoid authentication
        with patch.object(FabricOntologyClient, '_get_credential'):
            client = FabricOntologyClient(config)
        
        assert isinstance(client.rate_limiter, NoOpRateLimiter)
    
    def test_client_get_rate_limit_statistics(self):
        """Test getting rate limit statistics from client."""
        from fabric_client import FabricConfig, FabricOntologyClient
        
        config = FabricConfig(
            workspace_id='12345678-1234-1234-1234-123456789012'
        )
        
        with patch.object(FabricOntologyClient, '_get_credential'):
            client = FabricOntologyClient(config)
        
        stats = client.get_rate_limit_statistics()
        
        assert 'rate' in stats
        assert 'total_requests' in stats
        assert 'times_waited' in stats


class TestRateLimitRequestIntegration:
    """Integration tests for rate limiting in request handling."""
    
    def test_make_request_acquires_token(self):
        """Test that _make_request acquires rate limit token."""
        from fabric_client import FabricConfig, FabricOntologyClient
        
        config = FabricConfig(
            workspace_id='12345678-1234-1234-1234-123456789012'
        )
        
        with patch.object(FabricOntologyClient, '_get_credential'):
            client = FabricOntologyClient(config)
        
        # Mock the actual request
        with patch('fabric_client.requests.request') as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_request.return_value = mock_response
            
            # Mock token acquisition
            client._access_token = 'test-token'
            client._token_expires = time.time() + 3600
            
            # Make request
            client._make_request('GET', 'http://test.com', 'Test operation')
            
            # Verify request was made
            mock_request.assert_called_once()
            
            # Verify token was consumed
            stats = client.get_rate_limit_statistics()
            assert stats['total_requests'] >= 1
