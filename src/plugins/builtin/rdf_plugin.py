"""
RDF Plugin wrapper.

This wraps the existing RDF converter as a plugin to provide
it through the unified plugin interface.
"""

from typing import Any, Dict, List, Optional, Set

from ..base import OntologyPlugin


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
        return {
            ".ttl",
            ".rdf",
            ".owl",
            ".nt",
            ".n3",
            ".xml",
            ".trig",
            ".nq",
            ".nquads",
            ".trix",
            ".hext",
            ".html",
            ".xhtml",
            ".htm",
            ".jsonld",
        }
    
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
        try:
            from rdf import RDFGraphParser
            return RDFGraphParser()
        except ImportError:
            raise ImportError("RDF modules not available")
    
    def get_validator(self) -> Any:
        """Return RDF validator."""
        try:
            from rdf import PreflightValidator
            return PreflightValidator()
        except ImportError:
            raise ImportError("RDF modules not available")
    
    def get_converter(self) -> Any:
        """Return RDF converter."""
        try:
            from rdf import RDFToFabricConverter
            return RDFToFabricConverter()
        except ImportError:
            raise ImportError("RDF modules not available")
    
    def get_type_mappings(self) -> Dict[str, str]:
        """Return XSD to Fabric type mappings."""
        try:
            from rdf import XSD_TO_FABRIC_TYPE
            return XSD_TO_FABRIC_TYPE
        except ImportError:
            return {}
    
    def register_cli_arguments(self, parser: Any) -> None:
        """Add RDF-specific CLI arguments."""
        parser.add_argument(
            "--rdf-format",
            type=str,
            choices=["turtle", "xml", "nt", "n3", "json-ld"],
            help="RDF serialization format (auto-detected; include json-ld for .jsonld files)"
        )
        parser.add_argument(
            "--include-individuals",
            action="store_true",
            help="Include OWL individuals as entity instances"
        )


# Export
__all__ = ["RDFPlugin"]
