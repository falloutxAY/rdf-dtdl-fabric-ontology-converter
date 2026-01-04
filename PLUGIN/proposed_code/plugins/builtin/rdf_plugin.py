"""
RDF Plugin wrapper.

This wraps the existing RDF converter as a plugin to demonstrate
how existing converters integrate with the plugin system.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Plugin base
import sys
_plugin_dir = Path(__file__).parent.parent
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))

from base import OntologyPlugin

# Existing RDF modules (adjust imports as needed)
try:
    from rdf.rdf_parser import RDFParser
    from rdf.preflight_validator import PreflightValidator
    from rdf.rdf_converter import RDFConverter
    from rdf.type_mapper import XSD_TO_FABRIC_TYPE
except ImportError:
    # Fallback for standalone reference
    RDFParser = None
    PreflightValidator = None
    RDFConverter = None
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
        if RDFParser is None:
            raise ImportError("RDF modules not available")
        return RDFParser()
    
    def get_validator(self) -> Any:
        """Return RDF validator."""
        if PreflightValidator is None:
            raise ImportError("RDF modules not available")
        return PreflightValidator()
    
    def get_converter(self) -> Any:
        """Return RDF converter."""
        if RDFConverter is None:
            raise ImportError("RDF modules not available")
        return RDFConverter()
    
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
