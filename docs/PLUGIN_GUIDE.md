# Plugin Development Guide

This guide explains how to create plugins for the Fabric Ontology Converter. Plugins allow
you to add support for new ontology formats beyond the built-in RDF, DTDL, and JSON-LD formats.

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

### Built-in Plugins

| Plugin | Format | Extensions | Description |
|--------|--------|------------|-------------|
| RDF | `rdf` | `.ttl`, `.rdf`, `.owl` | RDF/OWL ontologies in Turtle format |
| DTDL | `dtdl` | `.json`, `.dtdl` | Digital Twins Definition Language v2/v3/v4 |
| JSON-LD | `jsonld` | `.jsonld` | JSON-LD linked data format |

## Plugin Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Plugin Manager                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ RDF Plugin   │  │ DTDL Plugin  │  │ JSON-LD      │           │
│  │              │  │              │  │ Plugin       │           │
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

Create a new Python file in `src/plugins/builtin/` (for built-in) or a custom directory:

```python
from plugins.base import OntologyPlugin
from plugins.protocols import ParserProtocol, ValidatorProtocol, ConverterProtocol
from typing import Set, Dict, List, Any, Optional

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
    
    def create_parser(self) -> ParserProtocol:
        """Return parser instance."""
        return MyFormatParser()
    
    def create_validator(self) -> ValidatorProtocol:
        """Return validator instance."""
        return MyFormatValidator()
    
    def create_converter(self) -> ConverterProtocol:
        """Return converter instance."""
        return MyFormatConverter()
    
    def get_type_mappings(self) -> Dict[str, str]:
        """Return type mappings from source types to Fabric types."""
        return MYFORMAT_TYPE_MAPPINGS
```

### Step 2: Implement the Parser

```python
from typing import Any, Optional, Dict

class MyFormatParser:
    """Parser for MyFormat documents."""
    
    def parse(self, content: str, file_path: Optional[str] = None) -> Dict[str, Any]:
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
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
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
    
    def validate(self, content: str, file_path: Optional[str] = None) -> ValidationResult:
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
    
    def _validate_structure(self, data: Dict[str, Any], result: ValidationResult):
        """Check document structure."""
        # Your validation logic
        pass
    
    def _validate_fabric_compatibility(self, data: Dict[str, Any], result: ValidationResult):
        """Check Fabric compatibility."""
        # Your validation logic
        pass
```

### Step 4: Implement the Converter

```python
from models import ConversionResult, EntityType, EntityTypeProperty, RelationshipType
from typing import List, Any

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
        
        entity_types: List[EntityType] = []
        relationship_types: List[RelationshipType] = []
        skipped_items: List[SkippedItem] = []
        warnings: List[str] = []
        
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
    
    def _extract_types(self, data: Dict[str, Any]) -> List[Any]:
        """Extract type definitions from parsed data."""
        # Your extraction logic
        return []
    
    def _extract_relationships(self, data: Dict[str, Any]) -> List[Any]:
        """Extract relationship definitions from parsed data."""
        # Your extraction logic
        return []
    
    def _create_entity_type(self, type_def: Any) -> EntityType:
        """Create an EntityType from a type definition."""
        # Your conversion logic
        pass
    
    def _create_relationship_type(self, rel_def: Any) -> RelationshipType:
        """Create a RelationshipType from a relationship definition."""
        # Your conversion logic
        pass
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
    "text": "String",
    "integer": "BigInt",
    "int": "BigInt",
    "long": "BigInt",
    "float": "Double",
    "double": "Double",
    "decimal": "Double",
    "boolean": "Boolean",
    "bool": "Boolean",
    "datetime": "DateTime",
    "date": "DateTime",
    "timestamp": "DateTime",
}
```

### Fabric Types Reference

| Fabric Type | Description | Use For |
|-------------|-------------|---------|
| `String` | Text values | Names, descriptions, identifiers |
| `BigInt` | Integer numbers | Counts, IDs, whole numbers |
| `Double` | Floating-point numbers | Measurements, calculations |
| `Boolean` | True/false values | Flags, states |
| `DateTime` | Date and time values | Timestamps, dates |

## Validation

Use the unified validation framework for consistent error reporting:

```python
from common.validation import ValidationResult, Severity, IssueCategory

def validate(self, content: str, file_path: Optional[str] = None) -> ValidationResult:
    result = ValidationResult(format_name=self.format_name, source_path=file_path)
    
    # Add error (blocks conversion)
    result.add_error(
        IssueCategory.SYNTAX_ERROR,
        "Invalid syntax at line 10",
        location="line 10",
        details={"line": 10, "column": 5}
    )
    
    # Add warning (allows conversion)
    result.add_warning(
        IssueCategory.FABRIC_COMPATIBILITY,
        "Property name too long, will be truncated",
        recommendation="Use shorter property names (max 128 chars)"
    )
    
    # Add info (informational)
    result.add_info(
        IssueCategory.CUSTOM,
        "Processing 50 types"
    )
    
    return result
```

### Issue Categories

