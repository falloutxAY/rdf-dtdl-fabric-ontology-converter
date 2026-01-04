"""
Fabric API Schema Validation

Validates ontology definitions against the Microsoft Fabric Ontology API schema.
This ensures definitions match what the Fabric API actually accepts before upload.

Schema based on:
- https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/create-ontology
- https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/update-ontology-definition

Usage:
    from core.validators.fabric_schema import (
        FabricSchemaValidator,
        validate_fabric_definition,
        validate_entity_type,
        validate_relationship_type,
    )
    
    # Validate entire definition
    errors = validate_fabric_definition(definition)
    if errors:
        raise ValueError(f"Invalid definition: {errors}")
    
    # Or use the validator class
    validator = FabricSchemaValidator()
    result = validator.validate(definition)
    if not result.is_valid:
        print(result.errors)
"""

import base64
import json
import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Fabric API Constants (from API documentation)
# =============================================================================

# Valid Fabric property value types
FABRIC_VALUE_TYPES = frozenset({
    "String",
    "BigInt",
    "Double",
    "Decimal",
    "Boolean",
    "DateTime",
    "Binary",
    "Guid",
})

# Valid visibility values
FABRIC_VISIBILITY_VALUES = frozenset({
    "Visible",
    "Hidden",
})

# Valid namespace types
FABRIC_NAMESPACE_TYPES = frozenset({
    "Custom",
    "System",
})

# Reserved namespaces that cannot be used for custom types
FABRIC_RESERVED_NAMESPACES = frozenset({
    "system",
    "fabric",
    "microsoft",
})

# Name constraints
FABRIC_NAME_MAX_LENGTH = 256
FABRIC_NAME_PATTERN = re.compile(r'^[A-Za-z][A-Za-z0-9_]*$')

# ID constraints (IDs should be numeric strings)
FABRIC_ID_PATTERN = re.compile(r'^\d+$')

# Definition constraints
FABRIC_MAX_ENTITY_TYPES = 500
FABRIC_MAX_RELATIONSHIP_TYPES = 500
FABRIC_MAX_PROPERTIES_PER_ENTITY = 200


# =============================================================================
# Validation Result
# =============================================================================

