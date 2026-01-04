"""
RDF Plugin wrapper.

This wraps the existing RDF converter as a plugin to provide
it through the unified plugin interface.
"""

from typing import Any, Dict, List, Optional, Set

from ..base import OntologyPlugin

# Existing RDF modules
try:
    from ...rdf.rdf_parser import RDFGraphParser
    from ...rdf.preflight_validator import PreflightValidator
    from ...rdf.rdf_converter import RDFToFabricConverter
    from ...rdf.type_mapper import XSD_TO_FABRIC_TYPE
except ImportError:
    # Fallback for standalone reference
    RDFGraphParser = None  # type: ignore
    PreflightValidator = None  # type: ignore
    RDFToFabricConverter = None  # type: ignore
    XSD_TO_FABRIC_TYPE = {}


class RDFPlugin(OntologyPlugin):
    """
    RDF/Turtle format plugin.
    
    Wraps the existing RDF converter components as a plugin.
    
    Supported formats:
    - Turtle (.ttl)
    - RDF/XML (.rdf, .xml)
    - N-Triples (.nt)
    - N3 (.n3)
    """
    
    @property
    def format_name(self) -> str:
        return "rdf"
    
    @property
    def display_name(self) -> str:
        return "RDF (Turtle/RDF-XML)"
    
    @property
    def file_extensions(self) -> Set[str]:
        return {".ttl", ".rdf", ".xml", ".nt", ".n3"}
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def author(self) -> str:
        return "Fabric Ontology Converter Team"
    
    @property
    def dependencies(self) -> List[str]:
        return ["rdflib>=6.0.0"]
    
    def get_parser(self) -> Any:
        """Return RDF parser."""
        if RDFGraphParser is None:
            raise ImportError("RDF modules not available")
        return RDFGraphParser()
    
    def get_validator(self) -> Any:
        """Return RDF validator."""
        if PreflightValidator is None:
            raise ImportError("RDF modules not available")
        return PreflightValidator()
    
    def get_converter(self) -> Any:
        """Return RDF converter."""
        if RDFToFabricConverter is None:
            raise ImportError("RDF modules not available")
        return RDFToFabricConverter()
    
    def get_type_mappings(self) -> Dict[str, str]:
        """Return XSD to Fabric type mappings."""
        return XSD_TO_FABRIC_TYPE
    
    def register_cli_arguments(self, parser: Any) -> None:
        """Add RDF-specific CLI arguments."""
        parser.add_argument(
            "--rdf-format",
            type=str,
            choices=["turtle", "xml", "nt", "n3"],
            help="RDF serialization format (auto-detected by default)"
        )
        parser.add_argument(
            "--include-individuals",
            action="store_true",
            help="Include OWL individuals as entity instances"
        )


# Export
__all__ = ["RDFPlugin"]
