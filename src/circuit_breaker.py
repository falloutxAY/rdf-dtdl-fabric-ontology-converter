"""
Circuit Breaker Pattern Implementation

Provides fault tolerance for API calls by preventing cascading failures.
When a service is failing, the circuit breaker trips to OPEN state,
blocking requests and giving the service time to recover.

States:
- CLOSED: Normal operation, requests flow through
- OPEN: Service failing, requests blocked to prevent resource exhaustion
- HALF_OPEN: Testing if service has recovered

Usage:
    breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
    
    try:
        result = breaker.call(api_function, arg1, arg2)
    except CircuitBreakerOpenError:
        # Circuit is open, service is unavailable
        handle_service_unavailable()
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerError(Exception):
    """Base exception for circuit breaker errors."""
    pass


class CircuitBreakerOpenError(CircuitBreakerError):
    """Raised when circuit is open and not accepting requests."""
    
    def __init__(self, message: str, remaining_time: float = 0):
        """
        Args:
            message: Error description
            remaining_time: Seconds until recovery attempt
        """
        self.remaining_time = remaining_time
        super().__init__(message)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior.
    
    Attributes:
        failure_threshold: Number of failures before opening circuit (default: 5)
        recovery_timeout: Seconds to wait before trying half-open (default: 60)
        success_threshold: Successes needed in half-open to close (default: 2)
        monitored_exceptions: Exception types that count as failures
        excluded_exceptions: Exception types that don't count as failures
        name: Identifier for this circuit breaker (for logging)
    """
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 2
    monitored_exceptions: Set[Type[Exception]] = field(default_factory=lambda: {Exception})
    excluded_exceptions: Set[Type[Exception]] = field(default_factory=set)
    name: str = "default"
    
    def __post_init__(self):
        """Validate configuration values."""
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout < 0:
            raise ValueError("recovery_timeout must be >= 0")
        if self.success_threshold < 1:
            raise ValueError("success_threshold must be >= 1")
    
    @classmethod
    def from_dict(cls, config_dict: Optional[Dict[str, Any]], name: str = "default") -> 'CircuitBreakerConfig':
        """Create config from dictionary.
        
        Args:
            config_dict: Configuration dictionary (can be None for defaults)
            name: Name for this circuit breaker
            
        Returns:
            CircuitBreakerConfig instance
        """
        if config_dict is None:
            return cls(name=name)
        
        return cls(
            failure_threshold=config_dict.get('failure_threshold', 5),
            recovery_timeout=config_dict.get('recovery_timeout', 60.0),
            success_threshold=config_dict.get('success_threshold', 2),
            name=name
        )