| Category | Use For |
|----------|---------|
| `SYNTAX_ERROR` | Format/syntax problems |
| `MISSING_REQUIRED` | Missing required elements |
| `INVALID_VALUE` | Invalid property values |
| `NAME_TOO_LONG` | Names exceed Fabric limits (128 chars) |
| `INVALID_CHARACTER` | Unsupported characters in names |
| `UNSUPPORTED_CONSTRUCT` | Unsupported format features |
| `FABRIC_COMPATIBILITY` | Fabric-specific issues |
| `CUSTOM` | Plugin-specific issues |

## Testing Your Plugin

Create tests following the project patterns:

```python
# tests/plugins/test_myformat_plugin.py

import pytest
from plugins.builtin.myformat_plugin import MyFormatPlugin

class TestMyFormatPlugin:
    @pytest.fixture
    def plugin(self):
        return MyFormatPlugin()
    
    def test_format_name(self, plugin):
        assert plugin.format_name == "myformat"
    
    def test_display_name(self, plugin):
        assert plugin.display_name == "MyFormat"
    
    def test_extensions(self, plugin):
        assert ".myf" in plugin.file_extensions
        assert ".myformat" in plugin.file_extensions
    
    def test_version(self, plugin):
        assert plugin.version == "1.0.0"


class TestMyFormatParser:
    @pytest.fixture
    def parser(self):
        return MyFormatPlugin().create_parser()
    
    def test_parse_valid_content(self, parser):
        result = parser.parse('{"type": "Test"}')
        assert result is not None
    
    def test_parse_invalid_content_raises(self, parser):
        with pytest.raises(ValueError):
            parser.parse("not valid")


class TestMyFormatValidator:
    @pytest.fixture
    def validator(self):
        return MyFormatPlugin().create_validator()
    
    def test_validate_valid_content(self, validator):
        result = validator.validate('{"type": "Test", "properties": []}')
        assert result.is_valid
    
    def test_validate_invalid_content(self, validator):
        result = validator.validate("invalid content")
        assert not result.is_valid
        assert result.error_count > 0


class TestMyFormatConverter:
    @pytest.fixture
    def converter(self):
        return MyFormatPlugin().create_converter()
    
    def test_convert_creates_entities(self, converter):
        content = '{"types": [{"name": "Test"}]}'
        result = converter.convert(content)
        assert len(result.entity_types) > 0
    
    def test_convert_assigns_ids(self, converter):
        content = '{"types": [{"name": "Test"}]}'
        result = converter.convert(content, id_prefix=5000)
        assert result.entity_types[0].id == "5000"
```

Run tests:

```bash
# Run plugin tests only
pytest tests/plugins/test_myformat_plugin.py -v

# Run all tests
pytest
```

## Registration

### Built-in Plugin (Recommended for Core Plugins)

1. Create plugin file: `src/plugins/builtin/myformat_plugin.py`
2. Add export to `src/plugins/builtin/__init__.py`:

```python
from .myformat_plugin import MyFormatPlugin

__all__ = ["RDFPlugin", "DTDLPlugin", "JSONLDPlugin", "MyFormatPlugin"]
```

3. Register in `src/plugins/manager.py`:

```python
def _load_builtin_plugins(self) -> None:
    from .builtin import RDFPlugin, DTDLPlugin, JSONLDPlugin, MyFormatPlugin
    
    for plugin_class in [RDFPlugin, DTDLPlugin, JSONLDPlugin, MyFormatPlugin]:
        try:
            plugin = plugin_class()
            self.register(plugin)
        except Exception as e:
            logger.warning(f"Failed to load plugin: {e}")
```

### Entry Point (For External Packages)

Add to your package's `pyproject.toml`:

```toml
[project.entry-points."fabric_ontology.plugins"]
myformat = "mypackage.myformat_plugin:MyFormatPlugin"
```

### Manual Registration

```python
from plugins.manager import PluginManager
from mypackage.myformat_plugin import MyFormatPlugin

manager = PluginManager.get_instance()
manager.register(MyFormatPlugin())
```

## CLI Integration

After registration, your format works with all CLI commands:

```bash
# List available plugins
python -m src.main plugin list

# Validate
python -m src.main validate samples/myformat/example.myf --format myformat

# Convert (preview)
python -m src.main convert samples/myformat/example.myf --format myformat

# Convert with output
python -m src.main convert samples/myformat/example.myf --format myformat -o output/

# Upload to Fabric
python -m src.main upload samples/myformat/example.myf --format myformat --workspace my-ws
```

### Adding Custom CLI Arguments

Override `register_cli_arguments()` in your plugin:

```python
class MyFormatPlugin(OntologyPlugin):
    def register_cli_arguments(self, parser):
        """Add format-specific arguments."""
        parser.add_argument(
            "--myformat-strict",
            action="store_true",
            help="Enable strict validation for MyFormat"
        )
        parser.add_argument(
            "--myformat-version",
            type=str,
            choices=["1.0", "2.0"],
            default="2.0",
            help="MyFormat version to use"
        )
```

## Best Practices

### 1. Robust Parsing

