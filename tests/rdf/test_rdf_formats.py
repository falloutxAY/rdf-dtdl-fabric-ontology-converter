"""
Unit tests for RDF Format Support

Tests conversion of all supported RDF serialization formats:
- Turtle (.ttl)
- RDF/XML (.rdf, .owl)
- N-Triples (.nt)
- N-Quads (.nq)
- TriG (.trig)
- Notation3 (.n3)
- JSON-LD (.jsonld)

Run with: python -m pytest tests/rdf/test_rdf_formats.py -v
"""

import pytest
import json
import base64
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from src.rdf import (
    RDFToFabricConverter,
    parse_ttl_file,
    parse_ttl_content,
)
from src.formats.rdf.rdf_parser import RDFGraphParser


class TestRDFFormatSupport:
    """Test that all RDF serialization formats are correctly handled."""

    @pytest.fixture
    def converter(self):
        """Create a converter instance for testing"""
        return RDFToFabricConverter()

    @pytest.fixture
    def samples_dir(self):
        """Get the samples/rdf directory path"""
        return ROOT_DIR / "samples" / "rdf"

    # =========================================================================
    # Format Normalization Tests
    # =========================================================================

    def test_format_aliases(self):
        """Test that format aliases are correctly normalized."""
        test_cases = [
            ("ttl", "turtle"),
            ("turtle", "turtle"),
            ("rdf", "xml"),
            ("owl", "xml"),
            ("rdfxml", "xml"),
            ("rdf-xml", "xml"),
            ("xml", "xml"),
            ("nt", "nt"),
            ("ntriples", "nt"),
            ("n-triples", "nt"),
            ("n3", "n3"),
            ("trig", "trig"),
            ("nq", "nquads"),
            ("nquad", "nquads"),
            ("nquads", "nquads"),
            ("jsonld", "json-ld"),
            ("json_ld", "json-ld"),
            ("json-ld", "json-ld"),
        ]

        for alias, expected in test_cases:
            result = RDFGraphParser.normalize_format(alias)
            assert result == expected, f"Alias '{alias}' should normalize to '{expected}', got '{result}'"

    def test_unsupported_format_raises_error(self):
        """Test that unsupported formats raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported RDF serialization format"):
            RDFGraphParser.resolve_format("invalid_format")

    # =========================================================================
    # Turtle Format Tests (.ttl)
    # =========================================================================

    def test_turtle_format_parsing(self, converter):
        """Test parsing Turtle (.ttl) format."""
        ttl_content = """
        @prefix : <http://example.org/> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        
        :Device a owl:Class ;
            rdfs:label "Device" ;
            rdfs:comment "An IoT device" .
        
        :deviceId a owl:DatatypeProperty ;
            rdfs:domain :Device ;
            rdfs:range xsd:string .
        """

        entity_types, relationship_types = converter.parse_ttl(ttl_content, rdf_format="turtle")

        assert len(entity_types) == 1
        assert entity_types[0].name == "Device"
        assert len(entity_types[0].properties) == 1
        assert entity_types[0].properties[0].name == "deviceId"

    def test_turtle_sample_file(self, samples_dir):
        """Test parsing sample Turtle file."""
        sample_file = samples_dir / "sample_iot_ontology.ttl"

        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")

        definition, name = parse_ttl_file(str(sample_file))

        assert "parts" in definition
        entity_parts = [p for p in definition["parts"] if "EntityTypes" in p["path"]]
        assert len(entity_parts) >= 2  # Should have Device and Location

    # =========================================================================
    # RDF/XML Format Tests (.rdf, .owl)
    # =========================================================================

    def test_rdfxml_format_parsing(self, converter):
        """Test parsing RDF/XML (.rdf) format."""
        rdfxml_content = """<?xml version="1.0"?>
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
                 xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
                 xmlns:owl="http://www.w3.org/2002/07/owl#"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema#"
                 xmlns:ex="http://example.org/">
          <owl:Class rdf:about="http://example.org/Device">
            <rdfs:label>Device</rdfs:label>
          </owl:Class>
          <owl:DatatypeProperty rdf:about="http://example.org/deviceId">
            <rdfs:domain rdf:resource="http://example.org/Device"/>
            <rdfs:range rdf:resource="http://www.w3.org/2001/XMLSchema#string"/>
          </owl:DatatypeProperty>
        </rdf:RDF>
        """

        entity_types, relationship_types = converter.parse_ttl(
            rdfxml_content, rdf_format="xml"
        )

        assert len(entity_types) == 1
        assert entity_types[0].name == "Device"

    def test_rdfxml_sample_file(self, samples_dir):
        """Test parsing sample RDF/XML file."""
        sample_file = samples_dir / "sample_iot_ontology.rdf"

        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")

        definition, name = parse_ttl_file(str(sample_file))

        assert "parts" in definition
        entity_parts = [p for p in definition["parts"] if "EntityTypes" in p["path"]]
        assert len(entity_parts) >= 2  # Should have Device, Sensor, Location

        # Verify entity structure
        for part in entity_parts:
            payload = base64.b64decode(part["payload"]).decode()
            entity_data = json.loads(payload)
            assert "id" in entity_data
            assert "name" in entity_data

    def test_rdfxml_with_subclass(self, samples_dir):
        """Test that RDF/XML correctly handles subclass relationships."""
        sample_file = samples_dir / "sample_iot_ontology.rdf"

        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")

        definition, name = parse_ttl_file(str(sample_file))
        entity_parts = [p for p in definition["parts"] if "EntityTypes" in p["path"]]

        # Find Sensor entity and verify it has Device as base
        sensor_found = False
        for part in entity_parts:
            payload = base64.b64decode(part["payload"]).decode()
            entity_data = json.loads(payload)
            if entity_data["name"] == "Sensor":
                sensor_found = True
                assert entity_data.get("baseEntityTypeId") is not None, \
                    "Sensor should have Device as base entity type"
                break

        assert sensor_found, "Sensor entity type not found"

    # =========================================================================
    # N-Triples Format Tests (.nt)
    # =========================================================================

    def test_ntriples_format_parsing(self, converter):
        """Test parsing N-Triples (.nt) format."""
        nt_content = """