@dataclass
class CircuitBreakerMetrics:
    """Metrics for monitoring circuit breaker health.
    
    Provides visibility into circuit breaker state and history
    for debugging and monitoring purposes.
    """
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0  # Calls blocked by open circuit
    state_changes: List[Dict[str, Any]] = field(default_factory=list)
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    current_failure_streak: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for reporting."""
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "rejected_calls": self.rejected_calls,
            "success_rate": self.success_rate,
            "current_failure_streak": self.current_failure_streak,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "state_changes_count": len(self.state_changes),
        }
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_calls == 0:
            return 100.0
        return (self.successful_calls / self.total_calls) * 100


class CircuitBreaker:
    """
    Circuit breaker implementation for fault tolerance.
    
    The circuit breaker monitors calls to external services and prevents
    cascading failures by blocking requests when the service is unhealthy.
    
    State Machine:
        CLOSED --[failures >= threshold]--> OPEN
        OPEN --[recovery_timeout expires]--> HALF_OPEN
        HALF_OPEN --[success]--> CLOSED
        HALF_OPEN --[failure]--> OPEN
    
    Thread Safety:
        All state transitions are protected by a lock to ensure
        thread-safe operation in concurrent environments.
    
    Example:
        >>> breaker = CircuitBreaker(
        ...     failure_threshold=5,
        ...     recovery_timeout=60,
        ...     name="fabric_api"
        ... )
        >>> 
        >>> try:
        ...     result = breaker.call(client.create_ontology, name, definition)
        ... except CircuitBreakerOpenError as e:
        ...     print(f"Service unavailable, retry in {e.remaining_time:.0f}s")
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
        monitored_exceptions: Optional[Set[Type[Exception]]] = None,
        excluded_exceptions: Optional[Set[Type[Exception]]] = None,
        name: str = "default"
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Failures needed to open circuit
            recovery_timeout: Seconds before attempting recovery
            success_threshold: Successes needed in half-open to close
            monitored_exceptions: Exception types that count as failures
            excluded_exceptions: Exception types to ignore (not count as failures)
            name: Identifier for logging and metrics
        """
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold,
            monitored_exceptions=monitored_exceptions or {Exception},
            excluded_exceptions=excluded_exceptions or set(),
            name=name
        )
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0  # Used in half-open state
        self._last_failure_time: Optional[float] = None
        self._opened_at: Optional[float] = None
        self._lock = threading.RLock()
        self._metrics = CircuitBreakerMetrics()
        
        logger.info(
            f"Circuit breaker '{name}' initialized: "
            f"failure_threshold={failure_threshold}, "
            f"recovery_timeout={recovery_timeout}s, "
            f"success_threshold={success_threshold}"
        )
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state (thread-safe)."""
        with self._lock:
            self._check_state_transition()
            return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self.state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self.state == CircuitState.HALF_OPEN
    
    @property
    def metrics(self) -> CircuitBreakerMetrics:
        """Get circuit breaker metrics."""
        return self._metrics
    
    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        with self._lock:
            return self._failure_count
    
    def get_remaining_timeout(self) -> float:
        """Get seconds remaining until recovery attempt.
        
        Returns:
            Seconds until half-open state, or 0 if not open
        """
        with self._lock:
            if self._state != CircuitState.OPEN or self._opened_at is None:
                return 0.0
            
            elapsed = time.time() - self._opened_at
            remaining = self.config.recovery_timeout - elapsed
            return max(0.0, remaining)
    
    def _check_state_transition(self) -> None:
        """Check if state should transition (must hold lock)."""
        if self._state == CircuitState.OPEN and self._opened_at is not None:
            elapsed = time.time() - self._opened_at
            if elapsed >= self.config.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state (must hold lock)."""
        old_state = self._state
        if old_state == new_state:
            return
        
        self._state = new_state
        
        # Reset counters based on new state
        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
            self._opened_at = None
        elif new_state == CircuitState.OPEN:
            self._opened_at = time.time()
            self._success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._success_count = 0
        
        # Record state change
        self._metrics.state_changes.append({
            "timestamp": time.time(),
            "from": old_state.value,
            "to": new_state.value,
        })
        
        logger.warning(
            f"Circuit breaker '{self.config.name}' state changed: "
            f"{old_state.value} -> {new_state.value}"
        )
    
    def _on_success(self) -> None:
        """Record a successful call (must hold lock)."""
        self._metrics.total_calls += 1
        self._metrics.successful_calls += 1
        self._metrics.last_success_time = time.time()
        self._metrics.current_failure_streak = 0
        
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            logger.debug(
                f"Circuit breaker '{self.config.name}' half-open success "
                f"({self._success_count}/{self.config.success_threshold})"
            )
            
            if self._success_count >= self.config.success_threshold:
                logger.info(
                    f"Circuit breaker '{self.config.name}' recovered "
                    f"after {self.config.success_threshold} successes"
                )
                self._transition_to(CircuitState.CLOSED)
        
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success in closed state
            self._failure_count = 0
    
    def _on_failure(self, exception: Exception) -> None:
        """Record a failed call (must hold lock)."""
        self._metrics.total_calls += 1
        self._metrics.failed_calls += 1
        self._metrics.last_failure_time = time.time()
        self._metrics.current_failure_streak += 1
        self._last_failure_time = time.time()
        
        if self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open immediately opens circuit
            logger.warning(
                f"Circuit breaker '{self.config.name}' failed in half-open state, "
                f"reopening circuit"
            )
            self._transition_to(CircuitState.OPEN)
        
        elif self._state == CircuitState.CLOSED:
            self._failure_count += 1
            logger.debug(
                f"Circuit breaker '{self.config.name}' failure "
                f"({self._failure_count}/{self.config.failure_threshold})"
            )
            
            if self._failure_count >= self.config.failure_threshold:
                logger.error(
                    f"Circuit breaker '{self.config.name}' tripped open "
                    f"after {self._failure_count} failures"
                )
                self._transition_to(CircuitState.OPEN)
    
    def _is_monitored_exception(self, exception: Exception) -> bool:
        """Check if exception should count as a failure."""
        # Check exclusions first
        for exc_type in self.config.excluded_exceptions:
            if isinstance(exception, exc_type):
                return False
        
        # Then check if it's a monitored type
        for exc_type in self.config.monitored_exceptions:
            if isinstance(exception, exc_type):
                return True
        
        return False
    
    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute function through the circuit breaker.
        
        If the circuit is open, raises CircuitBreakerOpenError immediately
        without calling the function. If closed or half-open, the function
        is called and the result is used to update circuit state.
        
        Args:
            func: Function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Return value from func
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Any exception from func (after recording failure)
        """
        with self._lock:
            self._check_state_transition()
            
            if self._state == CircuitState.OPEN:
                remaining = self.get_remaining_timeout()
                self._metrics.rejected_calls += 1
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.config.name}' is open. "
                    f"Service unavailable. Retry in {remaining:.0f}s",
                    remaining_time=remaining
                )
        
        try:
            result = func(*args, **kwargs)
            
            with self._lock:
                self._on_success()
            
            return result
        
        except Exception as e:
            with self._lock:
                if self._is_monitored_exception(e):
                    self._on_failure(e)
            raise
    
    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        with self._lock:
            logger.info(f"Circuit breaker '{self.config.name}' manually reset")
            self._transition_to(CircuitState.CLOSED)
            self._failure_count = 0
            self._success_count = 0
    
    def force_open(self) -> None:
        """Manually open the circuit (for testing or emergency)."""
        with self._lock:
            logger.warning(f"Circuit breaker '{self.config.name}' manually opened")
            self._transition_to(CircuitState.OPEN)
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status for monitoring.
        
        Returns:
            Dictionary with state, metrics, and configuration
        """
        with self._lock:
            self._check_state_transition()
            return {
                "name": self.config.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "remaining_timeout": self.get_remaining_timeout(),
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "recovery_timeout": self.config.recovery_timeout,
                    "success_threshold": self.config.success_threshold,
                },
                "metrics": self._metrics.to_dict(),
            }


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.
    
    Provides a central location to create, access, and monitor
    circuit breakers for different services or endpoints.
    
    Example:
        >>> registry = CircuitBreakerRegistry()
        >>> registry.register("ontology_api", failure_threshold=5)
        >>> 
        >>> breaker = registry.get("ontology_api")
        >>> result = breaker.call(client.list_ontologies)
    """
    
    def __init__(self):
        """Initialize the registry."""
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()
    
    def register(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
        monitored_exceptions: Optional[Set[Type[Exception]]] = None,
        excluded_exceptions: Optional[Set[Type[Exception]]] = None
    ) -> CircuitBreaker:
        """
        Register a new circuit breaker.
        
        Args:
            name: Unique identifier for the circuit breaker
            failure_threshold: Failures before opening
            recovery_timeout: Seconds before recovery attempt
            success_threshold: Successes needed to close
            monitored_exceptions: Exception types to monitor
            excluded_exceptions: Exception types to exclude
            
        Returns:
            The created CircuitBreaker instance
            
        Raises:
            ValueError: If name already registered
        """
        with self._lock:
            if name in self._breakers:
                raise ValueError(f"Circuit breaker '{name}' already registered")
            
            breaker = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                success_threshold=success_threshold,
                monitored_exceptions=monitored_exceptions,
                excluded_exceptions=excluded_exceptions,
                name=name
            )
            self._breakers[name] = breaker
            return breaker
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name."""
        with self._lock:
            return self._breakers.get(name)
    
    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
        **kwargs: Any
    ) -> CircuitBreaker:
        """Get existing circuit breaker or create new one."""
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    success_threshold=success_threshold,
                    name=name,
                    **kwargs
                )
            return self._breakers[name]
    
    def remove(self, name: str) -> bool:
        """Remove a circuit breaker from the registry."""
        with self._lock:
            if name in self._breakers:
                del self._breakers[name]
                return True
            return False
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all registered circuit breakers."""
        with self._lock:
            return {
                name: breaker.get_status()
                for name, breaker in self._breakers.items()
            }
    
    def reset_all(self) -> None:
        """Reset all circuit breakers to closed state."""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()


# Default global registry
_default_registry = CircuitBreakerRegistry()


def get_circuit_breaker(name: str) -> Optional[CircuitBreaker]:
    """Get a circuit breaker from the default registry."""
    return _default_registry.get(name)


def register_circuit_breaker(
    name: str,
    **kwargs: Any
) -> CircuitBreaker:
    """Register a circuit breaker in the default registry."""
    return _default_registry.register(name, **kwargs)


def get_or_create_circuit_breaker(
    name: str,
    **kwargs: Any
) -> CircuitBreaker:
    """Get or create a circuit breaker in the default registry."""
    return _default_registry.get_or_create(name, **kwargs)
