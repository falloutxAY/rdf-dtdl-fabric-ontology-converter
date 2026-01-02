# RDF and DTDL to Microsoft Fabric Ontology Converter

[![CI](https://github.com/falloutxAY/rdf-fabric-ontology-converter/actions/workflows/ci.yml/badge.svg)](https://github.com/falloutxAY/rdf-fabric-ontology-converter/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Convert RDF TTL (Turtle) ontology files and DTDL to Microsoft Fabric Ontology format and upload them via the [Fabric Ontology REST API](https://learn.microsoft.com/rest/api/fabric/ontology/items). Also supports exporting Fabric ontologies back to TTL format for verification.

## Disclaimer

This is a **personal project** and is **not an official Microsoft product**. It is **not supported, endorsed, or maintained by Microsoft Corporation**. The views and implementations here are my own and do not represent Microsoft's positions or recommendations.

This tool was created as part of my personal learning with AI-assisted development. There may be errors, and outputs may not be complete or correct for all ontologies. **Use at your own risk.**

Please refer to the [LICENSE](LICENSE) file for full terms.

## Features

- **RDF/TTL Conversion** – Import Turtle ontologies to Fabric Ontology format
- **DTDL Import** – Convert Digital Twins Definition Language models 
- **Export & Compare** – Export Fabric ontologies back to TTL for verification
- **Pre-flight Validation** – Check compatibility before upload
- **Ontology API Coverage** – Create, read, update, delete, list ontologies

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [RDF/TTL Commands](#rdfttl-commands)
  - [DTDL Commands](#dtdl-commands)
- [Limitations](#limitations)
- [Documentation](#documentation)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Prerequisites

- Python 3.9 or higher
- Microsoft Fabric workspace with Ontology support
- Contributor role on the Fabric workspace

## Installation

1. Clone the repository:
```bash
git clone https://github.com/falloutxAY/rdf-fabric-ontology-converter.git
cd rdf-fabric-ontology-converter
```

2. Create and activate a virtual environment:
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python -m venv .venv
source .venv/bin/activate
```

3. Install the package with dependencies:
```bash
pip install -e .
```

4. Configure your settings:
```powershell
# Copy the sample configuration into src (config.json is git-ignored)
copy config.sample.json src\config.json

# Edit src/config.json with your Fabric workspace details
```

## Configuration

Create `src/config.json` from `config.sample.json` (config.json is git-ignored):

```json
{
  "fabric": {
    "workspace_id": "YOUR_WORKSPACE_ID",
    "tenant_id": "YOUR_TENANT_ID",
    "client_id": "",
    "use_interactive_auth": "true",
    "api_base_url": "https://api.fabric.microsoft.com/v1",
    "rate_limit": {
      "enabled": true,
      "requests_per_minute": 10,
      "burst": 15
    },
    "circuit_breaker": {
      "enabled": true,
      "failure_threshold": 5,
      "recovery_timeout": 60.0,
      "success_threshold": 2
    }
  },
  "ontology": {
    "default_namespace": "usertypes",
    "id_prefix": 1000000000000
  },
  "logging": {
    "level": "INFO",
    "file": "logs/app.log"
  }
}
```

For detailed configuration options, see [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## Quick Start

```powershell
# 1) Configure
copy config.sample.json src\config.json

# 2) Validate → Convert → Upload (use rdf- prefix for RDF commands)
python src/main.py rdf-validate samples/sample_supply_chain_ontology.ttl
python src/main.py rdf-upload   samples/sample_supply_chain_ontology.ttl --name "MyOntology"
```

## Usage

```powershell
# View all available commands
python src\main.py -h
```

### RDF/TTL Commands

> **Note:** RDF commands now use the `rdf-` prefix (e.g., `rdf-validate`, `rdf-upload`).
> Legacy command names without the prefix are deprecated but still work.

#### Validate TTL File (pre-flight)
```powershell
# Check if a TTL file can be imported seamlessly
python src\main.py rdf-validate <ttl_file> [--verbose] [--save-report]

# Save detailed validation report to JSON
python src\main.py rdf-validate <ttl_file> --output validation_report.json
```
You can try this for samples\sample_foaf_ontology.ttl

### Convert TTL to JSON
```powershell
python src\main.py rdf-convert <ttl_file> [--output <output.json>] --config src\config.json

# For large files (>100MB), use streaming mode for better memory efficiency
python src\main.py rdf-convert <ttl_file> --streaming

# For very large files (>500MB), bypass memory safety checks
python src\main.py rdf-convert <ttl_file> --force-memory
```

### Upload Ontology
```powershell
# Upload with pre-flight validation (default)
python src\main.py rdf-upload <ttl_file> [--name <ontology_name>] [--update] --config src\config.json

# Skip validation and upload directly
python src\main.py rdf-upload <ttl_file> --skip-validation --config src\config.json

# Force upload even if validation issues are found
python src\main.py rdf-upload <ttl_file> --force --config src\config.json

# For large files, use streaming mode for memory-efficient conversion
python src\main.py rdf-upload <ttl_file> --streaming --config src\config.json

# For very large files, bypass memory safety checks (use with caution)
python src\main.py rdf-upload <ttl_file> --force-memory --config src\config.json
```

### Export Ontology to TTL
```powershell
python src\main.py rdf-export <ontology_id> [--output <output.ttl>] --config src\config.json
```

### Compare Two TTL Files
```powershell
python src\main.py compare <ttl_file1> <ttl_file2> [--verbose]
```

### Round-Trip Test
```powershell
# Manual round-trip test with Fabric:
# 1) Upload ontology
python src\main.py rdf-upload <ttl_file> --name "TestOntology" --config src\config.json

# 2) Export ontology (use the ontology ID from step 1)
python src\main.py rdf-export <ontology_id> --output exported.ttl --config src\config.json

# 3) Compare original and exported
python src\main.py compare <ttl_file> exported.ttl --verbose
```

### List Ontologies
```powershell
python src\main.py list --config src\config.json
```

### Get Ontology Details
```powershell
python src\main.py get <ontology_id> --config src\config.json
```

### Delete Ontology
```powershell
python src\main.py delete <ontology_id> --config src\config.json
```

### Test Connection
```powershell
python src\main.py test --config src\config.json
```

---

### DTDL Commands

Import **Digital Twins Definition Language (DTDL)** models from Azure IoT/Digital Twins into Microsoft Fabric Ontology.

#### What is DTDL?

[DTDL](https://learn.microsoft.com/azure/digital-twins/concepts-models) is a JSON-LD based modeling language used by Azure Digital Twins and Azure IoT. It defines:
- **Interfaces** - Digital twin types with properties, telemetry, relationships, and commands
- **Properties** - Static attributes of a twin
- **Telemetry** - Time-series sensor data
- **Relationships** - Connections between twins
- **Components** - Reusable interface compositions

#### DTDL Usage

**Validate DTDL**
```powershell
# Validate a single DTDL file
python src\main.py dtdl-validate path/to/model.json

# Validate a directory of DTDL files recursively
python src\main.py dtdl-validate path/to/dtdl/ --recursive --verbose
```

#### Convert DTDL (without upload)
```powershell
# Convert DTDL to Fabric JSON format for inspection
python src\main.py dtdl-convert path/to/dtdl/ --recursive --output fabric_output.json
```

#### Import DTDL to Fabric
```powershell
# Full import: validate → convert → upload
python src\main.py dtdl-upload path/to/dtdl/ --recursive --ontology-name "MyDTDLOntology"

# Dry run: validate and convert without uploading
python src\main.py dtdl-upload path/to/dtdl/ --recursive --dry-run --output preview.json

# With custom namespace
python src\main.py dtdl-upload path/to/dtdl/ --namespace customtypes --ontology-name "CustomOntology"

# Flatten component properties into parent entities
python src\main.py dtdl-upload path/to/dtdl/ --flatten-components --ontology-name "FlatOntology"
```

### DTDL to Fabric Mapping

| DTDL Concept | Fabric Ontology Equivalent |
|--------------|---------------------------|
| Interface | EntityType |
| Property | Property (static) |
| Telemetry | TimeseriesProperty |
| Relationship | RelationshipType |
| Component | Nested properties (when flattened) |
| Inheritance (extends) | BaseEntityTypeId |
| Enum | String with allowed values |

### Supported DTDL Features

- ✅ DTDL v2, v3, and v4 contexts
- ✅ Properties with primitive and complex types
- ✅ Telemetry (mapped to timeseries properties)
- ✅ Relationships with target constraints
- ✅ Interface inheritance (extends)
- ✅ Components (with flatten option)
- ✅ Semantic types (@type annotations)
- ✅ Display names and descriptions
- ✅ **DTDL v4 Features:**
  - New primitive types: `byte`, `bytes`, `decimal`, `short`, `uuid`
  - Unsigned integer types: `unsignedByte`, `unsignedShort`, `unsignedInteger`, `unsignedLong`
  - `scaledDecimal` schema type for high-precision decimal values
  - Geospatial schemas: `point`, `lineString`, `polygon`, `multiPoint`, `multiLineString`, `multiPolygon`
  - Command request/response `nullable` property
  - Increased inheritance depth (12 levels) and complex schema depth (8 levels)

### DTDL Validation Checks

The validator performs comprehensive checks including:
- **DTMI format validation** - Ensures valid Digital Twin Model Identifiers
- **Inheritance cycle detection** - Prevents circular extends chains
- **Relationship target validation** - Warns about orphaned relationship targets
- **Component schema validation** - Warns about missing component schemas
- **Large ontology warnings** - Alerts when >200 interfaces may cause performance issues

### Example: RealEstateCore DTDL

```powershell
# Import the RealEstateCore DTDL ontology
python src\main.py dtdl-upload path/to/RealEstateCore/ --recursive --ontology-name "RealEstateCore"
```

The RealEstateCore DTDL ontology (~269 interfaces) has been successfully tested with this tool.

---

## Limitations

**Conversions are not 1:1**: RDF/OWL is highly expressive with features like complex class expressions, property restrictions, and inference-driven semantics that cannot be fully represented in Microsoft Fabric Ontology's business-friendly model. Similarly, some DTDL features have limited or no support in Fabric.

### ⚠️ Information Loss Warning

When converting ontologies to Fabric format, **some information may be lost or transformed**:

| Source Format | Feature Type | Impact |
|---------------|-------------|--------|
| **RDF/OWL** | Property restrictions (owl:Restriction, cardinality) | Lost - constraints not enforced |
| **RDF/OWL** | Property characteristics (transitive, symmetric) | Lost - semantic behavior lost |
| **RDF/OWL** | Complex class expressions (owl:intersectionOf) | Flattened - semantics simplified |
| **DTDL** | Commands | Not converted (optional include) |
| **DTDL** | Complex schemas (Enum, Object, Array, Map) | Serialized to JSON String |
| **DTDL** | Multiple inheritance (extends) | First parent only |

**Use compliance reports** to understand exactly what will be preserved, limited, or lost:

```python
from src.dtdl.dtdl_converter import DTDLToFabricConverter
converter = DTDLToFabricConverter()
result, report = converter.convert_with_compliance_report(interfaces)
if report:
    for warning in report.warnings:
        print(f"[{warning.impact.value}] {warning.feature}: {warning.message}")
```

### Pre-flight Validation

Use the **rdf-validate** command to check if your TTL file can be imported seamlessly:

```powershell
python src\main.py rdf-validate samples\sample_foaf_ontology.ttl --verbose
```

For complete details, see:
- **[Mapping Limitations](docs/MAPPING_LIMITATIONS.md)** - Full list of supported/unsupported features and their impact


## Documentation

### User Guides
- **[Configuration Guide](docs/CONFIGURATION.md)** – Detailed setup and API configuration
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** – Common issues and solutions
- **[Mapping Limitations](docs/MAPPING_LIMITATIONS.md)** – RDF/DTDL → Fabric conversion constraints

### Developer Guides  
- **[API Reference](docs/API.md)** – Fabric Ontology REST API usage
- **[Architecture Overview](docs/ARCHITECTURE.md)** – System design and patterns
- **[Testing Guide](docs/TESTING.md)** – Running tests and coverage

### Community
- **[Contributing Guidelines](CONTRIBUTING.md)** – How to contribute
- **[Code of Conduct](CODE_OF_CONDUCT.md)** – Community standards
- **[Security Policy](SECURITY.md)** – Reporting vulnerabilities
- **[Changelog](CHANGELOG.md)** – Version history

## Testing

```powershell
python -m pytest tests/ -v
# Or see docs/TESTING.md for markers and coverage
```

## 📁 Project Structure

```
rdf-fabric-ontology-converter/
├── src/
│   ├── main.py                   # CLI entry point
│   ├── formats/                  # NEW: Format-specific packages (recommended imports)
│   │   ├── rdf/                  # RDF/OWL/TTL format support
│   │   └── dtdl/                 # DTDL v2/v3/v4 format support
│   ├── cli/                      # Command handlers & parsers
│   │   └── commands/             # Modular command implementations
│   ├── converters/               # RDF type mapping & extraction components
│   ├── core/                     # Rate limiter, circuit breaker, streaming, validators
│   ├── models/                   # Shared data models
│   ├── dtdl/                     # DTDL module (parser, validator, converter)
│   ├── rdf_converter.py          # RDF/TTL conversion (legacy entry point)
│   ├── fabric_client.py          # Fabric API client
│   └── preflight_validator.py    # Pre-upload validation
├── tests/                        # 575+ passing tests
│   ├── fixtures/                 # Centralized test fixtures
│   └── integration/              # Integration tests
├── samples/                      # Example TTL & DTDL files
├── docs/                         # Full documentation
├── config.sample.json            # Configuration template
└── pyproject.toml                # Project metadata and dependencies
```

### Import Patterns

```python
# Recommended: Format-based imports
from src.formats.rdf import RDFToFabricConverter, PreflightValidator
from src.formats.dtdl import DTDLParser, DTDLToFabricConverter

# Legacy imports (still supported)
from src import RDFToFabricConverter
from src.dtdl import DTDLParser
```

For detailed architecture, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Code style guidelines  
- Pull request process
- Issue reporting

Please review our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## Related Links

- [Microsoft Fabric Documentation](https://learn.microsoft.com/fabric/)
- [RDFLib](https://github.com/RDFLib/rdflib) for RDF parsing support
- Sample vocabularies: [FOAF](http://xmlns.com/foaf/spec/) and [FIBO](https://spec.edmcouncil.org/fibo/)

---
