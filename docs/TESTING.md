# Testing Documentation

## Overview

This document describes the comprehensive test suite for the RDF to Fabric Ontology Converter. The test suite ensures that the converter correctly parses RDF TTL files and generates valid Microsoft Fabric Ontology definitions.

## Test Suite Structure

The test suite is organized into the following test classes:

### 1. TestRDFConverter
Tests the core RDF conversion functionality:
- **test_parse_simple_ttl**: Validates parsing of a basic TTL file with classes and properties
- **test_empty_ttl**: Ensures proper error handling for empty input
- **test_invalid_ttl_syntax**: Validates error handling for malformed TTL syntax
- **test_uri_to_name_conversion**: Tests URI to name extraction and cleaning
- **test_fabric_name_compliance**: Verifies names comply with Fabric naming requirements
- **test_subclass_relationships**: Tests handling of class inheritance (rdfs:subClassOf)
- **test_multiple_domains**: Tests properties with multiple domain classes
- **test_generate_fabric_definition**: Validates Fabric definition generation
- **test_parse_ttl_file**: Tests file-based parsing
- **test_xsd_type_mapping**: Validates XSD datatype to Fabric type mapping

### 2. TestEntityType
Tests the EntityType dataclass:
- **test_entity_type_creation**: Validates EntityType instantiation
- **test_entity_with_properties**: Tests EntityType with properties

### 3. TestRelationshipType
Tests the RelationshipType dataclass:
- **test_relationship_type_creation**: Validates RelationshipType instantiation

### 4. TestSampleOntologies
Tests with actual sample TTL files from the samples/ directory:
- **test_sample_ontology_ttl**: Tests parsing of sample_ontology.ttl (Manufacturing domain)
- **test_foaf_ontology_ttl**: Tests parsing of foaf_ontology.ttl (Friend of a Friend vocabulary)
- **test_iot_ontology_ttl**: Tests parsing of sample_iot_ontology.ttl (IoT devices)
- **test_fibo_ontology_ttl**: Tests parsing of sample_fibo_ontology.ttl (Financial ontology)
- **test_all_sample_ttl_files**: Batch test that validates all .ttl files in samples/

### 5. TestConversionAccuracy
Tests accuracy of RDF to Fabric conversion:
- **test_property_count_preservation**: Verifies all properties are converted
- **test_relationship_count_preservation**: Verifies all relationships are converted
- **test_fabric_definition_structure**: Validates the structure of generated definitions

### 6. TestErrorHandling
Tests error handling and edge cases:
- **test_nonexistent_file**: Tests handling of missing files
- **test_invalid_file_path**: Tests handling of invalid paths
- **test_empty_content**: Tests handling of empty content
- **test_none_content**: Tests handling of None input
- **test_malformed_ttl**: Tests handling of malformed TTL syntax
- **test_class_without_properties**: Tests handling of classes without properties

### 7. TestDataclassToDict
Tests serialization of dataclasses:
- **test_entity_type_to_dict**: Tests EntityType to dictionary conversion
- **test_relationship_type_to_dict**: Tests RelationshipType to dictionary conversion

## Running Tests

### Basic Test Run
```powershell
python -m pytest test_converter.py -v
```

### Run Specific Test Class
```powershell
python -m pytest test_converter.py::TestSampleOntologies -v
```

### Run Specific Test
```powershell
python -m pytest test_converter.py::TestSampleOntologies::test_foaf_ontology_ttl -v
```

### Run with Detailed Output
```powershell
python -m pytest test_converter.py -v -s
```

### Run with Coverage (if pytest-cov is installed)
```powershell
python -m pytest test_converter.py --cov=rdf_converter --cov-report=html
```

## Test Results

All 29 tests pass successfully:

```
test_converter.py::TestRDFConverter::test_parse_simple_ttl PASSED
test_converter.py::TestRDFConverter::test_empty_ttl PASSED
test_converter.py::TestRDFConverter::test_invalid_ttl_syntax PASSED
test_converter.py::TestRDFConverter::test_uri_to_name_conversion PASSED
test_converter.py::TestRDFConverter::test_fabric_name_compliance PASSED
test_converter.py::TestRDFConverter::test_subclass_relationships PASSED
test_converter.py::TestRDFConverter::test_multiple_domains PASSED
test_converter.py::TestRDFConverter::test_generate_fabric_definition PASSED
test_converter.py::TestRDFConverter::test_parse_ttl_file PASSED
test_converter.py::TestRDFConverter::test_xsd_type_mapping PASSED
test_converter.py::TestEntityType::test_entity_type_creation PASSED
test_converter.py::TestEntityType::test_entity_with_properties PASSED
test_converter.py::TestRelationshipType::test_relationship_type_creation PASSED
test_converter.py::TestSampleOntologies::test_sample_ontology_ttl PASSED
test_converter.py::TestSampleOntologies::test_foaf_ontology_ttl PASSED
test_converter.py::TestSampleOntologies::test_iot_ontology_ttl PASSED
test_converter.py::TestSampleOntologies::test_fibo_ontology_ttl PASSED
test_converter.py::TestSampleOntologies::test_all_sample_ttl_files PASSED
test_converter.py::TestConversionAccuracy::test_property_count_preservation PASSED
test_converter.py::TestConversionAccuracy::test_relationship_count_preservation PASSED
test_converter.py::TestConversionAccuracy::test_fabric_definition_structure PASSED
test_converter.py::TestErrorHandling::test_nonexistent_file PASSED
test_converter.py::TestErrorHandling::test_invalid_file_path PASSED
test_converter.py::TestErrorHandling::test_empty_content PASSED
test_converter.py::TestErrorHandling::test_none_content PASSED
test_converter.py::TestErrorHandling::test_malformed_ttl PASSED
test_converter.py::TestErrorHandling::test_class_without_properties PASSED
test_converter.py::TestDataclassToDict::test_entity_type_to_dict PASSED
test_converter.py::TestDataclassToDict::test_relationship_type_to_dict PASSED

========================= 29 passed in 0.95s =========================
```

