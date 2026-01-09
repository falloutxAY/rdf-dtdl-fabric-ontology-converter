# Refactor Research: Ontology v0.5 API SDK for RDF DTDL Ontology Converter

## Overview

This document researches the feasibility and approach for refactoring the **RDF DTDL Ontology Converter** to leverage the **Microsoft Fabric Ontology v0.5 API SDK** instead of direct REST API calls.

## Current Architecture

### Existing Implementation

The converter currently uses a custom `FabricOntologyClient` class that:

1. **Direct REST API Integration** ([fabric_client.py](src/core/platform/fabric_client.py))
   - Manual HTTP request handling via `requests` library
   - Custom authentication with `azure-identity` credentials
   - Token caching with thread-safe locking
   - Rate limiting via custom `TokenBucketRateLimiter`
   - Circuit breaker pattern for fault tolerance

2. **API Endpoints Used**
   - `POST /workspaces/{workspaceId}/ontologies` - Create ontology
   - `GET /workspaces/{workspaceId}/ontologies` - List ontologies
   - `GET /workspaces/{workspaceId}/ontologies/{ontologyId}` - Get ontology
   - `PATCH /workspaces/{workspaceId}/ontologies/{ontologyId}/definition` - Update definition
   - `DELETE /workspaces/{workspaceId}/ontologies/{ontologyId}` - Delete ontology

3. **Supporting Infrastructure**
   - Long-running operation (LRO) handling
   - Retry logic with tenacity
   - Error handling and logging

## Ontology v0.5 API SDK Research

### SDK Benefits

| Feature | Current (REST) | SDK v0.5 |
|---------|----------------|----------|
| Authentication | Manual token management | Built-in credential handling |
| Retry Logic | Custom tenacity wrapper | Native retry policies |
| Rate Limiting | Custom token bucket | SDK-managed throttling |
| Type Safety | Dictionary-based | Strongly typed models |
| Error Handling | HTTP status parsing | Typed exceptions |
| Async Support | Manual threading | Native async/await |
| Pagination | Manual implementation | Built-in iterators |

### SDK Installation

```bash
# Expected package name (verify availability)
pip install azure-fabric-ontology
# or
pip install microsoft-fabric-sdk
```

### Expected SDK Structure

```python
from azure.fabric.ontology import OntologyClient
from azure.fabric.ontology.models import (
    Ontology,
    OntologyDefinition,
    EntityType,
    RelationshipType,
    Property
)
from azure.identity import DefaultAzureCredential

# Client initialization
credential = DefaultAzureCredential()
client = OntologyClient(
    credential=credential,
    workspace_id="<workspace-id>"
)

# Operations
ontology = client.ontologies.create(
    display_name="MyOntology",
    description="..."
)

client.ontologies.update_definition(
    ontology_id=ontology.id,
    definition=OntologyDefinition(
        entity_types=[...],
        relationship_types=[...]
    )
)
```

## Refactoring Strategy

### Phase 1: SDK Integration Layer ✅ COMPLETED

**Status:** Implemented on January 8, 2026

Created an abstraction layer that can switch between REST and SDK implementations:

**Files Created/Modified:**
- [ontology_client_interface.py](src/core/platform/ontology_client_interface.py) - Abstract interface
- [client_factory.py](src/core/platform/client_factory.py) - Factory for client creation
- [fabric_client.py](src/core/platform/fabric_client.py) - Updated to implement interface
- [config.sample.json](config.sample.json) - Added `client_type` field

**Usage:**
```python
from src.core.platform import create_ontology_client, ClientType
from src.core.platform.fabric_client import FabricConfig

config = FabricConfig.from_file("config.json")

# Create REST client (default)
client = create_ontology_client(config, ClientType.REST)

# List ontologies using the interface
ontologies = client.list_ontologies()
```

**Interface Definition:**
```python
# src/core/platform/ontology_client_interface.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class IOntologyClient(ABC):
    """Abstract interface for ontology operations."""
    
    @abstractmethod
    def create_ontology(self, name: str, description: str = "") -> Dict[str, Any]:
        """Create a new ontology."""
        pass
    
    @abstractmethod
    def get_ontology(self, ontology_id: str) -> Dict[str, Any]:
        """Get ontology by ID."""
        pass
    
    @abstractmethod
    def list_ontologies(self) -> List[Dict[str, Any]]:
        """List all ontologies in workspace."""
        pass
    
    @abstractmethod
    def update_definition(
        self, 
        ontology_id: str, 
        entity_types: List[Dict], 
        relationship_types: List[Dict]
    ) -> Dict[str, Any]:
        """Update ontology definition."""
        pass
    
    @abstractmethod
    def delete_ontology(self, ontology_id: str) -> bool:
        """Delete an ontology."""
        pass
```

### Phase 2: SDK Implementation ✅ COMPLETED

**Status:** Implemented on January 8, 2026

Created the SDK-based client implementation that will wrap the Microsoft Fabric SDK when it becomes available.