@dataclass
class SchemaValidationResult:
    """Result of schema validation."""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, message: str) -> None:
        """Add a validation error."""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str) -> None:
        """Add a validation warning."""
        self.warnings.append(message)
    
    def merge(self, other: 'SchemaValidationResult') -> None:
        """Merge another result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False


class FabricSchemaValidationError(Exception):
    """Raised when definition fails Fabric API schema validation."""
    
    def __init__(self, message: str, errors: List[str]):
        self.errors = errors
        super().__init__(f"{message}: {'; '.join(errors)}")


# =============================================================================
# Schema Validator
# =============================================================================

class FabricSchemaValidator:
    """
    Validates ontology definitions against the Fabric API schema.
    
    This validator checks that:
    1. The definition has the correct structure (parts array)
    2. Each part has required fields (path, payload, payloadType)
    3. Entity types have valid structure and field values
    4. Relationship types have valid structure and field values
    5. IDs and names follow Fabric naming conventions
    6. Cross-references between entities and relationships are valid
    
    Example:
        validator = FabricSchemaValidator()
        result = validator.validate(definition)
        if not result.is_valid:
            for error in result.errors:
                print(f"Error: {error}")
    """
    
    def __init__(self, strict: bool = False):
        """
        Initialize the validator.
        
        Args:
            strict: If True, treat warnings as errors.
        """
        self.strict = strict
    
    def validate(self, definition: Dict[str, Any]) -> SchemaValidationResult:
        """
        Validate an ontology definition against the Fabric API schema.
        
        Args:
            definition: The ontology definition to validate.
            
        Returns:
            SchemaValidationResult with validation status and any errors/warnings.
        """
        result = SchemaValidationResult()
        
        if not isinstance(definition, dict):
            result.add_error(f"Definition must be a dict, got {type(definition).__name__}")
            return result
        
        # Check for required 'parts' array
        if "parts" not in definition:
            result.add_error("Definition missing required 'parts' array")
            return result
        
        parts = definition["parts"]
        if not isinstance(parts, list):
            result.add_error(f"'parts' must be a list, got {type(parts).__name__}")
            return result
        
        if not parts:
            result.add_warning("Definition has empty 'parts' array")
        
        # Track entity IDs for cross-reference validation
        entity_ids: Set[str] = set()
        entity_names: Set[str] = set()
        relationship_ids: Set[str] = set()
        
        entity_count = 0
        relationship_count = 0
        
        # Validate each part
        for i, part in enumerate(parts):
            part_result = self._validate_part(part, i)
            result.merge(part_result)
            
            # Extract and track IDs from valid parts
            if part_result.is_valid and "payload" in part and "path" in part:
                path = part["path"]
                try:
                    payload_data = self._decode_payload(part)
                    if payload_data:
                        if "EntityTypes" in path:
                            entity_count += 1
                            if "id" in payload_data:
                                entity_ids.add(str(payload_data["id"]))
                            if "name" in payload_data:
                                entity_names.add(payload_data["name"])
                        elif "RelationshipTypes" in path:
                            relationship_count += 1
                            if "id" in payload_data:
                                relationship_ids.add(str(payload_data["id"]))
                except Exception as e:
                    result.add_error(f"Part {i}: Failed to decode payload: {e}")
        
        # Check limits
        if entity_count > FABRIC_MAX_ENTITY_TYPES:
            result.add_error(
                f"Too many entity types: {entity_count} exceeds limit of {FABRIC_MAX_ENTITY_TYPES}"
            )
        
        if relationship_count > FABRIC_MAX_RELATIONSHIP_TYPES:
            result.add_error(
                f"Too many relationship types: {relationship_count} exceeds limit of {FABRIC_MAX_RELATIONSHIP_TYPES}"
            )
        
        # Validate cross-references in relationships
        for i, part in enumerate(parts):
            if "RelationshipTypes" in part.get("path", ""):
                try:
                    payload_data = self._decode_payload(part)
                    if payload_data:
                        self._validate_relationship_references(
                            payload_data, entity_ids, i, result
                        )
                except Exception:
                    pass  # Already reported above
        
        # Convert warnings to errors in strict mode
        if self.strict and result.warnings:
            result.errors.extend(result.warnings)
            result.warnings = []
            result.is_valid = False
        
        return result
    
    def _validate_part(self, part: Any, index: int) -> SchemaValidationResult:
        """Validate a single definition part."""
        result = SchemaValidationResult()
        prefix = f"Part {index}"
        
        if not isinstance(part, dict):
            result.add_error(f"{prefix}: Must be a dict, got {type(part).__name__}")
            return result
        
        # Required fields
        required_fields = ["path", "payload", "payloadType"]
        for field in required_fields:
            if field not in part:
                result.add_error(f"{prefix}: Missing required field '{field}'")
        
        if not result.is_valid:
            return result
        
        path = part["path"]
        payload = part["payload"]
        payload_type = part["payloadType"]
        
        # Validate path
        if not isinstance(path, str):
            result.add_error(f"{prefix}: 'path' must be a string")
        
        # Validate payloadType
        if payload_type != "InlineBase64":
            result.add_warning(
                f"{prefix}: Unexpected payloadType '{payload_type}', expected 'InlineBase64'"
            )
        
        # Validate payload is base64
        if not isinstance(payload, str):
            result.add_error(f"{prefix}: 'payload' must be a string")
            return result
        
        try:
            decoded = base64.b64decode(payload)
            decoded_str = decoded.decode('utf-8')
        except Exception as e:
            result.add_error(f"{prefix}: Invalid base64 payload: {e}")
            return result
        
        # Validate payload content based on path
        if "EntityTypes" in path:
            result.merge(self._validate_entity_type_payload(decoded_str, prefix))
        elif "RelationshipTypes" in path:
            result.merge(self._validate_relationship_type_payload(decoded_str, prefix))
        elif path == ".platform":
            result.merge(self._validate_platform_payload(decoded_str, prefix))
        elif path == "definition.json":
            result.merge(self._validate_definition_json_payload(decoded_str, prefix))
        
        return result
    
    def _decode_payload(self, part: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Decode and parse a part's payload."""
        try:
            decoded = base64.b64decode(part["payload"]).decode('utf-8')
            return json.loads(decoded)
        except Exception:
            return None
    
    def _validate_entity_type_payload(
        self, payload_str: str, prefix: str
    ) -> SchemaValidationResult:
        """Validate an EntityType payload."""
        result = SchemaValidationResult()
        
        try:
            data = json.loads(payload_str)
        except json.JSONDecodeError as e:
            result.add_error(f"{prefix}: Invalid JSON in payload: {e}")
            return result
        
        if not isinstance(data, dict):
            result.add_error(f"{prefix}: EntityType payload must be a dict")
            return result
        
        # Required fields for EntityType
        required = ["id", "name", "namespace", "namespaceType", "visibility"]
        for field in required:
            if field not in data:
                result.add_error(f"{prefix}: EntityType missing required field '{field}'")
        
        # Validate ID format
        if "id" in data:
            entity_id = str(data["id"])
            if not FABRIC_ID_PATTERN.match(entity_id):
                result.add_warning(f"{prefix}: EntityType ID '{entity_id}' is not numeric")
        
        # Validate name
        if "name" in data:
            name = data["name"]
            if len(name) > FABRIC_NAME_MAX_LENGTH:
                result.add_error(
                    f"{prefix}: EntityType name '{name[:50]}...' exceeds {FABRIC_NAME_MAX_LENGTH} chars"
                )
            if not FABRIC_NAME_PATTERN.match(name):
                result.add_warning(
                    f"{prefix}: EntityType name '{name}' may not be valid "
                    "(should start with letter, contain only letters/numbers/underscores)"
                )
        
        # Validate namespace
        if "namespace" in data:
            namespace = data["namespace"].lower()
            if namespace in FABRIC_RESERVED_NAMESPACES:
                result.add_error(f"{prefix}: Cannot use reserved namespace '{namespace}'")
        
        # Validate namespaceType
        if "namespaceType" in data:
            ns_type = data["namespaceType"]
            if ns_type not in FABRIC_NAMESPACE_TYPES:
                result.add_error(
                    f"{prefix}: Invalid namespaceType '{ns_type}', must be one of {FABRIC_NAMESPACE_TYPES}"
                )
        
        # Validate visibility
        if "visibility" in data:
            visibility = data["visibility"]
            if visibility not in FABRIC_VISIBILITY_VALUES:
                result.add_error(
                    f"{prefix}: Invalid visibility '{visibility}', must be one of {FABRIC_VISIBILITY_VALUES}"
                )
        
        # Validate properties
        if "properties" in data:
            properties = data["properties"]
            if not isinstance(properties, list):
                result.add_error(f"{prefix}: 'properties' must be a list")
            elif len(properties) > FABRIC_MAX_PROPERTIES_PER_ENTITY:
                result.add_error(
                    f"{prefix}: Too many properties ({len(properties)}) exceeds limit of "
                    f"{FABRIC_MAX_PROPERTIES_PER_ENTITY}"
                )
            else:
                for j, prop in enumerate(properties):
                    result.merge(self._validate_property(prop, f"{prefix}.properties[{j}]"))
        
        # Validate baseEntityTypeId if present
        if "baseEntityTypeId" in data:
            base_id = str(data["baseEntityTypeId"])
            if not FABRIC_ID_PATTERN.match(base_id):
                result.add_warning(f"{prefix}: baseEntityTypeId '{base_id}' is not numeric")
        
        return result
    
    def _validate_property(self, prop: Any, prefix: str) -> SchemaValidationResult:
        """Validate an EntityTypeProperty."""
        result = SchemaValidationResult()
        
        if not isinstance(prop, dict):
            result.add_error(f"{prefix}: Property must be a dict")
            return result
        
        # Required fields
        if "id" not in prop:
            result.add_error(f"{prefix}: Property missing 'id'")
        if "name" not in prop:
            result.add_error(f"{prefix}: Property missing 'name'")
        if "valueType" not in prop:
            result.add_error(f"{prefix}: Property missing 'valueType'")
        
        # Validate valueType
        if "valueType" in prop:
            value_type = prop["valueType"]
            if value_type not in FABRIC_VALUE_TYPES:
                result.add_error(
                    f"{prefix}: Invalid valueType '{value_type}', must be one of {FABRIC_VALUE_TYPES}"
                )
        
        # Validate name
        if "name" in prop:
            name = prop["name"]
            if len(name) > FABRIC_NAME_MAX_LENGTH:
                result.add_error(f"{prefix}: Property name too long")
        
        return result
    
    def _validate_relationship_type_payload(
        self, payload_str: str, prefix: str
    ) -> SchemaValidationResult:
        """Validate a RelationshipType payload."""
        result = SchemaValidationResult()
        
        try:
            data = json.loads(payload_str)
        except json.JSONDecodeError as e:
            result.add_error(f"{prefix}: Invalid JSON in payload: {e}")
            return result
        
        if not isinstance(data, dict):
            result.add_error(f"{prefix}: RelationshipType payload must be a dict")
            return result
        
        # Required fields
        required = ["id", "name", "namespace", "namespaceType", "source", "target"]
        for field in required:
            if field not in data:
                result.add_error(f"{prefix}: RelationshipType missing required field '{field}'")
        
        # Validate source and target
        for endpoint in ["source", "target"]:
            if endpoint in data:
                ep_data = data[endpoint]
                if not isinstance(ep_data, dict):
                    result.add_error(f"{prefix}: '{endpoint}' must be a dict")
                elif "entityTypeId" not in ep_data:
                    result.add_error(f"{prefix}: '{endpoint}' missing 'entityTypeId'")
        
        # Validate name
        if "name" in data:
            name = data["name"]
            if len(name) > FABRIC_NAME_MAX_LENGTH:
                result.add_error(f"{prefix}: RelationshipType name too long")
        
        return result
    
    def _validate_relationship_references(
        self,
        rel_data: Dict[str, Any],
        entity_ids: Set[str],
        index: int,
        result: SchemaValidationResult
    ) -> None:
        """Validate that relationship endpoints reference valid entities."""
        prefix = f"Part {index}"
        
        for endpoint in ["source", "target"]:
            if endpoint in rel_data and isinstance(rel_data[endpoint], dict):
                ep_id = str(rel_data[endpoint].get("entityTypeId", ""))
                if ep_id and ep_id not in entity_ids:
                    result.add_warning(
                        f"{prefix}: RelationshipType '{rel_data.get('name', '?')}' "
                        f"{endpoint} references unknown entityTypeId '{ep_id}'"
                    )
    
    def _validate_platform_payload(
        self, payload_str: str, prefix: str
    ) -> SchemaValidationResult:
        """Validate the .platform metadata payload."""
        result = SchemaValidationResult()
        
        try:
            data = json.loads(payload_str)
        except json.JSONDecodeError as e:
            result.add_error(f"{prefix}: Invalid JSON in .platform payload: {e}")
            return result
        
        # .platform should have specific structure
        if "$schema" not in data:
            result.add_warning(f"{prefix}: .platform missing '$schema' field")
        
        if "config" not in data:
            result.add_warning(f"{prefix}: .platform missing 'config' field")
        
        return result
    
    def _validate_definition_json_payload(
        self, payload_str: str, prefix: str
    ) -> SchemaValidationResult:
        """Validate the definition.json payload."""
        result = SchemaValidationResult()
        
        try:
            data = json.loads(payload_str)
        except json.JSONDecodeError as e:
            result.add_error(f"{prefix}: Invalid JSON in definition.json: {e}")
            return result
        
        # definition.json should have metadata
        if "version" not in data:
            result.add_warning(f"{prefix}: definition.json missing 'version' field")
        
        return result


