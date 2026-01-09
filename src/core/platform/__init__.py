"""Platform-level services for talking to Microsoft Fabric.

This module provides:
- IOntologyClient: Abstract interface for ontology operations
- FabricOntologyClient: REST API implementation (import from .fabric_client)
- SdkOntologyClient: SDK implementation (import from .sdk_client)
- create_ontology_client: Factory function for client creation
- ClientType: Enum for selecting client implementation

Example:
    >>> from src.core.platform import create_ontology_client, ClientType
    >>> from src.core.platform.fabric_client import FabricConfig
    >>> 
    >>> config = FabricConfig.from_file("config.json")
    >>> client = create_ontology_client(config, ClientType.REST)
    >>> ontologies = client.list_ontologies()

Note:
    FabricConfig, FabricOntologyClient, and related classes should be imported
    directly from .fabric_client to avoid circular import issues:
    
        from src.core.platform.fabric_client import FabricConfig, FabricOntologyClient
    
    For SDK client (when SDK is available):
    
        from src.core.platform.sdk_client import SdkOntologyClient, is_sdk_available
"""

# Abstract interface (no dependencies, safe to import)
from .ontology_client_interface import (
    IOntologyClient,
    ClientType,
    OntologyInfo,
    OntologyDefinition,
)

# Factory uses lazy imports to avoid circular dependencies
from .client_factory import (
    create_ontology_client,
    get_available_client_types,
    is_client_available,
    ClientNotAvailableError,
)

# SDK client utilities (safe to import - handles missing SDK gracefully)
from .sdk_client import (
    is_sdk_available,
    get_sdk_import_error,
    SdkNotAvailableError,
)

# Note: FabricConfig, FabricOntologyClient, SdkOntologyClient are NOT imported here
# to avoid circular imports. Import them directly:
#   from src.core.platform.fabric_client import FabricConfig, FabricOntologyClient
#   from src.core.platform.sdk_client import SdkOntologyClient

__all__ = [
    # Interface
    'IOntologyClient',
    'ClientType',
    'OntologyInfo',
    'OntologyDefinition',
    # Factory
    'create_ontology_client',
    'get_available_client_types',
    'is_client_available',
    'ClientNotAvailableError',
    # SDK utilities
    'is_sdk_available',
    'get_sdk_import_error',
    'SdkNotAvailableError',
]
