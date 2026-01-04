"""
Live Fabric API Integration Tests

These tests run against the REAL Fabric API to verify actual behavior.
They are opt-in and require:
1. Valid Azure credentials
2. A configured workspace_id in config.json
3. Explicit opt-in via --run-live flag or FABRIC_LIVE_TESTS=1 env var

Run with: pytest tests/integration/test_fabric_live.py -v --run-live

CAUTION: These tests will:
- Create real ontologies in your Fabric workspace
- Modify and delete ontologies
- Consume API quota

They are designed to clean up after themselves, but failures may leave
orphaned resources.
"""

import pytest
import os
import json
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime


# =============================================================================
# Live Test Configuration
# =============================================================================

def is_live_tests_enabled() -> bool:
    """Check if live tests should run."""
    return os.environ.get("FABRIC_LIVE_TESTS", "0") == "1"


def get_config() -> Optional[dict]:
    """Load configuration from config.json."""
    config_path = Path(__file__).parent.parent.parent / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return None


def get_workspace_id() -> Optional[str]:
    """Get workspace ID from config or environment."""
    workspace_id = os.environ.get("FABRIC_WORKSPACE_ID")
    if workspace_id:
        return workspace_id
    
    config = get_config()
    if config:
        return config.get("workspace_id")
    
    return None


# =============================================================================
# Test Markers and Fixtures
# =============================================================================

# Skip all tests in this module if live tests aren't enabled
pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not is_live_tests_enabled(),
        reason="Live tests disabled. Set FABRIC_LIVE_TESTS=1 or use --run-live"
    ),
]


@pytest.fixture(scope="module")
def workspace_id():
    """Get the workspace ID for live tests."""
    ws_id = get_workspace_id()
    if not ws_id:
        pytest.skip("No workspace_id configured. Set in config.json or FABRIC_WORKSPACE_ID env var.")
    return ws_id


@pytest.fixture(scope="module")
def azure_credential():
    """Get Azure credentials for live tests."""
    try:
        from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential
        
        # Try DefaultAzureCredential first (works in CI/CD with managed identity)
        try:
            cred = DefaultAzureCredential()
            # Test the credential works
            cred.get_token("https://api.fabric.microsoft.com/.default")
            return cred
        except Exception:
            # Fall back to interactive browser
            return InteractiveBrowserCredential()
    except ImportError:
        pytest.skip("azure-identity not installed. Run: pip install azure-identity")


@pytest.fixture(scope="module")
def fabric_client(azure_credential, workspace_id):
    """Create a live Fabric client."""
    from src.core.platform.fabric_client import FabricOntologyClient
    return FabricOntologyClient(azure_credential, workspace_id)


