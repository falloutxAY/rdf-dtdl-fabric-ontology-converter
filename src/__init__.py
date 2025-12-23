"""Source package for RDF to Fabric Ontology Converter."""

__version__ = "1.0.0"
__author__ = "RDF Fabric Converter Contributors"

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

__all__ = [
    # Converter
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
