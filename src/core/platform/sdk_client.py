"""
SDK-based Ontology API client.

This module provides an SDK-based implementation of the IOntologyClient interface,
wrapping the Microsoft Fabric Ontology SDK for ontology operations.

Note:
    This implementation requires the Microsoft Fabric SDK to be installed.
    Install it with: pip install azure-fabric (when available)

Example:
    >>> from src.core.platform.sdk_client import SdkOntologyClient
    >>> from src.core.platform.fabric_client import FabricConfig
    >>> 
    >>> config = FabricConfig.from_file("config.json")
    >>> client = SdkOntologyClient(config)
    >>> ontologies = client.list_ontologies()
"""

import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING

from .ontology_client_interface import IOntologyClient

if TYPE_CHECKING:
    from .fabric_client import FabricConfig
    from ..cancellation import CancellationToken

logger = logging.getLogger(__name__)

# SDK availability flag - will be set to True when SDK is installed
SDK_AVAILABLE = False
SDK_IMPORT_ERROR: Optional[str] = None

# Attempt to import the Fabric SDK
try:
    # Future SDK import - adjust package name when SDK is released
    # Expected package names:
    # - azure-fabric-ontology
    # - azure-fabric
    # - microsoft-fabric-sdk
    from azure.fabric.ontology import OntologyClient as FabricSdkClient
    from azure.fabric.ontology.models import (
        Ontology,
        OntologyDefinition as SdkOntologyDefinition,
        EntityType as SdkEntityType,
        RelationshipType as SdkRelationshipType,
    )
    SDK_AVAILABLE = True
except ImportError as e:
    SDK_IMPORT_ERROR = str(e)
    # Define placeholder types for type hints when SDK is not available
    FabricSdkClient = None  # type: ignore
    Ontology = None  # type: ignore
    SdkOntologyDefinition = None  # type: ignore
    SdkEntityType = None  # type: ignore
    SdkRelationshipType = None  # type: ignore


class SdkNotAvailableError(Exception):
    """Raised when SDK operations are attempted but SDK is not installed."""
    
    def __init__(self, message: Optional[str] = None):
        if message is None:
            message = (
                "Microsoft Fabric Ontology SDK is not installed. "
                "Please install it with: pip install azure-fabric-ontology (when available). "
                f"Import error: {SDK_IMPORT_ERROR}"
            )
        super().__init__(message)


def check_sdk_available() -> None:
    """Raise SdkNotAvailableError if SDK is not installed."""
    if not SDK_AVAILABLE:
        raise SdkNotAvailableError()


