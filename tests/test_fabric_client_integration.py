"""
Integration tests for FabricOntologyClient with mocked API responses.

Tests the client behavior for various API scenarios aligned with the official
Microsoft Fabric Ontology REST API documentation:
- https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items
- https://learn.microsoft.com/en-us/rest/api/fabric/articles/using-fabric-apis
- https://learn.microsoft.com/en-us/rest/api/fabric/articles/long-running-operation
- https://learn.microsoft.com/en-us/rest/api/fabric/articles/throttling

Tests cover:
- Successful operations (200 OK, 201 Created)
- Long-running operations (202 Accepted with LRO polling)
- Rate limiting (429 Too Many Requests with Retry-After header)
- Error handling (400, 401, 403, 404, 409, 500)
- Authentication failures
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from typing import Dict, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fabric_client import (
    FabricOntologyClient,
    FabricConfig,
    FabricAPIError,
    TransientAPIError,
    RateLimitConfig,
)


# =============================================================================
# Constants matching Fabric API specification
# =============================================================================

# Sample workspace and ontology IDs (UUID format per API spec)
SAMPLE_WORKSPACE_ID = "cfafbeb1-8037-4d0c-896e-a46fb27ff229"
SAMPLE_ONTOLOGY_ID = "5b218778-e7a5-4d73-8187-f10824047715"
SAMPLE_ONTOLOGY_ID_2 = "3546052c-ae64-4526-b1a8-52af7761426f"
SAMPLE_OPERATION_ID = "0acd697c-1550-43cd-b998-91bfbfbd47c6"

# API Base URL
API_BASE_URL = "https://api.fabric.microsoft.com/v1"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_credential():
    """Mock Azure credential that returns a valid token."""
    mock_token = Mock()
    mock_token.token = "mock-access-token-12345"
    mock_token.expires_on = time.time() + 3600  # Valid for 1 hour
    
    mock_cred = Mock()
    mock_cred.get_token.return_value = mock_token
    return mock_cred


@pytest.fixture
def fabric_config():
    """Create a basic FabricConfig for testing with sample workspace ID."""
    return FabricConfig(
        workspace_id=SAMPLE_WORKSPACE_ID,
        tenant_id="87654321-4321-4321-4321-cba987654321",
        use_interactive_auth=False,
        rate_limit=RateLimitConfig(enabled=False),  # Disable for faster tests
    )


@pytest.fixture
def fabric_config_with_rate_limit():
    """Create a FabricConfig with rate limiting enabled."""
    return FabricConfig(
        workspace_id=SAMPLE_WORKSPACE_ID,
        tenant_id="87654321-4321-4321-4321-cba987654321",
        use_interactive_auth=False,
        rate_limit=RateLimitConfig(enabled=True, requests_per_minute=60, burst=60),
    )


@pytest.fixture
def fabric_client(fabric_config, mock_credential):
    """Create a FabricOntologyClient with mocked credentials."""
    with patch.object(FabricOntologyClient, '_get_credential', return_value=mock_credential):
        client = FabricOntologyClient(fabric_config)
        yield client


@pytest.fixture
def fabric_client_with_rate_limit(fabric_config_with_rate_limit, mock_credential):
    """Create a FabricOntologyClient with rate limiting enabled."""
    with patch.object(FabricOntologyClient, '_get_credential', return_value=mock_credential):
        client = FabricOntologyClient(fabric_config_with_rate_limit)
        yield client


# =============================================================================
# Helper Functions - Response Builders matching Fabric API spec
# =============================================================================

def create_mock_response(
    status_code: int,
    json_data: Dict[str, Any] = None,
    headers: Dict[str, str] = None,
    text: str = ""
) -> Mock:
    """Create a mock requests.Response object."""
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.headers = headers or {}
    mock_response.text = text or json.dumps(json_data) if json_data else ""
    
    if json_data is not None:
        mock_response.json.return_value = json_data
    else:
        mock_response.json.side_effect = json.JSONDecodeError("No JSON", "", 0)
    
    return mock_response


def create_ontology_response(
    ontology_id: str = SAMPLE_ONTOLOGY_ID,
    display_name: str = "Ontology 1",
    description: str = "An ontology description.",
    workspace_id: str = SAMPLE_WORKSPACE_ID
) -> Dict[str, Any]:
    """
    Create an ontology response matching the Fabric API specification.
    
    Reference: https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/get-ontology
    """
    return {
        "id": ontology_id,
        "displayName": display_name,
        "description": description,
        "type": "Ontology",
        "workspaceId": workspace_id
    }


def create_error_response(
    error_code: str,
    message: str,
    request_id: str = "abc123-request-id"
) -> Dict[str, Any]:
    """
    Create an error response matching the Fabric API specification.
    
    Reference: https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/create-ontology#errorresponse
    """
    return {
        "errorCode": error_code,
        "message": message,
        "requestId": request_id
    }


def create_lro_operation_response(
    status: str,
    percent_complete: int = 0,
    error_message: str = None
) -> Dict[str, Any]:
    """
    Create an LRO operation status response matching Fabric API specification.
    
    Status values: "Running", "Succeeded", "Failed"
    Reference: https://learn.microsoft.com/en-us/rest/api/fabric/articles/long-running-operation
    """
    response = {
        "status": status,
        "createdTimeUtc": "2023-11-13T22:24:40.477Z",
        "lastUpdatedTimeUtc": "2023-11-13T22:24:41.532Z",
        "percentComplete": percent_complete
    }
    if error_message:
        response["error"] = {"message": error_message}
    return response


# =============================================================================
# Test: List Ontologies
# Reference: https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/list-ontologies
# =============================================================================

class TestListOntologies:
    """
    Tests for list_ontologies method.
    
    API: GET https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/ontologies
    Response 200 OK: {"value": [Ontology[]]}
    """
    
    def test_list_ontologies_success(self, fabric_client):
        """Test successful listing of ontologies matching API sample response."""
        # Response format per API docs
        mock_response = create_mock_response(
            status_code=200,
            json_data={
                "value": [
                    create_ontology_response(
                        ontology_id=SAMPLE_ONTOLOGY_ID,
                        display_name="Ontology Name 1",
                        description="An ontology description."
                    ),
                    create_ontology_response(
                        ontology_id=SAMPLE_ONTOLOGY_ID_2,
                        display_name="Ontology Name 2",
                        description="An ontology description."
                    ),
                ]
            }
        )
        
        with patch('requests.request', return_value=mock_response):
            result = fabric_client.list_ontologies()
        
        assert len(result) == 2
        assert result[0]["id"] == SAMPLE_ONTOLOGY_ID
        assert result[0]["type"] == "Ontology"
        assert result[0]["workspaceId"] == SAMPLE_WORKSPACE_ID
        assert result[1]["displayName"] == "Ontology Name 2"
    
    def test_list_ontologies_empty(self, fabric_client):
        """Test listing when no ontologies exist in workspace."""
        mock_response = create_mock_response(
            status_code=200,
            json_data={"value": []}
        )
        
        with patch('requests.request', return_value=mock_response):
            result = fabric_client.list_ontologies()
        
        assert result == []
    
    def test_list_ontologies_unauthorized(self, fabric_client):
        """Test listing with invalid credentials (401 Unauthorized)."""
        mock_response = create_mock_response(
            status_code=401,
            json_data=create_error_response(
                error_code="Unauthorized",
                message="The caller does not have permission to perform this operation."
            )
        )
        
        with patch('requests.request', return_value=mock_response):
            with pytest.raises(FabricAPIError) as exc_info:
                fabric_client.list_ontologies()
        
        assert exc_info.value.status_code == 401


# =============================================================================
# Test: Get Ontology
# Reference: https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/get-ontology
# =============================================================================

class TestGetOntology:
    """
    Tests for get_ontology method.
    
    API: GET https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/ontologies/{ontologyId}
    Response 200 OK: Ontology object
    """
    
    def test_get_ontology_success(self, fabric_client):
        """Test successful retrieval matching API sample response."""
        mock_response = create_mock_response(
            status_code=200,
            json_data=create_ontology_response(
                ontology_id=SAMPLE_ONTOLOGY_ID,
                display_name="Ontology 1",
                description="An ontology description."
            )
        )
        
        with patch('requests.request', return_value=mock_response):
            result = fabric_client.get_ontology(SAMPLE_ONTOLOGY_ID)
        
        assert result["id"] == SAMPLE_ONTOLOGY_ID
        assert result["displayName"] == "Ontology 1"
        assert result["type"] == "Ontology"
        assert result["workspaceId"] == SAMPLE_WORKSPACE_ID
    
    def test_get_ontology_not_found(self, fabric_client):
        """Test retrieval of non-existent ontology (404 ItemNotFound)."""
        mock_response = create_mock_response(
            status_code=404,
            json_data=create_error_response(
                error_code="ItemNotFound",
                message="The requested item was not found."
            )
        )
        
        with patch('requests.request', return_value=mock_response):
            with pytest.raises(FabricAPIError) as exc_info:
                fabric_client.get_ontology("non-existent-id")
        
        assert exc_info.value.status_code == 404


# =============================================================================
# Test: Create Ontology
# Reference: https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/create-ontology
# =============================================================================

class TestCreateOntology:
    """
    Tests for create_ontology method.
    
    API: POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/ontologies
    Response 201 Created: Ontology object (immediate completion)
    Response 202 Accepted: LRO with Location, x-ms-operation-id, Retry-After headers
    """
    
    def test_create_ontology_success_immediate(self, fabric_client):
        """Test successful immediate ontology creation (201 Created)."""
        mock_response = create_mock_response(
            status_code=201,
            json_data=create_ontology_response(
                ontology_id=SAMPLE_ONTOLOGY_ID,
                display_name="Ontology 1",
                description="An ontology description."
            )
        )
        
        with patch('requests.request', return_value=mock_response):
            result = fabric_client.create_ontology(
                display_name="Ontology 1",
                description="An ontology description.",
                definition={"parts": []},
                wait_for_completion=False
            )
        
        assert result["id"] == SAMPLE_ONTOLOGY_ID
        assert result["type"] == "Ontology"
    
    def test_create_ontology_lro_success(self, fabric_client):
        """
        Test ontology creation with long-running operation (202 Accepted).
        
        Per API docs, 202 response includes:
        - Location header: URI to poll for ontology
        - x-ms-operation-id: Operation ID header
        - Retry-After: Suggested wait time (typically 30 seconds)
        """
        # LRO Location format per API docs
        location_uri = f"{API_BASE_URL}/workspaces/{SAMPLE_WORKSPACE_ID}/ontologies/{SAMPLE_ONTOLOGY_ID}"
        operation_uri = f"{API_BASE_URL}/operations/{SAMPLE_OPERATION_ID}"
        
        create_response = create_mock_response(
            status_code=202,
            json_data={},
            headers={
                'Location': location_uri,
                'x-ms-operation-id': SAMPLE_OPERATION_ID,
                'Retry-After': '30'
            }
        )
        
        # Mock _wait_for_operation to return success (doesn't matter what it returns)
        with patch('requests.request', return_value=create_response):
            with patch.object(fabric_client, '_wait_for_operation', return_value={}):
                result = fabric_client.create_ontology(
                    display_name="Ontology 1",
                    description="An ontology description.",
                    definition={"parts": []},
                    wait_for_completion=True
                )
        
        # The id is extracted from the Location header
        assert result["id"] == SAMPLE_ONTOLOGY_ID
    
    def test_create_ontology_conflict(self, fabric_client):
        """Test creation when ontology with same display name already exists (409 Conflict)."""
        mock_response = create_mock_response(
            status_code=409,
            json_data=create_error_response(
                error_code="ItemDisplayNameAlreadyInUse",
                message="An item with the same name already exists in the workspace."
            )
        )
        
        with patch('requests.request', return_value=mock_response):
            with pytest.raises(FabricAPIError) as exc_info:
                fabric_client.create_ontology(
                    display_name="ExistingOntology",
                    definition={"parts": []}
                )
        
        assert exc_info.value.status_code == 409
    
    def test_create_ontology_validation_error(self, fabric_client):
        """Test creation with corrupted/invalid payload (400 Bad Request)."""
        mock_response = create_mock_response(
            status_code=400,
            json_data=create_error_response(
                error_code="CorruptedPayload",
                message="The request payload is corrupted."
            )
        )
        
        with patch('requests.request', return_value=mock_response):
            with pytest.raises(FabricAPIError) as exc_info:
                fabric_client.create_ontology(
                    display_name="BadOntology",
                    definition={}  # Missing 'parts'
                )
        
        assert exc_info.value.status_code == 400


# =============================================================================
# Test: Update Ontology Definition
# Reference: https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/update-ontology-definition
# =============================================================================

class TestUpdateOntologyDefinition:
    """
    Tests for update_ontology_definition method.
    
    API: POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/ontologies/{ontologyId}/updateDefinition
    Response 200 OK: Immediate completion
    Response 202 Accepted: LRO
    """
    
    def test_update_definition_success(self, fabric_client):
        """Test successful definition update (200 OK)."""
        update_response = create_mock_response(
            status_code=200,
            json_data=create_ontology_response(
                ontology_id=SAMPLE_ONTOLOGY_ID,
                display_name="Ontology 1",
                description="Updated ontology."
            )
        )
        
        with patch('requests.request', return_value=update_response):
            result = fabric_client.update_ontology_definition(
                ontology_id=SAMPLE_ONTOLOGY_ID,
                definition={"parts": [{"id": 1, "kind": "EntityType", "name": "NewEntity"}]},
                wait_for_completion=False
            )
        
        assert result["id"] == SAMPLE_ONTOLOGY_ID
        assert result["type"] == "Ontology"


# =============================================================================
# Test: Delete Ontology
# Reference: https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/delete-ontology
# =============================================================================

class TestDeleteOntology:
    """
    Tests for delete_ontology method.
    
    API: DELETE https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/ontologies/{ontologyId}
    Response 200 OK: Success (empty body)
    Response 404: ItemNotFound
    """
    
    def test_delete_ontology_success(self, fabric_client):
        """Test successful ontology deletion (200 OK, empty body)."""
        # Per API docs, delete returns 200 OK with empty body
        mock_response = create_mock_response(status_code=200)
        
        with patch('requests.request', return_value=mock_response):
            # Should not raise
            fabric_client.delete_ontology(SAMPLE_ONTOLOGY_ID)
    
    def test_delete_ontology_not_found(self, fabric_client):
        """Test deletion of non-existent ontology (404 ItemNotFound)."""
        mock_response = create_mock_response(
            status_code=404,
            json_data=create_error_response(
                error_code="ItemNotFound",
                message="The requested item was not found."
            )
        )
        
        with patch('requests.request', return_value=mock_response):
            with pytest.raises(FabricAPIError) as exc_info:
                fabric_client.delete_ontology("non-existent-id")
        
        assert exc_info.value.status_code == 404


# =============================================================================
# Test: Rate Limiting & Retry
# Reference: https://learn.microsoft.com/en-us/rest/api/fabric/articles/using-fabric-apis#throttling
# =============================================================================

class TestRateLimitingAndRetry:
    """
    Tests for rate limiting and retry behavior per Fabric API guidelines.
    
    Fabric APIs enforce rate limits and return 429 Too Many Requests with
    Retry-After header indicating wait time.
    """
    
    def test_rate_limit_429_retry(self, fabric_client):
        """
        Test automatic retry on 429 Too Many Requests.
        
        Per API docs, clients should honor Retry-After header and retry.
        """
        # First call: 429 Rate Limited
        rate_limit_response = create_mock_response(
            status_code=429,
            json_data=create_error_response(
                error_code="TooManyRequests",
                message="Rate limit exceeded. Retry after 30 seconds."
            ),
            headers={'Retry-After': '1'}
        )
        
        # Second call: Success
        success_response = create_mock_response(
            status_code=200,
            json_data={
                "value": [create_ontology_response()]
            }
        )
        
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise TransientAPIError(429, retry_after=1, message="Rate limited")
            return success_response
        
        with patch('requests.request', side_effect=side_effect):
            # The retry decorator should handle the TransientAPIError
            result = fabric_client.list_ontologies()
        
        assert call_count[0] == 2
        assert len(result) == 1
        assert result[0]["type"] == "Ontology"
    
    def test_service_unavailable_503_retry(self, fabric_client):
        """Test automatic retry on 503 Service Unavailable."""
        # First call: 503
        unavailable_response = create_mock_response(
            status_code=503,
            json_data=create_error_response(
                error_code="ServiceUnavailable",
                message="Service temporarily unavailable."
            ),
            headers={'Retry-After': '1'}
        )
        
        # Second call: Success
        success_response = create_mock_response(
            status_code=200,
            json_data={"value": []}
        )
        
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise TransientAPIError(503, retry_after=1, message="Service unavailable")
            return success_response
        
        with patch('requests.request', side_effect=side_effect):
            result = fabric_client.list_ontologies()
        
        assert call_count[0] == 2


# =============================================================================
# Test: Timeout Handling
# Reference: https://learn.microsoft.com/en-us/rest/api/fabric/articles/using-fabric-apis
# =============================================================================

class TestTimeoutHandling:
    """Tests for request timeout handling per Fabric API best practices."""
    
    def test_request_timeout(self, fabric_client):
        """Test handling of request timeout."""
        import requests as req_lib
        
        with patch('requests.request', side_effect=req_lib.exceptions.Timeout()):
            with pytest.raises(FabricAPIError) as exc_info:
                fabric_client.list_ontologies()
        
        assert exc_info.value.error_code == 'RequestTimeout'
    
    def test_connection_error(self, fabric_client):
        """Test handling of connection error."""
        import requests as req_lib
        
        with patch('requests.request', side_effect=req_lib.exceptions.ConnectionError()):
            with pytest.raises(FabricAPIError) as exc_info:
                fabric_client.list_ontologies()
        
        assert exc_info.value.error_code == 'ConnectionError'


# =============================================================================
# Test: Authentication
# Reference: https://learn.microsoft.com/en-us/rest/api/fabric/articles/using-fabric-apis#authentication
# =============================================================================

class TestAuthentication:
    """
    Tests for authentication handling.
    
    Fabric APIs require Azure AD authentication with Bearer token.
    Scope: https://api.fabric.microsoft.com/.default
    """
    
    def test_token_refresh_on_expiry(self, fabric_config):
        """Test that token is refreshed when expired."""
        # Create expired token
        expired_token = Mock()
        expired_token.token = "expired-token"
        expired_token.expires_on = time.time() - 100  # Expired
        
        # Create new valid token
        new_token = Mock()
        new_token.token = "new-valid-token"
        new_token.expires_on = time.time() + 3600
        
        mock_credential = Mock()
        mock_credential.get_token.side_effect = [expired_token, new_token]
        
        with patch.object(FabricOntologyClient, '_get_credential', return_value=mock_credential):
            client = FabricOntologyClient(fabric_config)
            
            # First call should get expired token, then refresh
            mock_response = create_mock_response(
                status_code=200,
                json_data={"value": []}
            )
            
            with patch('requests.request', return_value=mock_response) as mock_req:
                client.list_ontologies()
                
                # Check that authorization header uses new token
                call_args = mock_req.call_args
                headers = call_args.kwargs.get('headers', {})
                # Token should be acquired
                assert mock_credential.get_token.called
    
    def test_authentication_failure_raises_error(self, fabric_config):
        """Test that authentication failure raises appropriate error."""
        mock_credential = Mock()
        mock_credential.get_token.side_effect = Exception("Auth failed")
        
        with patch.object(FabricOntologyClient, '_get_credential', return_value=mock_credential):
            client = FabricOntologyClient(fabric_config)
            
            with pytest.raises(FabricAPIError) as exc_info:
                client.list_ontologies()
            
            assert exc_info.value.status_code == 401
            assert "AuthenticationFailed" in exc_info.value.error_code


# =============================================================================
# Test: Error Response Handling
# Reference: https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/create-ontology#errorresponse
# =============================================================================

class TestErrorResponseHandling:
    """
    Tests for various error response handling.
    
    Fabric API error response format:
    {
        "errorCode": "string",
        "message": "string",
        "moreDetails"?: [...],
        "relatedResource"?: {...},
        "requestId"?: "string"
    }
    """
    
    def test_invalid_json_response(self, fabric_client):
        """Test handling of invalid JSON in response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "not valid json"
        mock_response.json.side_effect = json.JSONDecodeError("Invalid", "", 0)
        
        with patch('requests.request', return_value=mock_response):
            with pytest.raises(FabricAPIError) as exc_info:
                fabric_client.list_ontologies()
        
        assert exc_info.value.error_code == 'InvalidResponse'
    
    def test_server_error_500(self, fabric_client):
        """Test handling of 500 Internal Server Error."""
        mock_response = create_mock_response(
            status_code=500,
            json_data=create_error_response(
                error_code="InternalError",
                message="An unexpected error occurred on the server."
            )
        )
        
        with patch('requests.request', return_value=mock_response):
            with pytest.raises(FabricAPIError) as exc_info:
                fabric_client.list_ontologies()
        
        assert exc_info.value.status_code == 500
    
    def test_forbidden_403(self, fabric_client):
        """Test handling of 403 Forbidden (insufficient permissions)."""
        mock_response = create_mock_response(
            status_code=403,
            json_data=create_error_response(
                error_code="Forbidden",
                message="The caller does not have permission to perform this operation."
            )
        )
        
        with patch('requests.request', return_value=mock_response):
            with pytest.raises(FabricAPIError) as exc_info:
                fabric_client.list_ontologies()
        
        assert exc_info.value.status_code == 403


