# RDF and DTDL to Microsoft Fabric Ontology Converter

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Convert RDF (Turtle, RDF/XML, N-Triples, N-Quads, TriG, Notation3, JSON-LD) and DTDL ontologies to Microsoft Fabric Ontology format via the [Fabric Ontology REST API](https://learn.microsoft.com/rest/api/fabric/ontology/items).

## Disclaimer

This is a **personal project** and is **not an official Microsoft product**. It is **not supported, endorsed, or maintained by Microsoft Corporation**. Use at your own risk. See [LICENSE](LICENSE) for terms.

## Features

- **RDF Import (Turtle, RDF/XML, N-Triples, TriG, N-Quads, N3, JSON-LD)** – Convert popular RDF/OWL serializations (including `.jsonld`) to Fabric format
- **DTDL Import** – Convert Azure Digital Twins models (v2/v3/v4)
- **Plugin System** – Extensible architecture for adding new formats
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
# 1. Configure
copy config.sample.json src\config.json  # Edit with your Fabric workspace details

# 2. Validate
python -m src.main validate --format rdf samples/rdf/sample_supply_chain_ontology.ttl

# 3. Upload
python -m src.main upload --format rdf samples/rdf/sample_supply_chain_ontology.ttl
```

All common RDF serializations are supported, including files with `.ttl`, `.rdf`, `.owl`, `.nt`, `.nq`, `.trig`, and `.n3` extensions.

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) and [docs/CLI_COMMANDS.md](docs/CLI_COMMANDS.md) for complete options.

## Command Overview

All format-specific commands use unified verbs with `--format {rdf,dtdl}`:

| Command | Description |
|---------|-------------|
| `validate` | Validate files for Fabric compatibility |
| `convert` | Convert to Fabric JSON (no upload) |
| `upload` | Validate, convert, and upload to Fabric |
| `list` | List ontologies in workspace |
| `export` | Export from Fabric to TTL (RDF only) |
| `delete` | Delete ontology |
| `plugin list` | Show available format plugins |

For complete syntax and options, see [docs/CLI_COMMANDS.md](docs/CLI_COMMANDS.md).

## Documentation

### 📚 User Guides
- **[Configuration Guide](docs/CONFIGURATION.md)** – Detailed setup, authentication, and API configuration
- **[Commands Reference](docs/CLI_COMMANDS.md)** – Complete command-line reference
- **[RDF Guide](docs/RDF_GUIDE.md)** – RDF/OWL import, mapping, limitations, and examples
- **[DTDL Guide](docs/DTDL_GUIDE.md)** – DTDL import, mapping, limitations, and examples
- **[Plugin Guide](docs/PLUGIN_GUIDE.md)** – Creating custom format plugins
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
├── plugins/                  # Plugin system
│   ├── base.py               # Plugin base class
│   ├── manager.py            # Plugin discovery/registration
│   └── builtin/              # Built-in plugins (RDF + DTDL)
├── common/                   # Shared plugin infrastructure
│   ├── validation.py         # Unified validation
│   ├── type_registry.py      # Type mapping registry
│   └── id_generator.py       # ID generation utilities
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
├── plugins/                  # Plugin system tests
├── cli/                      # CLI parsing/formatting coverage
├── models/                   # Shared model tests
├── integration/              # Cross-format pipelines using sample data
├── fixtures/                 # Reusable TTL/DTDL/config fixtures
└── run_tests.py              # Convenience launcher for pytest targets

samples/
├── rdf/                      # RDF/TTL sample ontologies
├── dtdl/                     # DTDL sample models
└── jsonld/                   # JSON-LD sample schemas (parsed via the RDF pipeline)
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
