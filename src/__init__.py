"""
Source package for RDF/DTDL to Fabric Ontology Converter.

Package Structure:
    src/
    ├── rdf/              # RDF/OWL/TTL format support
    │   ├── rdf_converter.py
    │   ├── preflight_validator.py
    │   ├── fabric_to_ttl.py
    │   └── ...
    ├── dtdl/             # DTDL v2/v3/v4 format support
    ├── core/             # Shared infrastructure (Fabric client, streaming, validators)
    │   ├── fabric_client.py
    │   ├── rate_limiter.py
    │   ├── circuit_breaker.py
    │   └── ...
    ├── models/           # Shared data models (EntityType, etc.)
    └── cli/              # Command-line interface

Usage:
    from src.rdf import RDFToFabricConverter, PreflightValidator
    from src.dtdl import DTDLParser, DTDLValidator
    from src.core import FabricConfig, FabricOntologyClient
"""

__version__ = "1.0.0"
__author__ = "RDF Fabric Converter Contributors"

# Main exports from rdf package
from .rdf import (
    RDFToFabricConverter,
    StreamingRDFConverter,
    EntityType,
    RelationshipType,
    EntityTypeProperty,
    RelationshipEnd,
    parse_ttl_file,
    parse_ttl_content,
    parse_ttl_with_result,
    convert_to_fabric_definition,
    PreflightValidator,
    FabricToTTLConverter,
)

from .core import (
    FabricConfig,
    FabricOntologyClient,
    FabricAPIError,
)

__all__ = [
    # RDF converter
    "RDFToFabricConverter",
    "StreamingRDFConverter",
    "PreflightValidator",
    "FabricToTTLConverter",
    # Models
    "EntityType",
    "RelationshipType",
    "EntityTypeProperty",
    "RelationshipEnd",
    # Functions
    "parse_ttl_file",
    "parse_ttl_content",
    "parse_ttl_with_result",
    "convert_to_fabric_definition",
    # Client
    "FabricConfig",
    "FabricOntologyClient",
    "FabricAPIError",
]
