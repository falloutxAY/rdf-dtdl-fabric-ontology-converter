"""
JSON-LD Plugin for Fabric Ontology Converter.

This plugin adds support for JSON-LD format, commonly used for
linked data on the web. It serves as a reference implementation
for third-party plugin developers.

JSON-LD (JavaScript Object Notation for Linked Data) is a method
of encoding Linked Data using JSON. It allows data to be serialized
in a way that is both human-readable and machine-processable.

Example JSON-LD:
{
    "@context": {
        "schema": "https://schema.org/",
        "name": "schema:name",
        "Person": "schema:Person"
    },
    "@type": "Person",
    "name": "John Doe"
}

Supported features:
- Inline @context definitions
- @graph for multiple nodes
- @type for type declarations
- Typed values with @value and @type
- Basic schema.org vocabulary support

Limitations:
- Remote context fetching not supported (inline only)
- No JSON-LD framing support
- No JSON-LD compaction/expansion algorithms
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from ..base import OntologyPlugin
from ...common.validation import ValidationResult, Severity, IssueCategory
from ...common.id_generator import get_id_generator
from ...models import (
    ConversionResult,
    EntityType,
    EntityTypeProperty,
    RelationshipType,
    RelationshipEnd,
    SkippedItem,
)

logger = logging.getLogger(__name__)


# JSON-LD / Schema.org to Fabric type mappings
JSONLD_TO_FABRIC_TYPE: Dict[str, str] = {
    # XSD types
    "http://www.w3.org/2001/XMLSchema#string": "String",
    "http://www.w3.org/2001/XMLSchema#boolean": "Boolean",
    "http://www.w3.org/2001/XMLSchema#integer": "BigInt",
    "http://www.w3.org/2001/XMLSchema#int": "BigInt",
    "http://www.w3.org/2001/XMLSchema#long": "BigInt",
    "http://www.w3.org/2001/XMLSchema#decimal": "Double",
    "http://www.w3.org/2001/XMLSchema#float": "Double",
    "http://www.w3.org/2001/XMLSchema#double": "Double",
    "http://www.w3.org/2001/XMLSchema#dateTime": "DateTime",
    "http://www.w3.org/2001/XMLSchema#date": "DateTime",
    "http://www.w3.org/2001/XMLSchema#time": "String",
    
    # Schema.org types
    "http://schema.org/Text": "String",
    "https://schema.org/Text": "String",
    "http://schema.org/Number": "Double",
    "https://schema.org/Number": "Double",
    "http://schema.org/Integer": "BigInt",
    "https://schema.org/Integer": "BigInt",
    "http://schema.org/Boolean": "Boolean",
    "https://schema.org/Boolean": "Boolean",
    "http://schema.org/Date": "DateTime",
    "https://schema.org/Date": "DateTime",
    "http://schema.org/DateTime": "DateTime",
    "https://schema.org/DateTime": "DateTime",
    "http://schema.org/Time": "String",
    "https://schema.org/Time": "String",
    "http://schema.org/URL": "String",
    "https://schema.org/URL": "String",
}


@dataclass
class JSONLDContext:
    """Parsed JSON-LD context."""
    prefixes: Dict[str, str] = field(default_factory=dict)
    terms: Dict[str, Any] = field(default_factory=dict)
    base: Optional[str] = None
    vocab: Optional[str] = None
    
    def expand_term(self, term: str) -> str:
        """Expand a term using the context."""
        if term.startswith("http://") or term.startswith("https://"):
            return term
        
        # Check if it's a prefixed term
        if ":" in term:
            prefix, local = term.split(":", 1)
            if prefix in self.prefixes:
                return self.prefixes[prefix] + local
        
        # Check term definitions
        if term in self.terms:
            term_def = self.terms[term]
            if isinstance(term_def, str):
                return self.expand_term(term_def)
            elif isinstance(term_def, dict) and "@id" in term_def:
                return self.expand_term(term_def["@id"])
        
        # Use vocab if available
        if self.vocab:
            return self.vocab + term
        
        return term


class JSONLDParser:
    """Parser for JSON-LD documents."""
    
    def parse(self, content: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse JSON-LD content.
        
        Args:
            content: JSON-LD string content.
            file_path: Optional path for error messages.
            
        Returns:
            Normalized JSON-LD document as dict.
            
        Raises:
            ValueError: If content is not valid JSON-LD.
        """
        try:
            data = json.loads(content)
            return self._normalize(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON-LD: {e}")
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse JSON-LD file.
        
        Args:
            file_path: Path to the JSON-LD file.
            
        Returns:
            Normalized JSON-LD document as dict.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return self.parse(f.read(), file_path)
    
    def _normalize(self, data: Any) -> Dict[str, Any]:
        """Normalize JSON-LD to standard form with @graph."""
        if isinstance(data, list):
            return {"@graph": data}
        if isinstance(data, dict):
            # If no @graph but has @type, wrap in graph
            if "@graph" not in data and "@type" in data:
                graph_data = {k: v for k, v in data.items() if k != "@context"}
                result = {"@graph": [graph_data]}
                if "@context" in data:
                    result["@context"] = data["@context"]
                return result
            return data
        raise ValueError("JSON-LD root must be an object or array")
    
    def extract_context(self, data: Dict[str, Any]) -> JSONLDContext:
        """
        Extract and parse @context.
        
        Args:
            data: Parsed JSON-LD document.
            
        Returns:
            JSONLDContext with extracted prefixes and terms.
        """
        ctx = data.get("@context", {})
        
        if isinstance(ctx, str):
            # Remote context - not supported
            logger.warning(f"Remote context not supported: {ctx}")
            return JSONLDContext()
        
        if isinstance(ctx, list):
            # Combine multiple contexts
            combined = JSONLDContext()
            for item in ctx:
                if isinstance(item, dict):
                    self._parse_context_dict(item, combined)
            return combined
        
        if isinstance(ctx, dict):
            result = JSONLDContext()
            self._parse_context_dict(ctx, result)
            return result
        
        return JSONLDContext()
    
    def _parse_context_dict(self, ctx: Dict[str, Any], result: JSONLDContext) -> None:
        """Parse a context dictionary into JSONLDContext."""
        for key, value in ctx.items():
            if key == "@base":
                result.base = value
            elif key == "@vocab":
                result.vocab = value
            elif isinstance(value, str):
                # Could be a prefix or term
                if value.endswith("/") or value.endswith("#"):
                    result.prefixes[key] = value
                else:
                    result.terms[key] = value
            elif isinstance(value, dict):
                result.terms[key] = value


class JSONLDValidator:
    """Validator for JSON-LD documents."""
    
    def validate(self, content: str, file_path: Optional[str] = None) -> ValidationResult:
        """
        Validate JSON-LD content.
        
        Args:
            content: JSON-LD string content.
            file_path: Optional path for reporting.
            
        Returns:
            ValidationResult with any issues found.
        """
        result = ValidationResult(
            format_name="jsonld",
            source_path=file_path
        )
        
        # Try to parse as JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            result.add_error(
                IssueCategory.SYNTAX_ERROR,
                f"Invalid JSON: {e.msg}",
                location=f"line {e.lineno}, column {e.colno}"
            )
            return result
        
        # Validate structure
        self._validate_structure(data, result)
        
        # Validate context
        self._validate_context(data, result)
        
        # Validate nodes
        self._validate_nodes(data, result)
        
        # Gather statistics
        result.statistics = self._gather_statistics(data)
        
        return result
    
    def validate_file(self, file_path: str) -> ValidationResult:
        """
        Validate JSON-LD file.
        
        Args:
            file_path: Path to the JSON-LD file.
            
        Returns:
            ValidationResult with any issues found.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return self.validate(f.read(), file_path)
        except FileNotFoundError:
            result = ValidationResult(format_name="jsonld", source_path=file_path)
            result.add_error(
                IssueCategory.SYNTAX_ERROR,
                f"File not found: {file_path}"
            )
            return result
        except IOError as e:
            result = ValidationResult(format_name="jsonld", source_path=file_path)
            result.add_error(
                IssueCategory.SYNTAX_ERROR,
                f"Error reading file: {e}"
            )
            return result
    
    def _validate_structure(self, data: Any, result: ValidationResult) -> None:
        """Validate JSON-LD structure."""
        if not isinstance(data, (dict, list)):
            result.add_error(
                IssueCategory.SYNTAX_ERROR,
                "JSON-LD root must be an object or array"
            )
            return
        
        if isinstance(data, dict):
            # Check for @context
            if "@context" not in data:
                result.add_warning(
                    IssueCategory.MISSING_REQUIRED,
                    "No @context found - document may not be valid JSON-LD",
                    recommendation="Add @context to define vocabulary terms"
                )
            
            # Check for @type or @graph
            if "@type" not in data and "@graph" not in data:
                result.add_warning(
                    IssueCategory.MISSING_REQUIRED,
                    "No @type or @graph found - no entities to convert",
                    recommendation="Add @type to define the node type"
                )
    
    def _validate_context(self, data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate @context."""
        if not isinstance(data, dict):
            return
            
        ctx = data.get("@context")
        if ctx is None:
            return
        
        if isinstance(ctx, str):
            result.add_info(
                IssueCategory.FABRIC_COMPATIBILITY,
                f"Remote context: {ctx}",
                recommendation="Remote contexts are not fetched - define terms inline"
            )
        elif isinstance(ctx, list):
            remote_count = sum(1 for c in ctx if isinstance(c, str))
            if remote_count > 0:
                result.add_info(
                    IssueCategory.FABRIC_COMPATIBILITY,
                    f"Combined context with {remote_count} remote references",
                    recommendation="Remote contexts are not fetched"
                )
    
    def _validate_nodes(self, data: Any, result: ValidationResult) -> None:
        """Validate nodes in the document."""
        if not isinstance(data, dict):
            return
        
        nodes = data.get("@graph", [])
        if "@type" in data and "@graph" not in data:
            nodes = [data]
        
        typed_count = 0
        for node in nodes:
            if isinstance(node, dict) and "@type" in node:
                typed_count += 1
        
        if typed_count == 0 and nodes:
            result.add_warning(
                IssueCategory.FABRIC_COMPATIBILITY,
                "No typed nodes found - entities require @type",
                recommendation="Add @type to nodes to create entity types"
            )
    
    def _gather_statistics(self, data: Any) -> Dict[str, Any]:
        """Gather document statistics."""
        stats = {
            "has_context": False,
            "node_count": 0,
            "type_count": 0,
            "property_count": 0,
            "types": [],
        }
        
        if isinstance(data, dict):
            stats["has_context"] = "@context" in data
            self._count_nodes(data, stats)
        
        return stats
    
    def _count_nodes(self, data: Any, stats: Dict[str, Any]) -> None:
        """Recursively count nodes and types."""
        if isinstance(data, dict):
            if "@type" in data:
                stats["type_count"] += 1
                node_type = data["@type"]
                if isinstance(node_type, list):
                    stats["types"].extend(node_type)
                else:
                    stats["types"].append(node_type)
            
            # Count properties (non-keyword keys)
            for key in data:
                if not key.startswith("@"):
                    stats["property_count"] += 1
            
            stats["node_count"] += 1
            
            for value in data.values():
                self._count_nodes(value, stats)
        elif isinstance(data, list):
            for item in data:
                self._count_nodes(item, stats)


