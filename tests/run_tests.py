#!/usr/bin/env python3
"""
Test Runner Script for RDF to Fabric Ontology Converter

This script provides convenient commands to run the test suite with different options.
"""

import sys
import subprocess
from pathlib import Path


def run_command(cmd, description):
    """Run a command and print results"""
    print(f"\n{'=' * 70}")
    print(f"  {description}")
    print('=' * 70)
    result = subprocess.run(cmd, shell=True)
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print("""
RDF Converter Test Runner

Usage:
    python run_tests.py <command>

Commands:
    all         - Run all tests with verbose output
    quick       - Run all tests quickly (no verbose)
    samples     - Run only sample ontology tests
    core        - Run only core converter tests
    coverage    - Run with coverage report (requires pytest-cov)
    single TEST - Run a specific test (e.g., 'single test_parse_simple_ttl')
    watch       - Run tests on file changes (requires pytest-watch)
    
Examples:
    python run_tests.py all
    python run_tests.py samples
    python run_tests.py single test_foaf_ontology_ttl
""")
        return 1

    command = sys.argv[1].lower()
    
    if command == "all":
        return run_command(
            "python -m pytest test_converter.py -v",
            "Running All Tests (Verbose)"
        )
    
    elif command == "quick":
        return run_command(
            "python -m pytest test_converter.py",
            "Running All Tests (Quick)"
        )
    
    elif command == "samples":
        return run_command(
            "python -m pytest test_converter.py::TestSampleOntologies -v -s",
            "Running Sample Ontology Tests"
        )
    
    elif command == "core":
        return run_command(
            "python -m pytest test_converter.py::TestRDFConverter -v",
            "Running Core Converter Tests"
        )
    
    elif command == "coverage":
        # Check if pytest-cov is installed
        try:
            import pytest_cov
            return run_command(
                "python -m pytest test_converter.py --cov=rdf_converter --cov-report=html --cov-report=term",
                "Running Tests with Coverage"
            )
        except ImportError:
            print("ERROR: pytest-cov is not installed.")
            print("Install it with: pip install pytest-cov")
            return 1
    
    elif command == "single":
        if len(sys.argv) < 3:
            print("ERROR: Please specify a test name")
            print("Example: python run_tests.py single test_parse_simple_ttl")
            return 1
        
        test_name = sys.argv[2]
        return run_command(
            f"python -m pytest test_converter.py -k {test_name} -v",
            f"Running Single Test: {test_name}"
        )
    
    elif command == "watch":
        try:
            import pytest_watch
            return run_command(
                "ptw test_converter.py -- -v",
                "Running Tests in Watch Mode"
            )
        except ImportError:
            print("ERROR: pytest-watch is not installed.")
            print("Install it with: pip install pytest-watch")
            return 1
    
    elif command == "help":
        return main()
    
    else:
        print(f"ERROR: Unknown command '{command}'")
        print("Run 'python run_tests.py' to see available commands")
        return 1


if __name__ == "__main__":
    sys.exit(main())
