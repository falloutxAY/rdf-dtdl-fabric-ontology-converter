"""
Tests for StreamingRDFConverter - Memory-efficient streaming parser for large ontologies.

Tests cover:
- Basic streaming conversion functionality
- Phase-based processing (classes, properties, relationships)
- Progress callback support
- Cancellation token support
- Error handling for invalid files
- Comparison with standard converter output
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from rdf_converter import (
    StreamingRDFConverter,
    RDFToFabricConverter,
    parse_ttl_streaming,
    parse_ttl_with_result,
    ConversionResult,
    EntityType,
    RelationshipType,
    SkippedItem
)


class TestStreamingRDFConverterBasic:
    """Test basic StreamingRDFConverter functionality."""
    
    def test_init_default_values(self):
        """Test converter initialization with default values."""
        converter = StreamingRDFConverter()
        
        assert converter.id_prefix == 1000000000000
        assert converter.batch_size == StreamingRDFConverter.DEFAULT_BATCH_SIZE
        assert converter.loose_inference is False
        assert converter.id_counter == 0
        assert len(converter.entity_types) == 0
        assert len(converter.relationship_types) == 0
    
    def test_init_custom_values(self):
        """Test converter initialization with custom values."""
        converter = StreamingRDFConverter(
            id_prefix=5000000000000,
            batch_size=5000,
            loose_inference=True
        )
        
        assert converter.id_prefix == 5000000000000
        assert converter.batch_size == 5000
        assert converter.loose_inference is True
    
    def test_reset_state(self):
        """Test state reset between conversions."""
        converter = StreamingRDFConverter()
        
        # Simulate some state
        converter.id_counter = 100
        converter.entity_types['test'] = Mock()
        converter.skipped_items.append(Mock())
        
        converter._reset_state()
        
        assert converter.id_counter == 0
        assert len(converter.entity_types) == 0
        assert len(converter.skipped_items) == 0
    
    def test_generate_id(self):
        """Test unique ID generation."""
        converter = StreamingRDFConverter(id_prefix=1000)
        
        id1 = converter._generate_id()
        id2 = converter._generate_id()
        id3 = converter._generate_id()
        
        assert id1 == "1001"
        assert id2 == "1002"
        assert id3 == "1003"
    
    def test_uri_to_name_fragment(self):
        """Test name extraction from URI with fragment."""
        from rdflib import URIRef
        converter = StreamingRDFConverter()
        
        uri = URIRef("http://example.org/ontology#PersonClass")
        name = converter._uri_to_name(uri)
        
        assert name == "PersonClass"
    
    def test_uri_to_name_path(self):
        """Test name extraction from URI with path."""
        from rdflib import URIRef
        converter = StreamingRDFConverter()
        
        uri = URIRef("http://example.org/ontology/PersonClass")
        name = converter._uri_to_name(uri)
        
        assert name == "PersonClass"
    
    def test_uri_to_name_special_chars(self):
        """Test name cleaning for special characters."""
        from rdflib import URIRef
        converter = StreamingRDFConverter()
        
        uri = URIRef("http://example.org/ontology#Person-Class.Name")
        name = converter._uri_to_name(uri)
        
        # Special chars should be replaced with underscore
        assert name == "Person_Class_Name"
    
    def test_uri_to_name_starts_with_number(self):
        """Test name cleaning when starting with number."""
        from rdflib import URIRef
        converter = StreamingRDFConverter()
        
        uri = URIRef("http://example.org/ontology#123Entity")
        name = converter._uri_to_name(uri)
        
        # Should be prefixed with E_ since it starts with number
        assert name.startswith("E_")


class TestStreamingParserWithFiles:
    """Test streaming parser with actual TTL files."""
    
    @pytest.fixture
    def simple_ttl_content(self):
        """Simple ontology for basic tests."""
        return """
        @prefix : <http://example.org/ontology#> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        
        :Person a owl:Class .
        :Organization a owl:Class .
        
        :name a owl:DatatypeProperty ;
            rdfs:domain :Person ;
            rdfs:range xsd:string .
        
        :age a owl:DatatypeProperty ;
            rdfs:domain :Person ;
            rdfs:range xsd:integer .
        
        :worksFor a owl:ObjectProperty ;
            rdfs:domain :Person ;
            rdfs:range :Organization .
        """
    
    @pytest.fixture
    def temp_ttl_file(self, simple_ttl_content):
        """Create a temporary TTL file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False, encoding='utf-8') as f:
            f.write(simple_ttl_content)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_parse_simple_ontology(self, temp_ttl_file):
        """Test parsing a simple ontology file."""
        converter = StreamingRDFConverter()
        result = converter.parse_ttl_streaming(temp_ttl_file)
        
        assert isinstance(result, ConversionResult)
        assert len(result.entity_types) == 2  # Person, Organization
        assert len(result.relationship_types) == 1  # worksFor
        assert result.triple_count > 0
    
    def test_entity_types_extracted(self, temp_ttl_file):
        """Test that entity types are correctly extracted."""
        converter = StreamingRDFConverter()
        result = converter.parse_ttl_streaming(temp_ttl_file)
        
        entity_names = {e.name for e in result.entity_types}
        assert "Person" in entity_names
        assert "Organization" in entity_names
    
    def test_data_properties_extracted(self, temp_ttl_file):
        """Test that data properties are correctly assigned to entities."""
        converter = StreamingRDFConverter()
        result = converter.parse_ttl_streaming(temp_ttl_file)
        
        person_entity = next((e for e in result.entity_types if e.name == "Person"), None)
        assert person_entity is not None
        
        prop_names = {p.name for p in person_entity.properties}
        assert "name" in prop_names
        assert "age" in prop_names
    
    def test_relationships_extracted(self, temp_ttl_file):
        """Test that relationships are correctly extracted."""
        converter = StreamingRDFConverter()
        result = converter.parse_ttl_streaming(temp_ttl_file)
        
        assert len(result.relationship_types) == 1
        rel = result.relationship_types[0]
        assert rel.name == "worksFor"
    
    def test_progress_callback_called(self, temp_ttl_file):
        """Test that progress callback is called during parsing."""
        converter = StreamingRDFConverter()
        progress_values = []
        
        def progress_callback(n):
            progress_values.append(n)
        
        result = converter.parse_ttl_streaming(
            temp_ttl_file,
            progress_callback=progress_callback
        )
        
        # Progress callback should be called at least once
        assert len(progress_values) >= 1
        # Final value should be total triples
        assert progress_values[-1] == result.triple_count
    
    def test_file_not_found_raises(self):
        """Test that FileNotFoundError is raised for missing files."""
        converter = StreamingRDFConverter()
        
        with pytest.raises(FileNotFoundError):
            converter.parse_ttl_streaming("/nonexistent/path/file.ttl")
    
    def test_invalid_ttl_raises(self):
        """Test that ValueError is raised for invalid TTL content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
            f.write("this is not valid turtle syntax {{{{")
            temp_path = f.name
        
        try:
            converter = StreamingRDFConverter()
            with pytest.raises(ValueError, match="Invalid RDF/TTL"):
                converter.parse_ttl_streaming(temp_path)
        finally:
            os.unlink(temp_path)


class TestStreamingVsStandardConverter:
    """Compare streaming converter output with standard converter."""
    
    @pytest.fixture
    def sample_ttl_content(self):
        """Sample ontology for comparison tests."""
        return """
        @prefix : <http://example.org/test#> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        
        :Animal a owl:Class .
        :Dog a owl:Class ;
            rdfs:subClassOf :Animal .
        :Cat a owl:Class ;
            rdfs:subClassOf :Animal .
        
        :name a owl:DatatypeProperty ;
            rdfs:domain :Animal ;
            rdfs:range xsd:string .
        
        :age a owl:DatatypeProperty ;
            rdfs:domain :Animal ;
            rdfs:range xsd:integer .
        
        :chases a owl:ObjectProperty ;
            rdfs:domain :Dog ;
            rdfs:range :Cat .
        """
    
    def test_same_entity_count(self, sample_ttl_content):
        """Test that streaming and standard converters produce same entity count."""
        # Standard converter
        standard = RDFToFabricConverter()
        standard_entities, _ = standard.parse_ttl(sample_ttl_content)
        
        # Streaming converter (write to temp file)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False, encoding='utf-8') as f:
            f.write(sample_ttl_content)
            temp_path = f.name
        
        try:
            streaming = StreamingRDFConverter()
            result = streaming.parse_ttl_streaming(temp_path)
            
            assert len(result.entity_types) == len(standard_entities)
        finally:
            os.unlink(temp_path)
    
    def test_same_entity_names(self, sample_ttl_content):
        """Test that streaming and standard converters produce same entity names."""
        standard = RDFToFabricConverter()
        standard_entities, _ = standard.parse_ttl(sample_ttl_content)
        standard_names = {e.name for e in standard_entities}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False, encoding='utf-8') as f:
            f.write(sample_ttl_content)
            temp_path = f.name
        
        try:
            streaming = StreamingRDFConverter()
            result = streaming.parse_ttl_streaming(temp_path)
            streaming_names = {e.name for e in result.entity_types}
            
            assert streaming_names == standard_names
        finally:
            os.unlink(temp_path)
    
    def test_same_relationship_count(self, sample_ttl_content):
        """Test that streaming and standard converters produce same relationship count."""
        standard = RDFToFabricConverter()
        _, standard_rels = standard.parse_ttl(sample_ttl_content)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False, encoding='utf-8') as f:
            f.write(sample_ttl_content)
            temp_path = f.name
        
        try:
            streaming = StreamingRDFConverter()
            result = streaming.parse_ttl_streaming(temp_path)
            
            assert len(result.relationship_types) == len(standard_rels)
        finally:
            os.unlink(temp_path)


class TestParseTTLStreamingFunction:
    """Test the parse_ttl_streaming convenience function."""
    
    @pytest.fixture
    def temp_ontology_file(self):
        """Create a temp ontology file."""
        content = """
        @prefix : <http://example.org/test#> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        
        :Product a owl:Class .
        :productName a owl:DatatypeProperty ;
            rdfs:domain :Product ;
            rdfs:range xsd:string .
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        yield temp_path
        
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_returns_tuple(self, temp_ontology_file):
        """Test that function returns (definition, name, result) tuple."""
        definition, name, result = parse_ttl_streaming(temp_ontology_file)
        
        assert isinstance(definition, dict)
        assert isinstance(name, str)
        assert isinstance(result, ConversionResult)
    
    def test_definition_has_parts(self, temp_ontology_file):
        """Test that definition has parts array."""
        definition, _, _ = parse_ttl_streaming(temp_ontology_file)
        
        assert 'parts' in definition
        assert isinstance(definition['parts'], list)
    
    def test_name_derived_from_filename(self, temp_ontology_file):
        """Test that ontology name is derived from filename."""
        _, name, _ = parse_ttl_streaming(temp_ontology_file)
        
        # Name should be cleaned version of filename
        assert name  # Should not be empty
        assert name[0].isalpha()  # Should start with letter
    
    def test_custom_batch_size(self, temp_ontology_file):
        """Test custom batch size parameter."""
        definition, _, result = parse_ttl_streaming(
            temp_ontology_file,
            batch_size=100
        )
        
        assert isinstance(result, ConversionResult)
    
    def test_invalid_file_raises(self):
        """Test that invalid file path raises error."""
        with pytest.raises(FileNotFoundError):
            parse_ttl_streaming("/nonexistent/file.ttl")


