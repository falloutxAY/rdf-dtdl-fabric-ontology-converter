"""
Plugin infrastructure package for Fabric Ontology Converter.

This package provides the plugin system that allows adding new
ontology formats without modifying the core codebase.

Usage:
    from plugins import PluginManager, OntologyPlugin
    
    # Get plugin manager
    manager = PluginManager.get_instance()
    manager.discover_plugins()
    
    # Get a plugin
    rdf_plugin = manager.get_plugin("rdf")
    converter = rdf_plugin.get_converter()
    result = converter.convert(ttl_content)
"""

from .base import OntologyPlugin
from .protocols import (
    ParserProtocol,
    ValidatorProtocol,
    ConverterProtocol,
    ExporterProtocol,
)
from .manager import PluginManager

__all__ = [
    "OntologyPlugin",
    "ParserProtocol",
    "ValidatorProtocol",
    "ConverterProtocol",
    "ExporterProtocol",
    "PluginManager",
]
