# Plugin System Implementation Plan

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Research Findings](#research-findings)
3. [Current Architecture Analysis](#current-architecture-analysis)
4. [Plugin System Design](#plugin-system-design)
5. [Common Layer Extraction](#common-layer-extraction)
6. [Implementation Phases](#implementation-phases)
7. [Sample Plugin: JSON-LD](#sample-plugin-json-ld)
8. [Testing Strategy](#testing-strategy)
9. [Documentation Requirements](#documentation-requirements)
10. [Migration Guide](#migration-guide)

---

## Executive Summary

This document outlines a comprehensive plan to introduce a **plugin architecture** to the RDF/DTDL Ontology Converter project. The plugin system will enable users to:

- Add new ontology formats (e.g., JSON-LD, OWL/XML, SHACL, LinkML)
- Extend validation rules
- Customize type mappings
- Add new export formats

The design leverages existing patterns (Command, Strategy, Factory) and extracts common functionality from RDF and DTDL implementations into a shared layer.

---

## Research Findings

### Current Code Architecture

#### CLI Layer (`src/cli/`)
- **Entry Point:** `main.py` dispatches commands via `COMMAND_MAP`
- **Command Pattern:** `BaseCommand` ABC with `execute(args)` method
- **Format Dispatch:** `format.py` with `Format` enum and factory registries
- **Shared Flags:** `parsers.py` builds argument parsers with common options

#### Converter Layer
| Component | RDF (`src/rdf/`) | DTDL (`src/dtdl/`) |
|-----------|------------------|---------------------|
| Parser | `rdf_parser.py` | `dtdl_parser.py` |
| Validator | `preflight_validator.py` | `dtdl_validator.py` |
| Converter | `rdf_converter.py` | `dtdl_converter.py` |
| Type Mapper | `type_mapper.py` | `DTDL_TO_FABRIC_TYPE` dict |
| Models | Uses `models/fabric_types.py` | Uses `models/fabric_types.py` |

#### Core Infrastructure (`src/core/`)
- Rate limiter, circuit breaker, cancellation handler
- Input validators, Fabric limits validator
- Compliance validators (RDF/OWL, DTDL)
- Authentication, HTTP client, LRO handler

#### Shared Models (`src/models/`)
- `EntityType`, `RelationshipType`, `EntityTypeProperty`
- `ConversionResult`, `SkippedItem`, `ValidationResult`
- `ConverterProtocol` (abstract interface)

### Existing Extension Points

1. **Format Registry** (`cli/format.py`):
   ```python
   _VALIDATOR_FACTORIES: Dict[Format, Callable[[], Any]] = {}
   _CONVERTER_FACTORIES: Dict[Format, Callable[[], Any]] = {}
   register_validator(fmt, factory)
   register_converter(fmt, factory)
   ```

2. **Converter Protocol** (`models/base.py`):
   ```python
   class ConverterProtocol(Protocol):
       def convert(self, content: str, id_prefix: int, **kwargs) -> ConversionResult
       def validate(self, content: str) -> bool
   ```

3. **Base Command** (`cli/commands/base.py`):
   - Dependency injection via `IValidator`, `IConverter`, `IFabricClient`

### Patterns to Preserve

- Factory registration for format-specific services
- Protocol-based dependency injection
- Shared data models (`EntityType`, `ConversionResult`)
- Consistent exit codes and error handling

---

## Current Architecture Analysis

### Components That Can Be Shared

| Component | Current Location | Shareable? | Notes |
|-----------|------------------|------------|-------|
| Type Mapping Logic | `rdf/type_mapper.py`, `dtdl/dtdl_converter.py` | ✅ Yes | Extract common mapping infrastructure |
| Validation Report | `rdf/preflight_validator.py`, `dtdl/dtdl_validator.py` | ✅ Yes | Unify `ValidationReport` and `ValidationResult` |
| Entity ID Generation | Both converters | ✅ Yes | Standardize ID generation |
| Fabric Serialization | `rdf/fabric_serializer.py` | ✅ Yes | Move to core |
| Compliance Checking | `core/compliance.py` | ✅ Already shared | Good pattern |
| Property Extraction | Format-specific | ❌ No | Keep format-specific |

### Duplication to Eliminate

1. **Type Mapping Infrastructure:**
   - RDF: `XSD_TO_FABRIC_TYPE` dictionary
   - DTDL: `DTDL_TO_FABRIC_TYPE` dictionary
   - **Solution:** Common `TypeMappingRegistry` with format-specific extensions

2. **Validation Result Models:**
   - RDF: `ValidationReport`, `ValidationIssue`
   - DTDL: `ValidationResult`, `DTDLValidationError`
   - **Solution:** Unified `ValidationResult` in `models/`

3. **ID Generation:**
   - Both use counter-based ID generation
   - **Solution:** `IDGenerator` class in core

4. **CLI Argument Building:**
   - Both formats share many flags
   - **Solution:** Already good via `parsers.py` shared flags

---

## Plugin System Design

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Plugin Manager                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Plugin Registry                               │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐│   │
│  │  │ Format Plugins│ │Validator    │ │ Type Mapping Extensions  ││   │
│  │  │              │ │  Extensions │ │                          ││   │
│  │  └──────────────┘ └──────────────┘ └──────────────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   Built-in      │   │   Built-in      │   │    External     │
│   RDF Plugin    │   │   DTDL Plugin   │   │    Plugins      │
│                 │   │                 │   │  (User-created) │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

### Plugin Interface

```python
# src/plugins/base.py

from abc import ABC, abstractmethod
from typing import List, Set, Dict, Any, Optional
from models import ConversionResult, EntityType, RelationshipType

class OntologyPlugin(ABC):
    """Base class for ontology format plugins."""
    
    @property
    @abstractmethod
    def format_name(self) -> str:
        """Unique identifier for this format (e.g., 'rdf', 'dtdl', 'jsonld')."""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable format name."""
        pass
    
    @property
    @abstractmethod
    def file_extensions(self) -> Set[str]:
        """Supported file extensions (e.g., {'.ttl', '.rdf', '.owl'})."""
        pass
    
    @property
    def version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    @abstractmethod
    def get_parser(self) -> 'ParserProtocol':
        """Return parser instance for this format."""
        pass
    
    @abstractmethod
    def get_validator(self) -> 'ValidatorProtocol':
        """Return validator instance for this format."""
        pass
    
    @abstractmethod
    def get_converter(self) -> 'ConverterProtocol':
        """Return converter instance for this format."""
        pass
    
    def get_type_mappings(self) -> Dict[str, str]:
        """Return format-specific type mappings to Fabric types."""
        return {}
    
    def get_exporter(self) -> Optional['ExporterProtocol']:
        """Return exporter for reverse conversion (optional)."""
        return None
    
    def register_cli_arguments(self, parser) -> None:
        """Add format-specific CLI arguments (optional)."""
        pass
```

### Protocol Definitions

```python
# src/plugins/protocols.py

from typing import Protocol, Any, Dict, List, Optional, runtime_checkable
from models import ConversionResult

@runtime_checkable
class ParserProtocol(Protocol):
    """Protocol for parsing ontology content."""
    
    def parse(self, content: str, file_path: Optional[str] = None) -> Any:
        """Parse content and return format-specific representation."""
        ...
    
    def parse_file(self, file_path: str) -> Any:
        """Parse file and return format-specific representation."""
        ...

@runtime_checkable
class ValidatorProtocol(Protocol):
    """Protocol for validating ontology content."""
    
    def validate(self, content: str, file_path: Optional[str] = None) -> 'ValidationResult':
        """Validate content and return validation result."""
        ...
    
    def validate_file(self, file_path: str) -> 'ValidationResult':
        """Validate file and return validation result."""
        ...

@runtime_checkable
class ConverterProtocol(Protocol):
    """Protocol for converting to Fabric format."""
    
    def convert(self, content: str, id_prefix: int = 1000000000000, **kwargs) -> ConversionResult:
        """Convert content to Fabric ontology format."""
        ...

@runtime_checkable
class ExporterProtocol(Protocol):
    """Protocol for exporting from Fabric format."""
    
    def export(self, entity_types: List[Any], relationship_types: List[Any], **kwargs) -> str:
        """Export Fabric entities to this format."""
        ...
```

### Plugin Manager

```python
# src/plugins/manager.py

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Type
from .base import OntologyPlugin

logger = logging.getLogger(__name__)

class PluginManager:
    """
    Manages discovery, loading, and registration of ontology plugins.
    
    Supports:
    - Built-in plugins (RDF, DTDL)
    - External plugins via entry points
    - Local plugin directories
    """
    
    _instance: Optional['PluginManager'] = None
    
    def __init__(self):
        self._plugins: Dict[str, OntologyPlugin] = {}
        self._extension_map: Dict[str, str] = {}  # extension -> format_name
    
    @classmethod
    def get_instance(cls) -> 'PluginManager':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register_plugin(self, plugin: OntologyPlugin) -> None:
        """Register a plugin instance."""
        name = plugin.format_name.lower()
        if name in self._plugins:
            logger.warning(f"Overwriting existing plugin: {name}")
        
        self._plugins[name] = plugin
        
        # Map extensions to format
        for ext in plugin.file_extensions:
            self._extension_map[ext.lower()] = name
        
        logger.info(f"Registered plugin: {plugin.display_name} (v{plugin.version})")
    
    def get_plugin(self, format_name: str) -> Optional[OntologyPlugin]:
        """Get plugin by format name."""
        return self._plugins.get(format_name.lower())
    
    def get_plugin_for_extension(self, extension: str) -> Optional[OntologyPlugin]:
        """Get plugin that handles the given file extension."""
        ext = extension.lower() if extension.startswith('.') else f'.{extension.lower()}'
        format_name = self._extension_map.get(ext)
        return self._plugins.get(format_name) if format_name else None
    
    def list_plugins(self) -> List[OntologyPlugin]:
        """List all registered plugins."""
        return list(self._plugins.values())
    
    def list_formats(self) -> List[str]:
        """List all supported format names."""
        return list(self._plugins.keys())
    
    def list_extensions(self) -> Set[str]:
        """List all supported file extensions."""
        return set(self._extension_map.keys())
    
    def discover_plugins(self, plugin_dir: Optional[Path] = None) -> None:
        """
        Discover and load plugins.
        
        Searches:
        1. Built-in plugins
        2. Entry points (setuptools)
        3. Custom plugin directory
        """
        # Load built-in plugins
        self._load_builtin_plugins()
        
        # Load from entry points
        self._load_entrypoint_plugins()
        
        # Load from custom directory
        if plugin_dir:
            self._load_directory_plugins(plugin_dir)
    
    def _load_builtin_plugins(self) -> None:
        """Load built-in RDF and DTDL plugins."""
        try:
            from plugins.builtin.rdf_plugin import RDFPlugin
            self.register_plugin(RDFPlugin())
        except ImportError as e:
            logger.error(f"Failed to load RDF plugin: {e}")
        
        try:
            from plugins.builtin.dtdl_plugin import DTDLPlugin
            self.register_plugin(DTDLPlugin())
        except ImportError as e:
            logger.error(f"Failed to load DTDL plugin: {e}")
    
    def _load_entrypoint_plugins(self) -> None:
        """Load plugins from setuptools entry points."""
        try:
            from importlib.metadata import entry_points
            eps = entry_points(group='fabric_ontology.plugins')
            for ep in eps:
                try:
                    plugin_class = ep.load()
                    self.register_plugin(plugin_class())
                except Exception as e:
                    logger.error(f"Failed to load plugin {ep.name}: {e}")
        except Exception as e:
            logger.debug(f"Entry point loading not available: {e}")
    
    def _load_directory_plugins(self, plugin_dir: Path) -> None:
        """Load plugins from a directory."""
        if not plugin_dir.exists():
            logger.warning(f"Plugin directory does not exist: {plugin_dir}")
            return
        
        for py_file in plugin_dir.glob("*_plugin.py"):
            try:
                spec = importlib.util.spec_from_file_location(
                    py_file.stem, py_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find OntologyPlugin subclasses
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, OntologyPlugin) and 
                            attr is not OntologyPlugin):
                            self.register_plugin(attr())
            except Exception as e:
                logger.error(f"Failed to load plugin from {py_file}: {e}")
```

---

## Common Layer Extraction

### New Common Module Structure

```
src/
├── common/                    # NEW: Shared plugin infrastructure
│   ├── __init__.py
│   ├── type_registry.py       # Unified type mapping registry
│   ├── id_generator.py        # Consistent ID generation
│   ├── validation.py          # Unified validation result models
│   ├── serialization.py       # Fabric JSON serialization (from rdf/)
│   └── property_utils.py      # Common property handling utilities
│
├── plugins/                   # NEW: Plugin infrastructure
│   ├── __init__.py
│   ├── base.py                # OntologyPlugin ABC
│   ├── protocols.py           # Parser/Validator/Converter protocols
│   ├── manager.py             # PluginManager
│   ├── loader.py              # Plugin discovery and loading
│   └── builtin/               # Built-in plugins
│       ├── __init__.py
│       ├── rdf_plugin.py      # RDF format plugin
│       └── dtdl_plugin.py     # DTDL format plugin
```

### Type Mapping Registry

```python
# src/common/type_registry.py

from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field

# Fabric supported types
FABRIC_TYPES = frozenset({
    "String", "Boolean", "DateTime", 
    "BigInt", "Double", "Int", "Long", "Float", "Decimal"
})

@dataclass
class TypeMapping:
    """Represents a type mapping from source to Fabric type."""
    source_type: str
    fabric_type: str
    converter: Optional[Callable[[Any], Any]] = None
    notes: str = ""

class TypeMappingRegistry:
    """
    Centralized registry for type mappings from various formats to Fabric types.
    
    Allows plugins to register their own type mappings while maintaining
    a consistent interface.
    """
    
    def __init__(self):
        self._mappings: Dict[str, Dict[str, TypeMapping]] = {}
        self._default_type = "String"
    
    def register_format(self, format_name: str) -> None:
        """Register a new format namespace."""
        if format_name not in self._mappings:
            self._mappings[format_name] = {}
    
    def register_mapping(
        self,
        format_name: str,
        source_type: str,
        fabric_type: str,
        converter: Optional[Callable] = None,
        notes: str = ""
    ) -> None:
        """Register a type mapping for a format."""
        if format_name not in self._mappings:
            self.register_format(format_name)
        
        if fabric_type not in FABRIC_TYPES:
            raise ValueError(f"Invalid Fabric type: {fabric_type}")
        
        self._mappings[format_name][source_type] = TypeMapping(
            source_type=source_type,
            fabric_type=fabric_type,
            converter=converter,
            notes=notes
        )
    
    def register_mappings(self, format_name: str, mappings: Dict[str, str]) -> None:
        """Bulk register mappings for a format."""
        for source_type, fabric_type in mappings.items():
            self.register_mapping(format_name, source_type, fabric_type)
    
    def get_fabric_type(
        self,
        format_name: str,
        source_type: str,
        default: Optional[str] = None
    ) -> str:
        """Get the Fabric type for a source type."""
        mapping = self._mappings.get(format_name, {}).get(source_type)
        if mapping:
            return mapping.fabric_type
        return default or self._default_type
    
    def get_mapping(self, format_name: str, source_type: str) -> Optional[TypeMapping]:
        """Get full mapping details."""
        return self._mappings.get(format_name, {}).get(source_type)
    
    def list_mappings(self, format_name: str) -> Dict[str, str]:
        """List all mappings for a format."""
        return {
            k: v.fabric_type 
            for k, v in self._mappings.get(format_name, {}).items()
        }

# Global registry instance
_registry: Optional[TypeMappingRegistry] = None

def get_type_registry() -> TypeMappingRegistry:
    """Get the global type mapping registry."""
    global _registry
    if _registry is None:
        _registry = TypeMappingRegistry()
    return _registry
```

### Unified Validation Result

```python
# src/common/validation.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

class Severity(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class IssueCategory(Enum):
    """Standard issue categories across all formats."""
    SYNTAX_ERROR = "syntax_error"
    MISSING_REQUIRED = "missing_required"
    INVALID_REFERENCE = "invalid_reference"
    UNSUPPORTED_CONSTRUCT = "unsupported_construct"
    TYPE_MISMATCH = "type_mismatch"
    CONSTRAINT_VIOLATION = "constraint_violation"
    CONVERSION_LIMITATION = "conversion_limitation"
    CUSTOM = "custom"

@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    severity: Severity
    category: IssueCategory
    message: str
    location: Optional[str] = None  # URI, line number, or identifier
    details: Optional[str] = None
    recommendation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "location": self.location,
            "details": self.details,
            "recommendation": self.recommendation,
        }

@dataclass
class ValidationResult:
    """
    Unified validation result used across all format validators.
    
    Provides consistent structure for RDF, DTDL, and future formats.
    """
    format_name: str
    source_path: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    is_valid: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_issue(
        self,
        severity: Severity,
        category: IssueCategory,
        message: str,
        **kwargs
    ) -> None:
        """Add a validation issue."""
        self.issues.append(ValidationIssue(
            severity=severity,
            category=category,
            message=message,
            **kwargs
        ))
        if severity == Severity.ERROR:
            self.is_valid = False
    
    def add_error(self, category: IssueCategory, message: str, **kwargs) -> None:
        """Convenience method to add an error."""
        self.add_issue(Severity.ERROR, category, message, **kwargs)
    
    def add_warning(self, category: IssueCategory, message: str, **kwargs) -> None:
        """Convenience method to add a warning."""
        self.add_issue(Severity.WARNING, category, message, **kwargs)
    
    def add_info(self, category: IssueCategory, message: str, **kwargs) -> None:
        """Convenience method to add an info message."""
        self.add_issue(Severity.INFO, category, message, **kwargs)
    
    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)
    
    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.INFO)
    
    @property
    def can_convert(self) -> bool:
        """Check if conversion can proceed (no errors)."""
        return self.error_count == 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "format": self.format_name,
            "source_path": self.source_path,
            "timestamp": self.timestamp,
            "is_valid": self.is_valid,
            "summary": {
                "errors": self.error_count,
                "warnings": self.warning_count,
                "info": self.info_count,
            },
            "issues": [i.to_dict() for i in self.issues],
            "statistics": self.statistics,
            "metadata": self.metadata,
        }
    
    def save_to_file(self, path: str) -> None:
        """Save validation result to JSON file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def get_summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Validation Result ({self.format_name})",
            "=" * 50,
            f"Status: {'✓ Valid' if self.is_valid else '✗ Invalid'}",
            f"Errors: {self.error_count}",
            f"Warnings: {self.warning_count}",
            f"Info: {self.info_count}",
        ]
        
        if self.issues:
            lines.append("\nIssues:")
            for issue in self.issues[:10]:
                icon = {"error": "✗", "warning": "⚠", "info": "ℹ"}[issue.severity.value]
                lines.append(f"  {icon} [{issue.category.value}] {issue.message}")
            
            if len(self.issues) > 10:
                lines.append(f"  ... and {len(self.issues) - 10} more")
        
        return "\n".join(lines)
```

### ID Generator

```python
# src/common/id_generator.py

from typing import Dict, Optional
import threading

class IDGenerator:
    """
    Thread-safe ID generator for Fabric entity and property IDs.
    
    Provides consistent 13-digit numeric IDs across all converters.
    """
    
    DEFAULT_PREFIX = 1000000000000
    
    def __init__(self, prefix: int = DEFAULT_PREFIX):
        self._counter = prefix
        self._lock = threading.Lock()
        self._namespace_counters: Dict[str, int] = {}
    
    def next_id(self) -> str:
        """Generate the next sequential ID."""
        with self._lock:
            current = self._counter
            self._counter += 1
            return str(current)
    
    def next_id_for_namespace(self, namespace: str) -> str:
        """Generate ID within a specific namespace for tracking."""
        with self._lock:
            if namespace not in self._namespace_counters:
                self._namespace_counters[namespace] = 0
            current = self._counter + self._namespace_counters[namespace]
            self._namespace_counters[namespace] += 1
            return str(current)
    
    def reset(self, prefix: Optional[int] = None) -> None:
        """Reset the counter."""
        with self._lock:
            self._counter = prefix or self.DEFAULT_PREFIX
            self._namespace_counters.clear()
    
    @property
    def current(self) -> int:
        """Get current counter value without incrementing."""
        return self._counter

# Global instance
_generator: Optional[IDGenerator] = None

def get_id_generator() -> IDGenerator:
    """Get the global ID generator instance."""
    global _generator
    if _generator is None:
        _generator = IDGenerator()
    return _generator

def reset_id_generator(prefix: Optional[int] = None) -> None:
    """Reset the global ID generator."""
    global _generator
    if _generator:
        _generator.reset(prefix)
    else:
        _generator = IDGenerator(prefix or IDGenerator.DEFAULT_PREFIX)
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goals:**
- Create plugin infrastructure without breaking existing functionality
- Extract common utilities

**Tasks:**

1. Create `src/common/` module:
   - [x] `type_registry.py` - Type mapping infrastructure
   - [x] `id_generator.py` - ID generation
   - [x] `validation.py` - Unified validation result

2. Create `src/plugins/` module:
   - [x] `base.py` - `OntologyPlugin` ABC
   - [x] `protocols.py` - Parser/Validator/Converter protocols
   - [x] `manager.py` - `PluginManager`

3. Update existing imports:
   - [x] Add compatibility layer for existing code
   - [x] Ensure all tests pass

**Deliverables:**
- ✅ New module structure created
- ✅ Existing functionality unchanged
- ✅ Unit tests for new modules

### Phase 2: Built-in Plugins (Week 3-4)

**Goals:**
- Refactor RDF and DTDL as plugins
- Maintain backward compatibility

**Tasks:**

1. Create RDF Plugin (`plugins/builtin/rdf_plugin.py`):
   - [x] Wrap existing `RDFToFabricConverter`
   - [x] Wrap existing `PreflightValidator`
   - [x] Register type mappings

2. Create DTDL Plugin (`plugins/builtin/dtdl_plugin.py`):
   - [x] Wrap existing `DTDLToFabricConverter`
   - [x] Wrap existing `DTDLValidator`
   - [x] Register type mappings

3. Update CLI:
   - [x] Modify `format.py` to use `PluginManager`
   - [x] Update command dispatch

4. Update `_register_defaults()` in `format.py`:
   - [x] Use plugin manager instead of direct imports

**Deliverables:**
- ✅ RDF and DTDL working as plugins
- ✅ All existing CLI commands work unchanged
- ✅ Integration tests pass

### Phase 3: Sample Plugin (Week 5-6)

**Goals:**
- Create JSON-LD plugin as reference implementation
- Document plugin development process

**Tasks:**

1. Create JSON-LD Plugin:
   - [x] Parser for JSON-LD format
   - [x] Validator for JSON-LD structure
   - [x] Converter to Fabric format

2. Create plugin documentation:
   - [x] Plugin development guide
   - [x] API reference
   - [x] Sample code walkthrough

3. Create plugin tests:
   - [x] Unit tests for JSON-LD plugin
   - [x] Integration tests

**Deliverables:**
- ✅ Working JSON-LD plugin
- ✅ Complete plugin development documentation
- ✅ Test suite for plugins

### Phase 4: Polish and Documentation (Week 7-8)

**Goals:**
- Complete documentation
- Performance optimization
- Release preparation

**Tasks:**

1. Documentation:
   - [x] Update ARCHITECTURE.md
   - [x] Create PLUGIN_GUIDE.md
   - [x] Update API.md
   - [x] Update CLI_COMMANDS.md
   - [x] If required, Update RDF_GUIDE.md and DTDL_GUIDE.md
   - [x] If required,  Update TESTING.md, TROUBLESHOOTING.md, CONFIGURATION.md README.md
   - [x] Ensure that all documents in docs folder and README.md are , not repetative.

2. Performance:
   - [x] Benchmark plugin loading
   - [x] Optimize discovery

3. Testing:
   - [x] End-to-end plugin tests
   - [x] Plugin isolation tests
   - [x] Error handling tests
   - [x] End to end full test including sample data files in samples folder

4. When all completed
   - [ ] Upload to github, plugin branch and merge to main branch.

**Deliverables:**
- Complete documentation
- Performance benchmarks
- Release-ready code

---

## Sample Plugin: JSON-LD

### Plugin Implementation

```python
# src/plugins/builtin/jsonld_plugin.py
# (Also serves as sample in samples/plugins/)

"""
JSON-LD Plugin for Fabric Ontology Converter

This plugin adds support for JSON-LD format, commonly used for
linked data on the web.

Example JSON-LD:
{
    "@context": {
        "schema": "https://schema.org/",
        "name": "schema:name",
        "Person": "schema:Person"
    },
    "@type": "Person",
    "name": "John Doe"
}
"""

import json
import logging
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass

from plugins.base import OntologyPlugin
from plugins.protocols import ParserProtocol, ValidatorProtocol, ConverterProtocol
from common.validation import ValidationResult, Severity, IssueCategory
from common.type_registry import get_type_registry
from common.id_generator import get_id_generator
from models import (
    ConversionResult,
    EntityType,
    EntityTypeProperty,
    RelationshipType,
    RelationshipEnd,
    SkippedItem,
)

logger = logging.getLogger(__name__)


# JSON-LD to Fabric type mappings
JSONLD_TO_FABRIC_TYPE = {
    "http://www.w3.org/2001/XMLSchema#string": "String",
    "http://www.w3.org/2001/XMLSchema#boolean": "Boolean",
    "http://www.w3.org/2001/XMLSchema#integer": "BigInt",
    "http://www.w3.org/2001/XMLSchema#decimal": "Double",
    "http://www.w3.org/2001/XMLSchema#dateTime": "DateTime",
    "http://www.w3.org/2001/XMLSchema#date": "DateTime",
    "http://schema.org/Text": "String",
    "http://schema.org/Number": "Double",
    "http://schema.org/Boolean": "Boolean",
    "http://schema.org/Date": "DateTime",
    "http://schema.org/DateTime": "DateTime",
}


@dataclass
class JSONLDContext:
    """Parsed JSON-LD context."""
    prefixes: Dict[str, str]
    terms: Dict[str, Any]
    base: Optional[str] = None
    vocab: Optional[str] = None


class JSONLDParser:
    """Parser for JSON-LD documents."""
    
    def parse(self, content: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """Parse JSON-LD content."""
        try:
            data = json.loads(content)
            return self._normalize(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON-LD: {e}")
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parse JSON-LD file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return self.parse(f.read(), file_path)
    
    def _normalize(self, data: Any) -> Dict[str, Any]:
        """Normalize JSON-LD to standard form."""
        if isinstance(data, list):
            return {"@graph": data}
        return data
    
    def extract_context(self, data: Dict[str, Any]) -> JSONLDContext:
        """Extract and parse @context."""
        ctx = data.get("@context", {})
        if isinstance(ctx, str):
            # Remote context - would need fetching
            return JSONLDContext(prefixes={}, terms={})
        
        prefixes = {}
        terms = {}
        base = None
        vocab = None
        
        if isinstance(ctx, dict):
            for key, value in ctx.items():
                if key == "@base":
                    base = value
                elif key == "@vocab":
                    vocab = value
                elif isinstance(value, str) and value.endswith('/'):
                    prefixes[key] = value
                else:
                    terms[key] = value
        
        return JSONLDContext(
            prefixes=prefixes,
            terms=terms,
            base=base,
            vocab=vocab
        )


class JSONLDValidator:
    """Validator for JSON-LD documents."""
    
    def validate(self, content: str, file_path: Optional[str] = None) -> ValidationResult:
        """Validate JSON-LD content."""
        result = ValidationResult(
            format_name="jsonld",
            source_path=file_path
        )
        
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            result.add_error(
                IssueCategory.SYNTAX_ERROR,
                f"Invalid JSON: {e}",
                location=f"line {e.lineno}, column {e.colno}"
            )
            return result
        
        # Validate structure
        self._validate_structure(data, result)
        
        # Validate context
        self._validate_context(data, result)
        
        # Count statistics
        result.statistics = self._gather_statistics(data)
        
        return result
    
    def validate_file(self, file_path: str) -> ValidationResult:
        """Validate JSON-LD file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return self.validate(f.read(), file_path)
    
    def _validate_structure(self, data: Any, result: ValidationResult) -> None:
        """Validate JSON-LD structure."""
        if not isinstance(data, (dict, list)):
            result.add_error(
                IssueCategory.SYNTAX_ERROR,
                "JSON-LD root must be an object or array"
            )
            return
        
        if isinstance(data, dict):
            # Check for @context
            if "@context" not in data:
                result.add_warning(
                    IssueCategory.MISSING_REQUIRED,
                    "No @context found - document may not be valid JSON-LD"
                )
    
    def _validate_context(self, data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate @context."""
        ctx = data.get("@context")
        if ctx is None:
            return
        
        if isinstance(ctx, str):
            result.add_info(
                IssueCategory.CUSTOM,
                f"Remote context: {ctx}",
                recommendation="Remote contexts will be resolved during conversion"
            )
        elif isinstance(ctx, list):
            result.add_info(
                IssueCategory.CUSTOM,
                f"Combined context with {len(ctx)} parts"
            )
    
    def _gather_statistics(self, data: Any) -> Dict[str, Any]:
        """Gather document statistics."""
        stats = {
            "has_context": False,
            "node_count": 0,
            "type_count": 0,
        }
        
        if isinstance(data, dict):
            stats["has_context"] = "@context" in data
            self._count_nodes(data, stats)
        
        return stats
    
    def _count_nodes(self, data: Any, stats: Dict[str, Any]) -> None:
        """Recursively count nodes."""
        if isinstance(data, dict):
            stats["node_count"] += 1
            if "@type" in data:
                stats["type_count"] += 1
            for value in data.values():
                self._count_nodes(value, stats)
        elif isinstance(data, list):
            for item in data:
                self._count_nodes(item, stats)


class JSONLDConverter:
    """Converter from JSON-LD to Fabric format."""
    
    def __init__(self):
        self.parser = JSONLDParser()
        self._id_gen = get_id_generator()
    
    def convert(
        self,
        content: str,
        id_prefix: int = 1000000000000,
        **kwargs
    ) -> ConversionResult:
        """Convert JSON-LD to Fabric ontology format."""
        entity_types: List[EntityType] = []
        relationship_types: List[RelationshipType] = []
        skipped: List[SkippedItem] = []
        warnings: List[str] = []
        
        try:
            data = self.parser.parse(content)
            context = self.parser.extract_context(data)
            
            # Extract types from @graph or root
            nodes = data.get("@graph", [data] if "@type" in data else [])
            
            # Group by @type to create entity types
            type_instances: Dict[str, List[Dict]] = {}
            for node in nodes:
                if isinstance(node, dict) and "@type" in node:
                    node_type = node["@type"]
                    if isinstance(node_type, list):
                        node_type = node_type[0]  # Take first type
                    if node_type not in type_instances:
                        type_instances[node_type] = []
                    type_instances[node_type].append(node)
            
            # Create entity type for each @type
            for type_name, instances in type_instances.items():
                entity = self._create_entity_type(
                    type_name, instances, context, id_prefix
                )
                entity_types.append(entity)
            
        except Exception as e:
            warnings.append(f"Conversion error: {e}")
        
        return ConversionResult(
            entity_types=entity_types,
            relationship_types=relationship_types,
            skipped_items=skipped,
            warnings=warnings,
        )
    
    def _create_entity_type(
        self,
        type_name: str,
        instances: List[Dict],
        context: JSONLDContext,
        id_prefix: int
    ) -> EntityType:
        """Create an EntityType from JSON-LD type."""
        # Extract local name from URI
        name = self._extract_name(type_name)
        
        # Collect all properties from instances
        all_props: Dict[str, str] = {}
        for instance in instances:
            for key, value in instance.items():
                if not key.startswith("@"):
                    prop_type = self._infer_fabric_type(value)
                    if key not in all_props:
                        all_props[key] = prop_type
        
        # Create properties
        properties = []
        for prop_name, prop_type in all_props.items():
            properties.append(EntityTypeProperty(
                id=self._id_gen.next_id(),
                name=self._extract_name(prop_name),
                valueType=prop_type
            ))
        
        return EntityType(
            id=self._id_gen.next_id(),
            name=name,
            properties=properties
        )
    
    def _extract_name(self, uri_or_name: str) -> str:
        """Extract local name from URI or use as-is."""
        if uri_or_name.startswith("http"):
            # Extract fragment or last path segment
            if "#" in uri_or_name:
                return uri_or_name.split("#")[-1]
            return uri_or_name.rstrip("/").split("/")[-1]
        return uri_or_name
    
    def _infer_fabric_type(self, value: Any) -> str:
        """Infer Fabric type from JSON value."""
        if isinstance(value, bool):
            return "Boolean"
        elif isinstance(value, int):
            return "BigInt"
        elif isinstance(value, float):
            return "Double"
        elif isinstance(value, dict):
            # Check for typed value
            if "@type" in value:
                return JSONLD_TO_FABRIC_TYPE.get(value["@type"], "String")
            if "@value" in value:
                return self._infer_fabric_type(value["@value"])
        return "String"


class JSONLDPlugin(OntologyPlugin):
    """
    JSON-LD format plugin for Fabric Ontology Converter.
    
    Supports conversion of JSON-LD documents containing schema.org
    or custom vocabularies to Fabric ontology format.
    """
    
    @property
    def format_name(self) -> str:
        return "jsonld"
    
    @property
    def display_name(self) -> str:
        return "JSON-LD"
    
    @property
    def file_extensions(self) -> Set[str]:
        return {".jsonld", ".json-ld"}
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def get_parser(self) -> JSONLDParser:
        return JSONLDParser()
    
    def get_validator(self) -> JSONLDValidator:
        return JSONLDValidator()
    
    def get_converter(self) -> JSONLDConverter:
        return JSONLDConverter()
    
    def get_type_mappings(self) -> Dict[str, str]:
        return JSONLD_TO_FABRIC_TYPE
    
    def register_cli_arguments(self, parser) -> None:
        """Add JSON-LD specific CLI arguments."""
        parser.add_argument(
            "--expand-context",
            action="store_true",
            help="Expand remote @context references"
        )
        parser.add_argument(
            "--base-uri",
            help="Base URI for relative references"
        )
```

### Sample JSON-LD Files

```json
// samples/jsonld/simple_person.jsonld
{
    "@context": {
        "schema": "https://schema.org/",
        "name": "schema:name",
        "email": "schema:email",
        "birthDate": {
            "@id": "schema:birthDate",
            "@type": "http://www.w3.org/2001/XMLSchema#date"
        },
        "knows": {
            "@id": "schema:knows",
            "@type": "@id"
        }
    },
    "@graph": [
        {
            "@id": "person:1",
            "@type": "schema:Person",
            "name": "Alice",
            "email": "alice@example.com",
            "birthDate": "1990-05-15"
        },
        {
            "@id": "person:2",
            "@type": "schema:Person",
            "name": "Bob",
            "email": "bob@example.com",
            "knows": "person:1"
        }
    ]
}
```

---

## Testing Strategy

### Test Structure

```
tests/
├── plugins/                   # NEW: Plugin tests
│   ├── __init__.py
│   ├── test_plugin_base.py    # OntologyPlugin ABC tests
│   ├── test_plugin_manager.py # PluginManager tests
│   ├── test_plugin_loading.py # Discovery and loading tests
│   └── builtin/
│       ├── test_rdf_plugin.py
│       ├── test_dtdl_plugin.py
│       └── test_jsonld_plugin.py
│
├── common/                    # NEW: Common module tests
│   ├── __init__.py
│   ├── test_type_registry.py
│   ├── test_id_generator.py
│   └── test_validation.py
│
├── fixtures/
│   ├── __init__.py
│   ├── ttl_fixtures.py        # Existing
│   ├── dtdl_fixtures.py       # Existing
│   └── jsonld_fixtures.py     # NEW
```

### Test Fixtures

```python
# tests/fixtures/jsonld_fixtures.py

SIMPLE_JSONLD = '''{
    "@context": {
        "name": "http://schema.org/name"
    },
    "@type": "Person",
    "name": "Test Person"
}'''

JSONLD_WITH_TYPES = '''{
    "@context": {
        "schema": "https://schema.org/",
        "xsd": "http://www.w3.org/2001/XMLSchema#"
    },
    "@graph": [
        {
            "@type": "schema:Person",
            "schema:name": "Alice",
            "schema:age": {
                "@value": "30",
                "@type": "xsd:integer"
            }
        }
    ]
}'''

JSONLD_WITH_RELATIONSHIPS = '''{
    "@context": {
        "knows": {"@id": "http://xmlns.com/foaf/0.1/knows", "@type": "@id"}
    },
    "@graph": [
        {"@id": "person:1", "@type": "Person", "name": "Alice"},
        {"@id": "person:2", "@type": "Person", "name": "Bob", "knows": "person:1"}
    ]
}'''
```

### Sample Test Cases

```python
# tests/plugins/test_plugin_manager.py

import pytest
from plugins.manager import PluginManager
from plugins.base import OntologyPlugin

class TestPluginManager:
    """Tests for PluginManager."""
    
    def test_register_plugin(self):
        """Test plugin registration."""
        manager = PluginManager()
        
        class MockPlugin(OntologyPlugin):
            format_name = "mock"
            display_name = "Mock Format"
            file_extensions = {".mock"}
            
            def get_parser(self): return None
            def get_validator(self): return None
            def get_converter(self): return None
        
        manager.register_plugin(MockPlugin())
        assert manager.get_plugin("mock") is not None
    
    def test_get_plugin_for_extension(self):
        """Test extension-based plugin lookup."""
        manager = PluginManager()
        manager.discover_plugins()
        
        rdf_plugin = manager.get_plugin_for_extension(".ttl")
        assert rdf_plugin is not None
        assert rdf_plugin.format_name == "rdf"
    
    def test_list_formats(self):
        """Test listing available formats."""
        manager = PluginManager()
        manager.discover_plugins()
        
        formats = manager.list_formats()
        assert "rdf" in formats
        assert "dtdl" in formats


# tests/plugins/builtin/test_jsonld_plugin.py

import pytest
from plugins.builtin.jsonld_plugin import (
    JSONLDPlugin,
    JSONLDParser,
    JSONLDValidator,
    JSONLDConverter,
)
from fixtures.jsonld_fixtures import (
    SIMPLE_JSONLD,
    JSONLD_WITH_TYPES,
    JSONLD_WITH_RELATIONSHIPS,
)

class TestJSONLDParser:
    """Tests for JSON-LD parser."""
    
    def test_parse_simple(self):
        """Test parsing simple JSON-LD."""
        parser = JSONLDParser()
        result = parser.parse(SIMPLE_JSONLD)
        assert "@type" in result
        assert result["@type"] == "Person"
    
    def test_parse_with_graph(self):
        """Test parsing JSON-LD with @graph."""
        parser = JSONLDParser()
        result = parser.parse(JSONLD_WITH_TYPES)
        assert "@graph" in result


class TestJSONLDValidator:
    """Tests for JSON-LD validator."""
    
    def test_validate_valid_document(self):
        """Test validation of valid JSON-LD."""
        validator = JSONLDValidator()
        result = validator.validate(SIMPLE_JSONLD)
        assert result.is_valid
        assert result.error_count == 0
    
    def test_validate_invalid_json(self):
        """Test validation of invalid JSON."""
        validator = JSONLDValidator()
        result = validator.validate("not valid json")
        assert not result.is_valid
        assert result.error_count > 0


class TestJSONLDConverter:
    """Tests for JSON-LD converter."""
    
    def test_convert_simple(self):
        """Test converting simple JSON-LD."""
        converter = JSONLDConverter()
        result = converter.convert(SIMPLE_JSONLD)
        
        assert len(result.entity_types) == 1
        assert result.entity_types[0].name == "Person"
    
    def test_convert_with_properties(self):
        """Test property extraction."""
        converter = JSONLDConverter()
        result = converter.convert(SIMPLE_JSONLD)
        
        entity = result.entity_types[0]
        prop_names = [p.name for p in entity.properties]
        assert "name" in prop_names
```

---

## Documentation Requirements

### New Documentation Files

1. **PLUGIN_GUIDE.md** - Complete guide for plugin development
2. **API.md** - Update with plugin APIs
3. **ARCHITECTURE.md** - Update with plugin architecture
4. **CLI_COMMANDS.md** - Update with plugin-related commands

### PLUGIN_GUIDE.md Outline

```markdown
# Plugin Development Guide

## Introduction
- What are plugins
- Use cases for plugins
- Built-in vs external plugins

## Quick Start
- Creating your first plugin
- Minimal plugin implementation
- Testing your plugin

## Plugin Structure
- OntologyPlugin base class
- Required methods
- Optional methods

## Parser Implementation
- ParserProtocol
- Handling different file formats
- Error handling

## Validator Implementation
- ValidatorProtocol
- Using ValidationResult
- Issue categories and severities

## Converter Implementation
- ConverterProtocol
- Using ConversionResult
- Type mapping

## CLI Integration
- Adding format-specific arguments
- Custom commands

## Distribution
- Entry points for pip install
- Local plugin directories

## Best Practices
- Error handling
- Logging
- Performance

## Reference
- Complete API reference
- Example plugins
```

---

## Migration Guide

### For Existing Users

The plugin system is **backward compatible**. Existing commands work unchanged:

```bash
# These continue to work exactly as before
python -m src.main validate --format rdf ontology.ttl
python -m src.main convert --format dtdl models/
```

### For Developers Extending the Project

**Before (direct imports):**
```python
from rdf import RDFToFabricConverter
from dtdl import DTDLParser
```

**After (plugin-based):**
```python
from plugins.manager import PluginManager

manager = PluginManager.get_instance()
manager.discover_plugins()

rdf_plugin = manager.get_plugin("rdf")
converter = rdf_plugin.get_converter()
```

### Deprecation Timeline

| Phase | Timeline | Action |
|-------|----------|--------|
| Phase 1 | Immediate | Old imports continue working |
| Phase 2 | +3 months | Deprecation warnings added |
| Phase 3 | +6 months | Old imports removed |

---

## File Structure Summary

### New Files to Create

```
src/
├── common/
│   ├── __init__.py
│   ├── type_registry.py
│   ├── id_generator.py
│   ├── validation.py
│   ├── serialization.py
│   └── property_utils.py
│
├── plugins/
│   ├── __init__.py
│   ├── base.py
│   ├── protocols.py
│   ├── manager.py
│   ├── loader.py
│   └── builtin/
│       ├── __init__.py
│       ├── rdf_plugin.py
│       ├── dtdl_plugin.py
│       └── jsonld_plugin.py

samples/
├── jsonld/
│   ├── simple_person.jsonld
│   ├── organization.jsonld
│   └── product_catalog.jsonld
│
├── plugins/
│   └── sample_plugin.py

tests/
├── common/
│   ├── __init__.py
│   ├── test_type_registry.py
│   ├── test_id_generator.py
│   └── test_validation.py
│
├── plugins/
│   ├── __init__.py
│   ├── test_plugin_base.py
│   ├── test_plugin_manager.py
│   └── builtin/
│       ├── test_rdf_plugin.py
│       ├── test_dtdl_plugin.py
│       └── test_jsonld_plugin.py

docs/
├── PLUGIN_GUIDE.md
├── API.md (updated)
├── ARCHITECTURE.md (updated)
└── CLI_COMMANDS.md (updated)
```

### Files to Modify

| File | Changes |
|------|---------|
| `src/cli/format.py` | Use PluginManager for format registration |
| `src/cli/parsers.py` | Add plugin-specific argument builders |
| `src/cli/commands/unified.py` | Get converter/validator from plugins |
| `src/models/__init__.py` | Re-export common validation types |
| `pyproject.toml` | Add entry points configuration |
| `docs/ARCHITECTURE.md` | Document plugin architecture |
| `docs/API.md` | Document plugin APIs |

---

## Success Criteria

1. ✅ Plugin system loads without errors
2. ✅ All existing tests pass
3. ✅ RDF format works as plugin
4. ✅ DTDL format works as plugin
5. ✅ Sample JSON-LD plugin works
6. ✅ External plugins can be loaded
7. ✅ Documentation is complete
8. ✅ No performance regression

---

## Next Steps

After reviewing this plan:

1. **Approve** the overall design
2. **Prioritize** which phases to implement first
3. **Identify** any additional formats to support
4. **Discuss** any concerns or modifications

---

*Document Created: January 3, 2026*
*Last Updated: January 3, 2026*
*Implementation Status: All phases complete. Ready for GitHub upload.*
