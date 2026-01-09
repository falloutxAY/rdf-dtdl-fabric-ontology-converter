"""
Abstract interface for Ontology API clients.

This module defines the contract for ontology operations, enabling
multiple implementations (REST API, SDK) to be used interchangeably.

The interface supports:
- CRUD operations on ontologies
- Definition management (entity types, relationship types)
- Cancellation support for long-running operations
- Circuit breaker and rate limiting status

Example:
    >>> from src.core.platform import create_ontology_client, ClientType
    >>> client = create_ontology_client(config, ClientType.REST)
    >>> ontologies = client.list_ontologies()
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

# Import CancellationToken type for type hints
from ..cancellation import CancellationToken


class ClientType(Enum):
    """Supported ontology client implementations."""
    REST = "rest"
    SDK = "sdk"


@dataclass
class OntologyInfo:
    """Basic ontology information."""
    id: str
    display_name: str
    description: str = ""
    workspace_id: str = ""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OntologyInfo':
        """Create from API response dictionary."""
        return cls(
            id=data.get('id', ''),
            display_name=data.get('displayName', ''),
            description=data.get('description', ''),
            workspace_id=data.get('workspaceId', ''),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'displayName': self.display_name,
            'description': self.description,
            'workspaceId': self.workspace_id,
        }


@dataclass
class OntologyDefinition:
    """Ontology definition containing entity and relationship types."""
    parts: List[Dict[str, Any]]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OntologyDefinition':
        """Create from API response dictionary."""
        return cls(parts=data.get('parts', []))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API requests."""
        return {'parts': self.parts}
    
    @property
    def entity_types(self) -> List[Dict[str, Any]]:
        """Extract entity types from parts."""
        return [
            p.get('part', {}) for p in self.parts 
            if p.get('path', '').endswith('.entityType.json')
        ]
    
    @property
    def relationship_types(self) -> List[Dict[str, Any]]:
        """Extract relationship types from parts."""
        return [
            p.get('part', {}) for p in self.parts 
            if p.get('path', '').endswith('.relationshipType.json')
        ]