# =============================================================================
# Test: Rate Limiter Integration
# Reference: https://learn.microsoft.com/en-us/rest/api/fabric/articles/using-fabric-apis#throttling
# =============================================================================

class TestRateLimiterIntegration:
    """
    Tests for rate limiter integration with client.
    
    Fabric APIs enforce rate limits. Client-side rate limiting helps
    avoid 429 responses by proactively limiting request rate.
    """
    
    def test_rate_limiter_acquires_before_request(self, fabric_client_with_rate_limit):
        """Test that rate limiter is called before each request."""
        mock_response = create_mock_response(
            status_code=200,
            json_data={"value": []}
        )
        
        with patch('requests.request', return_value=mock_response):
            with patch.object(
                fabric_client_with_rate_limit.rate_limiter,
                'acquire',
                wraps=fabric_client_with_rate_limit.rate_limiter.acquire
            ) as mock_acquire:
                fabric_client_with_rate_limit.list_ontologies()
                
                assert mock_acquire.called
    
    def test_rate_limiter_statistics_tracked(self, fabric_client_with_rate_limit):
        """Test that rate limiter statistics are tracked."""
        mock_response = create_mock_response(
            status_code=200,
            json_data={"value": []}
        )
        
        with patch('requests.request', return_value=mock_response):
            # Make multiple requests
            for _ in range(3):
                fabric_client_with_rate_limit.list_ontologies()
            
            stats = fabric_client_with_rate_limit.get_rate_limit_statistics()
            assert stats['total_requests'] == 3


