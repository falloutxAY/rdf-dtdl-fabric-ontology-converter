# Quick Test Guide

## 🚀 Quick Start

```powershell
# Run all tests
python -m pytest test_converter.py test_integration.py -v

# Or use the test runner
python run_tests.py all
```

## 📊 Test Statistics

| Metric | Count | Status |
|--------|-------|--------|
| **Total Tests** | 44 | ✅ ALL PASSING |
| Unit Tests | 29 | ✅ |
| Integration Tests | 15 | ✅ |
| Sample TTL Files Validated | 4 | ✅ |

## 🧪 Test Categories

### Unit Tests (test_converter.py)
```powershell
python run_tests.py core
```
- ✅ TTL parsing
- ✅ Entity type extraction
- ✅ Relationship extraction
- ✅ Type mapping
- ✅ Name sanitization
- ✅ Error handling

### Sample File Tests
```powershell
python run_tests.py samples
```
- ✅ sample_ontology.ttl (Manufacturing)
- ✅ foaf_ontology.ttl (Social network)
- ✅ sample_iot_ontology.ttl (IoT devices)
- ✅ sample_fibo_ontology.ttl (Finance)

### Integration Tests (test_integration.py)
```powershell
python -m pytest test_integration.py -v
```
- ✅ Config loading
- ✅ End-to-end workflows
- ✅ Large file handling
- ✅ Unicode support

## 📝 Running Specific Tests

```powershell
# Run a single test
python run_tests.py single test_foaf_ontology_ttl

# Run a test class
python -m pytest test_converter.py::TestSampleOntologies -v

# Run with output
python -m pytest test_converter.py::TestSampleOntologies::test_all_sample_ttl_files -v -s
```

## 📋 Test Files

| File | Purpose | Tests |
|------|---------|-------|
| `test_converter.py` | Unit tests for converter | 29 |
| `test_integration.py` | Integration & E2E tests | 15 |
| `run_tests.py` | Test runner utility | - |

## 📚 Documentation

- [TESTING.md](TESTING.md) - Comprehensive testing guide
- [TEST_SUMMARY.md](TEST_SUMMARY.md) - Detailed test results
- [README.md](README.md) - Main project documentation

## ✨ Sample Test Output

```
test_converter.py::TestSampleOntologies::test_all_sample_ttl_files

Sample TTL Files Parsing Results:
----------------------------------------------------------------------
foaf_ontology.ttl              SUCCESS    26 parts
sample_fibo_ontology.ttl       SUCCESS    85 parts
sample_iot_ontology.ttl        SUCCESS    5 parts
sample_ontology.ttl            SUCCESS    9 parts
----------------------------------------------------------------------
PASSED
```

## 🎯 What's Tested

### Core Functionality
- ✅ Parse TTL files
- ✅ Extract classes, properties, relationships
- ✅ Convert to Fabric format
- ✅ Handle inheritance (rdfs:subClassOf)
- ✅ Map XSD types to Fabric types
- ✅ Sanitize names for Fabric compliance

### Error Handling
- ✅ Empty/invalid input
- ✅ Malformed TTL syntax
- ✅ Missing files
- ✅ Invalid configuration
- ✅ Permission errors

### Real-World Scenarios
- ✅ Manufacturing ontology
- ✅ Social network (FOAF)
- ✅ IoT devices
- ✅ Financial ontology (FIBO)
- ✅ Large files (100+ classes)
- ✅ Unicode characters
- ✅ Special characters

## 🔍 Test Coverage

Run with coverage (requires pytest-cov):
```powershell
pip install pytest-cov
python -m pytest --cov=rdf_converter --cov-report=html
# Open htmlcov/index.html to view coverage
```

## 💡 Tips

- Run tests before committing changes
- Add tests for new features
- Use `-v` flag for verbose output
- Use `-s` flag to see print statements
- Use `-k` to filter tests by name
- Check test results in test_results.txt

## 🎉 Success!

All **44 tests passing** ensures the RDF to Fabric Ontology Converter is:
- ✅ Reliable
- ✅ Well-tested
- ✅ Production-ready
- ✅ Easy to maintain
