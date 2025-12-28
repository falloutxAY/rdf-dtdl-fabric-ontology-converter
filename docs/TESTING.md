# Testing Documentation

## 🚀 Quick Start

```powershell
# Run all tests (286 tests)
python -m pytest tests/ -v

# Or use the test runner
python tests/run_tests.py all
```

## 📋 Test Files

| File | Purpose |
|------|----------|
| `test_converter.py` | Core RDF conversion |
| `test_exporter.py` | Fabric to TTL export |
| `test_integration.py` | Integration & E2E |
| `test_preflight_validator.py` | Pre-flight validation |
| `test_rate_limiter.py` | Rate limiting functionality |
| `test_fabric_client_integration.py` | Fabric API client integration tests |
| `test_cancellation.py` | Cancellation support & signal handling |
| `test_streaming_converter.py` | Streaming parser for large files |
| `run_tests.py` | Test runner utility |

## Running Tests

### Quick Commands
```powershell
# Run all tests
python tests/run_tests.py all

# Run unit tests only
python tests/run_tests.py core

# Run sample file tests
python tests/run_tests.py samples

# Run a specific test
python tests/run_tests.py single test_foaf_ontology_ttl

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
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

# Rate limiter tests
python -m pytest tests/test_rate_limiter.py -v

# Fabric API integration tests
python -m pytest tests/test_fabric_client_integration.py -v

# Cancellation support tests
python -m pytest tests/test_cancellation.py -v

# Streaming converter tests
python -m pytest tests/test_streaming_converter.py -v
```

### Specific Tests
```powershell
# Run a test class
python -m pytest tests/test_converter.py::TestSampleOntologies -v

# Run a single test
python -m pytest tests/test_converter.py::TestSampleOntologies::test_foaf_ontology_ttl -v -s

# Run Fabric API integration test classes
python -m pytest tests/test_fabric_client_integration.py::TestListOntologies -v
python -m pytest tests/test_fabric_client_integration.py::TestCreateOntology -v
python -m pytest tests/test_fabric_client_integration.py::TestRateLimitingAndRetry -v
```

## ✨ Sample Test Output

Run the sample file tests to see current results:

```powershell
python -m pytest tests/test_converter.py::TestSampleOntologies::test_all_sample_ttl_files -v -s
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
- ✅ EntityTypes/ and RelationshipTypes/ path structure
- ✅ Base64 payload encoding
- ✅ Topological sorting (parents before children)

### Error Handling ✅
- ✅ Empty/invalid input
- ✅ Malformed TTL syntax
- ✅ Missing files
- ✅ Invalid configuration
- ✅ Permission errors
- ✅ Path traversal protection

### Rate Limiting ✅
- ✅ Token bucket algorithm
- ✅ Thread safety
- ✅ Burst handling
- ✅ Statistics tracking
- ✅ Retry-After header compliance

### Fabric API Client Integration ✅
Mock-based integration tests aligned with [Microsoft Fabric REST API](https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items):

- ✅ List ontologies (GET /workspaces/{workspaceId}/ontologies)
- ✅ Get ontology (GET /ontologies/{ontologyId})
- ✅ Create ontology (POST with 201/202 responses)
- ✅ Update ontology definition
- ✅ Delete ontology (DELETE with 200 OK)
- ✅ Long-running operations (LRO) with polling
- ✅ Rate limiting (429 Too Many Requests)
- ✅ Authentication (Bearer token, refresh)
- ✅ Error responses (400, 401, 403, 404, 500, 503)
- ✅ Request timeout handling
- ✅ Configuration validation

### Cancellation Support ✅
- ✅ CancellationToken operations (cancel, is_cancelled, throw_if_cancelled)
- ✅ Thread-safe cancellation with callbacks
- ✅ Signal handler setup/restore (SIGINT)
- ✅ Interruptible wait loops
- ✅ Cleanup callback execution
- ✅ Fabric client cancellation integration
- ✅ Pre-cancelled token behavior

### Streaming Converter ✅
- ✅ Phase-based processing (classes → properties → relationships)
- ✅ Memory-efficient batch processing
- ✅ Progress callback integration
- ✅ Streaming vs standard converter equivalence
- ✅ Cancellation token support in streaming mode
- ✅ Skipped item tracking for incomplete properties
- ✅ Subclass/inheritance chain handling
- ✅ Sample ontology streaming tests
- ✅ Threshold constant validation

### Sample Ontologies
All sample ontology files in the `samples/` directory are tested.

## Adding New Tests

To add a new test:

1. Choose the appropriate test class or create a new one
2. Follow the naming convention: `test_<description>`
3. Use pytest fixtures for common setup (e.g., `converter`, `samples_dir`)
4. Add descriptive docstrings
5. Use assertions to validate expected behavior

### Example: Unit Test
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

### Example: Integration Test with Mocked API
```python
def test_create_ontology_success(self, fabric_client):
    """Test successful ontology creation with mocked Fabric API."""
    mock_response = create_mock_response(
        status_code=201,
        json_data=create_ontology_response(
            ontology_id="5b218778-e7a5-4d73-8187-f10824047715",
            display_name="MyOntology"
        )
    )
    
    with patch('requests.request', return_value=mock_response):
        result = fabric_client.create_ontology(
            display_name="MyOntology",
            definition={"parts": []},
            wait_for_completion=False
        )
    
    assert result["id"] == "5b218778-e7a5-4d73-8187-f10824047715"
    assert result["type"] == "Ontology"
```

## Troubleshooting

### Import errors
Ensure you're running from the project root directory with dependencies installed:

```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run tests from project root
python -m pytest tests/ -v
```

### Tests run slowly
Use pytest-xdist for parallel execution:
```powershell
pip install pytest-xdist
python -m pytest tests/ -n auto
```

## Dependencies

Required packages:
```
pytest>=7.4.0
rdflib>=7.0.0
azure-identity>=1.15.0
requests>=2.31.0
tenacity>=8.2.0
tqdm>=4.66.0
```

Optional testing tools:
```powershell
pip install pytest-cov pytest-watch pytest-xdist
```

## 💡 Testing Best Practices

- ✅ Run tests before committing changes
- ✅ Add tests for new features (TDD)
- ✅ Keep test data in samples/ directory
- ✅ Use descriptive test names
- ✅ Review test coverage regularly
- ✅ Update tests when requirements change
- ✅ Use mock responses that match official API documentation
- ✅ Include both success and error path tests

## 📚 API Documentation References

Integration tests are aligned with official Microsoft Fabric API documentation:

- [Using Fabric APIs](https://learn.microsoft.com/en-us/rest/api/fabric/articles/using-fabric-apis)
- [Ontology Items API](https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items)
- [Long Running Operations](https://learn.microsoft.com/en-us/rest/api/fabric/articles/long-running-operation)
- [Rate Limiting/Throttling](https://learn.microsoft.com/en-us/rest/api/fabric/articles/using-fabric-apis#throttling)

