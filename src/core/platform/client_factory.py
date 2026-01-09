"""
Factory for creating Ontology API clients.

This module provides a factory function to create the appropriate
ontology client implementation based on configuration.

Supported client types:
- REST: Direct REST API calls (current implementation)
- SDK: Microsoft Fabric SDK (future implementation)

Example:
    >>> from src.core.platform import create_ontology_client, ClientType
    >>> from src.core.platform.fabric_client import FabricConfig
    >>> 
    >>> config = FabricConfig.from_file("config.json")
    >>> 
    >>> # Create REST client (default)
    >>> client = create_ontology_client(config)
    >>> 
    >>> # Explicitly create REST client
    >>> client = create_ontology_client(config, ClientType.REST)
    >>> 
    >>> # Create SDK client (when available)
    >>> client = create_ontology_client(config, ClientType.SDK)
"""

import logging
from typing import Optional, TYPE_CHECKING

from .ontology_client_interface import ClientType, IOntologyClient

if TYPE_CHECKING:
    from .fabric_client import FabricConfig

logger = logging.getLogger(__name__)


class ClientNotAvailableError(Exception):
    """Raised when a requested client type is not available."""
    pass


def create_ontology_client(
    config: 'FabricConfig',
    client_type: Optional[ClientType] = None,
) -> IOntologyClient:
    """
    Factory function to create an ontology client.
    
    Creates the appropriate client implementation based on the specified
    client type. If no client type is specified, uses REST by default.
    
    Args:
        config: FabricConfig instance with connection details
        client_type: Type of client to create (REST or SDK).
                    Defaults to REST if not specified.
    
    Returns:
        IOntologyClient: An ontology client instance implementing the interface
    
    Raises:
        ClientNotAvailableError: If the requested client type is not available
        ValueError: If config is invalid
    
    Example:
        >>> config = FabricConfig.from_file("config.json")
        >>> client = create_ontology_client(config, ClientType.REST)
        >>> ontologies = client.list_ontologies()
    """
    # Default to REST client
    if client_type is None:
        client_type = ClientType.REST
    
    logger.info(f"Creating ontology client: {client_type.value}")
    
    if client_type == ClientType.REST:
        return _create_rest_client(config)
    elif client_type == ClientType.SDK:
        return _create_sdk_client(config)
    else:
        raise ClientNotAvailableError(f"Unknown client type: {client_type}")


def _create_rest_client(config: 'FabricConfig') -> IOntologyClient:
    """
    Create a REST API-based ontology client.
    
    Args:
        config: FabricConfig instance
        
    Returns:
        FabricOntologyClient instance (implements IOntologyClient)
    """
    from .fabric_client import FabricOntologyClient
    
    logger.debug("Initializing REST API client")
    return FabricOntologyClient(config)


def _create_sdk_client(config: 'FabricConfig') -> IOntologyClient:
    """
    Create an SDK-based ontology client.
    
    Args:
        config: FabricConfig instance
        
    Returns:
        SDK client instance (implements IOntologyClient)
        
    Raises:
        ClientNotAvailableError: If SDK is not installed
    """
    from .sdk_client import is_sdk_available, SdkOntologyClient, SdkNotAvailableError
    
    if not is_sdk_available():
        raise ClientNotAvailableError(
            "Microsoft Fabric Ontology SDK is not installed. "
            "Please install it with: pip install azure-fabric-ontology (when available). "
            "Alternatively, use ClientType.REST for REST API-based operations."
        )
    
    try:
        logger.debug("Initializing SDK client")
        return SdkOntologyClient(config)
    except SdkNotAvailableError as e:
        raise ClientNotAvailableError(str(e))


def get_available_client_types() -> list[ClientType]:
    """
    Get list of currently available client types.
    
    Returns:
        List of ClientType enum values that are available for use
    """
    available = [ClientType.REST]  # REST is always available
    
    # Check if SDK is available
    from .sdk_client import is_sdk_available
    if is_sdk_available():
        available.append(ClientType.SDK)
    
    return available


def is_client_available(client_type: ClientType) -> bool:
    """
    Check if a specific client type is available.
    
    Args:
        client_type: The client type to check
        
    Returns:
        True if the client type is available, False otherwise
    """
    return client_type in get_available_client_types()


__all__ = [
    'create_ontology_client',
    'get_available_client_types',
    'is_client_available',
    'ClientNotAvailableError',
    'ClientType',
]
