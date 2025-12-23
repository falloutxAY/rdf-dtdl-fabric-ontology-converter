# RDF to Microsoft Fabric Ontology Converter

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-44%20passing-brightgreen.svg)](tests/)

Convert RDF TTL (Turtle) ontology files to Microsoft Fabric Ontology format and upload them via the Fabric REST API.

## ✨ Features

- 🔄 Parse RDF TTL files and convert to Fabric Ontology format
- 📤 Create and update ontologies in Microsoft Fabric
- 🔍 List, get, and delete ontologies
- 🏗️ Support for OWL classes, data properties, and object properties
- 🎯 Automatic XSD to Fabric type mapping
- 🔐 Interactive and service principal authentication
- ✅ Comprehensive test suite (44 tests)

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Configuration](#configuration)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Examples](#examples)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## 🔧 Prerequisites

- Python 3.9 or higher
- Microsoft Fabric workspace with Ontology support
- Contributor role on the Fabric workspace

## 📦 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/rdf-fabric-ontology-converter.git
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

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure your settings:
```bash
# Copy the sample configuration
cp config.sample.json config.json

# Edit config.json with your Fabric workspace details
```

## 🚀 Quick Start

```bash
# Convert a TTL file to Fabric format
python main.py convert samples/sample_ontology.ttl

# Upload an ontology to Fabric
python main.py upload samples/sample_ontology.ttl --name "MyOntology"

# List all ontologies in your workspace
python main.py list

# Run tests
python run_tests.py all
```

## 📖 Usage

### Convert TTL to JSON
```bash
python main.py convert <ttl_file> [--output <output.json>]
```

### Upload Ontology
```bash
python main.py upload <ttl_file> [--name <ontology_name>] [--update]
```

### List Ontologies
```bash
python main.py list
```

### Get Ontology Details
```bash
python main.py get <ontology_id>
```

### Delete Ontology
```bash
python main.py delete <ontology_id>
```

### Test Connection
```bash
python main.py test
```

## ⚙️ Configuration

Create `config.json` from `config.sample.json`:

```json
{
  "fabric": {
    "workspace_id": "YOUR_WORKSPACE_ID",
    "tenant_id": "YOUR_TENANT_ID",
    "client_id": "04b07795-8ddb-461a-bbee-02f9e1bf7b46",
    "use_interactive_auth": true
  },
  "ontology": {
    "default_namespace": "usertypes",
    "id_prefix": 1000000000000
  }
}
```

For detailed configuration options, see [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
python run_tests.py all

# Run unit tests only
python run_tests.py core

# Run sample file tests
python run_tests.py samples

# Run with coverage
python -m pytest --cov=src --cov-report=html
```

**Test Results:** ✅ 44/44 tests passing

For more details, see [docs/TESTING.md](docs/TESTING.md).

## 📁 Project Structure

```
rdf-fabric-ontology-converter/
├── src/                          # Source code
│   ├── __init__.py
│   ├── main.py                   # CLI entry point
│   ├── rdf_converter.py          # RDF parsing & conversion
│   └── fabric_client.py          # Fabric API client
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── test_converter.py         # Unit tests (29)
│   ├── test_integration.py       # Integration tests (15)
│   └── run_tests.py              # Test runner
├── samples/                      # Sample ontology files
│   ├── sample_ontology.ttl       # Manufacturing example
│   ├── foaf_ontology.ttl         # FOAF vocabulary
│   ├── sample_iot_ontology.ttl   # IoT devices
│   └── sample_fibo_ontology.ttl  # Financial ontology
├── docs/                         # Documentation
│   ├── CONFIGURATION.md          # Configuration guide
│   ├── TESTING.md                # Testing guide
│   ├── API_REFERENCE.md          # API documentation
│   └── TROUBLESHOOTING.md        # Common issues
├── config.sample.json            # Sample configuration
├── requirements.txt              # Python dependencies
├── .gitignore                    # Git ignore rules
├── LICENSE                       # MIT License
└── README.md                     # This file
```

## 💡 Examples

### Example 1: Manufacturing Ontology
```bash
python main.py upload samples/sample_ontology.ttl --name "ManufacturingOntology"
```

### Example 2: FOAF Vocabulary
```bash
python main.py upload samples/foaf_ontology.ttl --name "FOAF"
```

### Example 3: Convert Only (No Upload)
```bash
python main.py convert samples/sample_iot_ontology.ttl --output iot_definition.json
```

For more examples, see [docs/EXAMPLES.md](docs/EXAMPLES.md).

## 📚 Documentation

- **[Configuration Guide](docs/CONFIGURATION.md)** - Detailed setup instructions
- **[Testing Guide](docs/TESTING.md)** - How to run and write tests
- **[API Reference](docs/API_REFERENCE.md)** - Function and class documentation
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Contributing](docs/CONTRIBUTING.md)** - How to contribute

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- All tests pass (`python run_tests.py all`)
- Code follows Python best practices
- New features include tests
- Documentation is updated

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for Microsoft Fabric Ontology
- Uses [rdflib](https://github.com/RDFLib/rdflib) for RDF parsing
- Sample ontologies from [FOAF](http://xmlns.com/foaf/spec/) and [FIBO](https://spec.edmcouncil.org/fibo/)

## 📧 Support

For issues and questions:
- 🐛 [Report a bug](https://github.com/yourusername/rdf-fabric-ontology-converter/issues)
- 💡 [Request a feature](https://github.com/yourusername/rdf-fabric-ontology-converter/issues)
- 📖 [Read the docs](docs/)

## 🔗 Related Projects

- [Microsoft Fabric Documentation](https://learn.microsoft.com/fabric/)
- [RDFLib](https://github.com/RDFLib/rdflib)
- [OWL Ontologies](https://www.w3.org/OWL/)

---

**Made with ❤️ for the Fabric community**