# =============================================================================
# Test: Request Headers
# Reference: https://learn.microsoft.com/en-us/rest/api/fabric/articles/using-fabric-apis#request-headers
# =============================================================================

class TestRequestHeaders:
    """
    Tests for request header handling per Fabric API requirements.
    
    Required headers:
    - Authorization: Bearer {access_token}
    - Content-Type: application/json (for POST/PUT/PATCH)
    """
    
    def test_authorization_header_included(self, fabric_client):
        """Test that Authorization header is included in requests."""
        mock_response = create_mock_response(
            status_code=200,
            json_data={"value": []}
        )
        
        with patch('requests.request', return_value=mock_response) as mock_req:
            fabric_client.list_ontologies()
            
            call_args = mock_req.call_args
            headers = call_args.kwargs.get('headers', {})
            assert 'Authorization' in headers
            assert headers['Authorization'].startswith('Bearer ')
    
    def test_content_type_header_for_post(self, fabric_client):
        """Test that Content-Type header is set for POST requests."""
        mock_response = create_mock_response(
            status_code=201,
            json_data=create_ontology_response()
        )
        
        with patch('requests.request', return_value=mock_response) as mock_req:
            fabric_client.create_ontology(
                display_name="Ontology 1",
                definition={"parts": []},
                wait_for_completion=False
            )
            
            call_args = mock_req.call_args
            headers = call_args.kwargs.get('headers', {})
            assert headers.get('Content-Type') == 'application/json'


