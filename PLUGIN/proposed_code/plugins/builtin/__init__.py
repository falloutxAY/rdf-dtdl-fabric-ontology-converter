"""
Built-in plugins package.

This package contains the built-in format plugins:
- RDF (rdf_plugin.py) - Wraps existing RDF converter
- DTDL (dtdl_plugin.py) - Wraps existing DTDL converter
- JSON-LD (jsonld_plugin.py) - Sample plugin implementation

These plugins are automatically discovered and registered
by the PluginManager.
"""

from .jsonld_plugin import JSONLDPlugin
from .rdf_plugin import RDFPlugin
from .dtdl_plugin import DTDLPlugin

# All available built-in plugins
BUILTIN_PLUGINS = [
    JSONLDPlugin,
    RDFPlugin,
    DTDLPlugin,
]

__all__ = [
    "JSONLDPlugin",
    "RDFPlugin", 
    "DTDLPlugin",
    "BUILTIN_PLUGINS",
]