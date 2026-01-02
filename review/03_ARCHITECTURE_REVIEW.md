# Architecture and Naming Review

## 1. Current Architecture Analysis

### 1.1 Module Structure

```
src/
├── main.py              # Entry point
├── rdf_converter.py     # 2514 lines - TOO LARGE
├── fabric_client.py     # 1324 lines
├── preflight_validator.py
├── fabric_to_ttl.py     # Export functionality
├── rate_limiter.py
├── circuit_breaker.py
├── cancellation.py
├── config.json          # Should not be here (ignored)
├── cli/
│   ├── commands.py      # 1382 lines
│   ├── helpers.py
│   └── parsers.py
├── converters/
│   ├── type_mapper.py
│   ├── uri_utils.py
│   ├── class_resolver.py
│   └── fabric_serializer.py
└── dtdl/
    ├── dtdl_converter.py  # 806 lines
    ├── dtdl_parser.py     # 697 lines
    ├── dtdl_validator.py  # 615 lines
    ├── dtdl_models.py     # 651 lines
    └── dtdl_type_mapper.py
```

### 1.2 Issues Identified

#### Issue 1: No Common Models Module

**Problem:** `EntityType`, `RelationshipType`, `ConversionResult`, etc. are defined in:
- `src/rdf_converter.py` (lines 230-330)
- `src/dtdl/dtdl_converter.py` (lines 37-125)

**Impact:** 
- Code duplication
- Risk of divergence
- Harder maintenance

**Solution:** Create `src/models/` module

---

#### Issue 2: Format-Specific Code Mixed with Generic Code

**Current:**
```
src/
├── rdf_converter.py      # RDF-specific
├── fabric_client.py      # Generic
├── converters/           # RDF utilities only!
└── dtdl/                 # DTDL-specific
```

**Problem:** `converters/` sounds generic but only contains RDF utilities.

**Solution:** Reorganize by function:

```
src/
├── models/              # Shared data models
├── formats/             # Format-specific converters
│   ├── rdf/
│   └── dtdl/
├── fabric/              # Fabric API interaction
└── core/                # Shared utilities
```

---

#### Issue 3: No Abstract Converter Interface

**Problem:** RDF and DTDL converters have similar signatures but no shared interface.

**Current Usage:**
```python
# RDF
converter = RDFToFabricConverter()
result = converter.parse_ttl(content)

# DTDL  
parser = DTDLParser()
result = parser.parse_file(path)
converter = DTDLToFabricConverter()
fabric_result = converter.convert(result.interfaces)
```

**Solution:** Create a unified interface:

```python
from abc import ABC, abstractmethod
from typing import Union, Protocol
from pathlib import Path

class OntologySource(Protocol):
    """Protocol for ontology sources."""
    pass

class ConversionResult:
    """Unified conversion result."""
    entity_types: List[EntityType]
    relationship_types: List[RelationshipType]
    skipped_items: List[SkippedItem]
    warnings: List[str]

class BaseConverter(ABC):
    """Abstract base for all format converters."""
    
    @abstractmethod
    def convert_file(self, path: Path, **kwargs) -> ConversionResult:
        """Convert a file to Fabric format."""
        pass
    
    @abstractmethod
    def convert_string(self, content: str, **kwargs) -> ConversionResult:
        """Convert string content to Fabric format."""
        pass
    
    @abstractmethod
    def validate(self, source: Union[Path, str]) -> ValidationResult:
        """Validate source before conversion."""
        pass
    
    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """File extensions this converter supports."""
        pass


class RdfConverter(BaseConverter):
    """RDF/TTL to Fabric converter."""
    
    @property
    def supported_extensions(self) -> List[str]:
        return ['.ttl', '.rdf', '.owl', '.n3']
    
    def convert_file(self, path: Path, **kwargs) -> ConversionResult:
        ...


class DtdlConverter(BaseConverter):
    """DTDL to Fabric converter."""
    
    @property
    def supported_extensions(self) -> List[str]:
        return ['.json', '.dtdl']
    
    def convert_file(self, path: Path, **kwargs) -> ConversionResult:
        ...
```

---

#### Issue 4: Large Files

| File | Lines | Assessment |
|------|-------|------------|
| `rdf_converter.py` | 2514 | ❌ Too large |
| `cli/commands.py` | 1382 | ⚠️ Large |
| `fabric_client.py` | 1324 | ⚠️ Large |
| `dtdl_converter.py` | 806 | ⚠️ At limit |

**Target:** No file should exceed 500 lines for maintainability.

---

## 2. Naming Convention Issues

### 2.1 File Naming

