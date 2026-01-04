# Plugin Development Guide

This guide explains how to create plugins for the Fabric Ontology Converter. Plugins allow
you to add support for new ontology formats beyond the built-in RDF and DTDL formats.

## Table of Contents

1. [Overview](#overview)
2. [Plugin Architecture](#plugin-architecture)
3. [Creating a Plugin](#creating-a-plugin)
4. [Plugin Components](#plugin-components)
5. [Type Mappings](#type-mappings)
6. [Validation](#validation)
7. [Testing Your Plugin](#testing-your-plugin)
8. [Registration](#registration)
9. [CLI Integration](#cli-integration)
10. [Best Practices](#best-practices)
11. [Examples](#examples)

## Overview

The plugin system allows extending the Fabric Ontology Converter with new ontology formats.
Each plugin provides:

- **Parser**: Reads and parses the source format
- **Validator**: Validates documents for correctness and Fabric compatibility
- **Converter**: Transforms the format to Fabric entity and relationship types
- **Type Mappings**: Maps source types to Fabric types

## Plugin Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Plugin Manager                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ RDF Plugin   │  │ DTDL Plugin  │  │ Custom Plugin│           │
│  │              │  │              │  │              │           │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │           │
│  │ │  Parser  │ │  │ │  Parser  │ │  │ │  Parser  │ │           │
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │           │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │           │
│  │ │Validator │ │  │ │Validator │ │  │ │Validator │ │           │
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │           │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │           │
│  │ │Converter │ │  │ │Converter │ │  │ │Converter │ │           │
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                        Common Layer                               │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐     │
│  │ Type Registry  │  │  ID Generator  │  │   Validation   │     │
│  └────────────────┘  └────────────────┘  └────────────────┘     │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Fabric Models                                 │
│  EntityType  │  RelationshipType  │  ConversionResult            │
└──────────────────────────────────────────────────────────────────┘
```

## Creating a Plugin

### Step 1: Create the Plugin Class

Create a new Python file in `src/plugins/` (or a custom plugins directory):

```python
from plugins.base import OntologyPlugin
from typing import Set, Dict, List, Any

class MyFormatPlugin(OntologyPlugin):
    """Plugin for MyFormat ontology files."""
    
    @property
    def format_name(self) -> str:
        """Unique identifier for the format (lowercase)."""
        return "myformat"
    
    @property
    def display_name(self) -> str:
        """Human-readable name."""
        return "MyFormat"
    
    @property
    def file_extensions(self) -> Set[str]:
        """Supported file extensions (with dot)."""
        return {".myf", ".myformat"}
    
    @property
    def version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    @property
    def author(self) -> str:
        """Plugin author."""
        return "Your Name"
    
    @property
    def dependencies(self) -> List[str]:
        """Required Python packages (for validation)."""
        return []  # e.g., ["lxml>=4.9.0"]
    
    def get_parser(self):
        """Return parser instance."""
        return MyFormatParser()
    
    def get_validator(self):
        """Return validator instance."""
        return MyFormatValidator()
    
    def get_converter(self):
        """Return converter instance."""
        return MyFormatConverter()
    
    def get_type_mappings(self) -> Dict[str, str]:
        """Return type mappings."""
        return MYFORMAT_TYPE_MAPPINGS
```

### Step 2: Implement the Parser

```python
class MyFormatParser:
    """Parser for MyFormat documents."""
    
    def parse(self, content: str, file_path: str = None) -> Any:
        """
        Parse content string.
        
        Args:
            content: File content as string
            file_path: Optional path for error messages
            
        Returns:
            Parsed document structure
            
        Raises:
            ValueError: If content is invalid
        """
        # Your parsing logic here
        pass
    
    def parse_file(self, file_path: str) -> Any:
        """Parse a file."""
        from pathlib import Path
        content = Path(file_path).read_text(encoding='utf-8')
        return self.parse(content, file_path)
```

### Step 3: Implement the Validator

```python
from common.validation import ValidationResult, Severity, IssueCategory

class MyFormatValidator:
    """Validator for MyFormat documents."""
    
    def __init__(self):
        self.parser = MyFormatParser()
    
    def validate(self, content: str, file_path: str = None) -> ValidationResult:
        """
        Validate content.
        
        Args:
            content: Document content
            file_path: Optional file path
            
        Returns:
            ValidationResult with issues
        """
        result = ValidationResult(
            format_name="myformat",
            source_path=file_path
        )
        
        # Check syntax
        try:
            data = self.parser.parse(content, file_path)
        except ValueError as e:
            result.add_error(IssueCategory.SYNTAX_ERROR, str(e))
            return result
        
        # Add more validation checks...
        self._validate_structure(data, result)
        self._validate_fabric_compatibility(data, result)
        
        return result
    
    def _validate_structure(self, data, result):
        """Check document structure."""
        # Your validation logic
        pass
    
    def _validate_fabric_compatibility(self, data, result):
        """Check Fabric compatibility."""
        # Your validation logic
        pass
```

### Step 4: Implement the Converter

```python
from models import ConversionResult, EntityType, RelationshipType

class MyFormatConverter:
    """Converter from MyFormat to Fabric format."""
    
    def __init__(self):
        self.parser = MyFormatParser()
        self._id_counter = 1000000000000
    
    def convert(
        self,
        content: str,
        id_prefix: int = 1000000000000,
        **kwargs
    ) -> ConversionResult:
        """
        Convert content to Fabric format.
        
        Args:
            content: Document content
            id_prefix: Starting ID for entities
            **kwargs: Additional options
            
        Returns:
            ConversionResult with entities and relationships
        """
        self._id_counter = id_prefix
        
        entity_types = []
        relationship_types = []
        skipped_items = []
        warnings = []
        
        try:
            data = self.parser.parse(content)
            
            # Extract entity types
            for type_def in self._extract_types(data):
                entity = self._create_entity_type(type_def)
                entity_types.append(entity)
            
            # Extract relationships
            for rel_def in self._extract_relationships(data):
                rel = self._create_relationship_type(rel_def)
                relationship_types.append(rel)
                
        except Exception as e:
            warnings.append(f"Conversion error: {e}")
        
        return ConversionResult(
            entity_types=entity_types,
            relationship_types=relationship_types,
            skipped_items=skipped_items,
            warnings=warnings,
        )
    
    def _next_id(self) -> str:
        """Generate unique ID."""
        current = self._id_counter
        self._id_counter += 1
        return str(current)
```

## Plugin Components

### Required Components

| Component | Interface | Purpose |
|-----------|-----------|---------|
| Plugin | `OntologyPlugin` | Main entry point, metadata, factory |
| Parser | `ParserProtocol` | Parse source format |
| Validator | `ValidatorProtocol` | Validate documents |
| Converter | `ConverterProtocol` | Convert to Fabric format |

### Optional Components

| Component | Interface | Purpose |
|-----------|-----------|---------|
| Exporter | `ExporterProtocol` | Export Fabric format back to source |
| CLI Args | `register_cli_arguments()` | Add format-specific CLI options |

## Type Mappings

Define mappings from your source types to Fabric types:

```python
MYFORMAT_TYPE_MAPPINGS = {
    # Source type -> Fabric type
    "string": "String",
    "integer": "BigInt",
    "float": "Double",
    "boolean": "Boolean",
    "datetime": "DateTime",
    # Add more mappings...
}
```

### Fabric Types Reference

| Fabric Type | Description |
|-------------|-------------|
| `String` | Text values |
| `BigInt` | Integer numbers |
| `Double` | Floating-point numbers |
| `Boolean` | True/false values |
| `DateTime` | Date and time values |

## Validation

Use the unified validation framework for consistent error reporting:

```python
from common.validation import ValidationResult, Severity, IssueCategory

def validate(self, content: str, file_path: str = None) -> ValidationResult:
    result = ValidationResult(format_name=self.format_name, source_path=file_path)
    
    # Add error
    result.add_error(
        IssueCategory.SYNTAX_ERROR,
        "Invalid syntax at line 10",
        location="line 10",
        details={"line": 10, "column": 5}
    )
    
    # Add warning
    result.add_warning(
        IssueCategory.FABRIC_COMPATIBILITY,
        "Property name too long, will be truncated",
        recommendation="Use shorter property names"
    )
    
    # Add info
    result.add_info(
        IssueCategory.CUSTOM,
        "Processing 50 types"
    )
    
    return result
```

### Issue Categories

- `SYNTAX_ERROR`: Format/syntax problems
- `MISSING_REQUIRED`: Missing required elements
- `INVALID_VALUE`: Invalid property values
- `NAME_TOO_LONG`: Names exceed Fabric limits
- `INVALID_CHARACTER`: Unsupported characters
- `UNSUPPORTED_CONSTRUCT`: Unsupported format features
- `FABRIC_COMPATIBILITY`: Fabric-specific issues
- `CUSTOM`: Plugin-specific issues

## Testing Your Plugin

Create tests following the project patterns:

```python
# tests/plugins/test_myformat_plugin.py

import pytest
from plugins.myformat_plugin import MyFormatPlugin

class TestMyFormatPlugin:
    @pytest.fixture
    def plugin(self):
        return MyFormatPlugin()
    
    def test_format_name(self, plugin):
        assert plugin.format_name == "myformat"
    
    def test_extensions(self, plugin):
        assert ".myf" in plugin.file_extensions
    
    def test_parser_valid_content(self, plugin):
        parser = plugin.get_parser()
        result = parser.parse('{"type": "Test"}')
        assert result is not None
    
    def test_validator_detects_errors(self, plugin):
        validator = plugin.get_validator()
        result = validator.validate("invalid content")
        assert not result.is_valid
    
    def test_converter_creates_entities(self, plugin):
        converter = plugin.get_converter()
        result = converter.convert('{"type": "Test", "name": "Example"}')
        assert len(result.entity_types) > 0
```

Run tests:

```bash
pytest tests/plugins/test_myformat_plugin.py -v
```

## Registration

### Automatic Registration (Recommended)

1. Place plugin in `src/plugins/` directory
2. Use entry points in `pyproject.toml`:

```toml
[project.entry-points."fabric_ontology.plugins"]
myformat = "plugins.myformat_plugin:MyFormatPlugin"
```

### Manual Registration

```python
from plugins.manager import PluginManager
from plugins.myformat_plugin import MyFormatPlugin

manager = PluginManager.get_instance()
manager.register(MyFormatPlugin())
```

## CLI Integration

After registration, your format works with all CLI commands:

```bash
# Validate
python -m src.main validate samples/myformat/example.myf --format myformat

# Convert
python -m src.main convert samples/myformat/example.myf --format myformat -o output

# Upload
python -m src.main upload samples/myformat/example.myf --format myformat --workspace my-ws
```

### Adding Custom CLI Arguments

```python
class MyFormatPlugin(OntologyPlugin):
    def register_cli_arguments(self, parser):
        """Add format-specific arguments."""
        parser.add_argument(
            "--myformat-option",
            type=str,
            help="Custom option for MyFormat"
        )
```

## Best Practices

### 1. Robust Parsing

```python
def parse(self, content: str, file_path: str = None):
    """Always handle encoding and errors gracefully."""
    try:
        # Try parsing
        return self._do_parse(content)
    except UnicodeDecodeError:
        raise ValueError("File is not valid UTF-8")
    except Exception as e:
        raise ValueError(f"Parse error: {e}")
```

### 2. Comprehensive Validation

```python
def validate(self, content: str, file_path: str = None):
    result = ValidationResult(...)
    
    # 1. Check syntax
    # 2. Check structure  
    # 3. Check naming conventions
    # 4. Check Fabric compatibility
    # 5. Gather statistics
    
    return result
```

### 3. Consistent ID Generation

```python
# Use common ID generator
from common.id_generator import get_id_generator

class MyConverter:
    def __init__(self):
        self.id_gen = get_id_generator()
    
    def _create_entity(self, name: str):
        return EntityType(
            id=self.id_gen.next_id(),
            name=name,
            ...
        )
```

### 4. Type Mapping Fallbacks

```python
def _get_fabric_type(self, source_type: str) -> str:
    """Map source type with fallback."""
    # Check exact match
    if source_type in TYPE_MAPPINGS:
        return TYPE_MAPPINGS[source_type]
    
    # Check normalized
    normalized = source_type.lower()
    if normalized in TYPE_MAPPINGS:
        return TYPE_MAPPINGS[normalized]
    
    # Default fallback
    return "String"
```

### 5. Meaningful Error Messages

```python
result.add_error(
    IssueCategory.INVALID_VALUE,
    f"Property '{prop_name}' has unsupported type '{prop_type}'",
    location=f"Entity: {entity_name}",
    details={"property": prop_name, "type": prop_type},
    recommendation=f"Use one of: {', '.join(SUPPORTED_TYPES)}"
)
```

## Examples

### Complete Plugin Example

See `plugins/builtin/jsonld_plugin.py` for a complete reference implementation.

### Sample Files

Place sample files in `samples/myformat/`:

```
samples/
└── myformat/
    ├── simple.myf
    ├── complex.myf
    └── README.md
```

### Test Files

```
tests/
└── plugins/
    ├── __init__.py
    ├── test_myformat_plugin.py
    └── fixtures/
        ├── valid.myf
        └── invalid.myf
```

## Support

For questions or issues:

1. Check existing plugins for patterns
2. Review the PLUGIN_PLAN.md document
3. Run tests to verify functionality
4. Open an issue on the project repository