class SdkOntologyClient(IOntologyClient):
    """
    SDK-based implementation of the ontology client interface.
    
    This client wraps the Microsoft Fabric Ontology SDK to provide
    ontology operations through a strongly-typed API.
    
    Features:
    - Strongly typed models from SDK
    - Built-in retry and error handling from SDK
    - Native async support (future)
    - Automatic credential management
    
    Note:
        Requires the Microsoft Fabric SDK to be installed.
        Currently the SDK is not yet available - this implementation
        is prepared for when it becomes available.
    
    Example:
        >>> config = FabricConfig(workspace_id="...")
        >>> client = SdkOntologyClient(config)
        >>> ontologies = client.list_ontologies()
    """
    
    def __init__(self, config: 'FabricConfig'):
        """
        Initialize the SDK-based ontology client.
        
        Args:
            config: FabricConfig instance with connection details
            
        Raises:
            SdkNotAvailableError: If the Fabric SDK is not installed
            ValueError: If config is invalid
        """
        check_sdk_available()
        
        if not config:
            raise ValueError("config cannot be None")
        
        if not config.workspace_id:
            raise ValueError("workspace_id is required in configuration")
        
        self.config = config
        self._client: Optional[Any] = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize the underlying SDK client."""
        from azure.identity import DefaultAzureCredential
        
        logger.info("Initializing Fabric Ontology SDK client")
        
        # Create credential based on config
        if self.config.client_id and self.config.client_secret and self.config.tenant_id:
            from azure.identity import ClientSecretCredential
            credential = ClientSecretCredential(
                tenant_id=self.config.tenant_id,
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
            )
            logger.info("Using client secret credential")
        else:
            credential = DefaultAzureCredential()
            logger.info("Using default Azure credential")
        
        # Initialize SDK client
        # Note: Adjust constructor parameters based on actual SDK API
        self._client = FabricSdkClient(
            credential=credential,
            workspace_id=self.config.workspace_id,
            # base_url=self.config.api_base_url,  # if supported
        )
        
        logger.info(f"SDK client initialized for workspace: {self.config.workspace_id}")
    
    def _ensure_client(self) -> Any:
        """Ensure client is initialized and return it."""
        if self._client is None:
            self._initialize_client()
        return self._client
    
    # -------------------------------------------------------------------------
    # Ontology CRUD Operations
    # -------------------------------------------------------------------------
    
    def list_ontologies(self) -> List[Dict[str, Any]]:
        """
        List all ontologies in the workspace.
        
        Returns:
            List of ontology dictionaries
        """
        client = self._ensure_client()
        logger.info("Listing ontologies via SDK")
        
        # SDK call - adjust based on actual SDK API
        ontologies = client.ontologies.list()
        
        # Convert SDK models to dictionaries
        result = []
        for ontology in ontologies:
            result.append(self._ontology_to_dict(ontology))
        
        logger.info(f"Found {len(result)} ontologies")
        return result
    
    def get_ontology(self, ontology_id: str) -> Dict[str, Any]:
        """
        Get details of a specific ontology.
        
        Args:
            ontology_id: The ontology ID
            
        Returns:
            Ontology object dictionary
        """
        client = self._ensure_client()
        logger.info(f"Getting ontology via SDK: {ontology_id}")
        
        # SDK call
        ontology = client.ontologies.get(ontology_id)
        
        return self._ontology_to_dict(ontology)
    
    def create_ontology(
        self,
        display_name: str,
        description: str = "",
        definition: Optional[Dict[str, Any]] = None,
        wait_for_completion: bool = True,
        cancellation_token: Optional['CancellationToken'] = None,
    ) -> Dict[str, Any]:
        """
        Create a new ontology.
        
        Args:
            display_name: The ontology display name
            description: The ontology description
            definition: Optional ontology definition with parts
            wait_for_completion: Whether to wait for operation to complete
            cancellation_token: Optional token for cancellation support
            
        Returns:
            Created ontology object
        """
        client = self._ensure_client()
        logger.info(f"Creating ontology via SDK: {display_name}")
        
        # Check cancellation
        if cancellation_token:
            cancellation_token.throw_if_cancelled("create ontology")
        
        # Convert definition if provided
        sdk_definition = None
        if definition:
            sdk_definition = self._dict_to_definition(definition)
        
        # SDK call - adjust based on actual SDK API
        # The SDK likely handles LRO internally
        ontology = client.ontologies.create(
            display_name=display_name,
            description=description,
            definition=sdk_definition,
        )
        
        # If SDK returns a poller for LRO, handle it
        if hasattr(ontology, 'result') and wait_for_completion:
            logger.info("Waiting for create operation to complete...")
            ontology = ontology.result()
        
        logger.info(f"Ontology created: {getattr(ontology, 'id', 'Unknown')}")
        return self._ontology_to_dict(ontology)
    
    def update_ontology(
        self,
        ontology_id: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update ontology properties.
        
        Args:
            ontology_id: The ontology ID
            display_name: New display name (optional)
            description: New description (optional)
            
        Returns:
            Updated ontology object
        """
        client = self._ensure_client()
        logger.info(f"Updating ontology via SDK: {ontology_id}")
        
        # SDK call - adjust based on actual SDK API
        ontology = client.ontologies.update(
            ontology_id=ontology_id,
            display_name=display_name,
            description=description,
        )
        
        return self._ontology_to_dict(ontology)
    
    def delete_ontology(self, ontology_id: str) -> None:
        """
        Delete an ontology.
        
        Args:
            ontology_id: The ontology ID
        """
        client = self._ensure_client()
        logger.info(f"Deleting ontology via SDK: {ontology_id}")
        
        # SDK call
        client.ontologies.delete(ontology_id)
        
        logger.info(f"Ontology deleted: {ontology_id}")
    
    # -------------------------------------------------------------------------
    # Definition Operations
    # -------------------------------------------------------------------------
    
    def get_ontology_definition(self, ontology_id: str) -> Dict[str, Any]:
        """
        Get the definition of a specific ontology.
        
        Args:
            ontology_id: The ontology ID
            
        Returns:
            Ontology definition object with 'parts'
        """
        client = self._ensure_client()
        logger.info(f"Getting ontology definition via SDK: {ontology_id}")
        
        # SDK call
        definition = client.ontologies.get_definition(ontology_id)
        
        return self._definition_to_dict(definition)
    
    def update_ontology_definition(
        self,
        ontology_id: str,
        definition: Dict[str, Any],
        update_metadata: bool = True,
        wait_for_completion: bool = True,
        cancellation_token: Optional['CancellationToken'] = None,
    ) -> Dict[str, Any]:
        """
        Update the definition of an existing ontology.
        
        Args:
            ontology_id: The ontology ID
            definition: The new ontology definition
            update_metadata: Whether to update metadata
            wait_for_completion: Whether to wait for operation
            cancellation_token: Optional cancellation token
            
        Returns:
            Updated definition or operation result
        """
        client = self._ensure_client()
        logger.info(f"Updating ontology definition via SDK: {ontology_id}")
        
        # Check cancellation
        if cancellation_token:
            cancellation_token.throw_if_cancelled("update ontology definition")
        
        # Convert to SDK format
        sdk_definition = self._dict_to_definition(definition)
        
        # SDK call
        result = client.ontologies.update_definition(
            ontology_id=ontology_id,
            definition=sdk_definition,
            update_metadata=update_metadata,
        )
        
        # Handle LRO if needed
        if hasattr(result, 'result') and wait_for_completion:
            logger.info("Waiting for update operation to complete...")
            result = result.result()
        
        logger.info("Ontology definition updated successfully")
        
        # Return as dict if it's an SDK model, otherwise return as-is
        if hasattr(result, 'as_dict'):
            return result.as_dict()
        return result if isinstance(result, dict) else {}
    
    # -------------------------------------------------------------------------
    # Convenience Methods
    # -------------------------------------------------------------------------
    
    def find_ontology_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find an ontology by its display name.
        
        Args:
            name: The ontology display name
            
        Returns:
            Ontology object if found, None otherwise
        """
        ontologies = self.list_ontologies()
        
        for ontology in ontologies:
            if ontology.get('displayName') == name:
                return ontology
        
        return None
    
    def create_or_update_ontology(
        self,
        display_name: str,
        description: str = "",
        definition: Optional[Dict[str, Any]] = None,
        wait_for_completion: bool = True,
        cancellation_token: Optional['CancellationToken'] = None,
    ) -> Dict[str, Any]:
        """
        Create a new ontology or update an existing one.
        
        Args:
            display_name: The ontology display name
            description: The ontology description
            definition: Optional ontology definition
            wait_for_completion: Whether to wait for operation
            cancellation_token: Optional cancellation token
            
        Returns:
            Created or updated ontology object
        """
        # Check cancellation
        if cancellation_token:
            cancellation_token.throw_if_cancelled("create or update ontology")
        
        # Check if ontology exists
        existing = self.find_ontology_by_name(display_name)
        
        if existing:
            logger.info(f"Ontology '{display_name}' exists. Updating...")
            ontology_id = existing['id']
            
            # Update definition if provided
            if definition:
                self.update_ontology_definition(
                    ontology_id=ontology_id,
                    definition=definition,
                    wait_for_completion=wait_for_completion,
                    cancellation_token=cancellation_token,
                )
            
            # Update properties if description changed
            if description != existing.get('description', ''):
                self.update_ontology(
                    ontology_id=ontology_id,
                    description=description,
                )
            
            return self.get_ontology(ontology_id)
        else:
            logger.info(f"Ontology '{display_name}' does not exist. Creating...")
            return self.create_ontology(
                display_name=display_name,
                description=description,
                definition=definition,
                wait_for_completion=wait_for_completion,
                cancellation_token=cancellation_token,
            )
    
    # -------------------------------------------------------------------------
    # Status and Monitoring
    # -------------------------------------------------------------------------
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """
        Get circuit breaker status.
        
        Note: SDK may handle circuit breaker internally.
        
        Returns:
            Circuit breaker status (SDK-managed)
        """
        return {
            'enabled': False,
            'state': 'SDK_MANAGED',
            'message': 'Circuit breaker is managed internally by the SDK',
        }
    
    def get_rate_limit_statistics(self) -> Dict[str, Any]:
        """
        Get rate limit statistics.
        
        Note: SDK may handle rate limiting internally.
        
        Returns:
            Rate limit statistics (SDK-managed)
        """
        return {
            'enabled': False,
            'state': 'SDK_MANAGED',
            'message': 'Rate limiting is managed internally by the SDK',
        }
    
    def reset_circuit_breaker(self) -> bool:
        """
        Reset circuit breaker.
        
        Note: Not applicable for SDK client.
        
        Returns:
            False (SDK manages this internally)
        """
        logger.warning("Circuit breaker reset not supported for SDK client")
        return False
    
    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    
    @staticmethod
    def _ontology_to_dict(ontology: Any) -> Dict[str, Any]:
        """
        Convert SDK Ontology model to dictionary.
        
        Args:
            ontology: SDK Ontology model instance
            
        Returns:
            Dictionary representation
        """
        # If SDK model has as_dict method, use it
        if hasattr(ontology, 'as_dict'):
            return ontology.as_dict()
        
        # Otherwise, manually extract properties
        return {
            'id': getattr(ontology, 'id', ''),
            'displayName': getattr(ontology, 'display_name', getattr(ontology, 'displayName', '')),
            'description': getattr(ontology, 'description', ''),
            'workspaceId': getattr(ontology, 'workspace_id', getattr(ontology, 'workspaceId', '')),
        }
    
    @staticmethod
    def _definition_to_dict(definition: Any) -> Dict[str, Any]:
        """
        Convert SDK OntologyDefinition model to dictionary.
        
        Args:
            definition: SDK OntologyDefinition model instance
            
        Returns:
            Dictionary with 'parts' key
        """
        if hasattr(definition, 'as_dict'):
            return definition.as_dict()
        
        return {
            'parts': getattr(definition, 'parts', []),
        }
    
    @staticmethod
    def _dict_to_definition(definition_dict: Dict[str, Any]) -> Any:
        """
        Convert dictionary to SDK OntologyDefinition model.
        
        Args:
            definition_dict: Dictionary with 'parts' key
            
        Returns:
            SDK OntologyDefinition model instance
        """
        if not SDK_AVAILABLE or SdkOntologyDefinition is None:
            # Return dict as-is if SDK not available
            return definition_dict
        
        # Create SDK model from dict
        # Adjust based on actual SDK API
        return SdkOntologyDefinition(
            parts=definition_dict.get('parts', [])
        )


def is_sdk_available() -> bool:
    """
    Check if the Microsoft Fabric SDK is available.
    
    Returns:
        True if SDK is installed and importable, False otherwise
    """
    return SDK_AVAILABLE


def get_sdk_import_error() -> Optional[str]:
    """
    Get the SDK import error message if SDK is not available.
    
    Returns:
        Error message string, or None if SDK is available
    """
    return SDK_IMPORT_ERROR


__all__ = [
    'SdkOntologyClient',
    'SdkNotAvailableError',
    'is_sdk_available',
    'get_sdk_import_error',
    'check_sdk_available',
]
