"""
RDF/OWL/TTL Format Support Package

This package provides comprehensive support for RDF (Resource Description Framework)
ontology formats, including OWL and TTL (Turtle) files.

Components:
- converter: Main RDFToFabricConverter for converting TTL to Fabric Ontology
- validator: PreflightValidator for pre-conversion validation
- exporter: FabricToTTLConverter for exporting Fabric back to TTL
- parser: RDFGraphParser for parsing TTL files with memory management
- extractor: Property/class extraction from RDF graphs
- mapper: XSD to Fabric type mapping
- utils: URI parsing and utility functions
- resolver: OWL class expression resolution
- serializer: Fabric API JSON serialization

Usage:
    from src.formats.rdf import (
        RDFToFabricConverter,
        PreflightValidator,
        FabricToTTLConverter,
    )
    
    # Validate TTL file before conversion
    validator = PreflightValidator()
    report = validator.validate_file("ontology.ttl")
    
    # Convert TTL to Fabric format
    converter = RDFToFabricConverter()
    entity_types, relationship_types = converter.parse_ttl_file("ontology.ttl")
    
    # Export Fabric back to TTL
    exporter = FabricToTTLConverter()
    ttl_content = exporter.convert(fabric_definition)
"""

# Import main converter classes - these re-export from legacy locations for backward compatibility
try:
    # When imported as part of src package
    from ...rdf_converter import (
        RDFToFabricConverter,
        StreamingRDFConverter,
        parse_ttl_file,
        parse_ttl_content,
        parse_ttl_with_result,
        convert_to_fabric_definition,
    )
    from ...preflight_validator import (
        PreflightValidator,
        ValidationReport,
        ValidationIssue,
        IssueSeverity,
        IssueCategory,
    )
    from ...fabric_to_ttl import (
        FabricToTTLConverter,
        FABRIC_TO_XSD_TYPE,
    )
    # Import converter components
    from ...converters import (
        TypeMapper,
        XSD_TO_FABRIC_TYPE,
        URIUtils,
        ClassResolver,
        FabricSerializer,
        MemoryManager,
        RDFGraphParser,
        ClassExtractor,
        DataPropertyExtractor,
        ObjectPropertyExtractor,
        EntityIdentifierSetter,
    )
except ImportError:
    # When imported directly or in different context
    from src.rdf_converter import (
        RDFToFabricConverter,
        StreamingRDFConverter,
        parse_ttl_file,
        parse_ttl_content,
        parse_ttl_with_result,
        convert_to_fabric_definition,
    )
    from src.preflight_validator import (
        PreflightValidator,
        ValidationReport,
        ValidationIssue,
        IssueSeverity,
        IssueCategory,
    )
    from src.fabric_to_ttl import (
        FabricToTTLConverter,
        FABRIC_TO_XSD_TYPE,
    )
    from src.converters import (
        TypeMapper,
        XSD_TO_FABRIC_TYPE,
        URIUtils,
        ClassResolver,
        FabricSerializer,
        MemoryManager,
        RDFGraphParser,
        ClassExtractor,
        DataPropertyExtractor,
        ObjectPropertyExtractor,
        EntityIdentifierSetter,
    )


__all__ = [
    # Main converter
    'RDFToFabricConverter',
    'StreamingRDFConverter',
    # Convenience functions
    'parse_ttl_file',
    'parse_ttl_content',
    'parse_ttl_with_result',
    'convert_to_fabric_definition',
    # Validation
    'PreflightValidator',
    'ValidationReport',
    'ValidationIssue',
    'IssueSeverity',
    'IssueCategory',
    # Export
    'FabricToTTLConverter',
    'FABRIC_TO_XSD_TYPE',
    # Converter components
    'TypeMapper',
    'XSD_TO_FABRIC_TYPE',
    'URIUtils',
    'ClassResolver',
    'FabricSerializer',
    'MemoryManager',
    'RDFGraphParser',
    'ClassExtractor',
    'DataPropertyExtractor',
    'ObjectPropertyExtractor',
    'EntityIdentifierSetter',
]