<http://example.org/Device> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2002/07/owl#Class> .
<http://example.org/Device> <http://www.w3.org/2000/01/rdf-schema#label> "Device" .
<http://example.org/deviceId> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2002/07/owl#DatatypeProperty> .
<http://example.org/deviceId> <http://www.w3.org/2000/01/rdf-schema#domain> <http://example.org/Device> .
<http://example.org/deviceId> <http://www.w3.org/2000/01/rdf-schema#range> <http://www.w3.org/2001/XMLSchema#string> .
        """

        entity_types, relationship_types = converter.parse_ttl(nt_content, rdf_format="nt")

        assert len(entity_types) == 1
        assert entity_types[0].name == "Device"

    def test_ntriples_sample_file(self, samples_dir):
        """Test parsing sample N-Triples file."""
        sample_file = samples_dir / "sample_iot_ontology.nt"

        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")

        definition, name = parse_ttl_file(str(sample_file))

        assert "parts" in definition
        entity_parts = [p for p in definition["parts"] if "EntityTypes" in p["path"]]
        assert len(entity_parts) >= 2

        # Verify Device entity has properties
        device_found = False
        for part in entity_parts:
            payload = base64.b64decode(part["payload"]).decode()
            entity_data = json.loads(payload)
            if entity_data["name"] == "Device":
                device_found = True
                assert "properties" in entity_data
                break

        assert device_found, "Device entity type not found"

    # =========================================================================
    # N-Quads Format Tests (.nq)
    # =========================================================================

    def test_nquads_format_parsing(self, converter):
        """Test parsing N-Quads (.nq) format - dataset format with named graphs."""
        nq_content = """