## Sample TTL File Test Results

The test suite successfully parses all sample TTL files:

| File Name | Status | Parts Generated |
|-----------|--------|-----------------|
| foaf_ontology.ttl | SUCCESS | 26 parts |
| sample_fibo_ontology.ttl | SUCCESS | 85 parts |
| sample_iot_ontology.ttl | SUCCESS | 5 parts |
| sample_ontology.ttl | SUCCESS | 9 parts |

## What the Tests Validate

### Core Functionality
- ✅ TTL parsing with rdflib
- ✅ Entity type extraction from owl:Class definitions
- ✅ Property extraction from owl:DatatypeProperty
- ✅ Relationship extraction from owl:ObjectProperty
- ✅ URI to name conversion and sanitization
- ✅ XSD type to Fabric type mapping
- ✅ Class hierarchy (rdfs:subClassOf) handling
- ✅ Multiple domain/range handling

### Fabric Ontology Generation
- ✅ Correct structure with "parts" array
- ✅ .platform metadata generation
- ✅ definition.json generation
- ✅ EntityTypes/ path structure
- ✅ RelationshipTypes/ path structure
- ✅ Base64 payload encoding
- ✅ Topological sorting of entity types (parents before children)

### Error Handling
- ✅ Empty content
- ✅ None/null input
- ✅ Invalid TTL syntax
- ✅ Missing files
- ✅ Invalid file paths
- ✅ Malformed ontologies

### Real-world Ontologies
- ✅ Manufacturing ontology (Equipment, Sensors, Facilities)
- ✅ FOAF vocabulary (Person, Agent, Organization)
- ✅ IoT ontology (Devices, Locations)
- ✅ Financial ontology (FIBO sample)

## Test Coverage

The test suite provides comprehensive coverage of:
- **Core conversion logic**: All major functions in rdf_converter.py
- **Edge cases**: Empty inputs, malformed data, missing files
- **Data validation**: Type mappings, name compliance, structure validation
- **Real-world scenarios**: Multiple sample ontologies from different domains

## Adding New Tests

To add a new test:

1. Choose the appropriate test class or create a new one
2. Follow the naming convention: `test_<description>`
3. Use pytest fixtures for common setup (e.g., `converter`, `samples_dir`)
4. Add descriptive docstrings
5. Use assertions to validate expected behavior
6. Run the test to ensure it passes

Example:
```python
def test_my_new_feature(self, converter):
    """Test description"""
    ttl = """
    @prefix : <http://example.org/> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    
    :MyClass a owl:Class .
    """
    
    entity_types, _ = converter.parse_ttl(ttl)
    assert len(entity_types) == 1
```

## Continuous Integration

The test suite is designed to be run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -r requirements.txt
    python -m pytest test_converter.py -v --junitxml=test-results.xml
```

## Test Maintenance

- Keep tests up to date with code changes
- Add tests for new features before implementation (TDD)
- Update tests when requirements change
- Remove obsolete tests
- Maintain test documentation

## Dependencies

The test suite requires:
- `pytest >= 7.4.0` - Testing framework
- `rdflib >= 7.0.0` - RDF parsing
- All dependencies from requirements.txt

Optional:
- `pytest-cov` - For code coverage reports
- `pytest-xdist` - For parallel test execution

## Troubleshooting

### Tests fail with "No module named 'rdf_converter'"
Ensure you're running from the project root directory.

### Sample file tests are skipped
Ensure the samples/ directory exists with .ttl files.

### Import errors
Activate the virtual environment and install dependencies:
```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Future Enhancements

Potential additions to the test suite:
- [ ] Performance benchmarks for large ontologies
- [ ] Integration tests with actual Fabric API
- [ ] Mutation testing
- [ ] Property-based testing with Hypothesis
- [ ] Test fixtures for complex ontology patterns
- [ ] Load testing with very large TTL files
