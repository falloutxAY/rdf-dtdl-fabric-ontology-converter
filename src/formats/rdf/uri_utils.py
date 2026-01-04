"""
URI Utilities - URI parsing and name extraction for RDF to Fabric conversion.

This module handles the extraction and sanitization of names from RDF URIs
to comply with Microsoft Fabric Ontology naming requirements.

Extracted from RDFToFabricConverter for Single Responsibility Principle.
"""

import logging
from typing import Optional
from rdflib import URIRef

logger = logging.getLogger(__name__)


class URIUtils:
    """
    Utility class for URI parsing and name extraction.
    
    Handles:
    - Extracting local names from URIs (fragment or path-based)
    - Sanitizing names to match Fabric identifier requirements
    - Generating fallback names for edge cases
    
    Fabric naming requirements:
    - Must start with a letter
    - Can contain letters, numbers, and underscores only
    - Maximum 128 characters
    - Pattern: ^[a-zA-Z][a-zA-Z0-9_]{0,127}$
    """
    
    @staticmethod
    def uri_to_name(uri: Optional[URIRef], fallback_counter: int = 0) -> str:
        """
        Extract a clean, Fabric-compliant name from a URI.
        
        Args:
            uri: The URI to extract a name from
            fallback_counter: Counter for generating unique fallback names
            
        Returns:
            A sanitized name string suitable for Fabric identifiers
        """
        if uri is None:
            logger.warning("Received None URI, using default name")
            return f'Unknown_{fallback_counter}'
        
        uri_str = str(uri).strip()
        
        if not uri_str:
            logger.warning("Empty URI string, using default name")
            return f'Unknown_{fallback_counter}'
        
        # Try to get the fragment (after #)
        if '#' in uri_str:
            name = uri_str.split('#')[-1]
        elif '/' in uri_str:
            name = uri_str.split('/')[-1]
        else:
            name = uri_str
        
        # Handle empty extraction
        if not name:
            logger.warning(f"Could not extract name from URI: {uri_str}")
            return f'Entity_{fallback_counter}'
        
        # Sanitize the name for Fabric requirements
        return URIUtils.sanitize_name(name, fallback_counter)
    
    @staticmethod
    def sanitize_name(name: str, fallback_counter: int = 0) -> str:
        """
        Sanitize a name to match Fabric identifier requirements.
        
        Fabric requires identifiers to:
        - Start with a letter
        - Contain only letters, numbers, and underscores
        - Be at most 128 characters
        
        Args:
            name: The name to sanitize
            fallback_counter: Counter for generating unique fallback names
            
        Returns:
            A sanitized name string
        """
        if not name:
            return f'Entity_{fallback_counter}'
        
        # Replace invalid characters with underscores
        cleaned = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
        
        if not cleaned:
            logger.warning(f"Name produced empty cleaned result: {name}")
            return f'Entity_{fallback_counter}'
        
        # Ensure starts with a letter
        if not cleaned[0].isalpha():
            cleaned = 'E_' + cleaned
        
        # Truncate to 128 characters
        return cleaned[:128]
    
    @staticmethod
    def extract_namespace(uri: URIRef) -> str:
        """
        Extract the namespace portion of a URI.
        
        Args:
            uri: The URI to extract namespace from
            
        Returns:
            The namespace string (everything before the local name)
        """
        uri_str = str(uri)
        
        if '#' in uri_str:
            return uri_str.rsplit('#', 1)[0] + '#'
        elif '/' in uri_str:
            return uri_str.rsplit('/', 1)[0] + '/'
        
        return uri_str
    
    @staticmethod
    def is_valid_fabric_name(name: str) -> bool:
        """
        Check if a name is valid for Fabric identifiers.
        
        Args:
            name: The name to validate
            
        Returns:
            True if the name matches Fabric naming requirements
        """
        if not name or len(name) > 128:
            return False
        
        if not name[0].isalpha():
            return False
        
        return all(c.isalnum() or c == '_' for c in name)
