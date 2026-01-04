"""
JSON-LD Plugin for Fabric Ontology Converter.

This plugin adds support for JSON-LD (JSON for Linked Data) format,
commonly used for structured data on the web.

JSON-LD Features Supported:
- @context for namespace definitions
- @type for class definitions  
- @id for unique identifiers
- @graph for multiple nodes
- Nested objects and arrays
- Type coercion

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

Usage:
    from plugins.builtin.jsonld_plugin import JSONLDPlugin
    
    plugin = JSONLDPlugin()
    converter = plugin.get_converter()
    result = converter.convert(jsonld_content)
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Import plugin base (adjust path as needed)
import sys
_plugin_dir = Path(__file__).parent.parent
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))

from base import OntologyPlugin
from protocols import ParserProtocol, ValidatorProtocol, ConverterProtocol

# Import common utilities (adjust path as needed)
_common_dir = Path(__file__).parent.parent.parent / "common"
if str(_common_dir.parent) not in sys.path:
    sys.path.insert(0, str(_common_dir.parent))

try:
    from common.validation import ValidationResult, Severity, IssueCategory
    from common.id_generator import get_id_generator
except ImportError:
    # Fallback for standalone testing
    from dataclasses import dataclass as validation_dataclass
    ValidationResult = Any  # type: ignore
    Severity = Any  # type: ignore
    IssueCategory = Any  # type: ignore
    get_id_generator = None  # type: ignore

# Try to import Fabric models
try:
    from models import (
        ConversionResult,
        EntityType,
        EntityTypeProperty,
        RelationshipType,
        RelationshipEnd,
        SkippedItem,
    )
except ImportError:
    # Placeholder types for reference implementation
    ConversionResult = Any  # type: ignore
    EntityType = Any  # type: ignore
    EntityTypeProperty = Any  # type: ignore
    RelationshipType = Any  # type: ignore
    RelationshipEnd = Any  # type: ignore
    SkippedItem = Any  # type: ignore

logger = logging.getLogger(__name__)


# =============================================================================
# Type Mappings
# =============================================================================

# JSON-LD / XSD / Schema.org to Fabric type mappings
JSONLD_TO_FABRIC_TYPE: Dict[str, str] = {
    # XSD types (commonly used in JSON-LD)
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
    
    # Schema.org types
    "http://schema.org/Text": "String",
    "http://schema.org/Number": "Double",
    "http://schema.org/Integer": "BigInt",
    "http://schema.org/Boolean": "Boolean",
    "http://schema.org/Date": "DateTime",
    "http://schema.org/DateTime": "DateTime",
    "http://schema.org/URL": "String",
    
    # Short forms
    "xsd:string": "String",
    "xsd:boolean": "Boolean",
    "xsd:integer": "BigInt",
    "xsd:decimal": "Double",
    "xsd:dateTime": "DateTime",
}


# =============================================================================
# Context Handling
# =============================================================================

@dataclass
class JSONLDContext:
    """
    Parsed JSON-LD context.
    
    Attributes:
        prefixes: Namespace prefixes (e.g., {"schema": "https://schema.org/"})
        terms: Term definitions
        base: Base IRI
        vocab: Default vocabulary IRI
    """
    prefixes: Dict[str, str] = field(default_factory=dict)
    terms: Dict[str, Any] = field(default_factory=dict)
    base: Optional[str] = None
    vocab: Optional[str] = None
    
    def expand_term(self, term: str) -> str:
        """Expand a term using context."""
        if term.startswith("http://") or term.startswith("https://"):
            return term
        
        # Check if it's a prefixed name
        if ":" in term:
            prefix, local = term.split(":", 1)
            if prefix in self.prefixes:
                return f"{self.prefixes[prefix]}{local}"
        
        # Check term definitions
        if term in self.terms:
            term_def = self.terms[term]
            if isinstance(term_def, str):
                return self.expand_term(term_def)
            elif isinstance(term_def, dict) and "@id" in term_def:
                return self.expand_term(term_def["@id"])
        
        # Use vocab if available
        if self.vocab:
            return f"{self.vocab}{term}"
        
        return term
    
    def get_type_for_term(self, term: str) -> Optional[str]:
        """Get the @type for a term from context."""
        if term in self.terms:
            term_def = self.terms[term]
            if isinstance(term_def, dict):
                return term_def.get("@type")
        return None


# =============================================================================
# Parser
# =============================================================================

class JSONLDParser:
    """
    Parser for JSON-LD documents.
    
    Handles:
    - JSON parsing and validation
    - Context extraction
    - Document normalization
    """
    
    def parse(self, content: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse JSON-LD content.
        
        Args:
            content: JSON-LD string content.
            file_path: Optional file path for error messages.
        
        Returns:
            Normalized JSON-LD document.
        
        Raises:
            ValueError: If content is not valid JSON.
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON at line {e.lineno}, column {e.colno}: {e.msg}"
            )
        
        return self._normalize(data)
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a JSON-LD file.
        
        Args:
            file_path: Path to the file.
        
        Returns:
            Normalized JSON-LD document.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        content = path.read_text(encoding='utf-8')
        return self.parse(content, file_path)
    
    def _normalize(self, data: Any) -> Dict[str, Any]:
        """
        Normalize JSON-LD to consistent structure.
        
        - Wraps arrays in @graph
        - Ensures root is an object
        """
        if isinstance(data, list):
            return {"@graph": data}
        if not isinstance(data, dict):
            raise ValueError("JSON-LD root must be an object or array")
        return data
    
    def extract_context(self, data: Dict[str, Any]) -> JSONLDContext:
        """
        Extract and parse @context from document.
        
        Args:
            data: JSON-LD document.
        
        Returns:
            Parsed JSONLDContext.
        """
        ctx_value = data.get("@context")
        if ctx_value is None:
            return JSONLDContext()
        
        # Handle different context formats
        contexts = []
        if isinstance(ctx_value, str):
            # Remote context URL - not supported for now
            logger.warning(f"Remote context not fetched: {ctx_value}")
            return JSONLDContext()
        elif isinstance(ctx_value, list):
            contexts = ctx_value
        elif isinstance(ctx_value, dict):
            contexts = [ctx_value]
        
        # Merge contexts
        prefixes: Dict[str, str] = {}
        terms: Dict[str, Any] = {}
        base: Optional[str] = None
        vocab: Optional[str] = None
        
        for ctx in contexts:
            if isinstance(ctx, str):
                # Skip remote contexts
                continue
            if isinstance(ctx, dict):
                for key, value in ctx.items():
                    if key == "@base":
                        base = value
                    elif key == "@vocab":
                        vocab = value
                    elif isinstance(value, str):
                        if value.endswith('/') or value.endswith('#'):
                            prefixes[key] = value
                        else:
                            terms[key] = value
                    else:
                        terms[key] = value
        
        return JSONLDContext(
            prefixes=prefixes,
            terms=terms,
            base=base,
            vocab=vocab,
        )


# =============================================================================
# Validator
# =============================================================================

class JSONLDValidator:
    """
    Validator for JSON-LD documents.
    
    Checks:
    - Valid JSON syntax
    - JSON-LD structure
    - Context validity
    - Fabric compatibility
    """
    
    def __init__(self):
        self.parser = JSONLDParser()
    
    def validate(
        self,
        content: str,
        file_path: Optional[str] = None
    ) -> 'ValidationResult':
        """
        Validate JSON-LD content.
        
        Args:
            content: JSON-LD string content.
            file_path: Optional file path.
        
        Returns:
            ValidationResult with issues found.
        """
        # Import here to handle circular imports
        try:
            from common.validation import ValidationResult, Severity, IssueCategory
        except ImportError:
            # Create minimal result structure
            class MinimalResult:
                def __init__(self):
                    self.format_name = "jsonld"
                    self.source_path = file_path
                    self.is_valid = True
                    self.issues = []
                    self.statistics = {}
                
                def add_error(self, cat, msg, **kwargs):
                    self.issues.append({"severity": "error", "message": msg})
                    self.is_valid = False
                
                def add_warning(self, cat, msg, **kwargs):
                    self.issues.append({"severity": "warning", "message": msg})
                
                def add_info(self, cat, msg, **kwargs):
                    self.issues.append({"severity": "info", "message": msg})
                
                @property
                def error_count(self):
                    return sum(1 for i in self.issues if i.get("severity") == "error")
            
            result = MinimalResult()
            ValidationResult = type(result)
            
            class MockSeverity:
                ERROR = "error"
                WARNING = "warning"
                INFO = "info"
            Severity = MockSeverity
            
            class MockCategory:
                SYNTAX_ERROR = "syntax_error"
                MISSING_REQUIRED = "missing_required"
                UNSUPPORTED_CONSTRUCT = "unsupported_construct"
                CUSTOM = "custom"
            IssueCategory = MockCategory
        else:
            result = ValidationResult(format_name="jsonld", source_path=file_path)
        
        # Check JSON syntax
        try:
            data = self.parser.parse(content, file_path)
        except ValueError as e:
            result.add_error(IssueCategory.SYNTAX_ERROR, str(e))
            return result
        
        # Validate structure
        self._validate_structure(data, result, IssueCategory)
        
        # Validate context
        self._validate_context(data, result, IssueCategory)
        
        # Check for types
        self._validate_types(data, result, IssueCategory)
        
        # Gather statistics
        result.statistics = self._gather_statistics(data)
        
        return result
    
    def validate_file(self, file_path: str) -> 'ValidationResult':
        """Validate a JSON-LD file."""
        path = Path(file_path)
        if not path.exists():
            try:
                from common.validation import ValidationResult, IssueCategory
                result = ValidationResult(format_name="jsonld", source_path=file_path)
                result.add_error(IssueCategory.SYNTAX_ERROR, f"File not found: {file_path}")
                return result
            except ImportError:
                raise FileNotFoundError(f"File not found: {file_path}")
        
        content = path.read_text(encoding='utf-8')
        return self.validate(content, file_path)
    
    def _validate_structure(self, data: Dict, result: Any, IssueCategory: Any) -> None:
        """Validate JSON-LD structure."""
        if not isinstance(data, dict):
            result.add_error(
                IssueCategory.SYNTAX_ERROR,
                "JSON-LD root must be an object"
            )
    
    def _validate_context(self, data: Dict, result: Any, IssueCategory: Any) -> None:
        """Validate @context."""
        if "@context" not in data:
            result.add_warning(
                IssueCategory.MISSING_REQUIRED,
                "No @context found - document may not be valid JSON-LD"
            )
            return
        
        ctx = data["@context"]
        if isinstance(ctx, str):
            result.add_info(
                IssueCategory.CUSTOM,
                f"Remote context referenced: {ctx}",
                recommendation="Remote contexts are not fetched during validation"
            )
    
    def _validate_types(self, data: Dict, result: Any, IssueCategory: Any) -> None:
        """Check for @type definitions."""
        has_types = False
        
        def check_node(node: Any) -> None:
            nonlocal has_types
            if isinstance(node, dict):
                if "@type" in node:
                    has_types = True
                for value in node.values():
                    check_node(value)
            elif isinstance(node, list):
                for item in node:
                    check_node(item)
        
        check_node(data)
        
        if not has_types:
            result.add_warning(
                IssueCategory.MISSING_REQUIRED,
                "No @type found - no entity types will be created"
            )
    
    def _gather_statistics(self, data: Dict) -> Dict[str, Any]:
        """Gather document statistics."""
        stats = {
            "has_context": "@context" in data,
            "has_graph": "@graph" in data,
            "node_count": 0,
            "type_count": 0,
            "unique_types": set(),
        }
        
        def count_nodes(node: Any) -> None:
            if isinstance(node, dict):
                stats["node_count"] += 1
                if "@type" in node:
                    stats["type_count"] += 1
                    t = node["@type"]
                    if isinstance(t, str):
                        stats["unique_types"].add(t)
                    elif isinstance(t, list):
                        stats["unique_types"].update(t)
                for value in node.values():
                    count_nodes(value)
            elif isinstance(node, list):
                for item in node:
                    count_nodes(item)
        
        count_nodes(data)
        stats["unique_types"] = list(stats["unique_types"])
        
        return stats


# =============================================================================
# Converter
# =============================================================================

class JSONLDConverter:
    """
    Converter from JSON-LD to Fabric Ontology format.
    
    Conversion strategy:
    - @type definitions become EntityType
    - Properties become EntityTypeProperty
    - @id references become RelationshipType
    """
    
    def __init__(self):
        self.parser = JSONLDParser()
        self._id_counter = 1000000000000
    
    def _next_id(self) -> str:
        """Generate next entity ID."""
        current = self._id_counter
        self._id_counter += 1
        return str(current)
    
    def convert(
        self,
        content: str,
        id_prefix: int = 1000000000000,
        **kwargs: Any
    ) -> 'ConversionResult':
        """
        Convert JSON-LD to Fabric Ontology format.
        
        Args:
            content: JSON-LD string content.
            id_prefix: Starting ID for entities.
            **kwargs: Additional options.
        
        Returns:
            ConversionResult with entities and relationships.
        """
        self._id_counter = id_prefix
        
        entity_types: List[Any] = []
        relationship_types: List[Any] = []
        skipped_items: List[Any] = []
        warnings: List[str] = []
        
        try:
            # Parse document
            data = self.parser.parse(content)
            context = self.parser.extract_context(data)
            
            # Get nodes to process
            if "@graph" in data:
                nodes = data["@graph"]
            elif "@type" in data:
                nodes = [data]
            else:
                nodes = []
                warnings.append("No @type or @graph found - nothing to convert")
            
            # Group nodes by @type
            type_instances: Dict[str, List[Dict]] = {}
            for node in nodes:
                if isinstance(node, dict) and "@type" in node:
                    node_types = node["@type"]
                    if isinstance(node_types, str):
                        node_types = [node_types]
                    
                    for t in node_types:
                        expanded = context.expand_term(t)
                        if expanded not in type_instances:
                            type_instances[expanded] = []
                        type_instances[expanded].append(node)
            
            # Create entity type for each @type
            type_id_map: Dict[str, str] = {}  # type URI -> entity ID
            
            for type_uri, instances in type_instances.items():
                entity = self._create_entity_type(
                    type_uri, instances, context
                )
                entity_types.append(entity)
                type_id_map[type_uri] = entity.id
            
            # Create relationships from @id references
            for type_uri, instances in type_instances.items():
                for instance in instances:
                    rels = self._extract_relationships(
                        instance, type_id_map, type_uri, context
                    )
                    relationship_types.extend(rels)
        
        except Exception as e:
            warnings.append(f"Conversion error: {e}")
            logger.exception("Conversion failed")
        
        # Create result
        try:
            from models import ConversionResult
            return ConversionResult(
                entity_types=entity_types,
                relationship_types=relationship_types,
                skipped_items=skipped_items,
                warnings=warnings,
            )
        except ImportError:
            # Return dict for standalone testing
            return {
                "entity_types": entity_types,
                "relationship_types": relationship_types,
                "skipped_items": skipped_items,
                "warnings": warnings,
            }
    
    def _create_entity_type(
        self,
        type_uri: str,
        instances: List[Dict],
        context: JSONLDContext,
    ) -> Any:
        """Create EntityType from instances of a @type."""
        name = self._extract_local_name(type_uri)
        
        # Collect all properties from all instances
        all_properties: Dict[str, str] = {}  # name -> Fabric type
        
        for instance in instances:
            for key, value in instance.items():
                if key.startswith("@"):
                    continue  # Skip JSON-LD keywords
                
                prop_name = self._extract_local_name(key)
                fabric_type = self._infer_fabric_type(value, context, key)
                
                if prop_name not in all_properties:
                    all_properties[prop_name] = fabric_type
        
        # Create property objects
        properties = []
        for prop_name, fabric_type in sorted(all_properties.items()):
            try:
                from models import EntityTypeProperty
                properties.append(EntityTypeProperty(
                    id=self._next_id(),
                    name=prop_name,
                    valueType=fabric_type,
                ))
            except ImportError:
                properties.append({
                    "id": self._next_id(),
                    "name": prop_name,
                    "valueType": fabric_type,
                })
        
        # Create entity type
        try:
            from models import EntityType
            return EntityType(
                id=self._next_id(),
                name=name,
                properties=properties,
            )
        except ImportError:
            return {
                "id": self._next_id(),
                "name": name,
                "properties": properties,
            }
    
    def _extract_relationships(
        self,
        instance: Dict,
        type_id_map: Dict[str, str],
        source_type: str,
        context: JSONLDContext,
    ) -> List[Any]:
        """Extract relationships from an instance."""
        relationships = []
        source_id = type_id_map.get(source_type)
        if not source_id:
            return relationships
        
        for key, value in instance.items():
            if key.startswith("@"):
                continue
            
            # Check if value is an @id reference
            targets = []
            if isinstance(value, dict) and "@id" in value:
                targets = [value]
            elif isinstance(value, list):
                targets = [v for v in value if isinstance(v, dict) and "@id" in v]
            
            for target in targets:
                # Find target type
                target_type = target.get("@type")
                if target_type:
                    if isinstance(target_type, list):
                        target_type = target_type[0]
                    expanded = context.expand_term(target_type)
                    target_id = type_id_map.get(expanded)
                    
                    if target_id:
                        rel_name = self._extract_local_name(key)
                        try:
                            from models import RelationshipType, RelationshipEnd
                            relationships.append(RelationshipType(
                                id=self._next_id(),
                                name=rel_name,
                                source=RelationshipEnd(entityTypeId=source_id),
                                target=RelationshipEnd(entityTypeId=target_id),
                            ))
                        except ImportError:
                            relationships.append({
                                "id": self._next_id(),
                                "name": rel_name,
                                "source": {"entityTypeId": source_id},
                                "target": {"entityTypeId": target_id},
                            })
        
        return relationships
    
    def _extract_local_name(self, uri_or_term: str) -> str:
        """Extract local name from URI or term."""
        if uri_or_term.startswith("http"):
            # Extract fragment or last path segment
            if "#" in uri_or_term:
                return uri_or_term.split("#")[-1]
            return uri_or_term.rstrip("/").split("/")[-1]
        
        # Check for prefix
        if ":" in uri_or_term and not uri_or_term.startswith("http"):
            return uri_or_term.split(":")[-1]
        
        return uri_or_term
    
    def _infer_fabric_type(
        self,
        value: Any,
        context: JSONLDContext,
        term: str,
    ) -> str:
        """Infer Fabric type from JSON value."""
        # Check context for explicit type
        ctx_type = context.get_type_for_term(term)
        if ctx_type:
            expanded = context.expand_term(ctx_type)
            if expanded in JSONLD_TO_FABRIC_TYPE:
                return JSONLD_TO_FABRIC_TYPE[expanded]
        
        # Check typed value
        if isinstance(value, dict):
            if "@type" in value:
                val_type = value["@type"]
                expanded = context.expand_term(val_type)
                if expanded in JSONLD_TO_FABRIC_TYPE:
                    return JSONLD_TO_FABRIC_TYPE[expanded]
            if "@value" in value:
                return self._infer_fabric_type(value["@value"], context, term)
            if "@id" in value:
                return "String"  # Reference
        
        # Infer from Python type
        if isinstance(value, bool):
            return "Boolean"
        elif isinstance(value, int):
            return "BigInt"
        elif isinstance(value, float):
            return "Double"
        elif isinstance(value, list):
            return "String"  # Arrays stored as JSON strings
        
        return "String"


# =============================================================================
# Plugin Class
# =============================================================================

class JSONLDPlugin(OntologyPlugin):
    """
    JSON-LD format plugin for Fabric Ontology Converter.
    
    Supports JSON-LD 1.0/1.1 documents with:
    - Local @context definitions
    - @type for class definitions
    - @id for unique identifiers
    - @graph for multiple nodes
    - Schema.org and custom vocabularies
    
    Note: Remote @context URLs are not fetched.
    """
    
    @property
    def format_name(self) -> str:
        return "jsonld"
    
    @property
    def display_name(self) -> str:
        return "JSON-LD"
    
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
        return []  # No external dependencies
    
    def get_parser(self) -> JSONLDParser:
        return JSONLDParser()
    
    def get_validator(self) -> JSONLDValidator:
        return JSONLDValidator()
    
    def get_converter(self) -> JSONLDConverter:
        return JSONLDConverter()
    
    def get_type_mappings(self) -> Dict[str, str]:
        return JSONLD_TO_FABRIC_TYPE
    
    def register_cli_arguments(self, parser: Any) -> None:
        """Add JSON-LD specific CLI arguments."""
        parser.add_argument(
            "--expand-context",
            action="store_true",
            help="Attempt to fetch and expand remote @context URLs"
        )
        parser.add_argument(
            "--base-uri",
            type=str,
            help="Base URI for resolving relative @id references"
        )


# =============================================================================
# Standalone Testing
# =============================================================================

if __name__ == "__main__":
    # Test the plugin
    plugin = JSONLDPlugin()
    print(f"Plugin: {plugin}")
    print(f"Format: {plugin.format_name}")
    print(f"Extensions: {plugin.file_extensions}")
    
    # Test with sample content
    sample = '''{
        "@context": {
            "schema": "https://schema.org/",
            "name": "schema:name",
            "age": {"@id": "schema:age", "@type": "http://www.w3.org/2001/XMLSchema#integer"}
        },
        "@type": "schema:Person",
        "name": "Alice",
        "age": 30
    }'''
    
    # Validate
    validator = plugin.get_validator()
    result = validator.validate(sample)
    print(f"\nValidation: {'Valid' if result.is_valid else 'Invalid'}")
    print(f"Statistics: {result.statistics}")
    
    # Convert
    converter = plugin.get_converter()
    conversion = converter.convert(sample)
    print(f"\nConversion:")
    if isinstance(conversion, dict):
        print(f"  Entity types: {len(conversion['entity_types'])}")
        for e in conversion['entity_types']:
            if isinstance(e, dict):
                print(f"    - {e['name']} ({len(e['properties'])} properties)")
            else:
                print(f"    - {e.name} ({len(e.properties)} properties)")
    else:
        print(f"  Entity types: {len(conversion.entity_types)}")
        for e in conversion.entity_types:
            print(f"    - {e.name} ({len(e.properties)} properties)")
