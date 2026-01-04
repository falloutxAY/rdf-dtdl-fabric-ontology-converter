"""
Tests for the Common Streaming Engine

Tests cover:
- StreamConfig configuration
- StreamStats statistics collection
- RDF streaming (RDFStreamReader, RDFChunkProcessor)
- DTDL streaming (DTDLStreamReader, DTDLChunkProcessor)
- StreamingEngine orchestration
- Adapters for existing converters
- Utility functions
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, List
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from src.core.streaming import (
    StreamFormat,
    StreamConfig,
    StreamStats,
    StreamResult,
    ChunkProcessor,
    StreamReader,
    StreamingEngine,
    RDFChunk,
    RDFPartialResult,
    RDFStreamReader,
    RDFChunkProcessor,
    DTDLChunk,
    DTDLPartialResult,
    DTDLStreamReader,
    DTDLChunkProcessor,
    RDFStreamAdapter,
    DTDLStreamAdapter,
    should_use_streaming,
    get_streaming_threshold,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_ttl_file(tmp_path):
    """Create a sample TTL file for testing."""
    content = """
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

ex:Person a owl:Class ;
    rdfs:label "Person" .

ex:Organization a owl:Class ;
    rdfs:label "Organization" .

ex:name a owl:DatatypeProperty ;
    rdfs:domain ex:Person ;
    rdfs:range xsd:string .

ex:worksFor a owl:ObjectProperty ;
    rdfs:domain ex:Person ;
    rdfs:range ex:Organization .
"""
    file_path = tmp_path / "sample.ttl"
    file_path.write_text(content)
    return str(file_path)


@pytest.fixture
def sample_dtdl_file(tmp_path):
    """Create a sample DTDL file for testing."""
    content = [
        {
            "@context": "dtmi:dtdl:context;3",
            "@id": "dtmi:com:example:Thermostat;1",
            "@type": "Interface",
            "displayName": "Thermostat",
            "contents": [
                {
                    "@type": "Property",
                    "name": "temperature",
                    "schema": "double"
                },
                {
                    "@type": "Property",
                    "name": "humidity",
                    "schema": "double"
                },
                {
                    "@type": "Relationship",
                    "name": "room",
                    "target": "dtmi:com:example:Room;1"
                }
            ]
        },
        {
            "@context": "dtmi:dtdl:context;3",
            "@id": "dtmi:com:example:Room;1",
            "@type": "Interface",
            "displayName": "Room",
            "contents": [
                {
                    "@type": "Property",
                    "name": "name",
                    "schema": "string"
                },
                {
                    "@type": "Component",
                    "name": "sensor",
                    "schema": "dtmi:com:example:Thermostat;1"
                }
            ]
        }
    ]
    file_path = tmp_path / "sample.json"
    file_path.write_text(json.dumps(content, indent=2))
    return str(file_path)


@pytest.fixture
def sample_dtdl_directory(tmp_path):
    """Create a directory with multiple DTDL files."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    
    # File 1: Thermostat
    thermostat = {
        "@context": "dtmi:dtdl:context;3",
        "@id": "dtmi:com:example:Thermostat;1",
        "@type": "Interface",
        "displayName": "Thermostat",
        "contents": [
            {"@type": "Property", "name": "temperature", "schema": "double"}
        ]
    }
    (models_dir / "thermostat.json").write_text(json.dumps(thermostat, indent=2))
    
    # File 2: Room
    room = {
        "@context": "dtmi:dtdl:context;3",
        "@id": "dtmi:com:example:Room;1",
        "@type": "Interface",
        "displayName": "Room",
        "contents": [
            {"@type": "Property", "name": "name", "schema": "string"}
        ]
    }
    (models_dir / "room.json").write_text(json.dumps(room, indent=2))
    
    # Subdirectory with more files
    subdir = models_dir / "devices"
    subdir.mkdir()
    
    sensor = {
        "@context": "dtmi:dtdl:context;3",
        "@id": "dtmi:com:example:Sensor;1",
        "@type": "Interface",
        "displayName": "Sensor",
        "contents": []
    }
    (subdir / "sensor.json").write_text(json.dumps(sensor, indent=2))
    
    return str(models_dir)


