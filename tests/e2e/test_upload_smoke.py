"""
End-to-End Upload Smoke Test

This smoke test performs a complete upload workflow using real files
and optionally the real Fabric API. It validates the entire pipeline:

1. RDF file parsing
2. Ontology conversion
3. Definition building
4. Schema validation
5. (Optional) Fabric API upload

Usage:
    # Dry-run mode (no API calls)
    pytest tests/e2e/test_upload_smoke.py -v
    
    # Live mode (requires FABRIC_LIVE_TESTS=1)
    pytest tests/e2e/test_upload_smoke.py -v --run-live

This test uses sample files from the samples/ directory.
"""

import pytest
import os
import sys
import json
import base64
from pathlib import Path
from typing import Dict, Any, List


# =============================================================================
# Configuration
# =============================================================================

SAMPLES_DIR = Path(__file__).parent.parent.parent / "samples"
RDF_SAMPLES_DIR = SAMPLES_DIR / "rdf"

# Sample files for smoke testing
SMOKE_TEST_FILES = [
    "sample_iot_ontology.ttl",
    "ecommerce_ontology.ttl",
    "vehicle_ontology.ttl",
]


def is_live_tests_enabled() -> bool:
    """Check if live tests should run."""
    return os.environ.get("FABRIC_LIVE_TESTS", "0") == "1"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_ttl_path():
    """Get path to a sample TTL file."""
    path = RDF_SAMPLES_DIR / "sample_iot_ontology.ttl"
    if not path.exists():
        pytest.skip(f"Sample file not found: {path}")
    return path


@pytest.fixture
def all_sample_files():
    """Get all available sample files for testing."""
    available = []
    for filename in SMOKE_TEST_FILES:
        path = RDF_SAMPLES_DIR / filename
        if path.exists():
            available.append(path)
    
    if not available:
        pytest.skip("No sample files available")
    return available


# =============================================================================
# Smoke Tests: File Parsing
# =============================================================================

class TestFileParsing:
    """Smoke tests for file parsing."""
    
    def test_parse_ttl_file(self, sample_ttl_path):
        """Verify TTL file can be parsed."""
        from rdflib import Graph
        
        # Act
        g = Graph()
        g.parse(sample_ttl_path, format="turtle")
        
        # Assert
        assert len(g) > 0
        print(f"Parsed {len(g)} triples from {sample_ttl_path.name}")
    
    @pytest.mark.parametrize("filename", [
        "sample_iot_ontology.ttl",
        "ecommerce_ontology.ttl",
        "vehicle_ontology.ttl",
        "healthcare_ontology.ttl",
        "library_ontology.ttl",
    ])
    def test_parse_multiple_formats(self, filename):
        """Verify multiple sample files can be parsed."""
        path = RDF_SAMPLES_DIR / filename
        if not path.exists():
            pytest.skip(f"File not found: {filename}")
        
        from rdflib import Graph
        
        # Act
        g = Graph()
        g.parse(path, format="turtle")
        
        # Assert
        assert len(g) > 0
        print(f"✓ {filename}: {len(g)} triples")


# =============================================================================
# Smoke Tests: Ontology Conversion
# =============================================================================

class TestOntologyConversion:
    """Smoke tests for RDF to ontology conversion."""
    
    def test_convert_to_entity_types(self, sample_ttl_path):
        """Verify conversion produces entity types."""
        from rdflib import Graph, RDF, RDFS, OWL
        
        # Parse the file
        g = Graph()
        g.parse(sample_ttl_path, format="turtle")
        
        # Extract classes (potential entity types)
        classes = list(g.subjects(RDF.type, OWL.Class))
        if not classes:
            classes = list(g.subjects(RDF.type, RDFS.Class))
        
        # Assert
        assert len(classes) > 0, "No classes found in ontology"
        print(f"Found {len(classes)} classes (potential entity types)")
    
    def test_extract_relationships(self, sample_ttl_path):
        """Verify relationships can be extracted."""
        from rdflib import Graph, RDF, OWL
        
        # Parse
        g = Graph()
        g.parse(sample_ttl_path, format="turtle")
        
        # Extract object properties (relationships)
        relationships = list(g.subjects(RDF.type, OWL.ObjectProperty))
        
        # Note: Not all ontologies have object properties
        print(f"Found {len(relationships)} object properties (relationships)")
    
    def test_extract_properties(self, sample_ttl_path):
        """Verify properties can be extracted."""
        from rdflib import Graph, RDF, OWL
        
        # Parse
        g = Graph()
        g.parse(sample_ttl_path, format="turtle")
        
        # Extract datatype properties
        datatype_props = list(g.subjects(RDF.type, OWL.DatatypeProperty))
        
        print(f"Found {len(datatype_props)} datatype properties")


