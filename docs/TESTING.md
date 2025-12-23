# Testing Documentation

## Overview

A comprehensive test suite has been created for the RDF to Fabric Ontology Converter with **44 tests** covering unit, integration, and end-to-end scenarios. The test suite ensures that the converter correctly parses RDF TTL files and generates valid Microsoft Fabric Ontology definitions.

### ✅ All Tests Passing

```
========================= 44 passed in 2.09s =========================
```

**Test Coverage:**
- Unit Tests: 29/29 ✅
- Integration Tests: 15/15 ✅
- Sample TTL Files: 4/4 ✅

## Test Files

### 1. **test_converter.py** (29 tests)
Unit tests for the core RDF conversion functionality:
- Core converter functionality (10 tests)
- Data type testing (2 tests)
- Relationship type testing (1 test)
- Sample ontology testing (5 tests)
- Conversion accuracy (3 tests)
- Error handling (6 tests)
- Dataclass serialization (2 tests)

### 2. **test_integration.py** (15 tests)
Integration and end-to-end tests:
- Configuration loading (5 tests)
- Logging setup (3 tests)
- Convert command (1 test)
- End-to-end workflows (3 tests)
- Robustness testing (3 tests)

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

### 8. TestConfigLoading (test_integration.py)
Tests configuration file handling:
- Configuration loading from valid JSON
- Default value handling
- Invalid JSON handling
- Missing file handling
- Permission error handling

### 9. TestLoggingSetup (test_integration.py)
Tests logging configuration:
- Log directory creation
- File handler setup
- Log level configuration

### 10. TestConvertCommand (test_integration.py)
Tests command-line interface:
- Convert command execution

### 11. TestEndToEnd (test_integration.py)
Tests complete workflows:
- Parse and convert workflow
- Large ontology handling (100+ classes)
- Unicode content support

### 12. TestRobustness (test_integration.py)
Tests edge cases and robustness:
- Very large ontologies
- Special character sanitization
- Complex inheritance hierarchies

## Sample TTL File Testing

All sample ontology files successfully parsed:

| File | Status | Parts Generated | Description |
|------|--------|-----------------|-------------|
| **sample_ontology.ttl** | ✅ SUCCESS | 9 parts | Manufacturing domain (Equipment, Sensors, Facilities) |
| **foaf_ontology.ttl** | ✅ SUCCESS | 26 parts | Friend of a Friend vocabulary (Person, Agent, Organization) |
| **sample_iot_ontology.ttl** | ✅ SUCCESS | 5 parts | IoT device management |
| **sample_fibo_ontology.ttl** | ✅ SUCCESS | 85 parts | Financial Industry Business Ontology sample |

## Running Tests

### Quick Start
```powershell
# Run all tests
python -m pytest tests/test_converter.py tests/test_integration.py -v

# Run unit tests only
python -m pytest tests/test_converter.py -v

# Run integration tests only
python -m pytest tests/test_integration.py -v
```

### Using Test Runner
```powershell
cd tests

# See all options
python run_tests.py

# Run all tests
python run_tests.py all

# Run sample ontology tests
python run_tests.py samples

# Run a specific test
python run_tests.py single test_foaf_ontology_ttl
```

### Test Categories
```powershell
# Core converter tests
python -m pytest tests/test_converter.py::TestRDFConverter -v

# Sample file tests
python -m pytest tests/test_converter.py::TestSampleOntologies -v

# Error handling tests
python -m pytest tests/test_converter.py::TestErrorHandling -v

# End-to-end tests
python -m pytest tests/test_integration.py::TestEndToEnd -v

# Robustness tests
python -m pytest tests/test_integration.py::TestRobustness -v
```

### Basic Test Run
```powershell
# From project root
python -m pytest tests/test_converter.py -v
```

### Run Specific Test Class
```powershell
python -m pytest tests/test_converter.py::TestSampleOntologies -v
```

### Run Specific Test
```powershell
python -m pytest tests/test_converter.py::TestSampleOntologies::test_foaf_ontology_ttl -v
```

### Run with Detailed Output
```powershell
python -m pytest tests/test_converter.py -v -s
```

### Run with Coverage (if pytest-cov is installed)
```powershell
python -m pytest tests/ --cov=src --cov-report=html
```

## Test Results

All 44 tests pass successfully (29 unit + 15 integration):

