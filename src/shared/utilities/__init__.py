"""
Common utilities module for Fabric Ontology Converter.

This module provides shared infrastructure for all format plugins:
- Type mapping registry for converting source types to Fabric types
- ID generator for consistent entity ID generation
- Unified validation models

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
)
from .validation import (
    ValidationResult,
    ValidationIssue,
    Severity,
    IssueCategory,
)

__all__ = [
    # Type Registry
    "TypeMappingRegistry",
    "TypeMapping",
    "FABRIC_TYPES",
    "get_type_registry",
    # ID Generator
    "IDGenerator",
    "get_id_generator",
    # Validation
    "ValidationResult",
    "ValidationIssue",
    "Severity",
    "IssueCategory",
]