@pytest.fixture
def unique_name():
    """Generate a unique name for test resources."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"LiveTest_{timestamp}_{unique_id}"


@pytest.fixture
def cleanup_ontologies(fabric_client):
    """Track and clean up ontologies created during tests."""
    created_ids = []
    
    yield created_ids
    
    # Cleanup: Delete all created ontologies
    for ontology_id in created_ids:
        try:
            fabric_client.delete_ontology(ontology_id)
            print(f"Cleaned up ontology: {ontology_id}")
        except Exception as e:
            print(f"Warning: Failed to clean up ontology {ontology_id}: {e}")


# =============================================================================
# Live Tests: List Ontologies
# =============================================================================

class TestListOntologiesLive:
    """Live tests for listing ontologies."""
    
    def test_list_ontologies_returns_list(self, fabric_client):
        """Verify list_ontologies returns a list from real API."""
        # Act
        result = fabric_client.list_ontologies()
        
        # Assert: Basic structure validation
        assert isinstance(result, list)
        
        # If there are ontologies, validate structure
        for ontology in result:
            assert "id" in ontology
            assert "displayName" in ontology
            assert "type" in ontology
            assert ontology["type"] == "Ontology"
    
    def test_list_handles_empty_gracefully(self, fabric_client):
        """Verify empty workspace returns empty list, not error."""
        # Act - This should not raise even if workspace is empty
        result = fabric_client.list_ontologies()
        
        # Assert
        assert result is not None


# =============================================================================
# Live Tests: Create and Get Ontology
# =============================================================================

class TestCreateOntologyLive:
    """Live tests for creating ontologies."""
    
    def test_create_ontology_succeeds(
        self, fabric_client, unique_name, cleanup_ontologies
    ):
        """Verify ontology creation works with real API."""
        # Act
        result = fabric_client.create_ontology(
            display_name=unique_name,
            description="Automated live test - safe to delete"
        )
        
        # Track for cleanup
        if result and "id" in result:
            cleanup_ontologies.append(result["id"])
        
        # Assert
        assert result is not None
        assert "id" in result
        assert result["displayName"] == unique_name
    
    def test_get_created_ontology(
        self, fabric_client, unique_name, cleanup_ontologies
    ):
        """Verify we can get an ontology we just created."""
        # Arrange: Create first
        created = fabric_client.create_ontology(
            display_name=unique_name,
            description="Automated live test - safe to delete"
        )
        ontology_id = created["id"]
        cleanup_ontologies.append(ontology_id)
        
        # Act: Get it back
        result = fabric_client.get_ontology(ontology_id)
        
        # Assert
        assert result["id"] == ontology_id
        assert result["displayName"] == unique_name
    
    def test_duplicate_name_fails(
        self, fabric_client, unique_name, cleanup_ontologies
    ):
        """Verify duplicate names are rejected."""
        # Arrange: Create first ontology
        created = fabric_client.create_ontology(
            display_name=unique_name,
            description="First ontology"
        )
        cleanup_ontologies.append(created["id"])
        
        # Act & Assert: Second with same name should fail
        with pytest.raises(Exception) as exc_info:
            fabric_client.create_ontology(
                display_name=unique_name,  # Same name
                description="Duplicate ontology"
            )
        
        # Verify it's a conflict error
        error_str = str(exc_info.value).lower()
        assert "409" in str(exc_info.value) or "conflict" in error_str or "exists" in error_str


# =============================================================================
# Live Tests: Delete Ontology
# =============================================================================

class TestDeleteOntologyLive:
    """Live tests for deleting ontologies."""
    
    def test_delete_ontology_succeeds(self, fabric_client, unique_name):
        """Verify ontology deletion works."""
        # Arrange: Create an ontology
        created = fabric_client.create_ontology(
            display_name=unique_name,
            description="Ontology to be deleted"
        )
        ontology_id = created["id"]
        
        # Act: Delete it
        fabric_client.delete_ontology(ontology_id)
        
        # Assert: Should not be found anymore
        with pytest.raises(Exception):
            fabric_client.get_ontology(ontology_id)
    
    def test_delete_nonexistent_fails(self, fabric_client):
        """Verify deleting non-existent ontology fails appropriately."""
        fake_id = str(uuid.uuid4())
        
        # Act & Assert
        with pytest.raises(Exception):
            fabric_client.delete_ontology(fake_id)


# =============================================================================
# Live Tests: Update Definition
# =============================================================================

class TestUpdateDefinitionLive:
    """Live tests for updating ontology definitions."""
    
    def test_upload_simple_definition(
        self, fabric_client, unique_name, cleanup_ontologies
    ):
        """Verify definition upload works with real API."""
        import base64
        
        # Arrange: Create ontology first
        created = fabric_client.create_ontology(
            display_name=unique_name,
            description="Ontology for definition upload test"
        )
        ontology_id = created["id"]
        cleanup_ontologies.append(ontology_id)
        
        # Create a minimal valid definition
        entity_id = "9999999999999"
        entity_data = {
            "id": entity_id,
            "namespace": "usertypes",
            "name": "TestEntity",
            "displayName": "Test Entity",
            "description": "A test entity type",
            "namespaceType": "Custom",
            "visibility": "Visible",
            "properties": []
        }
        
        platform_data = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/platformProperties.json",
            "config": {"version": "1.0", "type": "Ontology"}
        }
        
        definition_json = {"version": "1.0", "formatVersion": "1.0"}
        
        definition = {
            "parts": [
                {
                    "path": ".platform",
                    "payload": base64.b64encode(json.dumps(platform_data).encode()).decode(),
                    "payloadType": "InlineBase64"
                },
                {
                    "path": "definition.json",
                    "payload": base64.b64encode(json.dumps(definition_json).encode()).decode(),
                    "payloadType": "InlineBase64"
                },
                {
                    "path": "EntityTypes/TestEntity.json",
                    "payload": base64.b64encode(json.dumps(entity_data).encode()).decode(),
                    "payloadType": "InlineBase64"
                }
            ]
        }
        
        # Act: Upload definition
        fabric_client.update_definition(ontology_id, definition)
        
        # Assert: Get definition and verify
        # Note: Getting definition back may require additional API call
        result = fabric_client.get_ontology(ontology_id)
        assert result["id"] == ontology_id


# =============================================================================
# Live Tests: Error Conditions
# =============================================================================

class TestErrorConditionsLive:
    """Live tests for error handling."""
    
    def test_invalid_workspace_id(self, azure_credential):
        """Verify invalid workspace ID gives clear error."""
        from src.core.platform.fabric_client import FabricOntologyClient
        
        fake_workspace_id = str(uuid.uuid4())
        client = FabricOntologyClient(azure_credential, fake_workspace_id)
        
        # Act & Assert
        with pytest.raises(Exception):
            client.list_ontologies()
    
    def test_get_nonexistent_ontology(self, fabric_client):
        """Verify getting non-existent ontology returns 404."""
        fake_id = str(uuid.uuid4())
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            fabric_client.get_ontology(fake_id)
        
        # Should be a 404-type error
        error_str = str(exc_info.value).lower()
        assert "404" in str(exc_info.value) or "not found" in error_str


# =============================================================================
# Live Tests: Rate Limiting
# =============================================================================

class TestRateLimitingLive:
    """Live tests for rate limiting behavior."""
    
    @pytest.mark.slow
    def test_multiple_requests_work(self, fabric_client):
        """Verify rate limiter allows multiple sequential requests."""
        # Act: Make several requests
        results = []
        for i in range(5):
            result = fabric_client.list_ontologies()
            results.append(result is not None)
        
        # Assert: All should succeed
        assert all(results)


# =============================================================================
# Live Tests: Full Workflow
# =============================================================================

class TestFullWorkflowLive:
    """End-to-end live tests of complete workflows."""
    
    def test_complete_ontology_lifecycle(
        self, fabric_client, unique_name
    ):
        """Test complete create -> update -> get -> delete workflow."""
        import base64
        
        ontology_id = None
        
        try:
            # Step 1: Create
            created = fabric_client.create_ontology(
                display_name=unique_name,
                description="Full lifecycle test"
            )
            ontology_id = created["id"]
            assert ontology_id is not None
            
            # Step 2: Update with definition
            entity_data = {
                "id": "8888888888888",
                "namespace": "usertypes",
                "name": "LifecycleEntity",
                "displayName": "Lifecycle Entity",
                "namespaceType": "Custom",
                "visibility": "Visible",
                "properties": []
            }
            
            definition = {
                "parts": [
                    {
                        "path": ".platform",
                        "payload": base64.b64encode(json.dumps({
                            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/platformProperties.json",
                            "config": {"version": "1.0", "type": "Ontology"}
                        }).encode()).decode(),
                        "payloadType": "InlineBase64"
                    },
                    {
                        "path": "definition.json",
                        "payload": base64.b64encode(json.dumps({
                            "version": "1.0", "formatVersion": "1.0"
                        }).encode()).decode(),
                        "payloadType": "InlineBase64"
                    },
                    {
                        "path": "EntityTypes/LifecycleEntity.json",
                        "payload": base64.b64encode(json.dumps(entity_data).encode()).decode(),
                        "payloadType": "InlineBase64"
                    }
                ]
            }
            
            fabric_client.update_definition(ontology_id, definition)
            
            # Step 3: Get and verify
            retrieved = fabric_client.get_ontology(ontology_id)
            assert retrieved["displayName"] == unique_name
            
            # Step 4: Delete
            fabric_client.delete_ontology(ontology_id)
            ontology_id = None  # Prevent cleanup attempt
            
            # Step 5: Verify deleted
            with pytest.raises(Exception):
                fabric_client.get_ontology(created["id"])
            
        finally:
            # Cleanup if test failed partway
            if ontology_id:
                try:
                    fabric_client.delete_ontology(ontology_id)
                except Exception:
                    pass
