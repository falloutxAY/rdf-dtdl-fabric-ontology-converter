"""Platform-level services for talking to Microsoft Fabric.

This module provides:
- FabricOntologyClient: Legacy client with rate limiting and circuit breaker
- SDKClientAdapter: Adapter for the official Fabric Ontology SDK
- create_client: Factory that selects SDK or legacy based on feature flag

Migration:
    Set FABRIC_USE_SDK=true environment variable to use SDK instead of legacy client.
    Or use create_client(config, use_sdk=True) explicitly.
"""

# Legacy client exports (existing functionality)
from .fabric_client import (
    FabricConfig,
    FabricOntologyClient,
    FabricAPIError,
    TransientAPIError,
    RateLimitConfig,
    CircuitBreakerSettings,
)

from .auth import (
    TokenManager,
    CredentialFactory,
    FABRIC_SCOPE,
)

from .http import (
    RequestHandler,
    ResponseHandler,
)

# SDK adapter exports (new SDK integration)
from .sdk_adapter import (
    SDKClientAdapter,
    SDKConfig,
    create_sdk_client,
    create_client,
    is_sdk_available,
    USE_SDK,
)

__all__ = [
    # Legacy client
    "FabricConfig",
    "FabricOntologyClient",
    "FabricAPIError",
    "TransientAPIError",
    "RateLimitConfig",
    "CircuitBreakerSettings",
    # Auth
    "TokenManager",
    "CredentialFactory",
    "FABRIC_SCOPE",
    # HTTP
    "RequestHandler",
    "ResponseHandler",
    # SDK adapter
    "SDKClientAdapter",
    "SDKConfig",
    "create_sdk_client",
    "create_client",
    "is_sdk_available",
    "USE_SDK",
]