```
tests/test_converter.py::TestRDFConverter::test_parse_simple_ttl PASSED
```
tests/test_converter.py::TestRDFConverter::test_parse_simple_ttl PASSED
tests/test_converter.py::TestRDFConverter::test_empty_ttl PASSED
tests/test_converter.py::TestRDFConverter::test_invalid_ttl_syntax PASSED
tests/test_converter.py::TestRDFConverter::test_uri_to_name_conversion PASSED
tests/test_converter.py::TestRDFConverter::test_fabric_name_compliance PASSED
tests/test_converter.py::TestRDFConverter::test_subclass_relationships PASSED
tests/test_converter.py::TestRDFConverter::test_multiple_domains PASSED
tests/test_converter.py::TestRDFConverter::test_generate_fabric_definition PASSED
tests/test_converter.py::TestRDFConverter::test_parse_ttl_file PASSED
tests/test_converter.py::TestRDFConverter::test_xsd_type_mapping PASSED
tests/test_converter.py::TestEntityType::test_entity_type_creation PASSED
tests/test_converter.py::TestEntityType::test_entity_with_properties PASSED
tests/test_converter.py::TestRelationshipType::test_relationship_type_creation PASSED
tests/test_converter.py::TestSampleOntologies::test_sample_ontology_ttl PASSED
tests/test_converter.py::TestSampleOntologies::test_foaf_ontology_ttl PASSED
tests/test_converter.py::TestSampleOntologies::test_iot_ontology_ttl PASSED
tests/test_converter.py::TestSampleOntologies::test_fibo_ontology_ttl PASSED
tests/test_converter.py::TestSampleOntologies::test_all_sample_ttl_files PASSED
tests/test_converter.py::TestConversionAccuracy::test_property_count_preservation PASSED
tests/test_converter.py::TestConversionAccuracy::test_relationship_count_preservation PASSED
tests/test_converter.py::TestConversionAccuracy::test_fabric_definition_structure PASSED
tests/test_converter.py::TestErrorHandling::test_nonexistent_file PASSED
tests/test_converter.py::TestErrorHandling::test_invalid_file_path PASSED
tests/test_converter.py::TestErrorHandling::test_empty_content PASSED
tests/test_converter.py::TestErrorHandling::test_none_content PASSED
tests/test_converter.py::TestErrorHandling::test_malformed_ttl PASSED
tests/test_converter.py::TestErrorHandling::test_class_without_properties PASSED
tests/test_converter.py::TestDataclassToDict::test_entity_type_to_dict PASSED
tests/test_converter.py::TestDataclassToDict::test_relationship_type_to_dict PASSED
tests/test_integration.py::TestConfigLoading::test_config_loading PASSED
tests/test_integration.py::TestConfigLoading::test_config_defaults PASSED
tests/test_integration.py::TestConfigLoading::test_invalid_json PASSED
tests/test_integration.py::TestConfigLoading::test_missing_config PASSED
tests/test_integration.py::TestConfigLoading::test_permission_error PASSED
tests/test_integration.py::TestLoggingSetup::test_log_directory_creation PASSED
tests/test_integration.py::TestLoggingSetup::test_file_handler PASSED
tests/test_integration.py::TestLoggingSetup::test_log_level PASSED
tests/test_integration.py::TestConvertCommand::test_convert_command PASSED
tests/test_integration.py::TestEndToEnd::test_parse_and_convert PASSED
tests/test_integration.py::TestEndToEnd::test_large_ontology PASSED
tests/test_integration.py::TestEndToEnd::test_unicode_content PASSED
tests/test_integration.py::TestRobustness::test_very_large_ontology PASSED
tests/test_integration.py::TestRobustness::test_special_characters PASSED
tests/test_integration.py::TestRobustness::test_complex_inheritance PASSED

========================= 44 passed in 2.09s =========================
```

## What the Tests Validate

### Core Functionality ✅
- ✅ TTL parsing with rdflib
- ✅ Entity type extraction (owl:Class)
- ✅ Property extraction (owl:DatatypeProperty)
- ✅ Relationship extraction (owl:ObjectProperty)
- ✅ URI to name conversion and sanitization
- ✅ XSD type to Fabric type mapping
- ✅ Class hierarchy (rdfs:subClassOf) handling
- ✅ Multiple domain/range handling

### Fabric Ontology Generation ✅
- ✅ Correct "parts" array structure
- ✅ .platform metadata generation
- ✅ definition.json generation
- ✅ EntityTypes/ path structure
- ✅ RelationshipTypes/ path structure
- ✅ Base64 payload encoding
- ✅ Topological sorting (parents before children)

### Error Handling ✅
- ✅ Empty content
- ✅ None/null input
- ✅ Invalid TTL syntax
- ✅ Missing files
- ✅ Invalid file paths
- ✅ Malformed ontologies
- ✅ Invalid JSON configuration
- ✅ Permission errors

### Integration Testing ✅
- ✅ Configuration file loading
- ✅ Logging setup
- ✅ Command-line interface
- ✅ End-to-end parsing workflows
- ✅ Large file handling (100+ classes)
- ✅ Unicode content support
- ✅ Special character sanitization

### Real-world Ontologies ✅
- ✅ Manufacturing ontology (Equipment, Sensors, Facilities)
- ✅ FOAF vocabulary (Person, Agent, Organization)
- ✅ IoT ontology (Devices, Locations)
- ✅ Financial ontology (FIBO sample)

## Test Utilities

### Files
1. **tests/test_converter.py** - Core unit tests (29 tests)
2. **tests/test_integration.py** - Integration tests (15 tests)
3. **tests/run_tests.py** - Test runner utility
4. **docs/TESTING.md** - This comprehensive testing guide

### Test Runner Commands
```powershell
cd tests

