"""
Type Mapping Registry - Unified type mapping infrastructure.

This module provides a centralized registry for mapping source format types
to Microsoft Fabric Ontology types. Each plugin registers its type mappings
with this registry.

Usage:
    from common.type_registry import get_type_registry
    
    # Register mappings for a format
    registry = get_type_registry()
    registry.register_mapping("rdf", "http://www.w3.org/2001/XMLSchema#string", "String")
    
    # Get Fabric type
    fabric_type = registry.get_fabric_type("rdf", "http://www.w3.org/2001/XMLSchema#integer")
    # Returns: "BigInt"
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Fabric supported value types
FABRIC_TYPES: FrozenSet[str] = frozenset({
    "String",
    "Boolean", 
    "DateTime",
    "BigInt",
    "Double",
    "Int",
    "Long",
    "Float",
    "Decimal",
})


@dataclass
class TypeMapping:
    """
    Represents a mapping from a source type to a Fabric type.
    
    Attributes:
        source_type: The source type URI or identifier.
        fabric_type: The corresponding Fabric value type.
        converter: Optional function to convert values (e.g., for units).
        notes: Additional documentation about the mapping.
        precision_loss: True if the mapping may lose precision.
    """
    source_type: str
    fabric_type: str
    converter: Optional[Callable[[Any], Any]] = None
    notes: str = ""
    precision_loss: bool = False
    
    def __post_init__(self) -> None:
        """Validate the mapping."""
        if self.fabric_type not in FABRIC_TYPES:
            raise ValueError(
                f"Invalid Fabric type '{self.fabric_type}'. "
                f"Must be one of: {', '.join(sorted(FABRIC_TYPES))}"
            )


class TypeMappingRegistry:
    """
    Centralized registry for type mappings from various formats to Fabric types.
    
    Each format plugin registers its mappings here, allowing:
    - Consistent type resolution across formats
    - Custom type converters
    - Documentation of precision loss
    - Fallback type handling
    
    Example:
        >>> registry = TypeMappingRegistry()
        >>> registry.register_mapping("rdf", str(XSD.string), "String")
        >>> registry.register_mapping("rdf", str(XSD.integer), "BigInt")
        >>> 
        >>> fabric_type = registry.get_fabric_type("rdf", str(XSD.integer))
        >>> print(fabric_type)  # "BigInt"
    """
    
    def __init__(self, default_type: str = "String"):
        """
        Initialize the registry.
        
        Args:
            default_type: Default Fabric type when no mapping found.
        """
        if default_type not in FABRIC_TYPES:
            raise ValueError(f"Invalid default type: {default_type}")
        
        self._mappings: Dict[str, Dict[str, TypeMapping]] = {}
        self._default_type = default_type
        self._aliases: Dict[str, Dict[str, str]] = {}  # format -> alias -> canonical
    
    def register_format(self, format_name: str) -> None:
        """
        Register a new format namespace.
        
        Args:
            format_name: Unique format identifier (e.g., "rdf", "dtdl").
        """
        format_key = format_name.lower()
        if format_key not in self._mappings:
            self._mappings[format_key] = {}
            self._aliases[format_key] = {}
            logger.debug(f"Registered format namespace: {format_name}")
    
    def register_mapping(
        self,
        format_name: str,
        source_type: str,
        fabric_type: str,
        converter: Optional[Callable[[Any], Any]] = None,
        notes: str = "",
        precision_loss: bool = False,
    ) -> None:
        """
        Register a type mapping for a format.
        
        Args:
            format_name: Format identifier.
            source_type: Source type URI or identifier.
            fabric_type: Target Fabric value type.
            converter: Optional value converter function.
            notes: Documentation about the mapping.
            precision_loss: True if precision may be lost.
        
        Raises:
            ValueError: If fabric_type is not valid.
        """
        format_key = format_name.lower()
        if format_key not in self._mappings:
            self.register_format(format_name)
        
        mapping = TypeMapping(
            source_type=source_type,
            fabric_type=fabric_type,
            converter=converter,
            notes=notes,
            precision_loss=precision_loss,
        )
        
        self._mappings[format_key][source_type] = mapping
        logger.debug(f"Registered mapping: {format_name}:{source_type} -> {fabric_type}")
    
    def register_mappings(
        self,
        format_name: str,
        mappings: Dict[str, str],
    ) -> None:
        """
        Bulk register mappings for a format.
        
        Args:
            format_name: Format identifier.
            mappings: Dict of source_type -> fabric_type.
        """
        for source_type, fabric_type in mappings.items():
            self.register_mapping(format_name, source_type, fabric_type)
    
    def register_alias(
        self,
        format_name: str,
        alias: str,
        canonical: str,
    ) -> None:
        """
        Register an alias for a source type.
        
        Useful for formats with multiple representations of the same type.
        
        Args:
            format_name: Format identifier.
            alias: Alias type identifier.
            canonical: Canonical type identifier.
        """
        format_key = format_name.lower()
        if format_key not in self._aliases:
            self._aliases[format_key] = {}
        self._aliases[format_key][alias] = canonical
    
    def get_fabric_type(
        self,
        format_name: str,
        source_type: str,
        default: Optional[str] = None,
    ) -> str:
        """
        Get the Fabric type for a source type.
        
        Args:
            format_name: Format identifier.
            source_type: Source type to map.
            default: Override default type for this call.
        
        Returns:
            Corresponding Fabric type, or default if not found.
        """
        format_key = format_name.lower()
        
        # Check for alias
        canonical = self._aliases.get(format_key, {}).get(source_type, source_type)
        
        # Look up mapping
        mapping = self._mappings.get(format_key, {}).get(canonical)
        if mapping:
            return mapping.fabric_type
        
        # Return default
        return default if default is not None else self._default_type
    
    def get_mapping(
        self,
        format_name: str,
        source_type: str,
    ) -> Optional[TypeMapping]:
        """
        Get full mapping details for a source type.
        
        Args:
            format_name: Format identifier.
            source_type: Source type to look up.
        
        Returns:
            TypeMapping if found, None otherwise.
        """
        format_key = format_name.lower()
        canonical = self._aliases.get(format_key, {}).get(source_type, source_type)
        return self._mappings.get(format_key, {}).get(canonical)
    
    def convert_value(
        self,
        format_name: str,
        source_type: str,
        value: Any,
    ) -> Any:
        """
        Convert a value using the registered converter.
        
        Args:
            format_name: Format identifier.
            source_type: Source type of the value.
            value: Value to convert.
        
        Returns:
            Converted value, or original if no converter registered.
        """
        mapping = self.get_mapping(format_name, source_type)
        if mapping and mapping.converter:
            return mapping.converter(value)
        return value
    
    def list_mappings(self, format_name: str) -> Dict[str, str]:
        """
        List all mappings for a format.
        
        Args:
            format_name: Format identifier.
        
        Returns:
            Dict of source_type -> fabric_type.
        """
        format_key = format_name.lower()
        return {
            source: mapping.fabric_type
            for source, mapping in self._mappings.get(format_key, {}).items()
        }
    
    def list_formats(self) -> List[str]:
        """List all registered format names."""
        return list(self._mappings.keys())
    
    def get_precision_loss_types(self, format_name: str) -> List[str]:
        """
        Get types that may lose precision during conversion.
        
        Args:
            format_name: Format identifier.
        
        Returns:
            List of source types with potential precision loss.
        """
        format_key = format_name.lower()
        return [
            source
            for source, mapping in self._mappings.get(format_key, {}).items()
            if mapping.precision_loss
        ]
    
    @property
    def default_type(self) -> str:
        """Get the default Fabric type."""
        return self._default_type
    
    @default_type.setter
    def default_type(self, value: str) -> None:
        """Set the default Fabric type."""
        if value not in FABRIC_TYPES:
            raise ValueError(f"Invalid default type: {value}")
        self._default_type = value


# =============================================================================
# Global Registry Instance
# =============================================================================

_registry: Optional[TypeMappingRegistry] = None


def get_type_registry() -> TypeMappingRegistry:
    """
    Get the global type mapping registry.
    
    Returns:
        The singleton TypeMappingRegistry instance.
    """
    global _registry
    if _registry is None:
        _registry = TypeMappingRegistry()
        _initialize_default_mappings(_registry)
    return _registry


def _initialize_default_mappings(registry: TypeMappingRegistry) -> None:
    """
    Initialize default mappings for built-in formats.
    
    This is called when the registry is first created.
    """
    # RDF/XSD type mappings
    XSD_NS = "http://www.w3.org/2001/XMLSchema#"
    registry.register_mappings("rdf", {
        # String types
        f"{XSD_NS}string": "String",
        f"{XSD_NS}anyURI": "String",
        f"{XSD_NS}normalizedString": "String",
        f"{XSD_NS}token": "String",
        f"{XSD_NS}language": "String",
        f"{XSD_NS}Name": "String",
        f"{XSD_NS}NCName": "String",
        f"{XSD_NS}NMTOKEN": "String",
        
        # Boolean
        f"{XSD_NS}boolean": "Boolean",
        
        # Date/Time
        f"{XSD_NS}dateTime": "DateTime",
        f"{XSD_NS}date": "DateTime",
        f"{XSD_NS}dateTimeStamp": "DateTime",
        f"{XSD_NS}time": "String",  # Time-only not directly supported
        f"{XSD_NS}duration": "String",
        
        # Integer types
        f"{XSD_NS}integer": "BigInt",
        f"{XSD_NS}int": "BigInt",
        f"{XSD_NS}long": "BigInt",
        f"{XSD_NS}short": "BigInt",
        f"{XSD_NS}byte": "BigInt",
        f"{XSD_NS}nonNegativeInteger": "BigInt",
        f"{XSD_NS}positiveInteger": "BigInt",
        f"{XSD_NS}unsignedInt": "BigInt",
        f"{XSD_NS}unsignedLong": "BigInt",
        
        # Floating point
        f"{XSD_NS}double": "Double",
        f"{XSD_NS}float": "Double",
        f"{XSD_NS}decimal": "Double",
    })
    
    # DTDL type mappings
    registry.register_mappings("dtdl", {
        "boolean": "Boolean",
        "byte": "BigInt",
        "short": "BigInt",
        "integer": "BigInt",
        "long": "BigInt",
        "unsignedByte": "BigInt",
        "unsignedShort": "BigInt",
        "unsignedInteger": "BigInt",
        "unsignedLong": "BigInt",
        "float": "Double",
        "double": "Double",
        "decimal": "Double",
        "string": "String",
        "uuid": "String",
        "bytes": "String",
        "date": "DateTime",
        "dateTime": "DateTime",
        "time": "String",
        "duration": "String",
        "point": "String",
        "lineString": "String",
        "polygon": "String",
        "multiPoint": "String",
        "multiLineString": "String",
        "multiPolygon": "String",
        "scaledDecimal": "String",
    })


# =============================================================================
# Type Hierarchy for Union Resolution
# =============================================================================

# When resolving union types, use this hierarchy (most to least specific)
TYPE_HIERARCHY: List[Tuple[List[str], str]] = [
    (["Boolean", "boolean"], "Boolean"),
    (["BigInt", "integer", "int", "long", "short", "byte"], "BigInt"),
    (["Double", "float", "double", "decimal"], "Double"),
    (["DateTime", "date", "dateTime"], "DateTime"),
    (["String"], "String"),
]


def resolve_union_type(types: List[str]) -> str:
    """
    Resolve a union of types to a single Fabric type.
    
    Uses least common denominator approach - finds the most general
    type that can represent all union members.
    
    Args:
        types: List of Fabric types in the union.
    
    Returns:
        The resolved Fabric type (usually "String" for mixed types).
    """
    if not types:
        return "String"
    
    if len(types) == 1:
        return types[0]
    
    type_set = set(types)
    
    # Check each level of hierarchy
    for type_group, result_type in TYPE_HIERARCHY:
        if type_set.issubset(set(type_group)):
            return result_type
    
    # Default to String for mixed types
    return "String"