class JSONLDConverter:
    """Converter from JSON-LD to Fabric format."""
    
    def __init__(self):
        self.parser = JSONLDParser()
    
    def convert(
        self,
        content: str,
        id_prefix: int = 1000000000000,
        **kwargs
    ) -> ConversionResult:
        """
        Convert JSON-LD to Fabric ontology format.
        
        Args:
            content: JSON-LD string content.
            id_prefix: Starting ID for generated entities.
            **kwargs: Additional options (expand_context, base_uri).
            
        Returns:
            ConversionResult with entities and relationships.
        """
        entity_types: List[EntityType] = []
        relationship_types: List[RelationshipType] = []
        skipped: List[SkippedItem] = []
        warnings: List[str] = []
        
        # Get ID generator
        id_gen = get_id_generator()
        
        try:
            data = self.parser.parse(content)
            context = self.parser.extract_context(data)
            
            # Extract nodes from @graph or root
            nodes = data.get("@graph", [])
            if "@type" in data and "@graph" not in data:
                # Single node document
                nodes = [{k: v for k, v in data.items() if k != "@context"}]
            
            # Group nodes by @type to create entity types
            type_instances: Dict[str, List[Dict[str, Any]]] = {}
            relationships_to_create: List[Dict[str, Any]] = []
            
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                    
                if "@type" not in node:
                    node_id = str(node.get("@id", "unknown"))
                    skipped.append(SkippedItem(
                        item_type="node",
                        name=node_id,
                        reason="No @type specified",
                        uri=node_id
                    ))
                    continue
                
                node_type = node["@type"]
                if isinstance(node_type, list):
                    node_type = node_type[0]  # Take first type
                
                if node_type not in type_instances:
                    type_instances[node_type] = []
                type_instances[node_type].append(node)
                
                # Collect relationships
                for key, value in node.items():
                    if key.startswith("@"):
                        continue
                    if isinstance(value, dict) and "@id" in value:
                        relationships_to_create.append({
                            "from_type": node_type,
                            "property": key,
                            "to_id": value["@id"]
                        })
                    elif isinstance(value, str) and value.startswith("http"):
                        # Could be a reference
                        relationships_to_create.append({
                            "from_type": node_type,
                            "property": key,
                            "to_id": value
                        })
            
            # Create entity types
            for type_name, instances in type_instances.items():
                try:
                    entity = self._create_entity_type(
                        type_name, instances, context, id_gen
                    )
                    entity_types.append(entity)
                except Exception as e:
                    logger.warning(f"Failed to create entity for {type_name}: {e}")
                    skipped.append(SkippedItem(
                        item_type="type",
                        name=type_name,
                        reason=str(e),
                        uri=type_name
                    ))
            
            # Create relationships
            for rel_info in relationships_to_create:
                # Find target type
                target_type = self._find_type_for_id(
                    rel_info["to_id"], type_instances
                )
                if target_type and target_type in type_instances:
                    from_entity = self._find_entity_by_type(
                        rel_info["from_type"], entity_types
                    )
                    to_entity = self._find_entity_by_type(
                        target_type, entity_types
                    )
                    
                    if from_entity and to_entity:
                        rel_name = self._extract_name(rel_info["property"])
                        # Check if relationship already exists
                        existing = any(
                            r.name == rel_name for r in relationship_types
                        )
                        if not existing:
                            relationship_types.append(RelationshipType(
                                id=id_gen.next_id(),
                                name=rel_name,
                                fromEntityType=RelationshipEnd(
                                    entityTypeId=from_entity.id,
                                    entityTypeName=from_entity.name
                                ),
                                toEntityType=RelationshipEnd(
                                    entityTypeId=to_entity.id,
                                    entityTypeName=to_entity.name
                                )
                            ))
        
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            warnings.append(f"Conversion error: {e}")
        
        return ConversionResult(
            entity_types=entity_types,
            relationship_types=relationship_types,
            skipped_items=skipped,
            warnings=warnings,
        )
    
    def _create_entity_type(
        self,
        type_name: str,
        instances: List[Dict[str, Any]],
        context: JSONLDContext,
        id_gen: Any
    ) -> EntityType:
        """Create an EntityType from JSON-LD type."""
        # Extract local name from URI
        name = self._extract_name(type_name)
        
        # Collect all properties from instances
        all_props: Dict[str, str] = {}
        for instance in instances:
            for key, value in instance.items():
                if not key.startswith("@"):
                    prop_type = self._infer_fabric_type(value, context)
                    if key not in all_props:
                        all_props[key] = prop_type
        
        # Create properties
        properties = []
        for prop_name, prop_type in all_props.items():
            properties.append(EntityTypeProperty(
                id=id_gen.next_id(),
                name=self._extract_name(prop_name),
                valueType=prop_type
            ))
        
        return EntityType(
            id=id_gen.next_id(),
            name=name,
            properties=properties
        )
    
    def _extract_name(self, uri_or_name: str) -> str:
        """Extract local name from URI or use as-is."""
        if uri_or_name.startswith("http://") or uri_or_name.startswith("https://"):
            # Extract fragment or last path segment
            if "#" in uri_or_name:
                return uri_or_name.split("#")[-1]
            return uri_or_name.rstrip("/").split("/")[-1]
        
        # Handle prefixed names
        if ":" in uri_or_name:
            return uri_or_name.split(":")[-1]
        
        return uri_or_name
    
    def _infer_fabric_type(self, value: Any, context: JSONLDContext) -> str:
        """Infer Fabric type from JSON value."""
        if isinstance(value, bool):
            return "Boolean"
        elif isinstance(value, int):
            return "BigInt"
        elif isinstance(value, float):
            return "Double"
        elif isinstance(value, dict):
            # Check for typed value
            if "@type" in value:
                type_uri = context.expand_term(value["@type"])
                return JSONLD_TO_FABRIC_TYPE.get(type_uri, "String")
            if "@value" in value:
                return self._infer_fabric_type(value["@value"], context)
            # Nested object - serialize as string
            return "String"
        elif isinstance(value, list):
            # Array - use String for JSON array
            return "String"
        return "String"
    
    def _find_type_for_id(
        self,
        node_id: str,
        type_instances: Dict[str, List[Dict[str, Any]]]
    ) -> Optional[str]:
        """Find the type of a node by its @id."""
        for type_name, instances in type_instances.items():
            for instance in instances:
                if instance.get("@id") == node_id:
                    return type_name
        return None
    
    def _find_entity_by_type(
        self,
        type_name: str,
        entity_types: List[EntityType]
    ) -> Optional[EntityType]:
        """Find an EntityType by its original type name."""
        extracted_name = self._extract_name(type_name)
        for entity in entity_types:
            if entity.name == extracted_name:
                return entity
        return None


