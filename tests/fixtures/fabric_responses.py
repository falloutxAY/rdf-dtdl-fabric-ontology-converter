"""
Validated Fabric API Response Fixtures

Mock responses validated against Microsoft Fabric Ontology API documentation.
These fixtures ensure tests use realistic API response structures.

Documentation sources:
- https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/list-ontologies
- https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/get-ontology
- https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/create-ontology
- https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/update-ontology-definition
- https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/delete-ontology

Usage:
    from tests.fixtures.fabric_responses import (
        create_ontology_response,
        create_list_response,
        create_error_response,
        create_lro_response,
        SAMPLE_WORKSPACE_ID,
    )
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid

# =============================================================================
# Sample IDs for Testing
# =============================================================================

# Well-formed GUIDs for testing
SAMPLE_WORKSPACE_ID = "cfafbeb1-8037-4d0c-896e-a46fb27ff229"
SAMPLE_ONTOLOGY_ID = "5b218778-e7a5-4d73-8187-f10824047715"
SAMPLE_ONTOLOGY_ID_2 = "3546052c-ae64-4526-b1a8-52af7761426f"
SAMPLE_OPERATION_ID = "0acd697c-1550-43cd-b998-91bfbfbd47c6"
SAMPLE_TENANT_ID = "72f988bf-86f1-41af-91ab-2d7cd011db47"

# API URLs
API_BASE_URL = "https://api.fabric.microsoft.com/v1"


# =============================================================================
# Ontology Response Factories
# =============================================================================

def create_ontology_response(
    ontology_id: str = SAMPLE_ONTOLOGY_ID,
    display_name: str = "TestOntology",
    description: str = "A test ontology",
    workspace_id: str = SAMPLE_WORKSPACE_ID,
    created_datetime: Optional[str] = None,
    modified_datetime: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create an ontology response matching Fabric API specification.
    
    Response structure validated against:
    https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/get-ontology
    
    Args:
        ontology_id: The ontology's unique identifier (GUID)
        display_name: Display name of the ontology
        description: Description of the ontology
        workspace_id: The workspace ID containing this ontology
        created_datetime: ISO 8601 creation timestamp
        modified_datetime: ISO 8601 modification timestamp
        
    Returns:
        Dict matching the Fabric API Ontology response schema
    """
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    return {
        "id": ontology_id,
        "displayName": display_name,
        "description": description,
        "type": "Ontology",
        "workspaceId": workspace_id,
        "createdDateTime": created_datetime or now,
        "modifiedDateTime": modified_datetime or now,
    }


