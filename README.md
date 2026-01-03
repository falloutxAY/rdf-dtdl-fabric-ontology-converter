# RDF and DTDL to Microsoft Fabric Ontology Converter

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Convert RDF in TTL and DTDL to Microsoft Fabric Ontology format via the [Fabric Ontology REST API](https://learn.microsoft.com/rest/api/fabric/ontology/items).

## Disclaimer

This is a **personal project** and is **not an official Microsoft product**. It is **not supported, endorsed, or maintained by Microsoft Corporation**. Use at your own risk. See [LICENSE](LICENSE) for terms.

## Features

- **RDF TTL Import** – Convert Turtle based RDF to Fabric format
- **DTDL Import** – Convert Azure Digital Twins models (v2/v3/v4)
- **Export & Compare** – Export Fabric ontologies back to TTL for verification
- **Pre-flight Validation** – Check compatibility before upload

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Common Commands](#common-commands)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Prerequisites

- Python 3.9 or higher
- Microsoft Fabric workspace with Ontology support
- Contributor role on the Fabric workspace

## Installation

```bash
# Clone the repository
git clone https://github.com/falloutxAY/rdf-fabric-ontology-converter.git
cd rdf-fabric-ontology-converter

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install with dependencies
pip install -e .
```

## Quick Start

```powershell
# 1. Configure (copy sample and edit with your Fabric workspace details)
copy config.sample.json src\config.json

# 2. Validate an RDF/TTL ontology
python -m src.main validate --format rdf samples/rdf/sample_supply_chain_ontology.ttl

# 3. Upload to Fabric
python -m src.main upload --format rdf samples/rdf/sample_supply_chain_ontology.ttl --ontology-name "MyOntology"

# 4. Import DTDL models
python -m src.main upload --format dtdl samples/dtdl/ --recursive --ontology-name "MyDTDL"
```

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for detailed configuration options.

## Common Commands

All format-specific commands use unified verbs with a `--format` flag:

```powershell
python -m src.main <command> --format {rdf,dtdl} <path> [options]
```

### Validation

```powershell
# Validate RDF/TTL
python -m src.main validate --format rdf <file.ttl> --verbose

# Validate DTDL models
python -m src.main validate --format dtdl <path> --recursive
```

### Conversion

```powershell
# Convert RDF to Fabric JSON (without upload)
python -m src.main convert --format rdf <file.ttl> --output output.json

# Convert DTDL to Fabric JSON
python -m src.main convert --format dtdl <path> --recursive --output output.json
```

### Upload to Fabric

```powershell
# Upload RDF ontology
python -m src.main upload --format rdf <file.ttl> --ontology-name "OntologyName"

# Upload DTDL models
python -m src.main upload --format dtdl <path> --recursive --ontology-name "MyDTDL"
```

### Workspace Operations

```powershell
# List all ontologies
python -m src.main list

# Export Fabric ontology back to TTL
python -m src.main export <ontology_id> --output exported.ttl

# Delete an ontology
python -m src.main delete <ontology_id>
```

### Large File Support

```powershell
# Use streaming mode for files >100MB
python -m src.main upload --format rdf <large_file.ttl> --streaming
python -m src.main convert --format dtdl <path> --streaming

# Force processing for files >500MB (bypass memory checks)
python -m src.main upload --format rdf <huge_file.ttl> --force-memory
python -m src.main convert --format dtdl <large_models> --force-memory
```

For the complete command reference, see [docs/COMMANDS.md](docs/COMMANDS.md).

## Documentation

### 📚 User Guides
- **[Configuration Guide](docs/CONFIGURATION.md)** – Detailed setup, authentication, and API configuration
- **[Commands Reference](docs/COMMANDS.md)** – Complete command-line reference
- **[RDF Guide](docs/RDF_GUIDE.md)** – RDF/OWL import, mapping, limitations, and examples
- **[DTDL Guide](docs/DTDL_GUIDE.md)** – DTDL import, mapping, limitations, and examples
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** – Common issues and solutions

### 🛠️ Developer Guides  
- **[API Reference](docs/API.md)** – Fabric Ontology REST API usage and examples
- **[Architecture Overview](docs/ARCHITECTURE.md)** – System design, patterns, and module structure
- **[Testing Guide](docs/TESTING.md)** – Running tests, markers, and coverage reports

### 📁 Project Structure

```
src/
├── main.py                   # CLI entry point
├── rdf/                      # RDF/OWL/TTL format support
│   ├── rdf_converter.py      # Main RDF → Fabric converter
│   ├── preflight_validator.py# Pre-conversion validation
│   ├── fabric_to_ttl.py      # Fabric → TTL export
│   └── ...                   # Type mapping, parsing, serialization
├── dtdl/                     # DTDL v2/v3/v4 format support
│   ├── dtdl_converter.py     # DTDL → Fabric converter
│   ├── dtdl_parser.py        # DTDL JSON parsing
│   └── dtdl_validator.py     # DTDL validation
├── core/                     # Shared infrastructure
│   ├── fabric_client.py      # Fabric API client
│   ├── rate_limiter.py       # Token bucket rate limiting
│   ├── circuit_breaker.py    # Fault tolerance
│   ├── cancellation.py       # Graceful shutdown
│   ├── validators.py         # Input validation, SSRF protection
│   └── streaming.py          # Memory-efficient processing
├── models/                   # Shared data models
└── cli/                      # Command handlers & parsers

tests/
├── core/                     # Fabric client, resilience, validation infrastructure
├── dtdl/                     # DTDL parser, validator, and edge cases
├── rdf/                      # RDF converter and validation suites
├── cli/                      # CLI parsing/formatting coverage
├── models/                   # Shared model tests
├── integration/              # Cross-format pipelines using sample data
├── fixtures/                 # Reusable TTL/DTDL/config fixtures
└── run_tests.py              # Convenience launcher for pytest targets
```

For detailed architecture, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

### 🤝 Community
- **[Contributing Guidelines](CONTRIBUTING.md)** – Development setup and contribution process
- **[Code of Conduct](CODE_OF_CONDUCT.md)** – Community standards
- **[Security Policy](SECURITY.md)** – Reporting vulnerabilities

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style guidelines, and the pull request process.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## Related Links

- [Microsoft Fabric Documentation](https://learn.microsoft.com/fabric/)
- [Fabric Ontology REST API](https://learn.microsoft.com/rest/api/fabric/ontology/items)
- [RDFLib](https://github.com/RDFLib/rdflib)