class TestCancellationSupport:
    """Test cancellation token support in streaming converter."""
    
    @pytest.fixture
    def large_ttl_file(self):
        """Create a larger ontology for cancellation tests."""
        lines = [
            "@prefix : <http://example.org/test#> .",
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            ""
        ]
        
        # Create many classes
        for i in range(50):
            lines.append(f":Class{i} a owl:Class .")
        
        # Create many properties
        for i in range(50):
            lines.append(f":prop{i} a owl:DatatypeProperty ;")
            lines.append(f"    rdfs:domain :Class{i % 50} ;")
            lines.append(f"    rdfs:range xsd:string .")
        
        content = "\n".join(lines)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        yield temp_path
        
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_cancellation_token_checked(self, large_ttl_file):
        """Test that cancellation token is checked during parsing."""
        from cancellation import CancellationToken
        
        token = CancellationToken()
        check_count = [0]
        
        # Wrap throw_if_cancelled to count calls
        original_throw = token.throw_if_cancelled
        def counting_throw():
            check_count[0] += 1
            original_throw()
        token.throw_if_cancelled = counting_throw
        
        converter = StreamingRDFConverter()
        converter.parse_ttl_streaming(large_ttl_file, cancellation_token=token)
        
        # Should have checked for cancellation multiple times
        assert check_count[0] > 0
    
    def test_pre_cancelled_token_raises(self, large_ttl_file):
        """Test that pre-cancelled token raises immediately."""
        from cancellation import CancellationToken, OperationCancelledException
        
        token = CancellationToken()
        token.cancel()  # Pre-cancel
        
        converter = StreamingRDFConverter()
        
        with pytest.raises(OperationCancelledException):
            converter.parse_ttl_streaming(large_ttl_file, cancellation_token=token)