class IOntologyClient(ABC):
    """
    Abstract interface for ontology operations.
    
    This interface defines the contract for interacting with ontology storage,
    whether through direct REST API calls or an SDK. Implementations must
    provide all abstract methods.
    
    Features:
    - Full CRUD operations for ontologies
    - Definition management (entity types, relationship types)
    - Cancellation support for long-running operations
    - Status reporting for circuit breaker and rate limiting
    
    Example:
        >>> class MyClient(IOntologyClient):
        ...     def list_ontologies(self) -> List[Dict[str, Any]]:
        ...         return [...]  # implementation
    """
    
    # -------------------------------------------------------------------------
    # Ontology CRUD Operations
    # -------------------------------------------------------------------------
    
    @abstractmethod
    def list_ontologies(self) -> List[Dict[str, Any]]:
        """
        List all ontologies in the workspace.
        
        Returns:
            List of ontology dictionaries with keys:
            - id: Ontology ID
            - displayName: Display name
            - description: Description
            - workspaceId: Workspace ID
            
        Raises:
            FabricAPIError: On API failure
        """
        pass
    
    @abstractmethod
    def get_ontology(self, ontology_id: str) -> Dict[str, Any]:
        """
        Get details of a specific ontology.
        
        Args:
            ontology_id: The ontology ID
            
        Returns:
            Ontology object dictionary
            
        Raises:
            FabricAPIError: On API failure or if ontology not found
        """
        pass
    
    @abstractmethod
    def create_ontology(
        self,
        display_name: str,
        description: str = "",
        definition: Optional[Dict[str, Any]] = None,
        wait_for_completion: bool = True,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> Dict[str, Any]:
        """
        Create a new ontology.
        
        Args:
            display_name: The ontology display name
            description: The ontology description
            definition: Optional ontology definition with parts
            wait_for_completion: Whether to wait for LRO to complete
            cancellation_token: Optional token for cancellation support
            
        Returns:
            Created ontology object with at least 'id' key
            
        Raises:
            FabricAPIError: On API failure
            OperationCancelledException: If cancellation is requested
        """
        pass
    
    @abstractmethod
    def update_ontology(
        self,
        ontology_id: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update ontology properties (name, description).
        
        Args:
            ontology_id: The ontology ID
            display_name: New display name (optional)
            description: New description (optional)
            
        Returns:
            Updated ontology object
            
        Raises:
            FabricAPIError: On API failure
        """
        pass
    
    @abstractmethod
    def delete_ontology(self, ontology_id: str) -> None:
        """
        Delete an ontology.
        
        Args:
            ontology_id: The ontology ID
            
        Raises:
            FabricAPIError: On API failure
        """
        pass
    
    # -------------------------------------------------------------------------
    # Definition Operations
    # -------------------------------------------------------------------------
    
    @abstractmethod
    def get_ontology_definition(self, ontology_id: str) -> Dict[str, Any]:
        """
        Get the definition of a specific ontology.
        
        Args:
            ontology_id: The ontology ID
            
        Returns:
            Ontology definition object with 'parts' containing 
            entity and relationship types
            
        Raises:
            FabricAPIError: On API failure
        """
        pass
    
    @abstractmethod
    def update_ontology_definition(
        self,
        ontology_id: str,
        definition: Dict[str, Any],
        update_metadata: bool = True,
        wait_for_completion: bool = True,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> Dict[str, Any]:
        """
        Update the definition of an existing ontology.
        
        Args:
            ontology_id: The ontology ID
            definition: The new ontology definition with 'parts' key
            update_metadata: Whether to update metadata from .platform file
            wait_for_completion: Whether to wait for LRO to complete
            cancellation_token: Optional token for cancellation support
            
        Returns:
            Updated ontology object or operation result
            
        Raises:
            FabricAPIError: On API failure
            OperationCancelledException: If cancellation is requested
        """
        pass
    
    # -------------------------------------------------------------------------
    # Convenience Methods
    # -------------------------------------------------------------------------
    
    @abstractmethod
    def find_ontology_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find an ontology by its display name.
        
        Args:
            name: The ontology display name to search for
            
        Returns:
            Ontology object if found, None otherwise
        """
        pass
    
    @abstractmethod
    def create_or_update_ontology(
        self,
        display_name: str,
        description: str = "",
        definition: Optional[Dict[str, Any]] = None,
        wait_for_completion: bool = True,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> Dict[str, Any]:
        """
        Create a new ontology or update an existing one.
        
        This method checks if an ontology with the given name exists:
        - If it exists, updates the definition
        - If it doesn't exist, creates a new one
        
        Args:
            display_name: The ontology display name
            description: The ontology description
            definition: Optional ontology definition with parts
            wait_for_completion: Whether to wait for LRO to complete
            cancellation_token: Optional token for cancellation support
            
        Returns:
            Created or updated ontology object
            
        Raises:
            FabricAPIError: On API failure
            OperationCancelledException: If cancellation is requested
        """
        pass
    
    # -------------------------------------------------------------------------
    # Status and Monitoring
    # -------------------------------------------------------------------------
    
    @abstractmethod
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """
        Get the current circuit breaker status and metrics.
        
        Returns:
            Dictionary with circuit breaker state and metrics:
            - enabled: Whether circuit breaker is enabled
            - state: Current state (CLOSED, OPEN, HALF_OPEN)
            - failure_count: Current failure count
            - time_until_recovery: Seconds until recovery attempt (if OPEN)
        """
        pass
    
    @abstractmethod
    def get_rate_limit_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about rate limiting.
        
        Returns:
            Dictionary with rate limit statistics:
            - rate: Requests allowed per time period
            - current_tokens: Available tokens
            - total_requests: Total requests made
            - times_waited: Number of times rate limit caused waiting
        """
        pass
    
    def reset_circuit_breaker(self) -> bool:
        """
        Manually reset the circuit breaker to CLOSED state.
        
        Default implementation returns False (not supported).
        Override in implementations that support this feature.
        
        Returns:
            True if reset was performed, False otherwise
        """
        return False


__all__ = [
    'ClientType',
    'IOntologyClient',
    'OntologyInfo',
    'OntologyDefinition',
]
