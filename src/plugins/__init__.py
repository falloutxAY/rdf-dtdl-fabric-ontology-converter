"""
Plugin infrastructure for Fabric Ontology Converter.

This module provides the plugin system that allows extending the converter
with new ontology formats beyond the built-in RDF and DTDL.

Usage:
    from plugins import PluginManager, OntologyPlugin
    
    # Get plugin manager
    manager = PluginManager.get_instance()
    manager.discover_plugins()
    
    # Get a plugin
    rdf_plugin = manager.get_plugin("rdf")
    converter = rdf_plugin.get_converter()
"""

from .base import OntologyPlugin
from .protocols import (
    ParserProtocol,
    ValidatorProtocol,
    ConverterProtocol,
    ExporterProtocol,
)
from .manager import (
    PluginManager,
    get_plugin_manager,
)

__all__ = [
    # Base class
    "OntologyPlugin",
    # Protocols
    "ParserProtocol",
    "ValidatorProtocol",
    "ConverterProtocol",
    "ExporterProtocol",
    # Manager
    "PluginManager",
    "get_plugin_manager",
]