| Current | Recommended | Reason |
|---------|-------------|--------|
| `rdf_converter.py` | `formats/rdf/converter.py` | Better organization |
| `dtdl_converter.py` | `formats/dtdl/converter.py` | Consistency |
| `dtdl_parser.py` | `formats/dtdl/parser.py` | Remove prefix |
| `fabric_to_ttl.py` | `formats/rdf/exporter.py` | Clearer purpose |
| `preflight_validator.py` | `formats/rdf/validator.py` | Consistent with DTDL |

### 2.2 Class Naming

| Current | Recommended | Reason |
|---------|-------------|--------|
| `RDFToFabricConverter` | `RdfConverter` | Simpler, consistent |
| `DTDLToFabricConverter` | `DtdlConverter` | Match casing style |
| `DTDLParser` | `DtdlParser` | Acronym casing |
| `DTDLValidator` | `DtdlValidator` | Consistency |

**Rationale:** Python naming conventions (PEP 8):
- Acronyms in class names should be capitalized: `HTTPServer` → acceptable
- But mixing makes it unclear: `DTDLToFabricConverter`
- Recommend: Treat DTDL/RDF as words: `DtdlConverter`, `RdfConverter`

### 2.3 Variable/Parameter Naming

| Current | Recommended | Reason |
|---------|-------------|--------|
| `ttl_file` | `input_file` or `source_file` | Format-agnostic |
| `ttl_content` | `source_content` | Format-agnostic |
| `parse_ttl()` | `parse()` | Class already indicates format |
| `entity_types` | `entity_types` | ✅ Good |
| `relationship_types` | `relationship_types` | ✅ Good |

### 2.4 Command Naming

| Current | Recommended | Reason |
|---------|-------------|--------|
| `dtdl-validate` | `dtdl validate` | Use subcommands |
| `dtdl-convert` | `dtdl convert` | Consistency |
| `dtdl-import` | `dtdl import` | Clarity |

**Example:**
```bash
# Current
python main.py dtdl-validate path/to/model.json

# Recommended
python main.py dtdl validate path/to/model.json
```

---

## 3. Proposed Architecture

### 3.1 New Directory Structure

```
src/
├── __init__.py
├── main.py                    # Entry point (minimal)
│
├── models/                    # Shared data models
│   ├── __init__.py
│   ├── fabric.py              # EntityType, RelationshipType, etc.
│   ├── conversion.py          # ConversionResult, SkippedItem
│   └── validation.py          # ValidationResult, ValidationError
│
├── formats/                   # Format-specific implementations
│   ├── __init__.py
│   ├── base.py                # BaseConverter, BaseValidator
│   ├── rdf/
│   │   ├── __init__.py
│   │   ├── converter.py       # RdfConverter
│   │   ├── validator.py       # RdfValidator (preflight)
│   │   ├── exporter.py        # FabricToRdf
│   │   └── utils/
│   │       ├── type_mapper.py
│   │       ├── uri_utils.py
│   │       └── class_resolver.py
│   └── dtdl/
│       ├── __init__.py
│       ├── converter.py       # DtdlConverter
│       ├── parser.py          # DtdlParser
│       ├── validator.py       # DtdlValidator
│       ├── models.py          # DTDLInterface, etc.
│       └── type_mapper.py
│
├── fabric/                    # Fabric API client
│   ├── __init__.py
│   ├── client.py              # FabricOntologyClient
│   ├── config.py              # FabricConfig
│   └── serializer.py          # FabricSerializer
│
├── core/                      # Shared utilities
│   ├── __init__.py
│   ├── rate_limiter.py
│   ├── circuit_breaker.py
│   ├── cancellation.py
│   ├── memory_manager.py
│   └── constants.py           # Shared constants
│
└── cli/                       # CLI layer
    ├── __init__.py
    ├── main.py                # Argument parsing, dispatch
    ├── commands/
    │   ├── __init__.py
    │   ├── base.py            # BaseCommand
    │   ├── rdf.py             # RDF commands
    │   ├── dtdl.py            # DTDL commands
    │   └── common.py          # list, get, delete
    └── helpers.py
```

### 3.2 Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `models/` | Data structures shared across formats |
| `formats/` | Format-specific parsing and conversion |
| `fabric/` | Fabric API communication |
| `core/` | Cross-cutting concerns (rate limiting, etc.) |
| `cli/` | User interface (command line) |

### 3.3 Import Strategy

**Use explicit relative imports within packages:**

```python
# In src/formats/rdf/converter.py
from ...models.fabric import EntityType, RelationshipType
from ...models.conversion import ConversionResult
from .utils.type_mapper import TypeMapper
```

**Use absolute imports for cross-package:**

```python
# In src/cli/commands/rdf.py
from src.formats.rdf import RdfConverter
from src.fabric import FabricOntologyClient
```