python run_tests.py all        # Run all tests with verbose output
python run_tests.py quick      # Run all tests quickly
python run_tests.py samples    # Run sample ontology tests
python run_tests.py core       # Run core converter tests
python run_tests.py coverage   # Run with coverage report
python run_tests.py single <test_name>  # Run a specific test
```

## Code Quality Metrics

### Test Organization
- **Modular**: Tests organized into logical classes
- **Fixtures**: Reusable test fixtures for common setup
- **Descriptive**: Clear test names and docstrings
- **Comprehensive**: Edge cases and error conditions covered

### Test Patterns Used
- **Arrange-Act-Assert**: Clear test structure
- **Fixtures**: pytest fixtures for setup/teardown
- **Parametrization**: Efficient test data handling
- **Mocking**: Isolated unit testing
- **Temporary Files**: Clean test data management

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

The test suite is designed for CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install -r requirements.txt
    python -m pytest tests/ -v --junitxml=test-results.xml
```

```yaml
# Example Azure Pipelines
- script: |
    python -m pytest tests/ -v --junitxml=junit/test-results.xml
  displayName: 'Run Tests'
```

## Testing Best Practices

- ✅ Run tests before commits
- ✅ Add tests for new features before implementation (TDD)
- ✅ Keep test data in samples/ directory
- ✅ Use descriptive test names and docstrings
- ✅ Maintain test documentation
- ✅ Review test coverage regularly
- ✅ Update tests when requirements change
- ✅ Remove obsolete tests

## Dependencies

Required packages (from requirements.txt):
```
pytest>=7.4.0
rdflib>=7.0.0
azure-identity>=1.15.0
requests>=2.31.0
msal>=1.26.0
tenacity>=8.2.0
tqdm>=4.66.0
```

Optional testing tools:
```
pytest-cov      # Coverage reports
pytest-watch    # Auto-run on file changes
pytest-xdist    # Parallel test execution
```

Install optional tools:
```powershell
pip install pytest-cov pytest-watch pytest-xdist
```

## Troubleshooting

### Tests fail with "No module named 'rdf_converter'" or import errors
Ensure the tests/ directory has __init__.py that adds src/ to the Python path, and you're running from the project root directory.

```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run tests from project root
python -m pytest tests/ -v
```

### Sample file tests are skipped
Ensure the samples/ directory exists with .ttl files in the correct location relative to the tests.

### Permission or path errors
On Windows, use forward slashes or raw strings for paths. Ensure you have read/write permissions for test directories.

### Tests run slowly
Use pytest-xdist for parallel execution:
```powershell
pip install pytest-xdist
python -m pytest tests/ -n auto
```

## Recommended Enhancements

Potential future additions to the test suite:

1. **Coverage Analysis**
   ```powershell
   pip install pytest-cov
   python -m pytest tests/ --cov=src --cov-report=html
   # Open htmlcov/index.html
   ```

2. **Performance Benchmarks**: Add timing tests for large ontologies
3. **Property-based Testing**: Use Hypothesis for fuzz testing
4. **Integration with Fabric API**: Mock or test with actual Microsoft Fabric endpoints
5. **Mutation Testing**: Use mutpy to test the test quality
6. **Load Testing**: Test with very large TTL files (10,000+ classes)
7. **Parallel Testing**: Optimize test execution time

## Success Criteria ✅

All success criteria met:
- ✅ 100% of tests passing (44/44)
- ✅ All sample TTL files successfully parsed (4/4)
- ✅ Core functionality thoroughly tested
- ✅ Error handling validated
- ✅ Integration scenarios covered
- ✅ Documentation complete
- ✅ Test utilities provided
- ✅ CI/CD ready

## Conclusion

The RDF to Fabric Ontology Converter has a robust, comprehensive test suite that ensures reliability and correctness. The **44 passing tests** cover:

- **Unit testing** of core conversion logic
- **Integration testing** of end-to-end workflows  
- **Sample validation** with real-world ontology files
- **Error handling** for edge cases and failures
- **Robustness** with large files and special characters

This provides confidence that the converter works correctly for various ontology formats and use cases, making it production-ready and maintainable.