class JSONLDPlugin(OntologyPlugin):
    """
    JSON-LD format plugin for Fabric Ontology Converter.
    
    Supports conversion of JSON-LD documents containing schema.org
    or custom vocabularies to Fabric ontology format.
    
    This plugin serves as a reference implementation for third-party
    plugin developers.
    """
    
    @property
    def format_name(self) -> str:
        return "jsonld"
    
    @property
    def display_name(self) -> str:
        return "JSON-LD (JavaScript Object Notation for Linked Data)"
    
    @property
    def file_extensions(self) -> Set[str]:
        return {".jsonld", ".json-ld"}
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def author(self) -> str:
        return "Fabric Ontology Converter Team"
    
    @property
    def dependencies(self) -> List[str]:
        return []  # Uses standard library only
    
    def get_parser(self) -> JSONLDParser:
        """Return JSON-LD parser."""
        return JSONLDParser()
    
    def get_validator(self) -> JSONLDValidator:
        """Return JSON-LD validator."""
        return JSONLDValidator()
    
    def get_converter(self) -> JSONLDConverter:
        """Return JSON-LD converter."""
        return JSONLDConverter()
    
    def get_type_mappings(self) -> Dict[str, str]:
        """Return JSON-LD to Fabric type mappings."""
        return JSONLD_TO_FABRIC_TYPE
    
    def register_cli_arguments(self, parser: Any) -> None:
        """Add JSON-LD specific CLI arguments."""
        parser.add_argument(
            "--expand-context",
            action="store_true",
            help="Expand remote @context references (not yet supported)"
        )
        parser.add_argument(
            "--base-uri",
            help="Base URI for relative references"
        )


# Export
__all__ = [
    "JSONLDPlugin",
    "JSONLDParser",
    "JSONLDValidator", 
    "JSONLDConverter",
    "JSONLDContext",
    "JSONLD_TO_FABRIC_TYPE",
]
