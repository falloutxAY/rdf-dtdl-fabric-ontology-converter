"""
Common utilities package for Fabric Ontology Converter plugins.

This package provides shared functionality used across all format plugins:
- Type mapping registry
- ID generation
- Unified validation results
- Property utilities
- Serialization helpers

Usage:
    from common import get_type_registry, get_id_generator, ValidationResult
"""

from .type_registry import (
    TypeMappingRegistry,
    TypeMapping,
    FABRIC_TYPES,
    get_type_registry,
)

from .id_generator import (
    IDGenerator,
    get_id_generator,
    reset_id_generator,
)

from .validation import (
    Severity,
    IssueCategory,
    ValidationIssue,
    ValidationResult,
)

__all__ = [
    # Type registry
    "TypeMappingRegistry",
    "TypeMapping",
    "FABRIC_TYPES",
    "get_type_registry",
    # ID generator
    "IDGenerator",
    "get_id_generator",
    "reset_id_generator",
    # Validation
    "Severity",
    "IssueCategory",
    "ValidationIssue",
    "ValidationResult",
]