# =============================================================================
# Smoke Tests: Definition Building
# =============================================================================

class TestDefinitionBuilding:
    """Smoke tests for Fabric definition building."""
    
    def test_build_entity_type_payload(self):
        """Verify entity type payload can be built."""
        # Arrange
        entity_id = "1234567890123"
        entity_name = "TestEntity"
        
        entity_type = {
            "id": entity_id,
            "namespace": "usertypes",
            "name": entity_name,
            "displayName": "Test Entity",
            "description": "A test entity",
            "namespaceType": "Custom",
            "visibility": "Visible",
            "properties": [
                {
                    "id": "9876543210987",
                    "name": "testProperty",
                    "displayName": "Test Property",
                    "valueType": "String"
                }
            ]
        }
        
        # Act: Encode as base64 (Fabric format)
        payload = base64.b64encode(json.dumps(entity_type).encode()).decode()
        
        # Assert
        assert len(payload) > 0
        
        # Verify round-trip
        decoded = json.loads(base64.b64decode(payload))
        assert decoded["id"] == entity_id
        assert decoded["name"] == entity_name
    
    def test_build_definition_structure(self):
        """Verify complete definition structure can be built."""
        # Arrange
        platform_data = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/platformProperties.json",
            "config": {"version": "1.0", "type": "Ontology"}
        }
        
        definition_json = {
            "version": "1.0",
            "formatVersion": "1.0"
        }
        
        entity_data = {
            "id": "1111111111111",
            "namespace": "usertypes",
            "name": "SmokeTestEntity",
            "displayName": "Smoke Test Entity",
            "namespaceType": "Custom",
            "visibility": "Visible",
            "properties": []
        }
        
        # Act: Build definition
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
                    "path": f"EntityTypes/{entity_data['name']}.json",
                    "payload": base64.b64encode(json.dumps(entity_data).encode()).decode(),
                    "payloadType": "InlineBase64"
                }
            ]
        }
        
        # Assert
        assert "parts" in definition
        assert len(definition["parts"]) == 3
        
        paths = [p["path"] for p in definition["parts"]]
        assert ".platform" in paths
        assert "definition.json" in paths


# =============================================================================
# Smoke Tests: Schema Validation
# =============================================================================

class TestSchemaValidation:
    """Smoke tests for schema validation."""
    
    def test_validate_valid_definition(self):
        """Verify valid definition passes validation."""
        from src.core.validators.fabric_schema import FabricSchemaValidator
        
        # Arrange: Build valid definition
        entity_data = {
            "id": "2222222222222",
            "namespace": "usertypes",
            "name": "ValidEntity",
            "displayName": "Valid Entity",
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
                    "path": "EntityTypes/ValidEntity.json",
                    "payload": base64.b64encode(json.dumps(entity_data).encode()).decode(),
                    "payloadType": "InlineBase64"
                }
            ]
        }
        
        # Act
        validator = FabricSchemaValidator()
        result = validator.validate(definition)
        
        # Assert
        assert result.is_valid, f"Validation errors: {result.errors}"
    
    def test_validate_invalid_definition_fails(self):
        """Verify invalid definition fails validation."""
        from src.core.validators.fabric_schema import FabricSchemaValidator
        
        # Arrange: Build invalid definition (missing required fields)
        entity_data = {
            "name": "InvalidEntity",
            # Missing: id, namespace, namespaceType
        }
        
        definition = {
            "parts": [
                {
                    "path": "EntityTypes/InvalidEntity.json",
                    "payload": base64.b64encode(json.dumps(entity_data).encode()).decode(),
                    "payloadType": "InlineBase64"
                }
            ]
        }
        
        # Act
        validator = FabricSchemaValidator()
        result = validator.validate(definition)
        
        # Assert
        assert not result.is_valid
        assert len(result.errors) > 0


# =============================================================================
# Smoke Tests: Full Pipeline (Dry Run)
# =============================================================================