def create_list_response(
    ontologies: Optional[List[Dict[str, Any]]] = None,
    continuation_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a list ontologies response matching Fabric API specification.
    
    Response structure validated against:
    https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/list-ontologies
    
    Args:
        ontologies: List of ontology objects. If None, creates a sample list.
        continuation_token: Optional token for pagination.
        
    Returns:
        Dict matching the Fabric API list response schema
    """
    if ontologies is None:
        ontologies = [
            create_ontology_response(
                ontology_id=SAMPLE_ONTOLOGY_ID,
                display_name="Ontology1",
            ),
            create_ontology_response(
                ontology_id=SAMPLE_ONTOLOGY_ID_2,
                display_name="Ontology2",
            ),
        ]
    
    response = {"value": ontologies}
    
    if continuation_token:
        response["continuationToken"] = continuation_token
    
    return response


def create_error_response(
    error_code: str,
    message: str,
    request_id: Optional[str] = None,
    more_details: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Create an error response matching Fabric API specification.
    
    Error codes from Fabric API:
    - Unauthorized: Missing or invalid authentication
    - ItemNotFound: Requested resource doesn't exist
    - ItemDisplayNameAlreadyInUse: Duplicate name conflict
    - CorruptedPayload: Invalid request body
    - TooManyRequests: Rate limit exceeded
    - InternalServerError: Server-side error
    
    Args:
        error_code: The error code (e.g., "ItemNotFound")
        message: Human-readable error message
        request_id: Optional request tracking ID
        more_details: Optional list of additional error details
        
    Returns:
        Dict matching the Fabric API error response schema
    """
    response = {
        "errorCode": error_code,
        "message": message,
    }
    
    if request_id:
        response["requestId"] = request_id
    else:
        response["requestId"] = str(uuid.uuid4())
    
    if more_details:
        response["moreDetails"] = more_details
    
    return response


def create_lro_response(
    status: str,
    percent_complete: int = 0,
    error: Optional[Dict[str, str]] = None,
    created_time: Optional[str] = None,
    last_updated_time: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a Long-Running Operation status response.
    
    LRO status values:
    - NotStarted: Operation queued but not started
    - Running: Operation in progress
    - Succeeded: Operation completed successfully
    - Failed: Operation failed
    
    Args:
        status: Operation status (NotStarted, Running, Succeeded, Failed)
        percent_complete: Progress percentage (0-100)
        error: Optional error details if status is Failed
        created_time: ISO 8601 timestamp when operation was created
        last_updated_time: ISO 8601 timestamp of last status update
        
    Returns:
        Dict matching the Fabric API LRO status response schema
    """
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    response = {
        "status": status,
        "percentComplete": percent_complete,
        "createdTimeUtc": created_time or now,
        "lastUpdatedTimeUtc": last_updated_time or now,
    }
    
    if error:
        response["error"] = error
    
    return response


def create_lro_headers(
    operation_id: str = SAMPLE_OPERATION_ID,
    location: Optional[str] = None,
    retry_after: int = 30,
) -> Dict[str, str]:
    """
    Create response headers for a 202 Accepted (LRO) response.
    
    Args:
        operation_id: The operation tracking ID
        location: URL to poll for status. If None, generates from IDs.
        retry_after: Suggested seconds to wait before polling
        
    Returns:
        Dict of response headers for LRO
    """
    if location is None:
        location = (
            f"{API_BASE_URL}/workspaces/{SAMPLE_WORKSPACE_ID}"
            f"/ontologies/{SAMPLE_ONTOLOGY_ID}"
        )
    
    return {
        "Location": location,
        "x-ms-operation-id": operation_id,
        "Retry-After": str(retry_after),
    }


# =============================================================================
# Common Error Responses
# =============================================================================

ERROR_UNAUTHORIZED = create_error_response(
    error_code="Unauthorized",
    message="The caller does not have permission to perform this operation.",
)

ERROR_NOT_FOUND = create_error_response(
    error_code="ItemNotFound",
    message="The requested item was not found in the workspace.",
)

ERROR_CONFLICT = create_error_response(
    error_code="ItemDisplayNameAlreadyInUse",
    message="An item with the same display name already exists in the workspace.",
)

ERROR_BAD_REQUEST = create_error_response(
    error_code="CorruptedPayload",
    message="The request payload is corrupted or invalid.",
)

ERROR_RATE_LIMITED = create_error_response(
    error_code="TooManyRequests",
    message="Rate limit exceeded. Please retry after the specified time.",
)

ERROR_SERVER = create_error_response(
    error_code="InternalServerError",
    message="An internal server error occurred. Please try again later.",
)


# =============================================================================
# Sample Definition Parts
# =============================================================================

def create_sample_definition(
    entity_count: int = 2,
    relationship_count: int = 1,
    id_prefix: int = 1000000000000,
) -> Dict[str, Any]:
    """
    Create a sample ontology definition with valid structure.
    
    This creates a minimal but valid definition that can be used
    for upload testing.
    
    Args:
        entity_count: Number of entity types to create
        relationship_count: Number of relationships to create
        id_prefix: Starting ID for generated entities
        
    Returns:
        Dict with 'parts' array matching Fabric definition schema
    """
    import base64
    import json
    
    parts = []
    
    # Add .platform metadata
    platform_data = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/platformProperties.json",
        "config": {
            "version": "1.0",
            "type": "Ontology"
        }
    }
    parts.append({
        "path": ".platform",
        "payload": base64.b64encode(json.dumps(platform_data).encode()).decode(),
        "payloadType": "InlineBase64"
    })
    
    # Add definition.json
    definition_json = {
        "version": "1.0",
        "formatVersion": "1.0"
    }
    parts.append({
        "path": "definition.json",
        "payload": base64.b64encode(json.dumps(definition_json).encode()).decode(),
        "payloadType": "InlineBase64"
    })
    
    # Generate entity types
    entity_ids = []
    for i in range(entity_count):
        entity_id = str(id_prefix + i)
        entity_ids.append(entity_id)
        
        entity_data = {
            "id": entity_id,
            "namespace": "usertypes",
            "name": f"Entity{i+1}",
            "displayName": f"Entity {i+1}",
            "description": f"Test entity {i+1}",
            "namespaceType": "Custom",
            "visibility": "Visible",
            "properties": [
                {
                    "id": str(id_prefix + 1000 + i),
                    "name": "name",
                    "displayName": "Name",
                    "valueType": "String",
                }
            ]
        }
        
        parts.append({
            "path": f"EntityTypes/{entity_data['name']}.json",
            "payload": base64.b64encode(json.dumps(entity_data).encode()).decode(),
            "payloadType": "InlineBase64"
        })
    
    # Generate relationships
    for i in range(min(relationship_count, len(entity_ids) - 1)):
        rel_id = str(id_prefix + 2000 + i)
        
        rel_data = {
            "id": rel_id,
            "namespace": "usertypes",
            "name": f"relatesTo{i+1}",
            "displayName": f"Relates To {i+1}",
            "namespaceType": "Custom",
            "source": {
                "entityTypeId": entity_ids[i]
            },
            "target": {
                "entityTypeId": entity_ids[(i + 1) % len(entity_ids)]
            }
        }
        
        parts.append({
            "path": f"RelationshipTypes/{rel_data['name']}.json",
            "payload": base64.b64encode(json.dumps(rel_data).encode()).decode(),
            "payloadType": "InlineBase64"
        })
    
    return {"parts": parts}


# =============================================================================
# HTTP Status Code Reference
# =============================================================================

HTTP_STATUS = {
    200: "OK",
    201: "Created",
    202: "Accepted (LRO)",
    204: "No Content",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    429: "Too Many Requests",
    500: "Internal Server Error",
    503: "Service Unavailable",
}