**Files Created:**
- [sdk_client.py](src/core/platform/sdk_client.py) - `SdkOntologyClient` implementing `IOntologyClient`

**Files Modified:**
- [client_factory.py](src/core/platform/client_factory.py) - Updated to use SDK client when available
- [src/core/platform/__init__.py](src/core/platform/__init__.py) - Export SDK utilities
- [src/core/__init__.py](src/core/__init__.py) - Export SDK utilities at package level

**Key Features:**
- Full `IOntologyClient` interface implementation
- Graceful handling when SDK is not installed
- `is_sdk_available()` function to check SDK availability
- `SdkNotAvailableError` for clear error messages
- Ready for SDK integration when package is released

**Usage (when SDK is available):**
```python
from src.core.platform import create_ontology_client, ClientType, is_sdk_available
from src.core.platform.fabric_client import FabricConfig

config = FabricConfig.from_file("config.json")

# Check if SDK is available
if is_sdk_available():
    client = create_ontology_client(config, ClientType.SDK)
else:
    client = create_ontology_client(config, ClientType.REST)

ontologies = client.list_ontologies()
```

**SDK Client Structure:**
```python
# src/core/platform/sdk_client.py
from azure.fabric.ontology import OntologyClient as SdkClient
from azure.identity import DefaultAzureCredential

class SdkOntologyClient(IOntologyClient):
    """SDK-based implementation of ontology client."""
    
    def __init__(self, config: FabricConfig):
        self._client = SdkClient(
            credential=DefaultAzureCredential(),
            workspace_id=config.workspace_id
        )
    
    def create_ontology(self, name: str, description: str = "") -> Dict[str, Any]:
        result = self._client.ontologies.create(
            display_name=name,
            description=description
        )
        return result.as_dict()
    
    # ... all IOntologyClient methods implemented
```

### Phase 3: Factory Pattern for Client Selection ✅ COMPLETED (in Phase 1)

The factory pattern was implemented as part of Phase 1. The `create_ontology_client()` function now supports both REST and SDK clients:

```python
# src/core/platform/client_factory.py
from enum import Enum

class ClientType(Enum):
    REST = "rest"
    SDK = "sdk"

def create_ontology_client(
    config: FabricConfig, 
    client_type: ClientType = ClientType.REST
) -> IOntologyClient:
    """Factory for creating ontology clients."""
    if client_type == ClientType.SDK:
        return SdkOntologyClient(config)

    else:
        return FabricOntologyClient(config)  # Existing REST client
```

## Migration Checklist

### Pre-Migration Tasks

- [ ] Verify SDK availability and version compatibility
- [ ] Review SDK documentation for API coverage
- [ ] Identify SDK feature gaps vs current implementation
- [ ] Plan backward compatibility strategy

### Code Changes

| File | Change Required |
|------|-----------------|
| `fabric_client.py` | Rename to `rest_client.py`, implement interface |
| `client_factory.py` | New file - factory pattern |
| `sdk_client.py` | New file - SDK wrapper |
| `ontology_client_interface.py` | New file - abstract interface |
| `config.json` | Add `client_type` option |
| Unit tests | Add SDK client tests |
| Integration tests | Test both client types |

### Configuration Updates

```json
{
  "fabric": {
    "workspace_id": "...",
    "client_type": "sdk",  // or "rest"
    "api_base_url": "https://api.fabric.microsoft.com/v1",
    "rate_limit": {
      "enabled": true,
      "requests_per_minute": 10
    }
  }
}
```

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| SDK not GA | High | Keep REST client as fallback |
| API version mismatch | Medium | Version pinning in requirements |
| Feature gaps in SDK | Medium | Use REST for missing features |
| Breaking changes | High | Interface abstraction layer |
| Performance differences | Low | Benchmark both implementations |

## Recommendations

1. **Phased Approach**: Implement abstraction layer first, then SDK client
2. **Feature Parity**: Ensure SDK supports all required operations before full migration
3. **Dual Support**: Maintain both REST and SDK clients initially
4. **Configuration Toggle**: Allow switching via config without code changes
5. **Comprehensive Testing**: Integration tests for both client types

## Next Steps

1. [ ] Confirm SDK package availability and installation
2. [ ] Create interface abstraction (`IOntologyClient`)
3. [ ] Refactor existing `FabricOntologyClient` to implement interface
4. [ ] Implement `SdkOntologyClient` wrapper
5. [ ] Create factory for client selection
6. [ ] Update configuration schema
7. [ ] Add integration tests
8. [ ] Update documentation

## References

- [Microsoft Fabric REST API - Ontology](https://learn.microsoft.com/rest/api/fabric/ontology/items)
- [Azure SDK Design Guidelines](https://azure.github.io/azure-sdk/python_design.html)
- [Fabric API Throttling](https://learn.microsoft.com/en-us/rest/api/fabric/articles/throttling)
- Current Implementation: [fabric_client.py](src/core/platform/fabric_client.py)