```python
def parse(self, content: str, file_path: Optional[str] = None):
    """Always handle encoding and errors gracefully."""
    if not content or not content.strip():
        raise ValueError("Empty content")
    
    try:
        return self._do_parse(content)
    except UnicodeDecodeError:
        raise ValueError("File is not valid UTF-8")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    except Exception as e:
        raise ValueError(f"Parse error: {e}")
```

### 2. Comprehensive Validation

```python
def validate(self, content: str, file_path: Optional[str] = None) -> ValidationResult:
    result = ValidationResult(...)
    
    # 1. Check syntax first
    try:
        data = self.parser.parse(content)
    except ValueError as e:
        result.add_error(IssueCategory.SYNTAX_ERROR, str(e))
        return result  # Stop early on syntax errors
    
    # 2. Check required structure
    self._validate_structure(data, result)
    
    # 3. Check naming conventions
    self._validate_names(data, result)
    
    # 4. Check Fabric compatibility
    self._validate_fabric_limits(data, result)
    
    # 5. Gather statistics
    result.statistics = self._gather_stats(data)
    
    return result
```

### 3. Consistent ID Generation

```python
from common.id_generator import get_id_generator

class MyConverter:
    def __init__(self):
        self.id_gen = get_id_generator()
    
    def convert(self, content: str, id_prefix: int = 1000000000000, **kwargs):
        # Reset generator with prefix
        self.id_gen.reset(id_prefix)
        
        # Use generator for all IDs
        for type_def in types:
            entity = EntityType(
                id=self.id_gen.next_id(),
                name=type_def["name"],
                ...
            )
```

### 4. Type Mapping with Fallbacks

```python
def _get_fabric_type(self, source_type: str) -> str:
    """Map source type with fallback."""
    # Check exact match
    if source_type in TYPE_MAPPINGS:
        return TYPE_MAPPINGS[source_type]
    
    # Check case-insensitive
    normalized = source_type.lower()
    if normalized in TYPE_MAPPINGS:
        return TYPE_MAPPINGS[normalized]
    
    # Check URI suffixes (e.g., xsd:string -> string)
    if "#" in source_type:
        suffix = source_type.split("#")[-1].lower()
        if suffix in TYPE_MAPPINGS:
            return TYPE_MAPPINGS[suffix]
    
    # Log warning and use default
    logger.warning(f"Unknown type '{source_type}', defaulting to String")
    return "String"
```

### 5. Meaningful Error Messages

```python
# Good: Specific, actionable
result.add_error(
    IssueCategory.NAME_TOO_LONG,
    f"Property name '{prop_name}' is {len(prop_name)} characters (max 128)",
    location=f"Entity: {entity_name}",
    details={"property": prop_name, "length": len(prop_name), "max": 128},
    recommendation="Shorten the property name to 128 characters or less"
)

# Bad: Vague
result.add_error(IssueCategory.INVALID_VALUE, "Invalid property")
```

### 6. Handle Edge Cases

```python
def _create_entity_type(self, type_def: Dict[str, Any]) -> EntityType:
    # Handle missing name
    name = type_def.get("name", "").strip()
    if not name:
        raise ValueError("Type definition missing name")
    
    # Handle special characters
    safe_name = self._sanitize_name(name)
    
    # Handle empty properties
    properties = type_def.get("properties", []) or []
    
    return EntityType(
        id=self._next_id(),
        name=safe_name,
        properties=[self._create_property(p) for p in properties if p],
    )
```

## Examples

### Complete Plugin Example

See `src/plugins/builtin/jsonld_plugin.py` for a complete reference implementation
that demonstrates:

- Full parser with context handling
- Comprehensive validation
- Entity and relationship extraction
- Type mapping from Schema.org and XSD types
- Error handling and logging

### Sample Directory Structure

```
samples/
└── myformat/
    ├── README.md           # Format description
    ├── simple.myf          # Basic example
    ├── complex.myf         # Complex example with relationships
    └── schema_types.myf    # Example showing type mappings
```

### Test Directory Structure

```
tests/
└── plugins/
    ├── __init__.py
    ├── test_myformat_plugin.py
    └── fixtures/
        ├── __init__.py
        ├── valid_simple.myf
        ├── valid_complex.myf
        └── invalid_syntax.myf
```

## Troubleshooting

### Plugin Not Found

```
Error: Unknown format 'myformat'
```

**Solutions:**
1. Ensure plugin is registered in `src/plugins/manager.py`
2. Check for import errors: `python -c "from plugins.builtin.myformat_plugin import MyFormatPlugin"`
3. Run `python -m src.main plugin list` to see loaded plugins

### Validation Issues

```
ValidationResult: 0 errors, 5 warnings
```

**Solutions:**
1. Check if warnings are acceptable or need to be errors
2. Review severity levels in your validator
3. Use `--verbose` flag for more details

### Conversion Errors

```
ConversionResult: 0 entities, 10 skipped
```

**Solutions:**
1. Check `skipped_items` for reasons
2. Review parser output
3. Verify type mappings cover all source types

## Support

For questions or issues:

1. Review the JSON-LD plugin implementation as a reference
2. Check existing plugins for common patterns
3. Run the test suite to verify functionality
4. Open an issue on the project repository

---

**Last Updated:** Phase 4 - Plugin System Documentation