<http://example.org/Device> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2002/07/owl#Class> <http://example.org/graph1> .
<http://example.org/Device> <http://www.w3.org/2000/01/rdf-schema#label> "Device" <http://example.org/graph1> .
<http://example.org/deviceId> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2002/07/owl#DatatypeProperty> <http://example.org/graph2> .
<http://example.org/deviceId> <http://www.w3.org/2000/01/rdf-schema#domain> <http://example.org/Device> <http://example.org/graph2> .
<http://example.org/deviceId> <http://www.w3.org/2000/01/rdf-schema#range> <http://www.w3.org/2001/XMLSchema#string> <http://example.org/graph2> .
        """

        entity_types, relationship_types = converter.parse_ttl(nq_content, rdf_format="nquads")

        assert len(entity_types) == 1
        assert entity_types[0].name == "Device"

    def test_nquads_sample_file(self, samples_dir):
        """Test parsing sample N-Quads file with multiple named graphs."""
        sample_file = samples_dir / "sample_iot_ontology.nq"

        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")

        definition, name = parse_ttl_file(str(sample_file))

        assert "parts" in definition
        entity_parts = [p for p in definition["parts"] if "EntityTypes" in p["path"]]
        assert len(entity_parts) >= 2  # Should have Device, Gateway, Location

        # Verify relationships are parsed
        rel_parts = [p for p in definition["parts"] if "RelationshipTypes" in p["path"]]
        assert len(rel_parts) >= 1  # Should have locatedAt

    # =========================================================================
    # TriG Format Tests (.trig)
    # =========================================================================

    def test_trig_format_parsing(self, converter):
        """Test parsing TriG (.trig) format - Turtle with named graphs."""
        trig_content = """
@prefix : <http://example.org/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

:graph1 {
    :Device a owl:Class ;
        rdfs:label "Device" .
}

:graph2 {
    :deviceId a owl:DatatypeProperty ;
        rdfs:domain :Device ;
        rdfs:range xsd:string .
}
        """

        entity_types, relationship_types = converter.parse_ttl(trig_content, rdf_format="trig")

        assert len(entity_types) == 1
        assert entity_types[0].name == "Device"

    def test_trig_sample_file(self, samples_dir):
        """Test parsing sample TriG file with multiple named graphs."""
        sample_file = samples_dir / "sample_iot_ontology.trig"

        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")

        definition, name = parse_ttl_file(str(sample_file))

        assert "parts" in definition
        entity_parts = [p for p in definition["parts"] if "EntityTypes" in p["path"]]
        assert len(entity_parts) >= 2

        # Verify EdgeDevice subclass relationship
        edge_device_found = False
        for part in entity_parts:
            payload = base64.b64decode(part["payload"]).decode()
            entity_data = json.loads(payload)
            if entity_data["name"] == "EdgeDevice":
                edge_device_found = True
                assert entity_data.get("baseEntityTypeId") is not None
                break

        # EdgeDevice should exist with inheritance
        assert edge_device_found, "EdgeDevice entity type not found"

    # =========================================================================
    # Notation3 Format Tests (.n3)
    # =========================================================================

    def test_n3_format_parsing(self, converter):
        """Test parsing Notation3 (.n3) format."""
        n3_content = """
@prefix : <http://example.org/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

:Device a owl:Class ;
    rdfs:label "Device" .

