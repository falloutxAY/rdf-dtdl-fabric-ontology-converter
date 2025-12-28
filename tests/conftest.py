"""
Pytest configuration and fixtures for the test suite.

Defines markers for selective test execution:
    pytest -m unit          # Fast unit tests
    pytest -m integration   # Integration tests  
    pytest -m slow          # Tests that take >1s
    pytest -m security      # Security-related tests
    pytest -m resilience    # Rate limiting, circuit breaker, cancellation
"""

import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Fast unit tests")
    config.addinivalue_line("markers", "integration: Integration tests requiring setup")
    config.addinivalue_line("markers", "slow: Tests that take more than 1 second")
    config.addinivalue_line("markers", "security: Security-related tests (path traversal, symlinks)")
    config.addinivalue_line("markers", "resilience: Rate limiting, circuit breaker, cancellation tests")
    config.addinivalue_line("markers", "samples: Tests using sample ontology files")


@pytest.fixture
def sample_ttl_content():
    """Minimal valid TTL content for testing."""
    return '''
        @prefix : <http://example.org/> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        
        :Person a owl:Class ;
            rdfs:label "Person" .
        
        :name a owl:DatatypeProperty ;
            rdfs:domain :Person ;
            rdfs:range xsd:string .
    '''


@pytest.fixture
def sample_ontology_path():
    """Path to sample supply chain ontology."""
    return os.path.join(
        os.path.dirname(__file__), 
        '..', 'samples', 'sample_supply_chain_ontology.ttl'
    )


@pytest.fixture
def temp_ttl_file(tmp_path, sample_ttl_content):
    """Create a temporary TTL file for testing."""
    ttl_file = tmp_path / "test_ontology.ttl"
    ttl_file.write_text(sample_ttl_content)
    return str(ttl_file)
