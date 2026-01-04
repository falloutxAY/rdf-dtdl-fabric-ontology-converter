# Architecture Overview

This document provides a comprehensive overview of the RDF/DTDL to Microsoft Fabric Ontology Converter architecture, design decisions, and component interactions.

## Table of Contents

- [High-Level Design](#high-level-design)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Module Structure](#module-structure)
- [Design Patterns](#design-patterns)
- [Extensibility](#extensibility)

---

## High-Level Design

The converter follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLI Layer                                   │
│  ┌─────────────────────────────────┐ ┌────────────────────────────┐│
│  │   Unified Commands              │ │  Common Cmds (list/get/etc)││
│  │  validate --format {rdf,dtdl}   │ │  list                      ││
│  │  convert  --format {rdf,dtdl}   │ │  get                       ││
│  │  upload   --format {rdf,dtdl}   │ │  delete                    ││
│  │  export   (RDF only)            │ │  compare, test             ││
│  └──────────────┬──────────────────┘ └────────────┬───────────────┘│
└─────────────────┼──────────────────────────────────┼───────────────┘
          │                │                      │
          ▼                ▼                      │
┌─────────────────────────────────────────────────────────────────────┐
│                       Converter Layer                                │
│  ┌──────────────────────┐          ┌──────────────────────────────┐│
│  │   RDF Pipeline       │          │      DTDL Pipeline           ││
│  │  ┌────────────────┐  │          │  ┌────────────────────────┐ ││
│  │  │PreflightValidator│ │          │  │   DTDLParser           │ ││
│  │  └────────┬─────────┘│          │  └──────────┬─────────────┘ ││
│  │           ▼          │          │             ▼               ││
│  │  ┌────────────────┐  │          │  ┌────────────────────────┐ ││
│  │  │ RDFToFabric    │  │          │  │   DTDLValidator        │ ││
│  │  │  Converter     │  │          │  └──────────┬─────────────┘ ││
│  │  │ (rdflib Graph) │  │          │             ▼               ││
│  │  └────────┬───────┘  │          │  ┌────────────────────────┐ ││
│  │           │          │          │  │  DTDLToFabricConverter │ ││
│  │           │          │          │  └──────────┬─────────────┘ ││
│  └───────────┼──────────┘          └─────────────┼───────────────┘│
│              │                                    │                 │
│              └────────────┬───────────────────────┘                 │
│                           ▼                                         │
│              ┌─────────────────────────┐                            │
│              │   Shared Models         │                            │
│              │  - EntityType           │                            │
│              │  - RelationshipType     │                            │
│              │  - ConversionResult     │                            │
│              │  - ValidationResult     │                            │
│              └────────────┬────────────┘                            │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Fabric Client Layer                               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────────┐│
│  │Rate Limiter  │ │Circuit Breaker│ │   Core Utilities             ││
│  │Token Bucket  │ │State Machine  │ │   - CancellationToken        ││
│  │10 req/min    │ │5 fail → OPEN  │ │   - MemoryManager            ││
│  └──────┬───────┘ └──────┬───────┘ └──────────┬───────────────────┘│
│         │                │                    │                     │
│         └────────────────┼────────────────────┘                     │
│                          ▼                                          │
│              ┌────────────────────────┐                             │
│              │ FabricOntologyClient   │                             │
│              │  - create_ontology()   │                             │
│              │  - update_definition() │                             │
│              │  - list_ontologies()   │                             │
│              │  - delete_ontology()   │                             │
│              └────────────┬───────────┘                             │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
                            ▼
               ┌─────────────────────────┐
               │  Microsoft Fabric API   │
               │  /v1/workspaces/{id}/   │
               │    ontology/items/*     │
               └─────────────────────────┘
```

---

## Component Architecture

### 1. CLI Layer (`src/app/cli/`)

**Responsibility:** User interface and command dispatch
```
src/
├── main.py                    # Entry point
├── constants.py               # Centralized constants
│
├── app/
│   └── cli/                   # User-facing CLI layer
│       ├── commands.py
│       ├── helpers.py
│       ├── format.py
│       ├── parsers.py
│       └── commands/
│           ├── base.py        # BaseCommand + protocols
│           ├── common.py      # List, Get, Delete, Compare
│           ├── rdf.py         # RDF-specific commands
│           ├── dtdl.py        # DTDL-specific commands
│           └── unified.py     # Format-agnostic workflows
│
├── formats/                   # Format pipelines
│   ├── base.py                # FormatPipeline contract
│   ├── rdf/                   # RDF implementation
│   │   ├── rdf_converter.py
│   │   ├── preflight_validator.py
│   │   ├── rdf_parser.py
│   │   └── ...
│   └── dtdl/                  # DTDL implementation
│       ├── dtdl_parser.py
│       ├── dtdl_validator.py
│       ├── dtdl_converter.py
│       ├── dtdl_models.py
│       └── dtdl_type_mapper.py
│
├── shared/
│   ├── models/                # Shared dataclasses
│   │   ├── base.py
│   │   ├── conversion.py
│   │   └── fabric_types.py
│   └── utilities/
│       ├── id_generator.py
│       └── type_registry.py
│
├── core/                      # Infrastructure + Fabric client
│   ├── __init__.py            # Back-compat exports
│   ├── auth.py
│   ├── cancellation.py
│   ├── circuit_breaker.py
│   ├── compliance/
│   ├── platform/
│   │   ├── fabric_client.py
│   │   └── auth.py / http.py helpers
│   ├── services/
│   │   ├── streaming.py
│   │   ├── memory.py
│   │   └── lro_handler.py
│   ├── rate_limiter.py
│   ├── streaming.py           # Legacy import path
│   └── validators.py
│
├── plugins/
│   ├── base.py                # OntologyPlugin ABC
│   ├── manager.py             # Plugin discovery
│   └── builtin/
│       ├── rdf_plugin.py
│       └── dtdl_plugin.py
│
├── dtdl/                      # Legacy facade → formats.dtdl
└── rdf/                       # Legacy facade → formats.rdf
```
- `fabric_serializer.py` - FabricSerializer for Fabric API JSON creation

**FabricToTTLExporter** (`rdf/fabric_to_ttl.py`)
- Reverse conversion: Fabric → TTL
- Preserves class hierarchy
- Generates valid RDF/OWL syntax

#### 2.2 DTDL Pipeline (`src/formats/dtdl/`)

**DTDLParser** (`dtdl_parser.py`)
- Parses DTDL v2, v3, and v4 JSON files
- Supports all DTDL primitive types including v4 additions:
  - `byte`, `bytes`, `decimal`, `short`, `uuid`
  - Unsigned types: `unsignedByte`, `unsignedShort`, `unsignedInteger`, `unsignedLong`
  - `scaledDecimal` for high-precision decimal values
- Handles complex schemas (Array, Enum, Map, Object)
- Supports geospatial schemas: `point`, `lineString`, `polygon`, `multiPoint`, `multiLineString`, `multiPolygon`
- Resolves `extends` inheritance (max 12 levels per v4 spec)

**DTDLValidator** (`dtdl_validator.py`)
- Validates DTMI format
- Checks interface structure
- Verifies relationship targets
- Validates semantic types and units
- Enforces v4 limits: 12 inheritance levels, 8 complex schema depth

**DTDLToFabricConverter** (`dtdl_converter.py`)
- Maps DTDL interfaces to EntityType
- Converts properties and telemetry
- Handles relationships with cardinality
- Flattens components to properties
- Maps `scaledDecimal` to JSON-encoded strings

> **Compatibility Note:** Existing imports that reference `src.dtdl.*` continue to work
> via shims that proxy to the `formats.dtdl` modules, so downstream tooling does not need
> to change immediately.

### 3. Shared Models (`src/shared/models/`)

**Purpose:** Single source of truth for data structures

**Components:**
- `base.py` - Abstract converter interface
- `fabric_types.py` - EntityType, RelationshipType definitions
- `conversion.py` - ConversionResult, SkippedItem, ValidationResult

**Benefits:**
- Eliminates code duplication
- Type safety across converters
- Easy to extend with new formats

### 4. Core Utilities (`src/core/`)

**Rate Limiter** (`rate_limiter.py`)
- Token bucket algorithm
- 10 requests/min default (configurable)
- Burst allowance for short spikes
- Thread-safe implementation

**Circuit Breaker** (`circuit_breaker.py`)
- Three states: CLOSED, OPEN, HALF_OPEN
- 5 failures → OPEN (configurable)
- 60s recovery timeout
- Per-endpoint isolation

**Cancellation Handler** (`cancellation.py`)
- Graceful Ctrl+C handling
- Callback registration for cleanup
- No resource leaks on interrupt

**Memory Manager** (`memory.py`)
- Pre-flight memory checks
- Prevents OOM crashes
- File size × 3.5 multiplier for RDF parsing
- Warning messages for large files

**Authentication** (`auth.py`)
- `CredentialFactory` - Creates Azure credentials (service principal, browser, managed identity)
- `TokenManager` - Thread-safe token caching with automatic refresh

**HTTP Client** (`http_client.py`)
- `RequestHandler` - Centralized HTTP request handling with rate limiting
- `ResponseHandler` - Response parsing and error handling
- `TransientAPIError` / `FabricAPIError` - Exception classes for API errors
- Helper functions: `is_transient_error`, `get_retry_wait_time`, `sanitize_display_name`

**LRO Handler** (`lro_handler.py`)
- `LROHandler` - Long-running operation polling with progress reporting
- Supports cancellation tokens
- Handles result fetching from operation URLs

**Streaming Engine** (`streaming.py`)
- `StreamingEngine` - Memory-efficient processing for large files
- Format adapters for RDF and DTDL
- Auto-detection based on file extension

### 5. Fabric Client (`core/fabric_client.py`)

**Responsibilities:**
- Authentication (interactive, service principal, managed identity)
- HTTP requests with retry logic (exponential backoff)
- Multi-part ontology definition upload
- Error handling and logging

**Authentication Modes:**
1. **Interactive** - Browser-based Azure login
2. **Service Principal** - Client ID + Secret/Certificate
3. **Managed Identity** - For Azure-hosted apps

---

## Data Flow

### RDF Import Flow

```
┌─────────────┐
│  User Input │
│  TTL File   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│  PreflightValidator     │
│  - Check file size      │
│  - Scan for unsupported │
│    OWL constructs       │
│  - Estimate memory      │
└──────┬──────────────────┘
       │ validation_ok?
       ▼ (yes)
┌─────────────────────────┐
│  RDFToFabricConverter   │
│  - Parse with rdflib    │
│  - Extract classes      │
│  - Extract properties   │
│  - Map XSD types        │
│  - Resolve URIs         │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  ConversionResult       │
│  - entity_types[]       │
│  - relationship_types[] │
│  - skipped_items[]      │
│  - warnings[]           │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  FabricSerializer       │
│  - Build JSON structure │
│  - Multi-part format    │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  FabricOntologyClient   │
│  - Rate limiting        │
│  - Circuit breaker      │
│  - POST /ontology/items │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  Microsoft Fabric API   │
└─────────────────────────┘
```

### DTDL Import Flow

```
┌─────────────┐
│  User Input │
│ DTDL JSON   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│  DTDLParser             │
│  - Parse JSON           │
│  - Build model graph    │
│  - Resolve extends      │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  DTDLValidator          │
│  - Validate DTMIs       │
│  - Check structure      │
│  - Verify references    │
└──────┬──────────────────┘
       │ valid?
       ▼ (yes)
┌─────────────────────────┐
│  DTDLToFabricConverter  │
│  - Map interfaces       │
│  - Convert properties   │
│  - Handle telemetry     │
│  - Create relationships │
└──────┬──────────────────┘
       │
       ▼
       ... (same as RDF flow)
```

---

## Module Structure

```
src/
├── main.py                    # Entry point (`python -m src.main`)
├── constants.py               # Shared literals + defaults
│
├── app/                       # User-facing experience layer
│   └── cli/
│       ├── commands.py        # Command registry + dispatcher
│       ├── format.py          # Format detection utilities
│       ├── helpers.py         # Logging/config helpers
│       ├── parsers.py         # Argparse configuration
│       └── commands/          # Command implementations
│           ├── base.py        # BaseCommand + protocols
│           ├── common.py      # list/get/delete/test/compare
│           ├── unified.py     # validate/convert/upload/export
│           ├── rdf.py         # RDF helpers
│           └── dtdl.py        # DTDL helpers
│
├── formats/                   # Format pipelines (new home for converters)
│   ├── base.py                # FormatPipeline contract
│   ├── rdf/
│   │   ├── rdf_converter.py
│   │   ├── preflight_validator.py
│   │   ├── fabric_to_ttl.py
│   │   ├── rdf_parser.py
│   │   ├── property_extractor.py
│   │   ├── type_mapper.py
│   │   └── fabric_serializer.py
│   └── dtdl/
│       ├── dtdl_parser.py
│       ├── dtdl_validator.py
│       ├── dtdl_converter.py
│       ├── dtdl_models.py
│       └── dtdl_type_mapper.py
│
├── shared/                    # Cross-format models + utilities
│   ├── models/
│   │   ├── base.py
│   │   ├── fabric_types.py
│   │   └── conversion.py
│   └── utilities/
│       ├── validation.py
│       ├── type_registry.py
│       └── id_generator.py
│
├── core/                      # Fabric client + resilience primitives
│   ├── fabric_client.py
│   ├── rate_limiter.py
│   ├── circuit_breaker.py
│   ├── cancellation.py
│   ├── memory.py
│   ├── streaming.py
│   ├── validators.py
│   ├── auth.py
│   ├── http_client.py
│   └── lro_handler.py
│
├── plugins/                   # Plugin base + discovery
│   ├── base.py
│   ├── manager.py
│   ├── protocols.py
│   └── builtin/
│       ├── rdf_plugin.py
│       └── dtdl_plugin.py
│
├── rdf/                       # Back-compat shim → formats.rdf
├── dtdl/                      # Back-compat shim → formats.dtdl
└── logs/                      # Default application logs directory
```

### Recommended Import Patterns

**Format-based imports:**
```python
# RDF format
from formats.rdf.rdf_converter import RDFToFabricConverter
from formats.rdf.preflight_validator import PreflightValidator

# DTDL format
from formats.dtdl.dtdl_parser import DTDLParser
from formats.dtdl.dtdl_validator import DTDLValidator

# Core infrastructure
from core.fabric_client import FabricOntologyClient
from core.cancellation import CancellationToken
from core.circuit_breaker import CircuitBreaker
```

**Back-compat imports (still supported):**
```python
from rdf import RDFToFabricConverter           # Proxies to formats.rdf
from dtdl import DTDLParser                    # Proxies to formats.dtdl
```

---

## Plugin Architecture

The converter supports a plugin system that enables users to add new ontology formats
beyond the built-in RDF and DTDL support.

### Plugin System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Plugin Manager                                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     Plugin Registry                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │   │
│  │  │Format Plugins│  │  Validators  │  │ Type Mapping Exts  │  │   │
│  │  └──────────────┘  └──────────────┘  └────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼
    ┌───────────────┐     ┌───────────────┐
    │  RDF Plugin   │     │  DTDL Plugin  │
    │  (Built-in)   │     │  (Built-in)   │
    └───────────────┘     └───────────────┘

    JSON-LD requests now reuse the RDF plugin path (via rdflib's JSON-LD parser)
    rather than a standalone plugin module.
```

### Plugin Structure

Each plugin provides three core components:

```
src/plugins/
├── __init__.py              # Package exports
├── base.py                  # OntologyPlugin ABC
├── protocols.py             # Parser, Validator, Converter protocols
├── manager.py               # PluginManager (singleton)
└── builtin/                 # Built-in plugin implementations
    ├── __init__.py
    ├── rdf_plugin.py        # RDF/TTL/OWL (includes JSON-LD)
    └── dtdl_plugin.py       # DTDL v2/v3/v4 format

src/shared/utilities/        # Shared infrastructure leveraged by plugins
├── validation.py            # ValidationResult + helpers
├── type_registry.py         # Common type mapping infrastructure
└── id_generator.py          # Standardized ID generation
```

### Plugin Base Class

```python
from plugins.base import OntologyPlugin

class MyFormatPlugin(OntologyPlugin):
    """Plugin for custom ontology format."""
    
    @property
    def format_name(self) -> str:
        return "myformat"  # CLI format identifier
    
    @property
    def display_name(self) -> str:
        return "My Format"  # Human-readable name
    
    @property
    def file_extensions(self) -> Set[str]:
        return {".myf", ".myformat"}
    
    def create_parser(self) -> ParserProtocol:
        return MyFormatParser()
    
    def create_validator(self) -> ValidatorProtocol:
        return MyFormatValidator()
    
    def create_converter(self) -> ConverterProtocol:
        return MyFormatConverter()
```

### Shared Utilities Layer

The `src/shared/utilities/` module provides shared infrastructure:

- **TypeRegistry**: Central type mapping with format-specific extensions
- **IDGenerator**: Consistent entity/relationship ID generation
- **Validation**: Unified validation reporting model (`ValidationResult`, `IssueCategory`, etc.)

### Plugin Discovery

Plugins are automatically discovered via:

1. **Built-in plugins**: Loaded from `src/plugins/builtin/`
2. **Installed packages**: Entry point group `fabric_ontology.plugins`
3. **Custom directories**: Via `--plugin-dir` CLI flag or config

### Using Plugins

**CLI Integration:**
```bash
# Validate JSON-LD via RDF plugin
python -m src.main validate --format rdf schema.jsonld
python -m src.main convert --format rdf schema.jsonld

# List available plugins
python -m src.main plugin list
```

**Programmatic Usage:**
```python
from plugins.manager import PluginManager

manager = PluginManager.get_instance()
manager.discover_plugins()

# Get a specific plugin (e.g., RDF)
rdf_plugin = manager.get_plugin("rdf")
converter = rdf_plugin.get_converter()
result = converter.convert(content)
```

For detailed plugin development instructions, see [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md).

---

## Design Patterns

### 1. Command Pattern (CLI)

Each CLI command is implemented as a separate function with consistent signature:

```python
def upload_command(args: argparse.Namespace) -> int:
    """Upload ontology to Fabric."""
    # Implementation
    return ExitCode.SUCCESS  # or ExitCode.ERROR
```

**Benefits:**
- Easy to add new commands
- Testable in isolation
- Consistent error handling

### 2. Strategy Pattern (Converters)

Multiple converters implementing the same interface:

```python
class BaseConverter(ABC):
    @abstractmethod
    def convert_file(self, path: Path) -> ConversionResult:
        pass

class RdfConverter(BaseConverter):
    def convert_file(self, path: Path) -> ConversionResult:
        # RDF-specific implementation
        pass

class DtdlConverter(BaseConverter):
    def convert_file(self, path: Path) -> ConversionResult:
        # DTDL-specific implementation
        pass
```

### 3. Circuit Breaker Pattern (Resilience)

Prevents cascading failures when Fabric API is unavailable:

```python
breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

try:
    result = breaker.call(client.create_ontology, name, definition)
except CircuitBreakerOpenError:
    print("Service temporarily unavailable, please retry later")
```

**States:**
- **CLOSED** - Normal operation
- **OPEN** - Blocking requests after failures
- **HALF_OPEN** - Testing if service recovered

### 4. Token Bucket (Rate Limiting)

Smooth rate limiting with burst support:

```python
limiter = TokenBucketRateLimiter(
    rate=10,      # requests per minute
    burst=15      # max burst size
)

limiter.acquire()  # Blocks if rate exceeded
make_api_call()
```

### 5. Observer Pattern (Cancellation)

Components register cleanup callbacks:

```python
token = CancellationToken()
token.register_callback(cleanup_temp_files)
token.register_callback(close_connections)

# On Ctrl+C, all callbacks execute
```

---

## Extensibility

### Adding a New Format Converter

1. **Create converter module:**
   ```python
   # src/formats/newformat/converter.py
   from shared.models.base import BaseConverter
   from shared.models.conversion import ConversionResult
   
   class NewFormatConverter(BaseConverter):
       @property
       def supported_extensions(self) -> List[str]:
           return ['.newext']
       
       def convert_file(self, path: Path) -> ConversionResult:
           # Implementation
           pass
   ```

2. **Expose via plugin:** (preferred)
   ```python
   # src/plugins/builtin/newformat_plugin.py
   class NewFormatPlugin(OntologyPlugin):
       def get_converter(self):
           from formats.newformat.converter import NewFormatConverter
           return NewFormatConverter()
   ```

3. **Wire up CLI (if needed):**
   - Add format enum/extension mapping in `src/app/cli/format.py`
   - Ensure plugin discovery (`PluginManager`) finds the new plugin
   - CLI commands automatically dispatch once the format is registered

### Adding Custom Type Mapping

Extend `formats/rdf/type_mapper.py` with new XSD types:

```python
XSD_TO_FABRIC_TYPE[str(XSD.gYear)] = "String"
XSD_TO_FABRIC_TYPE[str(XSD.gMonthDay)] = "String"
```

### Adding Custom Validation Rules

Extend `formats.rdf.preflight_validator.PreflightValidator` or `formats.dtdl.dtdl_validator.DTDLValidator`:

```python
class CustomValidator(PreflightValidator):
    def validate_custom_rule(self, graph):
        # Custom validation logic
        pass
```

---

## Performance Considerations

### Memory Management

- **RDF Parsing:** Uses ~3.5x file size in memory
- **Large Files:** Streaming mode reduces memory footprint
- **Memory Checks:** Pre-flight validation prevents OOM crashes

### API Rate Limiting

- **Default:** 10 requests/minute
- **Configurable:** Adjust based on Fabric plan limits
- **Burst Handling:** Short spikes allowed (15 req burst)

### Circuit Breaker

- **Fail Fast:** Prevents wasting time on unavailable services
- **Auto-Recovery:** Automatic retry after timeout

---

## Error Handling Strategy

1. **Validation Errors** - Exit code 2, detailed report
2. **Network Errors** - Retry with exponential backoff
3. **Authentication Errors** - Exit code 4, clear message
4. **User Cancellation** - Exit code 7, cleanup executed
5. **Internal Errors** - Exit code 1, stack trace logged

---

## Testing Architecture


CLI-facing assertions now live alongside the core and format-specific suites, eliminating
namespace clashes with `src.cli` and `src.models`.

```
tests/
├── core/          # Fabric client, resilience, validation infrastructure
├── dtdl/          # DTDL parser, validator, and edge-case suites
├── rdf/           # RDF converter and validation coverage
├── integration/   # Cross-format and pipeline end-to-end tests
├── fixtures/      # Shared sample content and config helpers
├── run_tests.py   # Convenience runner for common pytest targets
└── __init__.py    # Package marker for pytest discovery helpers
```

**Coverage:** Comprehensive unit and integration suites aligned with the new package layout

---

## References

- [Microsoft Fabric Ontology API](https://learn.microsoft.com/rest/api/fabric/ontology/items)
- [DTDL v4 Specification](https://github.com/Azure/opendigitaltwins-dtdl/blob/master/DTDL/v4/DTDL.v4.md)
- [RDF 1.1 Specification](https://www.w3.org/TR/rdf11-concepts/)
- [OWL 2 Web Ontology Language](https://www.w3.org/TR/owl2-overview/)
- [rdflib Documentation](https://rdflib.readthedocs.io/)

---

**Last Updated:** January 3, 2026