class TestSkippedItemTracking:
    """Test skipped item tracking in streaming converter."""
    
    @pytest.fixture
    def ttl_with_incomplete_properties(self):
        """TTL with properties missing domain/range."""
        return """
        @prefix : <http://example.org/test#> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        
        :Person a owl:Class .
        
        # Object property missing range
        :missingRange a owl:ObjectProperty ;
            rdfs:domain :Person .
        
        # Object property missing domain
        :missingDomain a owl:ObjectProperty ;
            rdfs:range :Person .
        
        # Object property missing both
        :missingBoth a owl:ObjectProperty .
        """
    
    def test_skipped_items_tracked(self, ttl_with_incomplete_properties):
        """Test that skipped items are tracked."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False, encoding='utf-8') as f:
            f.write(ttl_with_incomplete_properties)
            temp_path = f.name
        
        try:
            converter = StreamingRDFConverter()
            result = converter.parse_ttl_streaming(temp_path)
            
            # Should have skipped items
            assert len(result.skipped_items) > 0
            
            # Check skipped item types
            skipped_names = {item.name for item in result.skipped_items}
            assert "missingRange" in skipped_names or "missingDomain" in skipped_names
        finally:
            os.unlink(temp_path)


class TestSubclassHandling:
    """Test subclass (inheritance) handling in streaming converter."""
    
    @pytest.fixture
    def ttl_with_inheritance(self):
        """TTL with class inheritance."""
        return """
        @prefix : <http://example.org/test#> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        
        :Animal a owl:Class .
        :Mammal a owl:Class ;
            rdfs:subClassOf :Animal .
        :Dog a owl:Class ;
            rdfs:subClassOf :Mammal .
        """
    
    def test_parent_relationships_set(self, ttl_with_inheritance):
        """Test that parent relationships are correctly set."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False, encoding='utf-8') as f:
            f.write(ttl_with_inheritance)
            temp_path = f.name
        
        try:
            converter = StreamingRDFConverter()
            result = converter.parse_ttl_streaming(temp_path)
            
            # Find entities
            entities_by_name = {e.name: e for e in result.entity_types}
            
            assert "Animal" in entities_by_name
            assert "Mammal" in entities_by_name
            assert "Dog" in entities_by_name
            
            # Check parent relationships
            animal = entities_by_name["Animal"]
            mammal = entities_by_name["Mammal"]
            dog = entities_by_name["Dog"]
            
            assert animal.baseEntityTypeId is None  # Root class
            assert mammal.baseEntityTypeId == animal.id  # Mammal -> Animal
            assert dog.baseEntityTypeId == mammal.id  # Dog -> Mammal
        finally:
            os.unlink(temp_path)