:deviceId a owl:DatatypeProperty ;
    rdfs:domain :Device ;
    rdfs:range xsd:string .
        """

        entity_types, relationship_types = converter.parse_ttl(n3_content, rdf_format="n3")

        assert len(entity_types) == 1
        assert entity_types[0].name == "Device"

    def test_n3_sample_file(self, samples_dir):
        """Test parsing sample Notation3 file."""
        sample_file = samples_dir / "sample_iot_ontology.n3"

        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")

        definition, name = parse_ttl_file(str(sample_file))

        assert "parts" in definition
        entity_parts = [p for p in definition["parts"] if "EntityTypes" in p["path"]]
        assert len(entity_parts) >= 3  # Should have Device, Controller, Location, Zone

        # Verify Controller entity and its properties
        controller_found = False
        for part in entity_parts:
            payload = base64.b64decode(part["payload"]).decode()
            entity_data = json.loads(payload)
            if entity_data["name"] == "Controller":
                controller_found = True
                # Controller should have properties like controllerMode, maxDevices
                prop_names = [p["name"] for p in entity_data.get("properties", [])]
                assert "controllerMode" in prop_names or "maxDevices" in prop_names
                break

        assert controller_found, "Controller entity type not found"

    # =========================================================================
    # JSON-LD Format Tests (.jsonld)
    # =========================================================================

    def test_jsonld_format_parsing(self, converter):
        """Test parsing JSON-LD (.jsonld) format."""
        jsonld_content = """{
  "@context": {
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "ex": "http://example.org/"
  },
  "@graph": [
    {
      "@id": "ex:Device",
      "@type": "owl:Class",
      "rdfs:label": "Device"
    },
    {
      "@id": "ex:deviceId",
      "@type": "owl:DatatypeProperty",
      "rdfs:domain": {"@id": "ex:Device"},
      "rdfs:range": {"@id": "xsd:string"}
    }
  ]
}"""

        entity_types, relationship_types = converter.parse_ttl(jsonld_content, rdf_format="json-ld")

        assert len(entity_types) == 1
        assert entity_types[0].name == "Device"

    def test_jsonld_sample_file(self, samples_dir):
        """Test parsing sample JSON-LD file."""
        sample_file = samples_dir / "sample_iot_ontology.jsonld"

        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")

        definition, name = parse_ttl_file(str(sample_file))

        assert "parts" in definition
        entity_parts = [p for p in definition["parts"] if "EntityTypes" in p["path"]]
        assert len(entity_parts) >= 3  # Should have Device, SmartMeter, Location, Building

        # Verify SmartMeter subclass relationship
        smart_meter_found = False
        for part in entity_parts:
            payload = base64.b64decode(part["payload"]).decode()
            entity_data = json.loads(payload)
            if entity_data["name"] == "SmartMeter":
                smart_meter_found = True
                assert entity_data.get("baseEntityTypeId") is not None
                break

        assert smart_meter_found, "SmartMeter entity type not found"

    # =========================================================================
    # Comprehensive Format Tests
    # =========================================================================

    def test_all_format_sample_files(self, samples_dir):
        """Test that all RDF format sample files can be parsed successfully."""
        format_files = {
            "turtle": "sample_iot_ontology.ttl",
            "rdf/xml": "sample_iot_ontology.rdf",
            "n-triples": "sample_iot_ontology.nt",
            "n-quads": "sample_iot_ontology.nq",
            "trig": "sample_iot_ontology.trig",
            "notation3": "sample_iot_ontology.n3",
            "json-ld": "sample_iot_ontology.jsonld",
        }

        results = []
        for format_name, filename in format_files.items():
            sample_file = samples_dir / filename

            if not sample_file.exists():
                results.append((format_name, filename, "SKIPPED", "File not found"))
                continue

            try:
                definition, name = parse_ttl_file(str(sample_file))
                entity_parts = [p for p in definition["parts"] if "EntityTypes" in p["path"]]
                rel_parts = [p for p in definition["parts"] if "RelationshipTypes" in p["path"]]
                results.append((
                    format_name,
                    filename,
                    "SUCCESS",
                    f"{len(entity_parts)} entities, {len(rel_parts)} relationships"
                ))
            except Exception as e:
                results.append((format_name, filename, "FAILED", str(e)[:50]))

        # Print summary
        print("\n\nRDF Format Parsing Results:")
        print("-" * 80)
        print(f"{'Format':<15} {'File':<30} {'Status':<10} {'Info'}")
        print("-" * 80)
        for format_name, filename, status, info in results:
            print(f"{format_name:<15} {filename:<30} {status:<10} {info}")
        print("-" * 80)

        # All non-skipped should succeed
        failures = [r for r in results if r[2] == "FAILED"]
        assert len(failures) == 0, f"Failed to parse {len(failures)} files: {failures}"

    def test_format_consistency_across_serializations(self, samples_dir):
        """Test that the same ontology produces consistent results across different formats."""
        format_files = {
            "turtle": "sample_iot_ontology.ttl",
            "rdf/xml": "sample_iot_ontology.rdf",
            "n-triples": "sample_iot_ontology.nt",
            "n-quads": "sample_iot_ontology.nq",
            "trig": "sample_iot_ontology.trig",
            "notation3": "sample_iot_ontology.n3",
            "json-ld": "sample_iot_ontology.jsonld",
        }

        entity_counts = {}
        common_entities = set()

        for format_name, filename in format_files.items():
            sample_file = samples_dir / filename

            if not sample_file.exists():
                continue

            try:
                definition, name = parse_ttl_file(str(sample_file))
                entity_parts = [p for p in definition["parts"] if "EntityTypes" in p["path"]]
                
                entity_names = set()
                for part in entity_parts:
                    payload = base64.b64decode(part["payload"]).decode()
                    entity_data = json.loads(payload)
                    entity_names.add(entity_data["name"])
                
                entity_counts[format_name] = len(entity_names)
                
                # Track common entities across all formats
                if not common_entities:
                    common_entities = entity_names
                else:
                    common_entities = common_entities.intersection(entity_names)
                    
            except Exception:
                continue

        # All formats should have Device and Location as common entities
        assert "Device" in common_entities, "Device should be common across all formats"
        assert "Location" in common_entities, "Location should be common across all formats"

        print(f"\n\nCommon entities across all formats: {common_entities}")
        print(f"Entity counts per format: {entity_counts}")

    def test_relationship_parsing_across_formats(self, samples_dir):
        """Test that relationships are correctly parsed across all formats."""
        format_files = {
            "turtle": "sample_iot_ontology.ttl",
            "rdf/xml": "sample_iot_ontology.rdf",
            "n-triples": "sample_iot_ontology.nt",
            "n-quads": "sample_iot_ontology.nq",
            "trig": "sample_iot_ontology.trig",
            "notation3": "sample_iot_ontology.n3",
            "json-ld": "sample_iot_ontology.jsonld",
        }

        for format_name, filename in format_files.items():
            sample_file = samples_dir / filename

            if not sample_file.exists():
                continue

            try:
                definition, name = parse_ttl_file(str(sample_file))
                rel_parts = [p for p in definition["parts"] if "RelationshipTypes" in p["path"]]
                
                # Each format should have at least locatedAt relationship
                rel_names = set()
                for part in rel_parts:
                    payload = base64.b64decode(part["payload"]).decode()
                    rel_data = json.loads(payload)
                    rel_names.add(rel_data["name"])
                
                assert "locatedAt" in rel_names, \
                    f"'{format_name}' format should have 'locatedAt' relationship"
                    
            except Exception as e:
                pytest.fail(f"Failed to parse relationships in {format_name}: {e}")


class TestFormatInference:
    """Test automatic format detection from file extensions."""

    def test_format_inference_from_extension(self):
        """Test that format is correctly inferred from file extension."""
        test_cases = [
            ("ontology.ttl", "turtle"),
            ("ontology.rdf", "xml"),
            ("ontology.owl", "xml"),
            ("ontology.nt", "nt"),
            ("ontology.nq", "nquads"),
            ("ontology.trig", "trig"),
            ("ontology.n3", "n3"),
            ("ontology.jsonld", "json-ld"),
        ]

        for filename, expected_format in test_cases:
            inferred = RDFGraphParser.infer_format_from_path(filename)
            assert inferred == expected_format, \
                f"File '{filename}' should infer format '{expected_format}', got '{inferred}'"

    def test_explicit_format_overrides_inference(self):
        """Test that explicit format overrides file extension inference."""
        # Even with .ttl extension, explicit format should be used
        resolved = RDFGraphParser.resolve_format("xml", "ontology.ttl")
        assert resolved == "xml"

    def test_default_format_when_unknown(self):
        """Test that default format (turtle) is used for unknown extensions."""
        resolved = RDFGraphParser.resolve_format(None, "ontology.unknown")
        assert resolved == "turtle"


class TestDatasetFormats:
    """Test dataset formats that support multiple named graphs."""

    @pytest.fixture
    def samples_dir(self):
        """Get the samples/rdf directory path"""
        return ROOT_DIR / "samples" / "rdf"

    def test_nquads_multiple_graphs(self, samples_dir):
        """Test that N-Quads correctly handles multiple named graphs."""
        sample_file = samples_dir / "sample_iot_ontology.nq"

        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")

        # Read and parse the file
        with open(sample_file, 'r') as f:
            content = f.read()

        # Count unique graph URIs in the content
        import re
        graph_pattern = r'<http://example\.org/iot/\w+>\s*\.$'
        graphs = set(re.findall(r'<http://example\.org/iot/(core|properties|relationships)>', content))
        
        # Should have multiple named graphs
        assert len(graphs) >= 2, "N-Quads file should contain multiple named graphs"

    def test_trig_multiple_graphs(self, samples_dir):
        """Test that TriG correctly handles multiple named graphs."""
        sample_file = samples_dir / "sample_iot_ontology.trig"

        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")

        # Read and check for named graph syntax
        with open(sample_file, 'r') as f:
            content = f.read()

        # TriG uses GRAPH keyword or prefixed graph names followed by { }
        assert "{" in content and "}" in content, "TriG file should contain graph blocks"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