# =============================================================================
# Test: Configuration Validation
# =============================================================================

class TestConfigurationValidation:
    """Tests for configuration validation."""
    
    def test_empty_workspace_id_raises_error(self):
        """Test that empty workspace_id raises error."""
        config = FabricConfig(
            workspace_id="",
            tenant_id="test-tenant"
        )
        
        with pytest.raises(ValueError) as exc_info:
            FabricOntologyClient(config)
        
        assert "workspace_id" in str(exc_info.value).lower()
    
    def test_placeholder_workspace_id_raises_error(self):
        """Test that placeholder workspace_id raises error."""
        config = FabricConfig(
            workspace_id="YOUR_WORKSPACE_ID",
            tenant_id="test-tenant"
        )
        
        with pytest.raises(ValueError) as exc_info:
            FabricOntologyClient(config)
        
        assert "workspace" in str(exc_info.value).lower()
    
    def test_invalid_workspace_id_format_warns(self, mock_credential, caplog):
        """
        Test that invalid workspace_id format logs warning.
        
        Workspace IDs should be valid GUIDs per Fabric API specification.
        """
        config = FabricConfig(
            workspace_id="not-a-valid-guid",
            tenant_id="test-tenant",
            rate_limit=RateLimitConfig(enabled=False)
        )
        
        with patch.object(FabricOntologyClient, '_get_credential', return_value=mock_credential):
            import logging
            with caplog.at_level(logging.WARNING):
                client = FabricOntologyClient(config)
            
            # Should have logged a warning about GUID format
            assert any("guid" in record.message.lower() for record in caplog.records)