class TestSampleOntologiesStreaming:
    """Test streaming converter with sample ontology files."""
    
    @pytest.fixture
    def samples_dir(self):
        """Get path to samples directory."""
        samples = Path(__file__).parent.parent / "samples"
        if not samples.exists():
            pytest.skip("samples directory not found")
        return samples
    
    def test_supply_chain_ontology(self, samples_dir):
        """Test streaming parser with supply chain sample."""
        ttl_file = samples_dir / "sample_supply_chain_ontology.ttl"
        if not ttl_file.exists():
            pytest.skip("supply chain sample not found")
        
        converter = StreamingRDFConverter()
        result = converter.parse_ttl_streaming(str(ttl_file))
        
        assert isinstance(result, ConversionResult)
        assert len(result.entity_types) > 0
        assert result.triple_count > 0
    
    def test_iot_ontology(self, samples_dir):
        """Test streaming parser with IoT sample."""
        ttl_file = samples_dir / "sample_iot_ontology.ttl"
        if not ttl_file.exists():
            pytest.skip("IoT sample not found")
        
        converter = StreamingRDFConverter()
        result = converter.parse_ttl_streaming(str(ttl_file))
        
        assert isinstance(result, ConversionResult)
        assert len(result.entity_types) > 0
    
    def test_foaf_ontology(self, samples_dir):
        """Test streaming parser with FOAF sample."""
        ttl_file = samples_dir / "sample_foaf_ontology.ttl"
        if not ttl_file.exists():
            pytest.skip("FOAF sample not found")
        
        converter = StreamingRDFConverter()
        result = converter.parse_ttl_streaming(str(ttl_file))
        
        assert isinstance(result, ConversionResult)
        # FOAF might have skipped items due to missing domain/range
        assert result.success_rate > 0


class TestStreamingThreshold:
    """Test streaming threshold constant."""
    
    def test_threshold_value(self):
        """Test that streaming threshold is set appropriately."""
        # Should be at least 50MB
        assert StreamingRDFConverter.STREAMING_THRESHOLD_MB >= 50
        
        # Should be reasonable (not too high)
        assert StreamingRDFConverter.STREAMING_THRESHOLD_MB <= 500
    
    def test_default_batch_size(self):
        """Test default batch size is reasonable."""
        assert StreamingRDFConverter.DEFAULT_BATCH_SIZE >= 1000
        assert StreamingRDFConverter.DEFAULT_BATCH_SIZE <= 100000
