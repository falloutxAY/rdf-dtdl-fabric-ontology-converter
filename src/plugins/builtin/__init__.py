"""
Built-in plugins for RDF and DTDL formats.

JSON-LD support now flows through the rdflib-backed RDF pipeline,
so no standalone JSON-LD plugin is provided.
"""

from .rdf_plugin import RDFPlugin
from .dtdl_plugin import DTDLPlugin

__all__ = ["RDFPlugin", "DTDLPlugin"]
