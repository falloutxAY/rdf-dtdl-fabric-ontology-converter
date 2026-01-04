"""
DTDL to Fabric Converter

This module converts parsed DTDL interfaces to Microsoft Fabric Ontology format.

Mapping Strategy:
- DTDLInterface -> EntityType
- DTDLProperty -> EntityTypeProperty
- DTDLTelemetry -> EntityTypeProperty (timeseries)
- DTDLRelationship -> RelationshipType
- DTDLComponent -> Separate EntityType (SEPARATE) or flattened (FLATTEN)
- DTDLCommand -> CommandType entity (ENTITY) or string property (PROPERTY)
- DTDLScaledDecimal -> JSON, structured properties, or calculated value
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path

from .dtdl_models import (
    DTDLInterface,
    DTDLProperty,
    DTDLTelemetry,
    DTDLRelationship,
    DTDLComponent,
    DTDLCommand,
    DTDLCommandPayload,
    DTDLEnum,
    DTDLObject,
    DTDLArray,
    DTDLMap,
    DTDLPrimitiveSchema,
    DTDLScaledDecimal,
)

# Import shared Fabric models
from shared.models import (
    EntityType,
    EntityTypeProperty,
    RelationshipType,
    RelationshipEnd,
    ConversionResult,
    SkippedItem,
)
from core.validators import (
    FabricLimitsValidator,
    EntityIdPartsInferrer,
)
from core.compliance import (
    DTDLComplianceValidator,
    FabricComplianceChecker,
    ConversionReportGenerator,
    ConversionReport,
    DTDLVersion,
)

logger = logging.getLogger(__name__)


# Type mapping from DTDL to Fabric
DTDL_TO_FABRIC_TYPE: Dict[str, str] = {
    # Numeric types
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
    # String types
    "string": "String",
    "uuid": "String",
    "bytes": "String",  # Base64 encoded
    # Date/time types
    "date": "DateTime",
    "dateTime": "DateTime",
    "time": "String",  # Time-only not directly supported
    "duration": "String",
    # Geospatial types (stored as JSON strings)
    "point": "String",
    "lineString": "String",
    "polygon": "String",
    "multiPoint": "String",
    "multiLineString": "String",
    "multiPolygon": "String",
    # DTDL v4 Scaled Decimal (stored as JSON object with scale and value)
    "scaledDecimal": "String",
}


class ComponentMode(str, Enum):
    """Component handling modes for DTDL to Fabric conversion."""
    FLATTEN = "flatten"  # Flatten properties into parent entity (legacy)
    SEPARATE = "separate"  # Create separate entity types with relationships
    SKIP = "skip"  # Skip components entirely


class CommandMode(str, Enum):
    """Command handling modes for DTDL to Fabric conversion."""
    SKIP = "skip"  # Skip commands entirely (legacy)
    PROPERTY = "property"  # Create string property (legacy include_commands=True)
    ENTITY = "entity"  # Create separate CommandType entity with parameters


class ScaledDecimalMode(str, Enum):
    """ScaledDecimal handling modes for DTDL to Fabric conversion."""
    JSON_STRING = "json_string"  # Store as JSON string: {"scale": 7, "value": "123"}
    STRUCTURED = "structured"  # Store with separate _scale and _value properties
    CALCULATED = "calculated"  # Store calculated numeric value as Double


@dataclass
class ScaledDecimalValue:
    """
    Represents a parsed scaledDecimal value.
    
    The scaledDecimal schema type combines a decimal value with an explicit scale,
    useful for representing very large or small values efficiently.
    
    Attributes:
        scale: Count of decimal places to shift (positive=left, negative=right)
        value: The significand as a decimal string
    """
    scale: int
    value: str
    
    def calculate_actual_value(self) -> float:
        """
        Calculate the actual numeric value.
        
        Returns:
            float: The computed value (value * 10^scale)
            
        Example:
            ScaledDecimalValue(scale=7, value="1234.56").calculate_actual_value()
            # Returns 12345600000.0
        """
        try:
            base_value = float(self.value)
            return base_value * (10 ** self.scale)
        except (ValueError, OverflowError):
            return float('nan')
    
    def to_json_object(self) -> Dict[str, Any]:
        """Return JSON-serializable representation."""
        return {
            "scale": self.scale,
            "value": self.value,
            "calculatedValue": self.calculate_actual_value()
        }


class DTDLToFabricConverter:
    """
    Convert parsed DTDL interfaces to Microsoft Fabric Ontology format.
    
    This converter handles:
    - Interface to EntityType mapping
    - Property/Telemetry to EntityTypeProperty mapping
    - Relationship to RelationshipType mapping
    - Component handling (flatten, separate entity, or skip)
    - Command handling (skip, property, or separate entity)
    - ScaledDecimal handling (JSON, structured, or calculated)
    - Inheritance resolution
    - Complex schema type handling
    
    Example usage:
        converter = DTDLToFabricConverter()
        result = converter.convert(interfaces)
        definition = converter.to_fabric_definition(result, "MyOntology")
        
    Advanced usage:
        converter = DTDLToFabricConverter(
            component_mode=ComponentMode.SEPARATE,
            command_mode=CommandMode.ENTITY,
            scaled_decimal_mode=ScaledDecimalMode.STRUCTURED
        )
    """
    
    def __init__(
        self,
        id_prefix: int = 1000000000000,
        namespace: str = "usertypes",
        component_mode: ComponentMode = ComponentMode.SKIP,
        command_mode: CommandMode = CommandMode.SKIP,
        scaled_decimal_mode: ScaledDecimalMode = ScaledDecimalMode.JSON_STRING
    ):
        """
        Initialize the converter.
        
        Args:
            id_prefix: Base prefix for generated IDs
            namespace: Namespace for entity types
            component_mode: How to handle DTDL Components:
                - FLATTEN: Flatten properties into parent entity
                - SEPARATE: Create separate entity types with relationships
                - SKIP: Skip components entirely
            command_mode: How to handle DTDL Commands:
                - SKIP: Skip commands entirely
                - PROPERTY: Create string property per command
                - ENTITY: Create separate CommandType entities
            scaled_decimal_mode: How to handle scaledDecimal properties:
                - JSON_STRING: Store as JSON string {"scale": n, "value": "x"}
                - STRUCTURED: Create _scale (BigInt) and _value (String) properties
                - CALCULATED: Calculate and store as Double
        """
        self.id_prefix = id_prefix
        self.namespace = namespace
        self.scaled_decimal_mode = scaled_decimal_mode
        
        self.component_mode = component_mode
        self.command_mode = command_mode
        
        # Mapping tables
        self._dtmi_to_fabric_id: Dict[str, str] = {}
        self._interface_map: Dict[str, DTDLInterface] = {}
        self._property_id_counter = 0
        
        # Track property names and types across the entire hierarchy
        # Used to detect and resolve conflicts
        self._property_registry: Dict[str, str] = {}  # property_name -> first_seen_type
    
    def _get_ancestor_properties(self, interface: DTDLInterface) -> Dict[str, str]:
        """
        Get all property names and types from ancestor interfaces.
        
        Args:
            interface: The interface to check ancestors for
            
        Returns:
            Dict mapping property name to Fabric value type
        """
        ancestor_props: Dict[str, str] = {}
        
        for parent_dtmi in interface.extends:
            if parent_dtmi in self._interface_map:
                parent = self._interface_map[parent_dtmi]
                # Add parent's direct properties
                for prop in parent.properties:
                    prop_type = self._schema_to_fabric_type(prop.schema)
                    ancestor_props[prop.name] = prop_type
                # Recursively add grandparent properties
                ancestor_props.update(self._get_ancestor_properties(parent))
        
        return ancestor_props
    
    def _resolve_property_name(
        self,
        prop_name: str,
        prop_type: str,
        interface: DTDLInterface
    ) -> str:
        """
        Resolve a property name, adding type suffix if there's a conflict.
        
        Args:
            prop_name: Original property name
            prop_type: Fabric value type of the property
            interface: The interface containing the property
            
        Returns:
            Resolved property name (possibly with type suffix)
        """
        # Check if this property name exists in ancestors with a different type
        ancestor_props = self._get_ancestor_properties(interface)
        
        if prop_name in ancestor_props:
            ancestor_type = ancestor_props[prop_name]
            if ancestor_type != prop_type:
                # Conflict detected - add type suffix
                type_suffix = prop_type.lower()
                resolved_name = f"{prop_name}_{type_suffix}"
                logger.warning(
                    f"Property '{prop_name}' in {interface.name} conflicts with ancestor "
                    f"(ancestor type: {ancestor_type}, this type: {prop_type}). "
                    f"Renaming to '{resolved_name}'"
                )
                return resolved_name
        
        # Check global registry for sibling conflicts
        registry_key = prop_name
        if registry_key in self._property_registry:
            registered_type = self._property_registry[registry_key]
            if registered_type != prop_type:
                # Sibling conflict - add type suffix
                type_suffix = prop_type.lower()
                resolved_name = f"{prop_name}_{type_suffix}"
                logger.debug(
                    f"Property '{prop_name}' in {interface.name} has sibling with different type. "
                    f"Using name '{resolved_name}'"
                )
                return resolved_name
        else:
            # Register this property name and type
            self._property_registry[registry_key] = prop_type
        
        return prop_name
    
    def convert(self, interfaces: List[DTDLInterface]) -> ConversionResult:
        """
        Convert DTDL interfaces to Fabric ontology format.
        
        Args:
            interfaces: List of parsed DTDL interfaces
            
        Returns:
            ConversionResult with entity types, relationships, and any skipped items
        """
        result = ConversionResult()
        
        # Reset property registry for this conversion
        self._property_registry = {}
        
        # Build interface map for lookups
        self._interface_map = {iface.dtmi: iface for iface in interfaces}
        
        # Pre-generate Fabric IDs for all interfaces
        for interface in interfaces:
            self._get_or_create_fabric_id(interface.dtmi)
        
        # Sort interfaces so parents come before children
        sorted_interfaces = self._topological_sort(interfaces)
        
        # Convert each interface
        for interface in sorted_interfaces:
            try:
                entity_type = self._convert_interface(interface)
                result.entity_types.append(entity_type)
            except Exception as e:
                logger.warning(f"Failed to convert interface {interface.dtmi}: {e}")
                result.skipped_items.append(SkippedItem(
                    item_type="interface",
                    name=interface.name,
                    reason=str(e),
                    uri=interface.dtmi,
                ))
        
        # Convert relationships (second pass to ensure all entity IDs exist)
        for interface in interfaces:
            for rel in interface.relationships:
                try:
                    rel_type = self._convert_relationship(rel, interface)
                    if rel_type:
                        result.relationship_types.append(rel_type)
                except Exception as e:
                    logger.warning(f"Failed to convert relationship {rel.name}: {e}")
                    result.skipped_items.append(SkippedItem(
                        item_type="relationship",
                        name=rel.name,
                        reason=str(e),
                        uri=rel.dtmi or f"{interface.dtmi}:{rel.name}",
                    ))
        
        # Handle Components in SEPARATE mode (create entity types and relationships)
        if self.component_mode == ComponentMode.SEPARATE:
            for interface in interfaces:
                source_id = self._get_or_create_fabric_id(interface.dtmi)
                for component in interface.components:
                    try:
                        comp_entity, comp_rel = self._convert_component_to_entity(
                            component, interface, source_id
                        )
                        if comp_entity:
                            result.entity_types.append(comp_entity)
                        if comp_rel:
                            result.relationship_types.append(comp_rel)
                    except Exception as e:
                        logger.warning(f"Failed to convert component {component.name}: {e}")
                        result.skipped_items.append(SkippedItem(
                            item_type="component",
                            name=component.name,
                            reason=str(e),
                            uri=component.dtmi or f"{interface.dtmi}:{component.name}",
                        ))
        
        # Handle Commands in ENTITY mode (create entity types per command)
        if self.command_mode == CommandMode.ENTITY:
            for interface in interfaces:
                source_id = self._get_or_create_fabric_id(interface.dtmi)
                for command in interface.commands:
                    try:
                        cmd_entity, cmd_rel = self._convert_command_to_entity(
                            command, interface, source_id
                        )
                        if cmd_entity:
                            result.entity_types.append(cmd_entity)
                        if cmd_rel:
                            result.relationship_types.append(cmd_rel)
                    except Exception as e:
                        logger.warning(f"Failed to convert command {command.name}: {e}")
                        result.skipped_items.append(SkippedItem(
                            item_type="command",
                            name=command.name,
                            reason=str(e),
                            uri=command.dtmi or f"{interface.dtmi}:{command.name}",
                        ))
        
        return result
    
    def convert_with_compliance_report(
        self,
        interfaces: List[DTDLInterface],
        dtdl_version: Optional[str] = None
    ) -> Tuple[ConversionResult, Optional["ConversionReport"]]:
        """
        Convert DTDL interfaces to Fabric format with a compliance report.
        
        This method performs the standard conversion and additionally generates
        a detailed compliance report showing:
        - DTDL compliance issues
        - Fabric API limit compliance
        - Features that are preserved, limited, or lost in conversion
        
        Args:
            interfaces: List of parsed DTDL interfaces
            dtdl_version: Optional DTDL version string ("v2", "v3", "v4")
                         If None, auto-detected from interface contexts
        
        Returns:
            Tuple of (ConversionResult, ConversionReport or None)
            The report may be None if compliance module is not available
        """
        # Perform standard conversion
        result = self.convert(interfaces)
        
        # Generate compliance report if module is available
        report = None
        if ConversionReportGenerator is not None:
            # Auto-detect DTDL version if not specified
            detected_version = dtdl_version
            if not detected_version and interfaces:
                # Check first interface's context for version hint
                first_iface = interfaces[0]
                if hasattr(first_iface, 'context') and first_iface.context:
                    ctx = first_iface.context[0] if isinstance(first_iface.context, list) else first_iface.context
                    if "dtdl/dtdl/v4" in ctx.lower():
                        detected_version = "v4"
                    elif "dtdl/dtdl/v3" in ctx.lower():
                        detected_version = "v3"
                    else:
                        detected_version = "v2"
            
            # Convert to DTDLVersion enum
            version_enum = None
            if DTDLVersion is not None:
                if detected_version == "v4":
                    version_enum = DTDLVersion.V4
                elif detected_version == "v3":
                    version_enum = DTDLVersion.V3
                else:
                    version_enum = DTDLVersion.V2
            
            try:
                report = ConversionReportGenerator.generate_dtdl_report(
                    interfaces=interfaces,
                    conversion_result=result,
                    dtdl_version=version_enum
                )
                
                # Log conversion warnings
                for warning in report.warnings:
                    logger.warning(
                        f"Conversion warning [{warning.impact.value}]: "
                        f"{warning.feature} - {warning.message}"
                    )
                
                # Log summary
                logger.info(
                    f"Compliance report: {report.total_issues} issues, "
                    f"{len(report.warnings)} conversion warnings"
                )
            except Exception as e:
                logger.warning(f"Failed to generate compliance report: {e}")
        
        return result, report
    
    def _get_or_create_fabric_id(self, dtmi: str) -> str:
        """
        Get or create a Fabric-compatible ID for a DTMI.
        
        Uses a hash-based approach to create deterministic IDs.
        
        Args:
            dtmi: Digital Twin Model Identifier
            
        Returns:
            Fabric-compatible numeric string ID
        """
        if dtmi in self._dtmi_to_fabric_id:
            return self._dtmi_to_fabric_id[dtmi]
        
        # Remove dtmi: prefix and version for consistent hashing
        clean_dtmi = dtmi.replace("dtmi:", "").split(";")[0]
        
        # Create deterministic hash
        hash_bytes = hashlib.sha256(clean_dtmi.encode()).digest()
        hash_int = int.from_bytes(hash_bytes[:8], 'big')
        
        # Apply prefix and limit to reasonable range
        fabric_id = str(self.id_prefix + (hash_int % 1000000000000))
        
        self._dtmi_to_fabric_id[dtmi] = fabric_id
        return fabric_id
    
    def _create_property_id(self, base_id: str, property_name: str) -> str:
        """
        Create a unique property ID within an entity type.
        
        Args:
            base_id: The entity type's Fabric ID
            property_name: Name of the property
            
        Returns:
            Unique property ID string
        """
        # Hash property name to create deterministic sub-ID
        prop_hash = hashlib.md5(property_name.encode()).hexdigest()[:8]
        return f"{base_id}{int(prop_hash, 16) % 10000:04d}"
    
    def _convert_interface(self, interface: DTDLInterface) -> EntityType:
        """
        Convert a DTDL Interface to a Fabric EntityType.
        
        Args:
            interface: The DTDL interface to convert
            
        Returns:
            Fabric EntityType
        """
        fabric_id = self._get_or_create_fabric_id(interface.dtmi)
        
        # Determine parent ID - only if parent is in our interface set
        base_entity_type_id = None
        if interface.extends:
            # Use first parent for single inheritance
            parent_dtmi = interface.extends[0]
            # Only set parent if it's defined in our interface set
            if parent_dtmi in self._interface_map:
                base_entity_type_id = self._get_or_create_fabric_id(parent_dtmi)
            else:
                logger.warning(
                    f"Interface {interface.dtmi} extends external type {parent_dtmi}; "
                    f"parent reference will be removed (type becomes root entity)"
                )
            if len(interface.extends) > 1:
                logger.warning(
                    f"Interface {interface.dtmi} has multiple parents; "
                    f"using only first: {parent_dtmi}"
                )
        
        # Convert properties
        properties: List[EntityTypeProperty] = []
        timeseries_properties: List[EntityTypeProperty] = []
        
        display_name_property_id: Optional[str] = None
        
        # Process Properties
        for prop in interface.properties:
            entity_prop = self._convert_property(prop, fabric_id, interface)
            properties.append(entity_prop)
            
            # Use first string property as display name
            if display_name_property_id is None and entity_prop.valueType == "String":
                display_name_property_id = entity_prop.id
        
        # Process Telemetry as timeseries properties
        for telemetry in interface.telemetries:
            entity_prop = self._convert_telemetry(telemetry, fabric_id, interface)
            timeseries_properties.append(entity_prop)
        
        # Optionally process Commands
        if self.command_mode == CommandMode.PROPERTY:
            for command in interface.commands:
                # Create a string property to represent the command
                cmd_prop = EntityTypeProperty(
                    id=self._create_property_id(fabric_id, f"cmd_{command.name}"),
                    name=f"command_{command.name}",
                    valueType="String",
                )
                properties.append(cmd_prop)
        
        # Optionally flatten Components (legacy mode)
        if self.component_mode == ComponentMode.FLATTEN:
            for component in interface.components:
                component_props = self._flatten_component(component, fabric_id)
                properties.extend(component_props)
        
        # Handle scaledDecimal properties in STRUCTURED mode
        if self.scaled_decimal_mode == ScaledDecimalMode.STRUCTURED:
            for prop in interface.properties:
                if isinstance(prop.schema, DTDLScaledDecimal) or prop.schema == "scaledDecimal":
                    # Add _scale and _value suffix properties
                    scale_prop = EntityTypeProperty(
                        id=self._create_property_id(fabric_id, f"{prop.name}_scale"),
                        name=self._sanitize_name(f"{prop.name}_scale"),
                        valueType="BigInt",
                    )
                    value_prop = EntityTypeProperty(
                        id=self._create_property_id(fabric_id, f"{prop.name}_value"),
                        name=self._sanitize_name(f"{prop.name}_value"),
                        valueType="String",
                    )
                    properties.extend([scale_prop, value_prop])
        
        # Build preliminary entity for entityIdParts inference
        entity = EntityType(
            id=fabric_id,
            name=self._sanitize_name(interface.resolved_display_name),
            namespace=self.namespace,
            namespaceType="Custom",
            visibility="Visible",
            baseEntityTypeId=base_entity_type_id,
            entityIdParts=[],  # Will be set by inferrer
            displayNamePropertyId=display_name_property_id,
            properties=properties,
            timeseriesProperties=timeseries_properties,
        )
        
        # Use EntityIdPartsInferrer if available, otherwise fallback to legacy logic
        if EntityIdPartsInferrer is not None:
            inferrer = EntityIdPartsInferrer(strategy="auto")
            entity.entityIdParts = inferrer.infer_entity_id_parts(entity)
            if not entity.displayNamePropertyId:
                inferrer.set_display_name_property(entity)
        else:
            # Legacy fallback: use first BigInt property if available
            for prop in properties:
                if prop.valueType == "BigInt":
                    entity.entityIdParts = [prop.id]
                    break
            # Try first String property if no BigInt found
            if not entity.entityIdParts:
                for prop in properties:
                    if prop.valueType == "String":
                        entity.entityIdParts = [prop.id]
                        break
        
        return entity
    
    def _convert_property(
        self,
        prop: DTDLProperty,
        entity_id: str,
        interface: DTDLInterface
    ) -> EntityTypeProperty:
        """
        Convert a DTDL Property to a Fabric EntityTypeProperty.
        
        Args:
            prop: The DTDL property
            entity_id: Parent entity's Fabric ID
            interface: The interface containing this property (for conflict resolution)
            
        Returns:
            Fabric EntityTypeProperty
        """
        value_type = self._schema_to_fabric_type(prop.schema)
        
        # Resolve property name to handle conflicts with ancestors/siblings
        resolved_name = self._resolve_property_name(prop.name, value_type, interface)
        
        return EntityTypeProperty(
            id=self._create_property_id(entity_id, resolved_name),
            name=self._sanitize_name(resolved_name),
            valueType=value_type,
        )
    
    def _convert_telemetry(
        self,
        telemetry: DTDLTelemetry,
        entity_id: str,
        interface: DTDLInterface
    ) -> EntityTypeProperty:
        """
        Convert a DTDL Telemetry to a Fabric timeseries property.
        
        Args:
            telemetry: The DTDL telemetry element
            entity_id: Parent entity's Fabric ID
            interface: The interface containing this telemetry (for conflict resolution)
            
        Returns:
            Fabric EntityTypeProperty (for timeseriesProperties)
        """
        value_type = self._schema_to_fabric_type(telemetry.schema)
        
        # Resolve property name to handle conflicts with ancestors/siblings
        resolved_name = self._resolve_property_name(telemetry.name, value_type, interface)
        
        return EntityTypeProperty(
            id=self._create_property_id(entity_id, f"ts_{resolved_name}"),
            name=self._sanitize_name(resolved_name),
            valueType=value_type,
        )
    
    def _convert_relationship(
        self,
        rel: DTDLRelationship,
        source_interface: DTDLInterface
    ) -> Optional[RelationshipType]:
        """
        Convert a DTDL Relationship to a Fabric RelationshipType.
        
        Args:
            rel: The DTDL relationship
            source_interface: The interface containing the relationship
            
        Returns:
            Fabric RelationshipType, or None if target is not resolvable
        """
        source_id = self._get_or_create_fabric_id(source_interface.dtmi)
        
        # Determine target ID
        if rel.target:
            target_id = self._get_or_create_fabric_id(rel.target)
        else:
            # No specific target - skip or use generic
            logger.warning(
                f"Relationship {rel.name} has no target; skipping"
            )
            return None
        
        # Generate relationship ID
        rel_id = self._create_property_id(source_id, f"rel_{rel.name}")
        
        return RelationshipType(
            id=rel_id,
            name=self._sanitize_name(rel.name),
            source=RelationshipEnd(entityTypeId=source_id),
            target=RelationshipEnd(entityTypeId=target_id),
            namespace=self.namespace,
            namespaceType="Custom",
        )
    
    def _convert_component_to_entity(
        self,
        component: DTDLComponent,
        source_interface: DTDLInterface,
        source_entity_id: str
    ) -> Tuple[Optional[EntityType], Optional[RelationshipType]]:
        """
        Convert a DTDL Component to a separate EntityType with a relationship.
        
        In SEPARATE mode, components become their own entity types rather than
        being flattened into the parent. A "hasComponent" relationship links them.
        
        Args:
            component: The DTDL component to convert
            source_interface: The parent interface
            source_entity_id: Parent entity's Fabric ID
            
        Returns:
            Tuple of (EntityType, RelationshipType) or (None, None) if skipped
        """
        # Look up the component's interface schema
        component_interface = self._interface_map.get(component.schema)
        
        if component_interface:
            # Component references an interface we already converted
            # Just create the relationship
            target_id = self._get_or_create_fabric_id(component.schema)
            
            rel_id = self._create_property_id(source_entity_id, f"comp_{component.name}")
            rel_type = RelationshipType(
                id=rel_id,
                name=self._sanitize_name(f"has_{component.name}"),
                source=RelationshipEnd(entityTypeId=source_entity_id),
                target=RelationshipEnd(entityTypeId=target_id),
                namespace=self.namespace,
                namespaceType="Custom",
            )
            
            logger.info(
                f"Component '{component.name}' converted to relationship to existing "
                f"interface '{component_interface.name}'"
            )
            return None, rel_type
        else:
            # Component references an external interface - create stub entity
            stub_entity_id = self._get_or_create_fabric_id(component.schema)
            
            # Extract name from schema DTMI
            schema_name = component.schema.replace("dtmi:", "").split(";")[0].split(":")[-1]
            
            stub_entity = EntityType(
                id=stub_entity_id,
                name=self._sanitize_name(f"{component.name}_{schema_name}"),
                namespace=self.namespace,
                namespaceType="Custom",
                visibility="Visible",
                baseEntityTypeId=None,
                entityIdParts=[],
                displayNamePropertyId=None,
                properties=[
                    # Add stub identifier property
                    EntityTypeProperty(
                        id=self._create_property_id(stub_entity_id, "componentId"),
                        name="componentId",
                        valueType="String",
                    )
                ],
                timeseriesProperties=[],
            )
            
            # Set entityIdParts to the stub property
            stub_entity.entityIdParts = [stub_entity.properties[0].id]
            
            # Create relationship
            rel_id = self._create_property_id(source_entity_id, f"comp_{component.name}")
            rel_type = RelationshipType(
                id=rel_id,
                name=self._sanitize_name(f"has_{component.name}"),
                source=RelationshipEnd(entityTypeId=source_entity_id),
                target=RelationshipEnd(entityTypeId=stub_entity_id),
                namespace=self.namespace,
                namespaceType="Custom",
            )
            
            logger.warning(
                f"Component '{component.name}' references external interface "
                f"'{component.schema}'; created stub entity"
            )
            return stub_entity, rel_type
    
    def _convert_command_to_entity(
        self,
        command: DTDLCommand,
        source_interface: DTDLInterface,
        source_entity_id: str
    ) -> Tuple[EntityType, RelationshipType]:
        """
        Convert a DTDL Command to a separate CommandType EntityType.
        
        In ENTITY mode, commands become their own entity types with properties
        for request/response schemas. A "supportsCommand" relationship links them.
        
        Args:
            command: The DTDL command to convert
            source_interface: The parent interface
            source_entity_id: Parent entity's Fabric ID
            
        Returns:
            Tuple of (EntityType for command, RelationshipType linking to parent)
        """
        # Generate command entity ID
        cmd_dtmi = command.dtmi or f"{source_interface.dtmi}:cmd:{command.name}"
        cmd_entity_id = self._get_or_create_fabric_id(cmd_dtmi)
        
        # Build properties from command definition
        properties: List[EntityTypeProperty] = []
        
        # Command name property (identifier)
        name_prop = EntityTypeProperty(
            id=self._create_property_id(cmd_entity_id, "commandName"),
            name="commandName",
            valueType="String",
        )
        properties.append(name_prop)
        
        # Request schema as JSON property if present
        if command.request:
            request_schema = self._command_payload_to_json(command.request)
            req_prop = EntityTypeProperty(
                id=self._create_property_id(cmd_entity_id, "requestSchema"),
                name="requestSchema",
                valueType="String",  # JSON-encoded schema
            )
            properties.append(req_prop)
            
            # Also add individual request parameter properties
            if command.request.schema:
                req_params = self._extract_command_parameters(
                    command.request, cmd_entity_id, "request"
                )
                properties.extend(req_params)
        
        # Response schema as JSON property if present
        if command.response:
            response_schema = self._command_payload_to_json(command.response)
            resp_prop = EntityTypeProperty(
                id=self._create_property_id(cmd_entity_id, "responseSchema"),
                name="responseSchema",
                valueType="String",  # JSON-encoded schema
            )
            properties.append(resp_prop)
            
            # Also add individual response parameter properties
            if command.response.schema:
                resp_params = self._extract_command_parameters(
                    command.response, cmd_entity_id, "response"
                )
                properties.extend(resp_params)
        
        # Create command entity
        cmd_entity = EntityType(
            id=cmd_entity_id,
            name=self._sanitize_name(f"Command_{command.name}"),
            namespace=self.namespace,
            namespaceType="Custom",
            visibility="Visible",
            baseEntityTypeId=None,
            entityIdParts=[name_prop.id],
            displayNamePropertyId=name_prop.id,
            properties=properties,
            timeseriesProperties=[],
        )
        
        # Create relationship from interface to command
        rel_id = self._create_property_id(source_entity_id, f"cmd_rel_{command.name}")
        cmd_rel = RelationshipType(
            id=rel_id,
            name=self._sanitize_name(f"supports_{command.name}"),
            source=RelationshipEnd(entityTypeId=source_entity_id),
            target=RelationshipEnd(entityTypeId=cmd_entity_id),
            namespace=self.namespace,
            namespaceType="Custom",
        )
        
        logger.info(f"Command '{command.name}' converted to entity type with relationship")
        return cmd_entity, cmd_rel
    
    def _command_payload_to_json(self, payload: DTDLCommandPayload) -> Dict[str, Any]:
        """
        Convert a command payload to JSON schema representation.
        
        Args:
            payload: The command request or response payload
            
        Returns:
            JSON-serializable dictionary
        """
        result: Dict[str, Any] = {
            "name": payload.name,
        }
        
        if isinstance(payload.schema, str):
            result["schema"] = payload.schema
        elif isinstance(payload.schema, DTDLObject):
            result["schema"] = {
                "type": "object",
                "fields": [
                    {"name": f.name, "schema": f.schema if isinstance(f.schema, str) else "complex"}
                    for f in payload.schema.fields
                ]
            }
        else:
            result["schema"] = "complex"
        
        if payload.nullable:
            result["nullable"] = True
            
        return result
    
    def _extract_command_parameters(
        self,
        payload: DTDLCommandPayload,
        entity_id: str,
        prefix: str
    ) -> List[EntityTypeProperty]:
        """
        Extract properties from a command payload schema.
        
        For Object schemas, creates individual properties for each field.
        For primitive schemas, creates a single property.
        
        Args:
            payload: The command request or response payload
            entity_id: Parent command entity ID
            prefix: Property name prefix ("request" or "response")
            
        Returns:
            List of EntityTypeProperty for the parameters
        """
        properties: List[EntityTypeProperty] = []
        
        if isinstance(payload.schema, DTDLObject):
            # Extract each field as a property
            for field in payload.schema.fields:
                field_type = self._schema_to_fabric_type(field.schema)
                prop = EntityTypeProperty(
                    id=self._create_property_id(entity_id, f"{prefix}_{field.name}"),
                    name=self._sanitize_name(f"{prefix}_{field.name}"),
                    valueType=field_type,
                )
                properties.append(prop)
        elif isinstance(payload.schema, str):
            # Single parameter
            param_type = self._schema_to_fabric_type(payload.schema)
            prop = EntityTypeProperty(
                id=self._create_property_id(entity_id, f"{prefix}_{payload.name}"),
                name=self._sanitize_name(f"{prefix}_{payload.name}"),
                valueType=param_type,
            )
            properties.append(prop)
        
        return properties
    
    def _flatten_component(
        self,
        component: DTDLComponent,
        parent_entity_id: str
    ) -> List[EntityTypeProperty]:
        """
        Flatten a Component's properties into the parent entity.
        
        Args:
            component: The DTDL component
            parent_entity_id: Parent entity's Fabric ID
            
        Returns:
            List of properties with prefixed names
        """
        properties: List[EntityTypeProperty] = []
        
        # Look up the component's interface
        component_interface = self._interface_map.get(component.schema)
        if not component_interface:
            logger.warning(f"Component schema not found: {component.schema}")
            return properties
        
        # Prefix all properties with component name
        prefix = f"{component.name}_"
        
        for prop in component_interface.properties:
            prefixed_name = prefix + prop.name
            entity_prop = EntityTypeProperty(
                id=self._create_property_id(parent_entity_id, prefixed_name),
                name=self._sanitize_name(prefixed_name),
                valueType=self._schema_to_fabric_type(prop.schema),
            )
            properties.append(entity_prop)
        
        return properties
    
    def _schema_to_fabric_type(self, schema) -> str:
        """
        Convert a DTDL schema to Fabric value type.
        
        Args:
            schema: DTDL schema (string or complex type)
            
        Returns:
            Fabric value type string
        """
        if isinstance(schema, str):
            # Handle scaledDecimal in CALCULATED mode
            if schema == "scaledDecimal" and self.scaled_decimal_mode == ScaledDecimalMode.CALCULATED:
                return "Double"
            # Primitive type or DTMI reference
            return DTDL_TO_FABRIC_TYPE.get(schema, "String")
        
        # Complex types
        if isinstance(schema, DTDLEnum):
            # Store enum as the value schema type
            return DTDL_TO_FABRIC_TYPE.get(schema.value_schema, "String")
        
        if isinstance(schema, (DTDLObject, DTDLArray, DTDLMap)):
            # Complex types stored as JSON strings
            return "String"
        
        if isinstance(schema, DTDLScaledDecimal):
            # Handle based on mode
            if self.scaled_decimal_mode == ScaledDecimalMode.CALCULATED:
                return "Double"
            # JSON_STRING or STRUCTURED mode - base property is String
            return "String"
        
        return "String"
    
    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize a name to meet Fabric requirements.
        
        Fabric names must be alphanumeric with underscores,
        start with a letter, and be <= 90 characters.
        
        Args:
            name: Original name
            
        Returns:
            Sanitized name
        """
        if not name:
            return "Entity"
        
        # Replace invalid characters with underscore
        sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
        
        # Ensure starts with letter
        if not sanitized[0].isalpha():
            sanitized = 'E_' + sanitized
        
        # Truncate to max length
        return sanitized[:90]
    
    def _topological_sort(
        self,
        interfaces: List[DTDLInterface]
    ) -> List[DTDLInterface]:
        """
        Sort interfaces so parents come before children.
        
        Uses Kahn's algorithm for topological sorting.
        
        Args:
            interfaces: List of interfaces to sort
            
        Returns:
            Sorted list with parents first
        """
        dtmi_to_interface = {iface.dtmi: iface for iface in interfaces}
        
        # Calculate in-degree (number of parents in the input set)
        in_degree: Dict[str, int] = {iface.dtmi: 0 for iface in interfaces}
        children: Dict[str, List[str]] = {iface.dtmi: [] for iface in interfaces}
        
        for interface in interfaces:
            for parent_dtmi in interface.extends:
                if parent_dtmi in dtmi_to_interface:
                    in_degree[interface.dtmi] += 1
                    children[parent_dtmi].append(interface.dtmi)
        
        # Start with root interfaces (no parents in input set)
        queue = [dtmi for dtmi, degree in in_degree.items() if degree == 0]
        sorted_list: List[DTDLInterface] = []
        
        while queue:
            current_dtmi = queue.pop(0)
            sorted_list.append(dtmi_to_interface[current_dtmi])
            
            for child_dtmi in children.get(current_dtmi, []):
                in_degree[child_dtmi] -= 1
                if in_degree[child_dtmi] == 0:
                    queue.append(child_dtmi)
        
        # Add any remaining (cycle or external parent)
        for interface in interfaces:
            if interface not in sorted_list:
                sorted_list.append(interface)
        
        return sorted_list
    
    def to_fabric_definition(
        self,
        result: ConversionResult,
        ontology_name: str = "DTDLOntology",
        skip_fabric_limits: bool = False,
    ) -> Dict[str, Any]:
        """
        Create the Fabric API definition format from conversion result.
        
        Args:
            result: Conversion result with entity and relationship types
            ontology_name: Display name for the ontology
            skip_fabric_limits: If True, skip Fabric API limits validation
            
        Returns:
            Dictionary with "parts" array for Fabric API
            
        Raises:
            ValueError: If Fabric limits are exceeded (unless skip_fabric_limits=True)
        """
        import base64
        
        # Validate Fabric API limits (unless explicitly skipped)
        if not skip_fabric_limits and FabricLimitsValidator is not None:
            fabric_validator = FabricLimitsValidator()
            limit_errors = fabric_validator.validate_all(
                result.entity_types, 
                result.relationship_types
            )
            
            # Log limit validation issues
            for error in limit_errors:
                if error.level == "warning":
                    logger.warning(f"Fabric limit warning: {error.message}")
                else:
                    logger.error(f"Fabric limit error: {error.message}")
            
            # Fail on critical limit errors
            if fabric_validator.has_errors(limit_errors):
                critical_errors = fabric_validator.get_errors_only(limit_errors)
                error_msg = "Fabric API limit exceeded:\n" + "\n".join(
                    f"  - {e.message}" for e in critical_errors
                )
                raise ValueError(error_msg)
            
            warnings = fabric_validator.get_warnings_only(limit_errors)
            if warnings:
                logger.info(f"Fabric limits check passed with {len(warnings)} warning(s)")
        
        parts = []
        
        # .platform file
        platform_content = {
            "metadata": {
                "type": "Ontology",
                "displayName": ontology_name
            }
        }
        parts.append({
            "path": ".platform",
            "payload": base64.b64encode(
                json.dumps(platform_content, indent=2).encode()
            ).decode(),
            "payloadType": "InlineBase64"
        })
        
        # definition.json
        parts.append({
            "path": "definition.json",
            "payload": base64.b64encode(b"{}").decode(),
            "payloadType": "InlineBase64"
        })
        
        # Entity types
        for entity_type in result.entity_types:
            entity_content = entity_type.to_dict()
            parts.append({
                "path": f"EntityTypes/{entity_type.id}/definition.json",
                "payload": base64.b64encode(
                    json.dumps(entity_content, indent=2).encode()
                ).decode(),
                "payloadType": "InlineBase64"
            })
        
        # Relationship types
        for rel_type in result.relationship_types:
            rel_content = rel_type.to_dict()
            parts.append({
                "path": f"RelationshipTypes/{rel_type.id}/definition.json",
                "payload": base64.b64encode(
                    json.dumps(rel_content, indent=2).encode()
                ).decode(),
                "payloadType": "InlineBase64"
            })
        
        return {"parts": parts}
    
    def get_dtmi_mapping(self) -> Dict[str, str]:
        """
        Get the DTMI to Fabric ID mapping.
        
        Useful for debugging and reference tracking.
        
        Returns:
            Dictionary mapping DTMI strings to Fabric IDs
        """
        return dict(self._dtmi_to_fabric_id)