class TestFullPipelineDryRun:
    """Smoke tests for the complete upload pipeline in dry-run mode."""
    
    def test_parse_convert_validate_pipeline(self, sample_ttl_path):
        """Test complete pipeline: parse -> convert -> build -> validate."""
        from rdflib import Graph, RDF, RDFS, OWL, Namespace
        from src.core.validators.fabric_schema import FabricSchemaValidator
        
        # Step 1: Parse
        g = Graph()
        g.parse(sample_ttl_path, format="turtle")
        assert len(g) > 0
        print(f"Step 1: Parsed {len(g)} triples")
        
        # Step 2: Extract classes
        classes = list(g.subjects(RDF.type, OWL.Class))
        if not classes:
            classes = list(g.subjects(RDF.type, RDFS.Class))
        assert len(classes) > 0
        print(f"Step 2: Found {len(classes)} classes")
        
        # Step 3: Build definition
        parts = [
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
            }
        ]
        
        # Add entity types for each class
        for i, cls in enumerate(classes[:5]):  # Limit to 5 for smoke test
            local_name = str(cls).split('#')[-1].split('/')[-1]
            entity_id = str(1000000000000 + i)
            
            entity_data = {
                "id": entity_id,
                "namespace": "usertypes",
                "name": local_name,
                "displayName": local_name.replace("_", " "),
                "namespaceType": "Custom",
                "visibility": "Visible",
                "properties": []
            }
            
            parts.append({
                "path": f"EntityTypes/{local_name}.json",
                "payload": base64.b64encode(json.dumps(entity_data).encode()).decode(),
                "payloadType": "InlineBase64"
            })
        
        definition = {"parts": parts}
        print(f"Step 3: Built definition with {len(parts)} parts")
        
        # Step 4: Validate
        validator = FabricSchemaValidator()
        result = validator.validate(definition)
        assert result.is_valid, f"Validation errors: {result.errors}"
        print("Step 4: Definition validated successfully")
        
        print("✓ Full pipeline completed successfully (dry run)")


# =============================================================================
# Smoke Tests: Full Pipeline (Live)
# =============================================================================

@pytest.mark.live
@pytest.mark.skipif(
    not is_live_tests_enabled(),
    reason="Live tests disabled. Set FABRIC_LIVE_TESTS=1"
)
class TestFullPipelineLive:
    """Smoke tests for the complete upload pipeline with real API."""
    
    @pytest.fixture
    def live_fabric_client(self):
        """Create a live Fabric client."""
        try:
            from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential
            from src.core.platform.fabric_client import FabricOntologyClient
            
            # Load config
            config_path = Path(__file__).parent.parent.parent / "config.json"
            if not config_path.exists():
                pytest.skip("config.json not found")
            
            with open(config_path) as f:
                config = json.load(f)
            
            workspace_id = config.get("workspace_id")
            if not workspace_id:
                pytest.skip("workspace_id not configured")
            
            # Get credentials
            try:
                cred = DefaultAzureCredential()
                cred.get_token("https://api.fabric.microsoft.com/.default")
            except Exception:
                cred = InteractiveBrowserCredential()
            
            return FabricOntologyClient(cred, workspace_id)
            
        except ImportError as e:
            pytest.skip(f"Required packages not installed: {e}")
    
    def test_live_upload_smoke(self, sample_ttl_path, live_fabric_client):
        """Full live upload smoke test."""
        from rdflib import Graph, RDF, RDFS, OWL
        import uuid
        from datetime import datetime
        
        ontology_id = None
        
        try:
            # Step 1: Parse
            g = Graph()
            g.parse(sample_ttl_path, format="turtle")
            
            # Step 2: Extract classes
            classes = list(g.subjects(RDF.type, OWL.Class))
            if not classes:
                classes = list(g.subjects(RDF.type, RDFS.Class))
            
            # Step 3: Create ontology
            unique_name = f"SmokeTest_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            created = live_fabric_client.create_ontology(
                display_name=unique_name,
                description="E2E smoke test - safe to delete"
            )
            ontology_id = created["id"]
            print(f"Created ontology: {ontology_id}")
            
            # Step 4: Build definition
            parts = [
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
                }
            ]
            
            for i, cls in enumerate(classes[:3]):  # Limit for smoke test
                local_name = str(cls).split('#')[-1].split('/')[-1]
                entity_id = str(1000000000000 + i)
                
                entity_data = {
                    "id": entity_id,
                    "namespace": "usertypes",
                    "name": local_name,
                    "displayName": local_name.replace("_", " "),
                    "namespaceType": "Custom",
                    "visibility": "Visible",
                    "properties": []
                }
                
                parts.append({
                    "path": f"EntityTypes/{local_name}.json",
                    "payload": base64.b64encode(json.dumps(entity_data).encode()).decode(),
                    "payloadType": "InlineBase64"
                })
            
            definition = {"parts": parts}
            
            # Step 5: Upload definition
            live_fabric_client.update_definition(ontology_id, definition)
            print("Definition uploaded successfully")
            
            # Step 6: Verify
            result = live_fabric_client.get_ontology(ontology_id)
            assert result["displayName"] == unique_name
            print("✓ Live smoke test PASSED")
            
        finally:
            # Cleanup
            if ontology_id:
                try:
                    live_fabric_client.delete_ontology(ontology_id)
                    print(f"Cleaned up ontology: {ontology_id}")
                except Exception as e:
                    print(f"Warning: Cleanup failed: {e}")