---

## 4. Migration Plan

### Phase 1: Extract Models (Week 1)

1. Create `src/models/` directory
2. Move shared dataclasses from `rdf_converter.py`
3. Update imports in all files
4. Remove duplicates from `dtdl_converter.py`
5. Run tests to verify

### Phase 2: Reorganize Formats (Week 2)

1. Create `src/formats/` structure
2. Move RDF code to `src/formats/rdf/`
3. Move DTDL code to `src/formats/dtdl/`
4. Create `BaseConverter` interface
5. Update CLI imports

### Phase 3: Create Core Module (Week 3)

1. Create `src/core/` directory
2. Move resilience patterns (rate limiter, circuit breaker)
3. Move memory manager
4. Create constants module
5. Update imports

### Phase 4: Restructure CLI (Week 4)

1. Split `commands.py` into separate modules
2. Create command subgroups for RDF and DTDL
3. Update argument parsing
4. Add shell completion support

---

## 5. Naming Conventions Guide

### 5.1 For Contributors

```python
# Files
# - Use snake_case
# - Be descriptive but concise
# - No format prefix in format-specific directories
✓ src/formats/rdf/converter.py
✗ src/formats/rdf/rdf_converter.py

# Classes
# - Use PascalCase
# - Treat acronyms as words when mixed
✓ RdfConverter, DtdlParser, HttpClient
✗ RDFConverter, DTDLParser, HTTPClient

# Functions/Methods
# - Use snake_case
# - Start with verb
✓ parse_content(), validate_schema(), convert_to_fabric()
✗ content_parse(), schema_validation(), fabric_conversion()

# Variables
# - Use snake_case
# - Be descriptive
✓ entity_types, conversion_result, input_file
✗ et, cr, f

# Constants
# - Use UPPER_SNAKE_CASE
✓ MAX_FILE_SIZE_MB, DEFAULT_NAMESPACE
✗ maxFileSizeMb, defaultNamespace

# Type aliases
# - Use PascalCase
✓ FabricType = str
✓ EntityId = str
```

### 5.2 Public API Stability

Mark public vs internal APIs clearly:

```python
# Public API (stable)
__all__ = [
    'RdfConverter',
    'DtdlConverter', 
    'ConversionResult',
]

# Internal (may change)
def _internal_helper():
    ...
```

---

## 6. Action Items

### Immediate ✅ COMPLETED

- [x] Create `src/models/` with shared dataclasses
  - Created `src/models/__init__.py`, `base.py`, `fabric_types.py`, `conversion.py`
  - Shared EntityType, RelationshipType, ConversionResult, etc.
- [x] Remove duplicate definitions
  - Removed duplicates from rdf_converter.py and dtdl_converter.py
- [x] Standardize constants - Created `src/constants.py` with:
  - ExitCode enum (SUCCESS, ERROR, VALIDATION_ERROR, etc.)
  - MemoryLimits, ProcessingLimits, APIConfig, IDConfig, etc.

### Short-term ✅ COMPLETED

- [x] Create `BaseConverter` interface - `src/models/base.py`
  - Abstract base class with convert_file(), convert_string(), validate()
  - Protocol-based design for flexibility
- [x] Create `src/core/` module for cross-cutting concerns:
  - `src/core/__init__.py` - Module exports
  - `src/core/rate_limiter.py` - TokenBucketRateLimiter, RateLimiter Protocol
  - `src/core/circuit_breaker.py` - CircuitBreaker, CircuitState, Registry
  - `src/core/cancellation.py` - CancellationToken, signal handling
  - `src/core/memory.py` - MemoryManager with pre-flight checks

### In Progress / Deferred

- [ ] Reorganize into `formats/` structure (Major refactor - deferred)
  - Would require updating all imports across codebase
  - Recommend doing in a dedicated PR with thorough testing
- [ ] Split large files (rdf_converter.py at 2514 lines)
  - Would benefit from splitting into parser, processor, and output modules
  - Recommend after formats/ reorganization

### Long-term

- [ ] Full restructure per migration plan (Section 4)
- [ ] Add shell completion for CLI
- [ ] Plugin architecture for custom formats

---

## 7. Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| `src/models/` | ✅ Complete | Shared dataclasses for all converters |
| `src/constants.py` | ✅ Complete | Centralized configuration constants |
| `src/core/` | ✅ Complete | Rate limiter, circuit breaker, cancellation, memory |
| `src/formats/` | 🔄 Deferred | Major refactor - needs dedicated PR |
| CLI restructure | 🔄 Deferred | Split commands.py - needs dedicated PR |
| BaseConverter | ✅ Complete | Abstract base in models/base.py |
