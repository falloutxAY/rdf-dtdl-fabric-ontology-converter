"""
Base Plugin Class - Abstract base for ontology format plugins.

This module defines the OntologyPlugin abstract base class that all
format plugins must implement.

Usage:
    from plugins.base import OntologyPlugin
    
    class MyFormatPlugin(OntologyPlugin):
        @property
        def format_name(self) -> str:
            return "myformat"
        
        @property
        def display_name(self) -> str:
            return "My Custom Format"
        
        @property
        def file_extensions(self) -> Set[str]:
            return {".myf", ".myformat"}
        
        def get_parser(self) -> ParserProtocol:
            return MyFormatParser()
        
        def get_validator(self) -> ValidatorProtocol:
            return MyFormatValidator()
        
        def get_converter(self) -> ConverterProtocol:
            return MyFormatConverter()
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Type

from .protocols import (
    ParserProtocol,
    ValidatorProtocol,
    ConverterProtocol,
    ExporterProtocol,
)

logger = logging.getLogger(__name__)


class OntologyPlugin(ABC):
    """
    Abstract base class for ontology format plugins.
    
    Each plugin represents a single ontology format (e.g., RDF, DTDL, JSON-LD)
    and provides implementations for parsing, validating, and converting
    that format to Microsoft Fabric Ontology format.
    
    Required Properties:
        format_name: Unique identifier for CLI (e.g., "rdf", "dtdl")
        display_name: Human-readable name (e.g., "RDF/OWL TTL")
        file_extensions: Supported file extensions (e.g., {".ttl", ".rdf"})
    
    Required Methods:
        get_parser(): Returns parser for this format
        get_validator(): Returns validator for this format
        get_converter(): Returns converter to Fabric format
    
    Optional Methods:
        get_exporter(): Returns exporter from Fabric format (reverse conversion)
        get_type_mappings(): Returns type mapping dictionary
        register_cli_arguments(): Add format-specific CLI arguments
        get_streaming_adapter(): Return streaming adapter for large files
    
    Example:
        >>> class JSONLDPlugin(OntologyPlugin):
        ...     @property
        ...     def format_name(self) -> str:
        ...         return "jsonld"
        ...     
        ...     @property
        ...     def display_name(self) -> str:
        ...         return "JSON-LD"
        ...     
        ...     @property
        ...     def file_extensions(self) -> Set[str]:
        ...         return {".jsonld", ".json-ld"}
        ...     
        ...     def get_parser(self):
        ...         return JSONLDParser()
        ...     
        ...     def get_validator(self):
        ...         return JSONLDValidator()
        ...     
        ...     def get_converter(self):
        ...         return JSONLDConverter()
    """
    
    # =========================================================================
    # Required Abstract Properties
    # =========================================================================
    
    @property
    @abstractmethod
    def format_name(self) -> str:
        """
        Unique identifier for this format.
        
        Used in CLI commands (--format <name>) and internal registration.
        Should be lowercase, alphanumeric, no spaces.
        
        Examples: "rdf", "dtdl", "jsonld", "shacl"
        """
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """
        Human-readable format name.
        
        Used in help text, error messages, and UI.
        
        Examples: "RDF/OWL TTL", "DTDL v4", "JSON-LD 1.1"
        """
        pass
    
    @property
    @abstractmethod
    def file_extensions(self) -> Set[str]:
        """
        Set of supported file extensions.
        
        Extensions should include the leading dot and be lowercase.
        
        Examples: {".ttl", ".rdf", ".owl"}, {".json"}, {".jsonld"}
        """
        pass
    
    # =========================================================================
    # Required Abstract Methods
    # =========================================================================
    
    @abstractmethod
    def get_parser(self) -> ParserProtocol:
        """
        Get a parser instance for this format.
        
        The parser is responsible for reading and parsing files
        in this format into an internal representation.
        
        Returns:
            Parser instance implementing ParserProtocol.
        """
        pass
    
    @abstractmethod
    def get_validator(self) -> ValidatorProtocol:
        """
        Get a validator instance for this format.
        
        The validator checks format-specific rules and produces
        a ValidationResult.
        
        Returns:
            Validator instance implementing ValidatorProtocol.
        """
        pass
    
    @abstractmethod
    def get_converter(self) -> ConverterProtocol:
        """
        Get a converter instance for this format.
        
        The converter transforms parsed content into
        Fabric Ontology format (EntityType, RelationshipType).
        
        Returns:
            Converter instance implementing ConverterProtocol.
        """
        pass
    
    # =========================================================================
    # Optional Properties
    # =========================================================================
    
    @property
    def version(self) -> str:
        """
        Plugin version string.
        
        Follows semantic versioning (MAJOR.MINOR.PATCH).
        
        Returns:
            Version string (default: "1.0.0").
        """
        return "1.0.0"
    
    @property
    def author(self) -> str:
        """
        Plugin author information.
        
        Returns:
            Author name or organization (default: "Unknown").
        """
        return "Unknown"
    
    @property
    def description(self) -> str:
        """
        Plugin description.
        
        Returns:
            Description string (default: class docstring or empty).
        """
        return self.__class__.__doc__ or ""
    
    @property
    def documentation_url(self) -> Optional[str]:
        """
        URL to plugin documentation.
        
        Returns:
            URL string or None.
        """
        return None
    
    @property
    def supports_streaming(self) -> bool:
        """
        Whether this plugin supports streaming for large files.
        
        Returns:
            True if streaming is supported (default: False).
        """
        return False
    
    @property
    def supports_export(self) -> bool:
        """
        Whether this plugin supports export (Fabric -> this format).
        
        Returns:
            True if export is supported (default: False).
        """
        return self.get_exporter() is not None
    
    @property
    def dependencies(self) -> List[str]:
        """
        List of Python package dependencies.
        
        Returns:
            List of package names (e.g., ["rdflib", "jsonld"]).
        """
        return []
    
    # =========================================================================
    # Optional Methods
    # =========================================================================
    
    def get_exporter(self) -> Optional[ExporterProtocol]:
        """
        Get an exporter instance for reverse conversion.
        
        The exporter transforms Fabric Ontology format back into
        this format.
        
        Returns:
            Exporter instance or None if not supported.
        """
        return None
    
    def get_type_mappings(self) -> Dict[str, str]:
        """
        Get format-specific type mappings to Fabric types.
        
        Override to provide custom type mappings. These will be
        registered with the global TypeMappingRegistry.
        
        Returns:
            Dict mapping source types to Fabric types.
            
        Example:
            {
                "http://www.w3.org/2001/XMLSchema#string": "String",
                "http://www.w3.org/2001/XMLSchema#integer": "BigInt",
            }
        """
        return {}
    
    def get_streaming_adapter(self) -> Optional[Any]:
        """
        Get a streaming adapter for processing large files.
        
        Override to provide a streaming implementation that can
        process files without loading entirely into memory.
        
        Returns:
            Streaming adapter or None if not supported.
        """
        return None
    
    def register_cli_arguments(self, parser: Any) -> None:
        """
        Register format-specific CLI arguments.
        
        Override to add arguments specific to this format
        (e.g., DTDL's --flatten-components).
        
        Args:
            parser: argparse.ArgumentParser subparser.
        """
        pass
    
    def initialize(self) -> None:
        """
        Initialize the plugin.
        
        Called when the plugin is first loaded. Override to
        perform any setup needed before the plugin is used.
        
        Raises:
            RuntimeError: If initialization fails.
        """
        pass
    
    def cleanup(self) -> None:
        """
        Clean up plugin resources.
        
        Called when the plugin is unloaded. Override to
        release any resources held by the plugin.
        """
        pass
    
    def check_dependencies(self) -> List[str]:
        """
        Check if required dependencies are available.
        
        Returns:
            List of missing dependency names.
        """
        missing = []
        for dep in self.dependencies:
            try:
                __import__(dep)
            except ImportError:
                missing.append(dep)
        return missing
    
    def can_handle_extension(self, extension: str) -> bool:
        """
        Check if this plugin handles the given extension.
        
        Args:
            extension: File extension (with or without dot).
        
        Returns:
            True if the extension is handled.
        """
        ext = extension.lower() if extension.startswith('.') else f'.{extension.lower()}'
        return ext in self.file_extensions
    
    # =========================================================================
    # Built-in Methods
    # =========================================================================
    
    def matches_extension(self, file_path: str) -> bool:
        """
        Check if a file path matches this plugin's extensions.
        
        Args:
            file_path: Path to check.
        
        Returns:
            True if the extension matches.
        """
        from pathlib import Path
        ext = Path(file_path).suffix.lower()
        return ext in self.file_extensions
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get plugin information dictionary.
        
        Returns:
            Dict with plugin metadata.
        """
        return {
            "format_name": self.format_name,
            "display_name": self.display_name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "file_extensions": list(self.file_extensions),
            "supports_streaming": self.supports_streaming,
            "supports_export": self.supports_export,
            "dependencies": self.dependencies,
            "documentation_url": self.documentation_url,
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(format={self.format_name!r}, version={self.version!r})"
    
    def __str__(self) -> str:
        return f"{self.display_name} (v{self.version})"


# =============================================================================
# Plugin Registration Decorator
# =============================================================================

_plugin_registry: Dict[str, Type[OntologyPlugin]] = {}


def register_plugin(cls: Type[OntologyPlugin]) -> Type[OntologyPlugin]:
    """
    Decorator to register a plugin class.
    
    Can be used to automatically register plugins when their module is imported.
    
    Usage:
        @register_plugin
        class MyPlugin(OntologyPlugin):
            ...
    """
    # Create temporary instance to get format_name
    try:
        instance = cls()
        _plugin_registry[instance.format_name.lower()] = cls
        logger.debug(f"Registered plugin class: {cls.__name__}")
    except Exception as e:
        logger.warning(f"Could not register plugin {cls.__name__}: {e}")
    return cls


def get_registered_plugins() -> Dict[str, Type[OntologyPlugin]]:
    """Get all registered plugin classes."""
    return _plugin_registry.copy()
