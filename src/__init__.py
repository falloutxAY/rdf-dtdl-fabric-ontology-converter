"""
Source package for RDF/DTDL to Fabric Ontology Converter.

Package Structure:
    src/
    ├── formats/           # Format-specific converters (new organized structure)
    │   ├── rdf/          # RDF/OWL/TTL format support
    │   └── dtdl/         # DTDL v2/v3/v4 format support
    ├── core/             # Shared infrastructure (streaming, validators, etc.)
    ├── models/           # Shared data models (EntityType, etc.)
    ├── cli/              # Command-line interface
    ├── converters/       # RDF converter components (legacy, used by formats.rdf)
    ├── dtdl/             # DTDL module (legacy, used by formats.dtdl)
    └── *.py              # Legacy modules for backward compatibility

Usage (recommended - new format-based imports):
    from src.formats.rdf import RDFToFabricConverter, PreflightValidator
    from src.formats.dtdl import DTDLParser, DTDLToFabricConverter

Usage (legacy - still supported):
    from src import RDFToFabricConverter
    from src.dtdl import DTDLParser
"""

__version__ = "1.0.0"
__author__ = "RDF Fabric Converter Contributors"

# Legacy exports for backward compatibility
from .rdf_converter import (
    RDFToFabricConverter,
    EntityType,
    RelationshipType,
    EntityTypeProperty,
    RelationshipEnd,
    parse_ttl_file,
    parse_ttl_content,
    convert_to_fabric_definition,
)

from .fabric_client import (
    FabricConfig,
    FabricOntologyClient,
    FabricAPIError,
)

# New format-based package (recommended)
from . import formats

__all__ = [
    # Format packages (new structure)
    "formats",
    # Converter (legacy exports)
    "RDFToFabricConverter",
    "EntityType",
    "RelationshipType",
    "EntityTypeProperty",
    "RelationshipEnd",
    "parse_ttl_file",
    "parse_ttl_content",
    "convert_to_fabric_definition",
    # Client
    "FabricConfig",
    "FabricOntologyClient",
    "FabricAPIError",
]