@pytest.fixture
def large_dtdl_file(tmp_path):
    """Create a large DTDL file with many interfaces."""
    interfaces = []
    for i in range(50):
        interface = {
            "@context": "dtmi:dtdl:context;3",
            "@id": f"dtmi:com:example:Interface{i};1",
            "@type": "Interface",
            "displayName": f"Interface {i}",
            "contents": [
                {"@type": "Property", "name": f"prop{j}", "schema": "string"}
                for j in range(20)
            ]
        }
        interfaces.append(interface)
    
    file_path = tmp_path / "large.json"
    file_path.write_text(json.dumps(interfaces, indent=2))
    return str(file_path)


# ============================================================================
# StreamConfig Tests
# ============================================================================

class TestStreamConfig:
    """Tests for StreamConfig class."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = StreamConfig()
        assert config.chunk_size == 10000
        assert config.memory_threshold_mb == 100.0
        assert config.max_memory_usage_mb == 512.0
        assert config.enable_progress is True
        assert config.format == StreamFormat.AUTO
        assert config.buffer_size_bytes == 65536
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = StreamConfig(
            chunk_size=5000,
            memory_threshold_mb=50.0,
            format=StreamFormat.DTDL
        )
        assert config.chunk_size == 5000
        assert config.memory_threshold_mb == 50.0
        assert config.format == StreamFormat.DTDL
    
    def test_should_use_streaming_below_threshold(self):
        """Test streaming not recommended for small files."""
        config = StreamConfig(memory_threshold_mb=100.0)
        assert config.should_use_streaming(50.0) is False
    
    def test_should_use_streaming_above_threshold(self):
        """Test streaming recommended for large files."""
        config = StreamConfig(memory_threshold_mb=100.0)
        assert config.should_use_streaming(150.0) is True
    
    def test_should_use_streaming_at_threshold(self):
        """Test streaming not used exactly at threshold."""
        config = StreamConfig(memory_threshold_mb=100.0)
        assert config.should_use_streaming(100.0) is False


# ============================================================================
# StreamStats Tests
# ============================================================================

class TestStreamStats:
    """Tests for StreamStats class."""
    
    def test_default_values(self):
        """Test default statistics values."""
        stats = StreamStats()
        assert stats.chunks_processed == 0
        assert stats.items_processed == 0
        assert stats.bytes_read == 0
        assert stats.errors_encountered == 0
        assert stats.warnings == []
        assert stats.peak_memory_mb == 0.0
        assert stats.duration_seconds == 0.0
    
    def test_add_warning(self):
        """Test adding warnings."""
        stats = StreamStats()
        stats.add_warning("Test warning 1")
        stats.add_warning("Test warning 2")
        assert len(stats.warnings) == 2
        assert "Test warning 1" in stats.warnings
    
    def test_get_summary(self):
        """Test summary generation."""
        stats = StreamStats(
            chunks_processed=5,
            items_processed=1000,
            bytes_read=1024000,
            duration_seconds=2.5
        )
        summary = stats.get_summary()
        assert "Chunks processed: 5" in summary
        assert "Items processed: 1,000" in summary
        assert "Processing rate:" in summary


# ============================================================================
# RDF Streaming Tests
# ============================================================================

class TestRDFStreamReader:
    """Tests for RDFStreamReader class."""
    
    def test_supports_format_ttl(self, tmp_path):
        """Test TTL format detection."""
        reader = RDFStreamReader()
        assert reader.supports_format(str(tmp_path / "test.ttl")) is True
        assert reader.supports_format(str(tmp_path / "test.rdf")) is True
        assert reader.supports_format(str(tmp_path / "test.owl")) is True
        assert reader.supports_format(str(tmp_path / "test.n3")) is True
    
    def test_supports_format_non_rdf(self, tmp_path):
        """Test non-RDF format detection."""
        reader = RDFStreamReader()
        assert reader.supports_format(str(tmp_path / "test.json")) is False
        assert reader.supports_format(str(tmp_path / "test.txt")) is False
    
    def test_get_total_size(self, sample_ttl_file):
        """Test file size calculation."""
        reader = RDFStreamReader()
        size = reader.get_total_size(sample_ttl_file)
        assert size > 0
        assert size == os.path.getsize(sample_ttl_file)
    
    def test_read_chunks(self, sample_ttl_file):
        """Test reading TTL file in chunks."""
        reader = RDFStreamReader()
        config = StreamConfig(chunk_size=5)
        
        chunks = list(reader.read_chunks(sample_ttl_file, config))
        assert len(chunks) > 0
        
        # Each chunk should be a tuple of (RDFChunk, bytes_read)
        for chunk, bytes_read in chunks:
            assert isinstance(chunk, RDFChunk)
            assert isinstance(chunk.triples, list)
            assert bytes_read > 0


class TestRDFChunkProcessor:
    """Tests for RDFChunkProcessor class."""
    
    def test_process_chunk_with_classes(self):
        """Test processing chunk with class declarations."""
        from rdflib import RDF, OWL, URIRef
        
        processor = RDFChunkProcessor()
        
        # Create chunk with class declaration
        class_uri = URIRef("http://example.org/Person")
        chunk = RDFChunk(
            triples=[(class_uri, RDF.type, OWL.Class)],
            chunk_index=0
        )
        
        result = processor.process_chunk(chunk, 0)
        assert len(result.classes) == 1
        assert str(class_uri) in result.classes
    
    def test_merge_results(self):
        """Test merging partial results."""
        processor = RDFChunkProcessor()
        
        result1 = RDFPartialResult(
            classes={"class1": {"uri": "class1"}},
            triple_count=10
        )
        result2 = RDFPartialResult(
            classes={"class2": {"uri": "class2"}},
            triple_count=15
        )
        
        merged = processor.merge_results([result1, result2])
        assert len(merged.classes) == 2
        assert merged.triple_count == 25
    
    def test_finalize(self):
        """Test finalizing results."""
        processor = RDFChunkProcessor()
        result = RDFPartialResult(
            classes={"class1": {}},
            properties={"prop1": {}},
            triple_count=100
        )
        
        finalized = processor.finalize(result)
        assert finalized == result


# ============================================================================
# DTDL Streaming Tests
# ============================================================================

class TestDTDLStreamReader:
    """Tests for DTDLStreamReader class."""
    
    def test_supports_format_json(self, tmp_path):
        """Test JSON format detection."""
        reader = DTDLStreamReader()
        assert reader.supports_format(str(tmp_path / "test.json")) is True
        assert reader.supports_format(str(tmp_path / "test.dtdl")) is True
    
    def test_supports_format_directory(self, tmp_path):
        """Test directory format detection."""
        reader = DTDLStreamReader()
        assert reader.supports_format(str(tmp_path)) is True
    
    def test_supports_format_non_dtdl(self, tmp_path):
        """Test non-DTDL format detection."""
        reader = DTDLStreamReader()
        assert reader.supports_format(str(tmp_path / "test.ttl")) is False
        assert reader.supports_format(str(tmp_path / "test.xml")) is False
    
    def test_get_total_size_file(self, sample_dtdl_file):
        """Test file size calculation."""
        reader = DTDLStreamReader()
        size = reader.get_total_size(sample_dtdl_file)
        assert size > 0
        assert size == os.path.getsize(sample_dtdl_file)
    
    def test_get_total_size_directory(self, sample_dtdl_directory):
        """Test directory size calculation."""
        reader = DTDLStreamReader()
        size = reader.get_total_size(sample_dtdl_directory)
        assert size > 0
    
    def test_read_chunks_single_file(self, sample_dtdl_file):
        """Test reading single DTDL file."""
        reader = DTDLStreamReader()
        config = StreamConfig(chunk_size=1)
        
        chunks = list(reader.read_chunks(sample_dtdl_file, config))
        assert len(chunks) >= 1
        
        total_interfaces = sum(len(chunk.interfaces) for chunk, _ in chunks)
        assert total_interfaces == 2  # Two interfaces in sample file
    
    def test_read_chunks_directory(self, sample_dtdl_directory):
        """Test reading directory of DTDL files."""
        reader = DTDLStreamReader()
        config = StreamConfig(chunk_size=10)
        
        chunks = list(reader.read_chunks(sample_dtdl_directory, config))
        assert len(chunks) >= 1
        
        total_interfaces = sum(len(chunk.interfaces) for chunk, _ in chunks)
        assert total_interfaces == 3  # Three files with one interface each
    
    def test_read_chunks_with_array(self, sample_dtdl_file):
        """Test reading file with array of interfaces."""
        reader = DTDLStreamReader()
        config = StreamConfig(chunk_size=100)
        
        chunks = list(reader.read_chunks(sample_dtdl_file, config))
        
        # All interfaces should be in the chunks
        all_interfaces = []
        for chunk, _ in chunks:
            all_interfaces.extend(chunk.interfaces)
        
        dtmis = [i.get("@id") for i in all_interfaces]
        assert "dtmi:com:example:Thermostat;1" in dtmis
        assert "dtmi:com:example:Room;1" in dtmis


class TestDTDLChunkProcessor:
    """Tests for DTDLChunkProcessor class."""
    
    def test_process_chunk(self):
        """Test processing DTDL chunk."""
        processor = DTDLChunkProcessor()
        
        interfaces = [
            {
                "@type": "Interface",
                "@id": "dtmi:test:Interface1;1",
                "contents": [
                    {"@type": "Property", "name": "prop1"},
                    {"@type": "Relationship", "name": "rel1"},
                    {"@type": "Component", "name": "comp1"}
                ]
            }
        ]
        
        chunk = DTDLChunk(interfaces=interfaces, chunk_index=0)
        result = processor.process_chunk(chunk, 0)
        
        assert result.interface_count == 1
        assert result.property_count == 1
        assert result.relationship_count == 1
        assert result.component_count == 1
    
    def test_merge_results(self):
        """Test merging partial results."""
        processor = DTDLChunkProcessor()
        
        result1 = DTDLPartialResult(
            interfaces=[{"@id": "interface1"}],
            interface_count=1,
            property_count=5
        )
        result2 = DTDLPartialResult(
            interfaces=[{"@id": "interface2"}],
            interface_count=1,
            property_count=3
        )
        
        merged = processor.merge_results([result1, result2])
        assert merged.interface_count == 2
        assert merged.property_count == 8
        assert len(merged.interfaces) == 2
    
    def test_finalize(self):
        """Test finalizing results."""
        processor = DTDLChunkProcessor()
        result = DTDLPartialResult(
            interface_count=5,
            property_count=20
        )
        
        finalized = processor.finalize(result)
        assert finalized == result


# ============================================================================
# StreamingEngine Tests
# ============================================================================

class TestStreamingEngine:
    """Tests for StreamingEngine class."""
    
    def test_process_nonexistent_file(self, tmp_path):
        """Test processing non-existent file."""
        engine = StreamingEngine()
        result = engine.process_file(str(tmp_path / "nonexistent.json"))
        
        assert result.success is False
        assert "not found" in result.error_message.lower()
    
    def test_process_dtdl_file(self, sample_dtdl_file):
        """Test processing DTDL file."""
        engine = StreamingEngine(
            reader=DTDLStreamReader(),
            processor=DTDLChunkProcessor()
        )
        
        result = engine.process_file(sample_dtdl_file)
        
        assert result.success is True
        assert result.data is not None
        assert result.data.interface_count == 2
    
    def test_process_with_progress_callback(self, sample_dtdl_file):
        """Test processing with progress callback."""
        progress_calls = []
        
        def progress_callback(count):
            progress_calls.append(count)
        
        engine = StreamingEngine(
            reader=DTDLStreamReader(),
            processor=DTDLChunkProcessor()
        )
        
        result = engine.process_file(
            sample_dtdl_file,
            progress_callback=progress_callback
        )
        
        assert result.success is True
        # Progress should be called at least once
        assert len(progress_calls) >= 1
    
    def test_process_with_cancellation(self, sample_dtdl_file):
        """Test processing with cancellation."""
        
        class MockCancellationToken:
            def __init__(self):
                self.cancelled = False
            
            def throw_if_cancelled(self):
                if self.cancelled:
                    raise Exception("Operation cancelled")
        
        token = MockCancellationToken()
        
        engine = StreamingEngine(
            reader=DTDLStreamReader(),
            processor=DTDLChunkProcessor()
        )
        
        # Should succeed without cancellation
        result = engine.process_file(sample_dtdl_file, cancellation_token=token)
        assert result.success is True
    
    def test_auto_select_reader_ttl(self, sample_ttl_file):
        """Test auto-selecting reader for TTL files."""
        engine = StreamingEngine()
        reader = engine._auto_select_reader(sample_ttl_file)
        assert isinstance(reader, RDFStreamReader)
    
    def test_auto_select_reader_json(self, sample_dtdl_file):
        """Test auto-selecting reader for JSON files."""
        engine = StreamingEngine()
        reader = engine._auto_select_reader(sample_dtdl_file)
        assert isinstance(reader, DTDLStreamReader)
    
    def test_statistics_collection(self, sample_dtdl_file):
        """Test statistics are collected during processing."""
        engine = StreamingEngine(
            reader=DTDLStreamReader(),
            processor=DTDLChunkProcessor()
        )
        
        result = engine.process_file(sample_dtdl_file)
        
        assert result.stats.chunks_processed >= 1
        assert result.stats.bytes_read > 0
        assert result.stats.duration_seconds >= 0


# ============================================================================
# Adapter Tests
# ============================================================================

class TestRDFStreamAdapter:
    """Tests for RDFStreamAdapter class."""
    
    def test_initialization(self):
        """Test adapter initialization."""
        adapter = RDFStreamAdapter(
            id_prefix=2000000000000,
            batch_size=5000
        )
        assert adapter.id_prefix == 2000000000000
        assert adapter.batch_size == 5000
    
    @pytest.mark.skip(reason="Requires full RDF conversion infrastructure")
    def test_convert_streaming(self, sample_ttl_file):
        """Test streaming conversion."""
        adapter = RDFStreamAdapter()
        result = adapter.convert_streaming(sample_ttl_file)
        assert result is not None


class TestDTDLStreamAdapter:
    """Tests for DTDLStreamAdapter class."""
    
    def test_initialization(self):
        """Test adapter initialization."""
        adapter = DTDLStreamAdapter(
            ontology_name="TestOntology",
            namespace="custom_ns"
        )
        assert adapter.ontology_name == "TestOntology"
        assert adapter.namespace == "custom_ns"

    def test_convert_streaming_produces_definition(self, sample_dtdl_file):
        """Ensure adapter returns Fabric definition payload."""
        adapter = DTDLStreamAdapter(ontology_name="TestOntology")
        result = adapter.convert_streaming(sample_dtdl_file)

        assert result.success is True
        payload = result.data
        assert payload is not None
        assert "definition" in payload
        assert isinstance(payload["definition"], dict)
        assert payload["conversion_result"].entity_types


# ============================================================================
# Utility Function Tests
# ============================================================================

class TestUtilityFunctions:
    """Tests for utility functions."""
    
    def test_should_use_streaming_small_file(self, sample_dtdl_file):
        """Test streaming not recommended for small files."""
        assert should_use_streaming(sample_dtdl_file, threshold_mb=1000) is False
    
    def test_should_use_streaming_threshold_check(self, tmp_path):
        """Test streaming threshold check."""
        # Create a file and check against different thresholds
        test_file = tmp_path / "test.json"
        test_file.write_text("x" * 1024 * 1024)  # 1MB file
        
        assert should_use_streaming(str(test_file), threshold_mb=0.5) is True
        assert should_use_streaming(str(test_file), threshold_mb=2.0) is False
    
    def test_should_use_streaming_directory(self, sample_dtdl_directory):
        """Test streaming check for directories."""
        result = should_use_streaming(sample_dtdl_directory, threshold_mb=1000)
        assert result is False  # Small directory
    
    def test_get_streaming_threshold(self):
        """Test getting streaming threshold."""
        threshold = get_streaming_threshold()
        assert threshold > 0
        assert isinstance(threshold, float)


# ============================================================================
# Integration Tests
# ============================================================================

class TestStreamingIntegration:
    """Integration tests for streaming functionality."""
    
    def test_full_dtdl_streaming_pipeline(self, large_dtdl_file):
        """Test complete DTDL streaming pipeline."""
        config = StreamConfig(chunk_size=10)
        
        engine = StreamingEngine(
            reader=DTDLStreamReader(),
            processor=DTDLChunkProcessor(),
            config=config
        )
        
        result = engine.process_file(large_dtdl_file)
        
        assert result.success is True
        assert result.data.interface_count == 50
        assert result.data.property_count == 1000  # 50 interfaces × 20 properties
        assert result.stats.chunks_processed >= 5  # At least 5 chunks of 10
    
    def test_directory_streaming(self, sample_dtdl_directory):
        """Test streaming from directory."""
        engine = StreamingEngine(
            reader=DTDLStreamReader(),
            processor=DTDLChunkProcessor()
        )
        
        result = engine.process_file(sample_dtdl_directory)
        
        assert result.success is True
        assert result.data.interface_count == 3


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_json_file(self, tmp_path):
        """Test handling empty JSON array."""
        file_path = tmp_path / "empty.json"
        file_path.write_text("[]")
        
        engine = StreamingEngine(
            reader=DTDLStreamReader(),
            processor=DTDLChunkProcessor()
        )
        
        result = engine.process_file(str(file_path))
        assert result.success is True
        assert result.data.interface_count == 0
    
    def test_invalid_json_file(self, tmp_path):
        """Test handling invalid JSON."""
        file_path = tmp_path / "invalid.json"
        file_path.write_text("{ invalid json }")
        
        reader = DTDLStreamReader()
        config = StreamConfig()
        
        with pytest.raises(json.JSONDecodeError):
            list(reader.read_chunks(str(file_path), config))
    
    def test_single_interface_file(self, tmp_path):
        """Test handling single interface (not array)."""
        interface = {
            "@context": "dtmi:dtdl:context;3",
            "@id": "dtmi:com:example:Single;1",
            "@type": "Interface",
            "displayName": "Single Interface",
            "contents": []
        }
        
        file_path = tmp_path / "single.json"
        file_path.write_text(json.dumps(interface))
        
        engine = StreamingEngine(
            reader=DTDLStreamReader(),
            processor=DTDLChunkProcessor()
        )
        
        result = engine.process_file(str(file_path))
        assert result.success is True
        assert result.data.interface_count == 1
    
    def test_mixed_content_file(self, tmp_path):
        """Test handling file with interfaces and non-interfaces."""
        content = [
            {
                "@context": "dtmi:dtdl:context;3",
                "@id": "dtmi:com:example:Valid;1",
                "@type": "Interface",
                "contents": []
            },
            {
                "@type": "SomeOtherType",
                "name": "not an interface"
            }
        ]
        
        file_path = tmp_path / "mixed.json"
        file_path.write_text(json.dumps(content))
        
        reader = DTDLStreamReader()
        config = StreamConfig()
        
        chunks = list(reader.read_chunks(str(file_path), config))
        total_interfaces = sum(len(chunk.interfaces) for chunk, _ in chunks)
        
        # Only valid Interface types should be included
        assert total_interfaces == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
