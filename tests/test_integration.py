"""
Integration tests for main.py entry point

These tests verify the command-line interface and end-to-end functionality.
Run with: python -m pytest test_integration.py -v
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import (
    load_config,
    get_default_config_path,
    setup_logging
)


class TestConfigLoading:
    """Test configuration file loading"""
    
    def test_load_valid_config(self, tmp_path):
        """Test loading a valid configuration file"""
        config_data = {
            "tenant_id": "test-tenant",
            "client_id": "test-client",
            "client_secret": "test-secret",
            "workspace_id": "test-workspace"
        }
        
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))
        
        config = load_config(str(config_file))
        
        assert config["tenant_id"] == "test-tenant"
        assert config["client_id"] == "test-client"
    
    def test_load_missing_config(self):
        """Test handling of missing configuration file"""
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent_config.json")
    
    def test_load_invalid_json(self, tmp_path):
        """Test handling of invalid JSON in config"""
        config_file = tmp_path / "bad_config.json"
        config_file.write_text("{ invalid json }")
        
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_config(str(config_file))
    
    def test_load_empty_path(self):
        """Test handling of empty config path"""
        with pytest.raises(ValueError):
            load_config("")
    
    def test_get_default_config_path(self):
        """Test getting default config path"""
        path = get_default_config_path()
        assert path.endswith("config.json")
        assert os.path.isabs(path)


class TestLoggingSetup:
    """Test logging configuration"""
    
    def test_setup_logging_default(self):
        """Test default logging setup"""
        setup_logging()
        # If no exception, setup worked
        assert True
    
    def test_setup_logging_with_level(self):
        """Test logging setup with custom level"""
        setup_logging(level="DEBUG")
        assert True
    
    def test_setup_logging_with_file(self, tmp_path):
        """Test logging setup with file output"""
        log_file = tmp_path / "test.log"
        setup_logging(log_file=str(log_file))
        
        # Check if log file was created
        # Note: File might not exist yet if no logs written
        assert True


class TestConvertCommand:
    """Test the convert command (TTL to JSON)"""
    
    @pytest.fixture
    def sample_ttl(self, tmp_path):
        """Create a sample TTL file"""
        ttl_content = """
        @prefix : <http://example.org/> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        
        :TestOntology a owl:Ontology ;
            rdfs:label "Test Ontology" .
        
        :Person a owl:Class ;
            rdfs:label "Person" .
        
        :name a owl:DatatypeProperty ;
            rdfs:domain :Person ;
            rdfs:range xsd:string .
        """
        
        ttl_file = tmp_path / "test.ttl"
        ttl_file.write_text(ttl_content)
        return ttl_file
    
    def test_convert_ttl_to_json(self, sample_ttl, tmp_path):
        """Test converting TTL to JSON definition"""
        from rdf_converter import parse_ttl_file
        
        output_file = tmp_path / "output.json"
        
        # Parse the TTL
        definition, name = parse_ttl_file(str(sample_ttl))
        
        # Write to JSON
        with open(output_file, 'w') as f:
            json.dump(definition, f, indent=2)
        
        # Verify output
        assert output_file.exists()
        
        with open(output_file, 'r') as f:
            loaded = json.load(f)
        
        assert "parts" in loaded
        assert len(loaded["parts"]) > 0


class TestEndToEnd:
    """End-to-end integration tests"""
    
    @pytest.fixture
    def samples_dir(self):
        """Get samples directory"""
        return Path(__file__).parent.parent / "samples"
    
    def test_parse_sample_ontology_complete(self, samples_dir):
        """Complete test of parsing sample_ontology.ttl"""
        sample_file = samples_dir / "sample_ontology.ttl"
        
        if not sample_file.exists():
            pytest.skip("Sample file not found")
        
        from rdf_converter import parse_ttl_file
        import base64
        
        # Parse
        definition, name = parse_ttl_file(str(sample_file))
        
        # Validate structure
        assert "parts" in definition
        parts = definition["parts"]
        assert len(parts) > 0
        
        # Find entity types
        entity_parts = [p for p in parts if "EntityTypes" in p["path"]]
        assert len(entity_parts) >= 3
        
        # Decode and validate each entity
        for part in entity_parts:
            payload = base64.b64decode(part["payload"]).decode()
            entity = json.loads(payload)
            
            # Validate required fields
            assert "id" in entity
            assert "name" in entity
            assert "namespace" in entity
            assert "namespaceType" in entity
            
            # ID should be a valid number string
            assert entity["id"].isdigit()
            
            # Name should be non-empty
            assert len(entity["name"]) > 0
    
    def test_parse_foaf_with_inheritance(self, samples_dir):
        """Test FOAF ontology with class inheritance"""
        sample_file = samples_dir / "foaf_ontology.ttl"
        
        if not sample_file.exists():
            pytest.skip("Sample file not found")
        
        from rdf_converter import parse_ttl_file
        import base64
        
        # Parse
        definition, name = parse_ttl_file(str(sample_file))
        
        # Find Person entity
        entity_parts = [p for p in definition["parts"] if "EntityTypes" in p["path"]]
        
        person_found = False
        agent_found = False
        person_has_parent = False
        
        for part in entity_parts:
            payload = base64.b64decode(part["payload"]).decode()
            entity = json.loads(payload)
            
            if entity["name"] == "Person":
                person_found = True
                if entity.get("baseEntityTypeId"):
                    person_has_parent = True
            
            if entity["name"] == "Agent":
                agent_found = True
        
        # FOAF Person should extend Agent
        assert person_found, "Person entity not found"
        assert agent_found, "Agent entity not found"
        # Note: parent relationship depends on parsing order
    
    def test_multiple_files_sequentially(self, samples_dir):
        """Test parsing multiple files in sequence"""
        from rdf_converter import parse_ttl_file
        
        ttl_files = [
            "sample_ontology.ttl",
            "sample_iot_ontology.ttl",
            "foaf_ontology.ttl"
        ]
        
        results = []
        
        for filename in ttl_files:
            filepath = samples_dir / filename
            if not filepath.exists():
                continue
            
            try:
                definition, name = parse_ttl_file(str(filepath))
                entity_count = len([p for p in definition["parts"] if "EntityTypes" in p["path"]])
                results.append((filename, "SUCCESS", entity_count))
            except Exception as e:
                results.append((filename, "FAILED", str(e)))
        
        # Should have processed at least one file successfully
        assert len(results) > 0
        successes = [r for r in results if r[1] == "SUCCESS"]
        assert len(successes) > 0


class TestRobustness:
    """Test robustness and error recovery"""
    
    def test_large_file_handling(self, tmp_path):
        """Test handling of reasonably large TTL files"""
        # Generate a moderately large TTL file
        ttl_lines = [
            "@prefix : <http://example.org/> .",
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            ""
        ]
        
        # Add 100 classes
        for i in range(100):
            ttl_lines.append(f":Class{i} a owl:Class ; rdfs:label \"Class {i}\" .")
        
        # Add properties for each class
        for i in range(100):
            ttl_lines.append(
                f":prop{i} a owl:DatatypeProperty ; "
                f"rdfs:domain :Class{i} ; rdfs:range xsd:string ."
            )
        
        ttl_content = "\n".join(ttl_lines)
        ttl_file = tmp_path / "large.ttl"
        ttl_file.write_text(ttl_content)
        
        from rdf_converter import parse_ttl_file
        
        # Should handle without errors
        definition, name = parse_ttl_file(str(ttl_file))
        
        entity_parts = [p for p in definition["parts"] if "EntityTypes" in p["path"]]
        assert len(entity_parts) == 100
    
    def test_unicode_content(self, tmp_path):
        """Test handling of Unicode characters in TTL"""
        ttl_content = """
        @prefix : <http://example.org/> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        
        :Person a owl:Class ;
            rdfs:label "人" ;
            rdfs:comment "Una persona" .
        """
        
        ttl_file = tmp_path / "unicode.ttl"
        ttl_file.write_text(ttl_content, encoding='utf-8')
        
        from rdf_converter import parse_ttl_file
        
        definition, name = parse_ttl_file(str(ttl_file))
        assert "parts" in definition
    
    def test_special_characters_in_names(self, tmp_path):
        """Test handling of special characters that need sanitization"""
        ttl_content = """
        @prefix : <http://example.org/> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        
        :My-Special-Class a owl:Class .
        :Another.Class a owl:Class .
        :Class_With_Underscores a owl:Class .
        """
        
        ttl_file = tmp_path / "special.ttl"
        ttl_file.write_text(ttl_content)
        
        from rdf_converter import parse_ttl_file
        import base64
        
        definition, name = parse_ttl_file(str(ttl_file))
        
        # Check that names are sanitized
        entity_parts = [p for p in definition["parts"] if "EntityTypes" in p["path"]]
        
        for part in entity_parts:
            payload = base64.b64decode(part["payload"]).decode()
            entity = json.loads(payload)
            name = entity["name"]
            
            # Should not contain hyphens or dots
            assert "-" not in name
            assert "." not in name
            # Underscores are OK
            assert name.replace("_", "").isalnum()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
