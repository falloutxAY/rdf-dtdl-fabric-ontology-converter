"""
Protocol Definitions for Plugin Components.

This module defines the protocols (interfaces) that plugin components
must implement. Using protocols allows for duck typing while still
providing type hints and documentation.

Protocols:
    ParserProtocol: Parse ontology content
    ValidatorProtocol: Validate ontology content
    ConverterProtocol: Convert to Fabric format
    ExporterProtocol: Export from Fabric format
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

# Import from common module (when available)
# For now, define locally for reference
try:
    from common.validation import ValidationResult
    from models import ConversionResult, EntityType, RelationshipType
except ImportError:
    # Placeholder types for reference implementation
    ValidationResult = Any  # type: ignore
    ConversionResult = Any  # type: ignore
    EntityType = Any  # type: ignore
    RelationshipType = Any  # type: ignore


@runtime_checkable
class ParserProtocol(Protocol):
    """
    Protocol for parsing ontology content.
    
    Parsers are responsible for reading source content (strings or files)
    and converting them into an internal representation specific to the
    format (e.g., rdflib.Graph for RDF, list of DTDLInterface for DTDL).
    
    The internal representation is then used by validators and converters.
    
    Example implementation:
        class MyParser:
            def parse(self, content: str, file_path: Optional[str] = None) -> MyInternalRep:
                # Parse content into internal representation
                return parse_my_format(content)
            
            def parse_file(self, file_path: str) -> MyInternalRep:
                with open(file_path, 'r') as f:
                    return self.parse(f.read(), file_path)
    """
    
    def parse(self, content: str, file_path: Optional[str] = None) -> Any:
        """
        Parse content string.
        
        Args:
            content: Source content as string.
            file_path: Optional path for error messages.
        
        Returns:
            Format-specific internal representation.
        
        Raises:
            ValueError: If content cannot be parsed.
        """
        ...
    
    def parse_file(self, file_path: str) -> Any:
        """
        Parse a file.
        
        Args:
            file_path: Path to the file to parse.
        
        Returns:
            Format-specific internal representation.
        
        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If content cannot be parsed.
        """
        ...


@runtime_checkable
class ValidatorProtocol(Protocol):
    """
    Protocol for validating ontology content.
    
    Validators check that content is well-formed and compatible with
    Fabric Ontology conversion. They produce ValidationResult with
    any issues found.
    
    Validators should check:
    - Syntax correctness
    - Required elements present
    - Valid references
    - Fabric compatibility (conversion limitations)
    
    Example implementation:
        class MyValidator:
            def validate(self, content: str, file_path: Optional[str] = None) -> ValidationResult:
                result = ValidationResult(format_name="myformat", source_path=file_path)
                
                # Check syntax
                try:
                    parsed = parse(content)
                except SyntaxError as e:
                    result.add_error(IssueCategory.SYNTAX_ERROR, str(e))
                    return result
                
                # Check structure
                if not has_required_elements(parsed):
                    result.add_error(IssueCategory.MISSING_REQUIRED, "Missing required element")
                
                return result
            
            def validate_file(self, file_path: str) -> ValidationResult:
                with open(file_path, 'r') as f:
                    return self.validate(f.read(), file_path)
    """
    
    def validate(self, content: str, file_path: Optional[str] = None) -> Any:  # ValidationResult
        """
        Validate content string.
        
        Args:
            content: Source content to validate.
            file_path: Optional path for error messages.
        
        Returns:
            ValidationResult with any issues found.
        """
        ...
    
    def validate_file(self, file_path: str) -> Any:  # ValidationResult
        """
        Validate a file.
        
        Args:
            file_path: Path to the file to validate.
        
        Returns:
            ValidationResult with any issues found.
        """
        ...


@runtime_checkable
class ConverterProtocol(Protocol):
    """
    Protocol for converting to Fabric Ontology format.
    
    Converters transform source content into Fabric EntityType and
    RelationshipType objects, packaged in a ConversionResult.
    
    Converters should:
    - Map source types to Fabric types
    - Generate unique IDs for entities
    - Track skipped items and warnings
    - Handle inheritance and relationships
    
    Example implementation:
        class MyConverter:
            def convert(
                self,
                content: str,
                id_prefix: int = 1000000000000,
                **kwargs
            ) -> ConversionResult:
                entities = []
                relationships = []
                skipped = []
                warnings = []
                
                # Parse and convert
                parsed = parse(content)
                for item in parsed:
                    try:
                        entity = convert_item(item, id_prefix)
                        entities.append(entity)
                    except ConversionError as e:
                        skipped.append(SkippedItem(...))
                
                return ConversionResult(
                    entity_types=entities,
                    relationship_types=relationships,
                    skipped_items=skipped,
                    warnings=warnings,
                )
    """
    
    def convert(
        self,
        content: str,
        id_prefix: int = 1000000000000,
        **kwargs: Any,
    ) -> Any:  # ConversionResult
        """
        Convert content to Fabric Ontology format.
        
        Args:
            content: Source content to convert.
            id_prefix: Starting ID for generated entities.
            **kwargs: Format-specific options.
        
        Returns:
            ConversionResult with entities and relationships.
        """
        ...


@runtime_checkable
class ExporterProtocol(Protocol):
    """
    Protocol for exporting from Fabric Ontology format.
    
    Exporters transform Fabric EntityType and RelationshipType objects
    back into the plugin's format. This is optional - not all plugins
    need to support export.
    
    Example implementation:
        class MyExporter:
            def export(
                self,
                entity_types: List[EntityType],
                relationship_types: List[RelationshipType],
                **kwargs
            ) -> str:
                output_lines = []
                
                for entity in entity_types:
                    output_lines.append(format_entity(entity))
                
                for rel in relationship_types:
                    output_lines.append(format_relationship(rel))
                
                return "\\n".join(output_lines)
    """
    
    def export(
        self,
        entity_types: List[Any],  # List[EntityType]
        relationship_types: List[Any],  # List[RelationshipType]
        **kwargs: Any,
    ) -> str:
        """
        Export Fabric entities to this format.
        
        Args:
            entity_types: List of EntityType objects.
            relationship_types: List of RelationshipType objects.
            **kwargs: Format-specific options.
        
        Returns:
            Exported content as string.
        """
        ...
    
    def export_to_file(
        self,
        entity_types: List[Any],  # List[EntityType]
        relationship_types: List[Any],  # List[RelationshipType]
        file_path: str,
        **kwargs: Any,
    ) -> None:
        """
        Export Fabric entities to a file.
        
        Args:
            entity_types: List of EntityType objects.
            relationship_types: List of RelationshipType objects.
            file_path: Output file path.
            **kwargs: Format-specific options.
        """
        ...


@runtime_checkable
class StreamingAdapterProtocol(Protocol):
    """
    Protocol for streaming large file processing.
    
    Streaming adapters process large files incrementally to avoid
    loading the entire file into memory. This is optional and only
    needed for formats that may have very large files.
    
    Example implementation:
        class MyStreamingAdapter:
            def stream_convert(
                self,
                file_path: str,
                chunk_callback: Callable[[ConversionResult], None],
                id_prefix: int = 1000000000000,
                **kwargs
            ) -> ConversionResult:
                total_entities = []
                total_relationships = []
                
                for chunk in read_chunks(file_path):
                    chunk_result = convert_chunk(chunk)
                    chunk_callback(chunk_result)
                    total_entities.extend(chunk_result.entity_types)
                    total_relationships.extend(chunk_result.relationship_types)
                
                return ConversionResult(
                    entity_types=total_entities,
                    relationship_types=total_relationships,
                )
    """
    
    def stream_convert(
        self,
        file_path: str,
        chunk_callback: Any,  # Callable[[ConversionResult], None]
        id_prefix: int = 1000000000000,
        **kwargs: Any,
    ) -> Any:  # ConversionResult
        """
        Convert a file using streaming.
        
        Args:
            file_path: Path to the file to convert.
            chunk_callback: Called with each chunk's result.
            id_prefix: Starting ID for generated entities.
            **kwargs: Format-specific options.
        
        Returns:
            Combined ConversionResult.
        """
        ...
    
    def estimate_memory(self, file_path: str) -> int:
        """
        Estimate memory required to process a file.
        
        Args:
            file_path: Path to the file.
        
        Returns:
            Estimated bytes of memory required.
        """
        ...
    
    def should_stream(self, file_path: str) -> bool:
        """
        Determine if streaming should be used for a file.
        
        Args:
            file_path: Path to the file.
        
        Returns:
            True if streaming is recommended.
        """
        ...


# =============================================================================
# Type Checking Utilities
# =============================================================================

def is_parser(obj: Any) -> bool:
    """Check if object implements ParserProtocol."""
    return isinstance(obj, ParserProtocol)


def is_validator(obj: Any) -> bool:
    """Check if object implements ValidatorProtocol."""
    return isinstance(obj, ValidatorProtocol)


def is_converter(obj: Any) -> bool:
    """Check if object implements ConverterProtocol."""
    return isinstance(obj, ConverterProtocol)


def is_exporter(obj: Any) -> bool:
    """Check if object implements ExporterProtocol."""
    return isinstance(obj, ExporterProtocol)
