"""
Format-Specific Converter Packages

This package contains format-specific implementations for different ontology formats:
- rdf: RDF/OWL/TTL format support
- dtdl: DTDL (Digital Twins Definition Language) v2/v3/v4 support

Each format package contains:
- Parser: Read and parse the format
- Validator: Validate format compliance
- Converter: Convert to Fabric Ontology format
- Exporter: Export from Fabric back to the format (where applicable)

Usage:
    # RDF format
    from src.formats.rdf import RDFToFabricConverter, PreflightValidator
    
    # DTDL format
    from src.formats.dtdl import DTDLParser, DTDLValidator, DTDLToFabricConverter
"""

from . import rdf
from . import dtdl

__all__ = ['rdf', 'dtdl']
