# CLI Commands Reference

This document provides a comprehensive reference for all CLI commands available in the RDF/DTDL to Microsoft Fabric Ontology Converter.

## Table of Contents

- [Command Structure](#command-structure)
- [Supported Formats](#supported-formats)
- [Unified Commands](#unified-commands)
- [Common Commands](#common-commands)
- [Plugin Commands](#plugin-commands)
- [Streaming Mode](#streaming-mode)
- [Exit Codes](#exit-codes)
- [See Also](#see-also)

## Command Structure

All format-specific operations use a unified verb with a `--format` flag:

```bash
python -m src.main <command> --format {rdf,dtdl,jsonld} <path> [options]
```

| Command | Description |
|---------|-------------|
| `validate` | Validate ontology files for Fabric compatibility |
| `convert` | Convert ontology files to Fabric JSON format |
| `upload` | Upload ontology to Microsoft Fabric |
| `export` | Export ontology from Fabric to TTL (RDF only) |

Common workspace commands do not require a format flag:

| Command | Description |
|---------|-------------|
| `list` | List ontologies in the workspace |
| `get` | Get ontology details |
| `delete` | Delete an ontology |
| `compare` | Compare two TTL files |
| `test` | Test with sample ontology |

Plugin management commands:

| Command | Description |
|---------|-------------|
| `plugin list` | List available plugins |
| `plugin info` | Show plugin details |

## Supported Formats

The converter supports multiple ontology formats via a plugin system:

| Format | Extensions | Description |
|--------|------------|-------------|
| `rdf` | `.ttl`, `.rdf`, `.owl` | RDF/OWL ontologies in Turtle format |
| `dtdl` | `.json`, `.dtdl` | Digital Twins Definition Language v2/v3/v4 |
| `jsonld` | `.jsonld` | JSON-LD linked data format |

Use the `plugin list` command to see all available formats.

## Unified Commands

### validate

Validate ontology files for Fabric compatibility.

```bash
# Validate RDF/TTL file
python -m src.main validate --format rdf ontology.ttl

# Validate with verbose output
python -m src.main validate --format rdf ontology.ttl --verbose

# Validate all files in a directory recursively
python -m src.main validate --format rdf ./ontologies/ --recursive

# Save validation report
python -m src.main validate --format rdf ontology.ttl --output report.json
python -m src.main validate --format rdf ontology.ttl --save-report

# Validate DTDL files
python -m src.main validate --format dtdl models/
python -m src.main validate --format dtdl models/ --recursive --verbose
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--format` | | Input format: `rdf` or `dtdl` (required) |
| `--output` | `-o` | Output JSON report file path |
| `--save-report` | `-s` | Save report to `<file>.validation.json` |
| `--verbose` | `-v` | Show detailed human-readable report |
| `--recursive` | `-r` | Recursively search directories |
| `--allow-relative-up` | | Allow `..` in paths within current directory |
| `--continue-on-error` | | Continue validation even if parse errors occur |

### convert

Convert ontology files to Fabric JSON format without uploading.

```bash
# Convert RDF file
python -m src.main convert --format rdf ontology.ttl

# Convert with custom output path
python -m src.main convert --format rdf ontology.ttl --output fabric_def.json

# Batch convert all files in a directory
python -m src.main convert --format rdf ./ontologies/ --recursive

# Use streaming mode for large files
python -m src.main convert --format rdf large_ontology.ttl --streaming

# Convert DTDL with custom name
python -m src.main convert --format dtdl models/ --ontology-name MyDigitalTwin

# Save DTMI mapping for reference
python -m src.main convert --format dtdl models/ --save-mapping

# Flatten components into parent entities
python -m src.main convert --format dtdl models/ --flatten-components
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--format` | | Input format: `rdf` or `dtdl` (required) |
| `--output` | `-o` | Output JSON file path or directory |
| `--ontology-name` | `-n` | Name for the ontology |
| `--description` | `-d` | Ontology description |
| `--streaming` | | Use streaming mode for large files (>100MB) |
| `--force-memory` | | Skip memory safety checks |
| `--recursive` | `-r` | Recursively search directories |
| `--allow-relative-up` | | Allow `..` in paths within current directory |
| `--save-report` | `-s` | Save conversion report |
| `--namespace` | | Namespace for entity types (DTDL, default: `usertypes`) |
| `--flatten-components` | | Flatten component properties into parent (DTDL) |
| `--save-mapping` | | Save DTMI to Fabric ID mapping file (DTDL) |

### upload

Upload ontology to Microsoft Fabric.

```bash
# Upload RDF file
python -m src.main upload --format rdf ontology.ttl

# Upload with custom name
python -m src.main upload --format rdf ontology.ttl --ontology-name MyOntology

# Batch upload directory
python -m src.main upload --format rdf ./ontologies/ --recursive --force

# Update existing ontology
python -m src.main upload --format rdf ontology.ttl --ontology-name ExistingOntology --update

# Upload DTDL models
python -m src.main upload --format dtdl ./models/ --ontology-name MyDigitalTwin

# Dry run (convert without uploading)
python -m src.main upload --format dtdl ./models/ --dry-run --output preview.json

# Upload with custom namespace
python -m src.main upload --format dtdl ./models/ --namespace custom_ns
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--format` | | Input format: `rdf` or `dtdl` (required) |
| `--config` | `-c` | Path to configuration file |
| `--ontology-name` | `-n` | Name for the ontology |
| `--description` | `-d` | Ontology description |
| `--update` | `-u` | Update if ontology exists |
| `--skip-validation` | | Skip pre-flight validation |
| `--force` | `-f` | Proceed even if issues found |
| `--streaming` | | Use streaming mode for large files |
| `--force-memory` | | Skip memory safety checks |
| `--recursive` | `-r` | Batch upload all files in directory |
| `--allow-relative-up` | | Allow `..` in paths within current directory |
| `--dry-run` | | Convert but do not upload |
| `--output` | `-o` | Output file path for dry-run mode |
| `--namespace` | | Namespace for entity types (DTDL, default: `usertypes`) |
| `--flatten-components` | | Flatten component properties into parent (DTDL) |
| `--continue-on-error` | | Continue on parse errors |

### export

Export an ontology from Fabric to TTL format (RDF only).

```bash
# Export by ontology ID
python -m src.main export 12345678-1234-1234-1234-123456789012

# Export with custom output path
python -m src.main export 12345678-1234-1234-1234-123456789012 --output exported.ttl
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--config` | `-c` | Path to configuration file |
| `--output` | `-o` | Output TTL file path |

## Common Commands

### list

List all ontologies in the configured Fabric workspace.

```bash
python -m src.main list
python -m src.main list --config custom_config.json
```

### get

Get details of a specific ontology.

```bash
python -m src.main get 12345678-1234-1234-1234-123456789012
python -m src.main get 12345678-1234-1234-1234-123456789012 --with-definition
```

### delete

Delete an ontology from Fabric.

```bash
python -m src.main delete 12345678-1234-1234-1234-123456789012
python -m src.main delete 12345678-1234-1234-1234-123456789012 --force
```

### compare

Compare two TTL files for semantic equivalence.

```bash
python -m src.main compare original.ttl exported.ttl
python -m src.main compare original.ttl exported.ttl --verbose
```

### test

Test the converter with a sample ontology.

```bash
python -m src.main test
python -m src.main test --upload-test  # Also upload to Fabric
```

## Plugin Commands

### plugin list

List all available format plugins.

```bash
# List all plugins
python -m src.main plugin list

# Example output:
# Available Plugins:
# ┌─────────┬─────────────┬─────────┬────────────────────────┐
# │ Format  │ Name        │ Version │ Extensions             │
# ├─────────┼─────────────┼─────────┼────────────────────────┤
# │ rdf     │ RDF/OWL     │ 1.0.0   │ .ttl, .rdf, .owl       │
# │ dtdl    │ DTDL        │ 1.0.0   │ .json, .dtdl           │
# │ jsonld  │ JSON-LD     │ 1.0.0   │ .jsonld                │
# └─────────┴─────────────┴─────────┴────────────────────────┘
```

### plugin info

Show detailed information about a specific plugin.

```bash
# Show plugin details
python -m src.main plugin info jsonld

# Example output:
# Plugin: JSON-LD
# Format Name: jsonld
# Version: 1.0.0
# Author: Fabric Ontology Team
# Extensions: .jsonld
# Dependencies: (none)
#
# Description:
# JSON-LD (JavaScript Object Notation for Linked Data) plugin
# for converting JSON-LD schemas to Microsoft Fabric ontology format.
```

### Using Plugins

Once a plugin is loaded, use its format name with standard commands:

```bash
# Validate JSON-LD file
python -m src.main validate --format jsonld schema.jsonld

# Convert JSON-LD file
python -m src.main convert --format jsonld schema.jsonld

# Convert with output file
python -m src.main convert --format jsonld schema.jsonld -o fabric_output.json

# Upload to Fabric
python -m src.main upload --format jsonld schema.jsonld --workspace my-workspace
```

### Auto-Detection

The converter can auto-detect the format based on file extension:

```bash
# Format detected from .jsonld extension
python -m src.main validate schema.jsonld

# Format detected from .ttl extension
python -m src.main validate ontology.ttl

# Explicit format overrides auto-detection
python -m src.main validate --format rdf custom.txt
```

## Streaming Mode

Streaming mode enables memory-efficient processing of large ontology files. The converter automatically suggests streaming when files exceed 100MB.

### When to Use Streaming

- Files larger than 100MB
- Systems with limited memory
- Processing multiple large files
- Avoiding out-of-memory errors

### Streaming Examples

```bash
# Convert large RDF file with streaming
python -m src.main convert --format rdf large_ontology.ttl --streaming

# Upload with streaming mode
python -m src.main upload --format rdf large_ontology.ttl --streaming

# Convert large DTDL file with streaming
python -m src.main convert --format dtdl large_models.json --streaming

# Force memory checks off (use with caution)
python -m src.main convert --format rdf huge_ontology.ttl --force-memory
```

### Streaming Architecture

The converter uses a common streaming engine (`src/core/streaming.py`) that supports both RDF and DTDL formats:

| Component | Description |
|-----------|-------------|
| `StreamConfig` | Configuration for chunk sizes and memory thresholds |
| `StreamReader` | Format-specific file readers (RDF, DTDL) |
| `ChunkProcessor` | Format-specific chunk processors |
| `StreamingEngine` | Main orchestrator for streaming operations |

### Streaming Features

- **Chunked Processing**: Files are processed in configurable chunks (default: 10,000 items)
- **Progress Callbacks**: Real-time progress reporting during conversion
- **Memory Monitoring**: Automatic memory pressure detection
- **Cancellation Support**: Operations can be cancelled mid-stream
- **Statistics Tracking**: Detailed processing statistics and timing

### Programmatic Streaming

```python
from src.core.streaming import (
    StreamingEngine,
    DTDLStreamReader,
    DTDLChunkProcessor,
    StreamConfig,
)

# Configure streaming
config = StreamConfig(
    chunk_size=5000,           # Process 5000 items per chunk
    memory_threshold_mb=50,    # Suggest streaming above 50MB
    enable_progress=True,
)

# Create and run streaming engine
engine = StreamingEngine(
    reader=DTDLStreamReader(),
    processor=DTDLChunkProcessor(),
    config=config
)

result = engine.process_file(
    "./large_models/",
    progress_callback=lambda n: print(f"Processed: {n}")
)

print(result.stats.get_summary())
```

See [API.md](API.md#streaming-engine) for complete API documentation.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Warning/minor issues |
| 2 | Error/parse failure |
| 130 | Cancelled by user (Ctrl+C) |

## See Also

- [CONFIGURATION.md](CONFIGURATION.md) - Configuration file reference
- [API.md](API.md) - Programmatic API documentation
- [RDF_GUIDE.md](RDF_GUIDE.md) - RDF conversion details and limitations
- [DTDL_GUIDE.md](DTDL_GUIDE.md) - DTDL conversion details and limitations
