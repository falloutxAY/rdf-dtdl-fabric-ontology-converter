"""
ID Generator - Consistent ID generation for Fabric entities.

This module provides thread-safe ID generation for Fabric entity types,
relationship types, and properties. All IDs are 13-digit numeric strings
as required by the Fabric Ontology API.

Usage:
    from common.id_generator import get_id_generator
    
    gen = get_id_generator()
    entity_id = gen.next_id()  # "1000000000000"
    prop_id = gen.next_id()    # "1000000000001"
"""

import threading
from typing import Dict, Optional

# Default starting prefix for IDs
DEFAULT_PREFIX = 1000000000000


class IDGenerator:
    """
    Thread-safe ID generator for Fabric ontology entities.
    
    Generates sequential 13-digit numeric string IDs suitable for:
    - EntityType.id
    - RelationshipType.id
    - EntityTypeProperty.id
    
    Supports namespaced counters for tracking IDs by category.
    
    Example:
        >>> gen = IDGenerator()
        >>> gen.next_id()
        '1000000000000'
        >>> gen.next_id()
        '1000000000001'
        
        >>> gen.next_id_for_namespace("entities")
        '1000000000002'
        >>> gen.next_id_for_namespace("properties")
        '1000000000003'
    """
    
    def __init__(self, prefix: int = DEFAULT_PREFIX):
        """
        Initialize the ID generator.
        
        Args:
            prefix: Starting ID value (default: 1000000000000).
        """
        self._counter = prefix
        self._lock = threading.Lock()
        self._namespace_counters: Dict[str, int] = {}
        self._namespace_ranges: Dict[str, range] = {}
    
    def next_id(self) -> str:
        """
        Generate the next sequential ID.
        
        Returns:
            13-digit numeric string ID.
        
        Thread-safe.
        """
        with self._lock:
            current = self._counter
            self._counter += 1
            return str(current)
    
    def next_id_for_namespace(self, namespace: str) -> str:
        """
        Generate ID tracked under a specific namespace.
        
        Useful for tracking how many IDs were generated for each
        category (entities, relationships, properties).
        
        Args:
            namespace: Namespace identifier (e.g., "entities").
        
        Returns:
            13-digit numeric string ID.
        
        Thread-safe.
        """
        with self._lock:
            if namespace not in self._namespace_counters:
                self._namespace_counters[namespace] = 0
            
            current = self._counter
            self._counter += 1
            self._namespace_counters[namespace] += 1
            return str(current)
    
    def get_namespace_count(self, namespace: str) -> int:
        """
        Get number of IDs generated for a namespace.
        
        Args:
            namespace: Namespace identifier.
        
        Returns:
            Count of IDs generated for this namespace.
        """
        return self._namespace_counters.get(namespace, 0)
    
    def reserve_range(self, namespace: str, count: int) -> range:
        """
        Reserve a range of IDs for a namespace.
        
        Useful for batch operations where you need to know
        the ID range in advance.
        
        Args:
            namespace: Namespace identifier.
            count: Number of IDs to reserve.
        
        Returns:
            Range of reserved ID values.
        
        Thread-safe.
        """
        with self._lock:
            start = self._counter
            self._counter += count
            end = self._counter
            
            id_range = range(start, end)
            self._namespace_ranges[namespace] = id_range
            
            if namespace not in self._namespace_counters:
                self._namespace_counters[namespace] = 0
            self._namespace_counters[namespace] += count
            
            return id_range
    
    def reset(self, prefix: Optional[int] = None) -> None:
        """
        Reset the generator to initial state.
        
        Args:
            prefix: Optional new starting prefix.
        
        Thread-safe.
        """
        with self._lock:
            self._counter = prefix if prefix is not None else DEFAULT_PREFIX
            self._namespace_counters.clear()
            self._namespace_ranges.clear()
    
    @property
    def current(self) -> int:
        """
        Get current counter value without incrementing.
        
        Returns:
            Current counter value.
        """
        return self._counter
    
    @property
    def total_generated(self) -> int:
        """
        Get total number of IDs generated.
        
        Returns:
            Total count since initialization or last reset.
        """
        return self._counter - DEFAULT_PREFIX
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get generation statistics.
        
        Returns:
            Dict with counts by namespace and total.
        """
        stats = {
            "total": self.total_generated,
            "current": self._counter,
        }
        stats.update(self._namespace_counters)
        return stats


# =============================================================================
# Global Instance Management
# =============================================================================

_generator: Optional[IDGenerator] = None
_generator_lock = threading.Lock()


def get_id_generator() -> IDGenerator:
    """
    Get the global ID generator instance.
    
    Creates a new instance if one doesn't exist.
    
    Returns:
        The singleton IDGenerator instance.
    
    Thread-safe.
    """
    global _generator
    with _generator_lock:
        if _generator is None:
            _generator = IDGenerator()
        return _generator


def reset_id_generator(prefix: Optional[int] = None) -> None:
    """
    Reset the global ID generator.
    
    Args:
        prefix: Optional new starting prefix.
    
    Thread-safe.
    """
    global _generator
    with _generator_lock:
        if _generator is not None:
            _generator.reset(prefix)
        else:
            _generator = IDGenerator(prefix or DEFAULT_PREFIX)


def create_id_generator(prefix: int = DEFAULT_PREFIX) -> IDGenerator:
    """
    Create a new independent ID generator.
    
    Use this when you need a separate ID sequence,
    e.g., for testing or isolated conversions.
    
    Args:
        prefix: Starting ID value.
    
    Returns:
        New IDGenerator instance.
    """
    return IDGenerator(prefix)


# =============================================================================
# ID Validation Utilities
# =============================================================================

def is_valid_fabric_id(id_value: str) -> bool:
    """
    Check if a string is a valid Fabric ID.
    
    Fabric IDs are 13-digit numeric strings.
    
    Args:
        id_value: String to validate.
    
    Returns:
        True if valid Fabric ID format.
    """
    if not isinstance(id_value, str):
        return False
    if len(id_value) != 13:
        return False
    return id_value.isdigit()


def validate_id_format(id_value: str) -> None:
    """
    Validate that a string is a valid Fabric ID.
    
    Args:
        id_value: String to validate.
    
    Raises:
        ValueError: If not a valid Fabric ID.
    """
    if not is_valid_fabric_id(id_value):
        raise ValueError(
            f"Invalid Fabric ID format: '{id_value}'. "
            f"Expected 13-digit numeric string."
        )