# =============================================================================
# Convenience Functions
# =============================================================================

def validate_fabric_definition(
    definition: Dict[str, Any],
    strict: bool = False,
    raise_on_error: bool = False
) -> List[str]:
    """
    Validate an ontology definition against the Fabric API schema.
    
    Args:
        definition: The ontology definition to validate.
        strict: If True, treat warnings as errors.
        raise_on_error: If True, raise FabricSchemaValidationError on failure.
        
    Returns:
        List of validation errors (empty if valid).
        
    Raises:
        FabricSchemaValidationError: If raise_on_error=True and validation fails.
    """
    validator = FabricSchemaValidator(strict=strict)
    result = validator.validate(definition)
    
    if raise_on_error and not result.is_valid:
        raise FabricSchemaValidationError("Definition validation failed", result.errors)
    
    return result.errors


def validate_entity_type(entity_data: Dict[str, Any]) -> List[str]:
    """
    Validate a single EntityType dict.
    
    Args:
        entity_data: The EntityType data to validate.
        
    Returns:
        List of validation errors.
    """
    validator = FabricSchemaValidator()
    payload_str = json.dumps(entity_data)
    result = validator._validate_entity_type_payload(payload_str, "EntityType")
    return result.errors


def validate_relationship_type(rel_data: Dict[str, Any]) -> List[str]:
    """
    Validate a single RelationshipType dict.
    
    Args:
        rel_data: The RelationshipType data to validate.
        
    Returns:
        List of validation errors.
    """
    validator = FabricSchemaValidator()
    payload_str = json.dumps(rel_data)
    result = validator._validate_relationship_type_payload(payload_str, "RelationshipType")
    return result.errors
