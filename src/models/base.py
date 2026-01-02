"""
Base converter protocol and abstract types.

This module defines the common interface that all format converters
(RDF, DTDL, etc.) must implement for consistent behavior.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from .conversion import ConversionResult


@runtime_checkable
class ConverterProtocol(Protocol):
    """
    Protocol defining the interface for ontology format converters.
    
    All converters (RDF, DTDL, future formats) should implement this
    protocol to ensure consistent behavior across the codebase.
    
    Example:
        >>> class MyConverter:
        ...     def convert(self, content: str, **kwargs) -> ConversionResult:
        ...         # Implementation
        ...         pass
        ...     
        ...     def validate(self, content: str) -> bool:
        ...         # Implementation
        ...         pass
        >>> 
        >>> converter: ConverterProtocol = MyConverter()
    """
    
    def convert(
        self,
        content: str,
        id_prefix: int = 1000000000000,
        **kwargs: Any,
    ) -> ConversionResult:
        """
        Convert content from source format to Fabric Ontology format.
        
        Args:
            content: The source content (TTL string, JSON string, etc.).
            id_prefix: Starting ID for generated entities.
            **kwargs: Format-specific options.
            
        Returns:
            ConversionResult with converted entities and relationships.
        """
        ...
    
    def validate(self, content: str) -> bool:
        """
        Validate that the content is well-formed for this format.
        
        Args:
            content: The source content to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        ...


class BaseConverter(ABC):
    """
    Abstract base class for ontology format converters.
    
    Provides common functionality and enforces the converter interface.
    Subclasses must implement convert() and validate() methods.
    
    Attributes:
        default_namespace: Default namespace for generated entities.
        id_counter: Counter for generating unique IDs.
    """
    
    def __init__(
        self,
        default_namespace: str = "usertypes",
        id_prefix: int = 1000000000000,
    ) -> None:
        """
        Initialize the converter.
        
        Args:
            default_namespace: Namespace for generated entities.
            id_prefix: Starting ID for entity generation.
        """
        self.default_namespace = default_namespace
        self.id_counter = id_prefix
    
    def _next_id(self) -> str:
        """Generate the next unique ID."""
        current = self.id_counter
        self.id_counter += 1
        return str(current)
    
    @abstractmethod
    def convert(
        self,
        content: str,
        id_prefix: int = 1000000000000,
        **kwargs: Any,
    ) -> ConversionResult:
        """
        Convert content to Fabric Ontology format.
        
        Must be implemented by subclasses.
        """
        pass
    
    @abstractmethod
    def validate(self, content: str) -> bool:
        """
        Validate source content.
        
        Must be implemented by subclasses.
        """
        pass
    
    def get_format_name(self) -> str:
        """
        Get the name of the source format this converter handles.
        
        Returns:
            Human-readable format name (e.g., "RDF/TTL", "DTDL v4").
        """
        return self.__class__.__name__.replace("Converter", "").replace("ToFabric", "")