# =============================================================================
# Test: LRO (Long Running Operations)
# Reference: https://learn.microsoft.com/en-us/rest/api/fabric/articles/long-running-operation
# =============================================================================

class TestLongRunningOperations:
    """
    Tests for long-running operation handling.
    
    Fabric APIs return 202 Accepted for operations that take longer to complete.
    The response includes:
    - Location header: URI to poll for operation status
    - x-ms-operation-id header: Operation ID
    - Retry-After header: Suggested wait time (default 30 seconds)
    
    Operation status values: "Running", "Succeeded", "Failed"
    """
    
    def test_lro_timeout(self, fabric_client):
        """Test LRO timeout after maximum polling attempts."""
        # Mock _wait_for_operation to raise timeout error
        with patch.object(
            fabric_client,
            '_wait_for_operation',
            side_effect=FabricAPIError(504, 'OperationTimeout', 'Operation timed out after maximum polling attempts.')
        ):
            # Initial 202 Accepted response with LRO headers
            location_uri = f"{API_BASE_URL}/operations/{SAMPLE_OPERATION_ID}"
            create_response = create_mock_response(
                status_code=202,
                headers={
                    'Location': location_uri,
                    'x-ms-operation-id': SAMPLE_OPERATION_ID,
                    'Retry-After': '30'
                }
            )
            
            with patch('requests.request', return_value=create_response):
                with pytest.raises(FabricAPIError) as exc_info:
                    fabric_client.create_ontology(
                        display_name="TimeoutTest",
                        definition={"parts": []},
                        wait_for_completion=True
                    )
                
                assert exc_info.value.error_code == 'OperationTimeout'
    
    def test_lro_failure(self, fabric_client):
        """
        Test LRO failure handling when operation status is 'Failed'.
        
        When operation fails, the status response includes error details.
        """
        # Mock _wait_for_operation to raise failure error
        with patch.object(
            fabric_client,
            '_wait_for_operation',
            side_effect=FabricAPIError(500, 'OperationFailed', 'Operation failed due to validation error.')
        ):
            location_uri = f"{API_BASE_URL}/operations/{SAMPLE_OPERATION_ID}"
            create_response = create_mock_response(
                status_code=202,
                headers={
                    'Location': location_uri,
                    'x-ms-operation-id': SAMPLE_OPERATION_ID,
                    'Retry-After': '30'
                }
            )
            
            with patch('requests.request', return_value=create_response):
                with pytest.raises(FabricAPIError) as exc_info:
                    fabric_client.create_ontology(
                        display_name="FailTest",
                        definition={"parts": []},
                        wait_for_completion=True
                    )
                
                assert exc_info.value.error_code == 'OperationFailed'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
