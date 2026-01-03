# DTDL to Fabric Ontology Guide

This guide provides comprehensive information about importing **Digital Twins Definition Language (DTDL)** models from Azure IoT/Digital Twins into Microsoft Fabric Ontology.

## Table of Contents

- [What is DTDL?](#what-is-dtdl)
- [DTDL Commands](#dtdl-commands)
- [DTDL to Fabric Mapping](#dtdl-to-fabric-mapping)
  - [Core Mappings](#core-mappings)
  - [Type Mapping](#type-mapping)
  - [Configurable Features](#configurable-features)
- [What Gets Converted?](#what-gets-converted)
  - [Fully Supported](#-fully-supported-dtdl-v2v3v4)
  - [Configurable Features](#-configurable-features)
  - [Limited Support](#-limited-support-information-loss)
  - [Not Supported](#-not-supported-skipped)
  - [Version-Specific Limits](#version-specific-limits)
- [DTDL Validation Checks](#dtdl-validation-checks)
- [Examples](#examples)
- [Key Considerations](#key-considerations)
  - [Information Loss During Conversion](#information-loss-during-conversion)
  - [Fabric API Limits](#fabric-api-limits)
  - [Configuration Options](#configuration-options)
  - [Before You Convert](#before-you-convert)
  - [Best Practices for DTDL Sources](#best-practices-for-dtdl-sources)
  - [Common Warnings & Fixes](#common-warnings--fixes)
  - [Compliance Reports](#compliance-reports)
- [Related Resources](#related-resources)

## What is DTDL?

[DTDL](https://learn.microsoft.com/azure/digital-twins/concepts-models) is a JSON-LD based modeling language used by Azure Digital Twins and Azure IoT. It defines:

- **Interfaces** - Digital twin types with properties, telemetry, relationships, and commands
- **Properties** - Static attributes of a twin
- **Telemetry** - Time-series sensor data  
- **Relationships** - Connections between twins
- **Components** - Reusable interface compositions

DTDL supports semantic modeling, inheritance, and type composition to create rich digital twin representations of physical environments, IoT devices, and business processes.

## DTDL Commands

> **📘 For complete command reference, see [COMMANDS.md](COMMANDS.md#dtdl-commands)**

This section shows the typical workflow for working with DTDL models.

### Quick Workflow

```powershell
# 1. Validate your DTDL models
python -m src.main validate --format dtdl ./models/ --recursive --verbose

# 2. Convert to Fabric JSON (optional - for inspection)
python -m src.main convert --format dtdl ./models/ --recursive --output fabric_output.json

# 3. Upload to Fabric
python -m src.main upload --format dtdl ./models/ --recursive --ontology-name "MyDigitalTwin"
```

### Available Commands

| Command | Purpose |
|---------|----------|
| `validate --format dtdl` | Validate DTDL schema and structure |
| `convert --format dtdl` | Convert DTDL to Fabric JSON (no upload) |
| `upload --format dtdl` | Full pipeline: validate → convert → upload |

### Common Options

- `--format dtdl` - Specify DTDL format (required for unified commands)
- `--recursive` - Process directories recursively
- `--verbose` - Show detailed interface information
- `--output` - Specify output file path
- `--ontology-name` - Set the ontology name
- `--namespace` - Custom namespace (default: `usertypes`)
- `--flatten-components` - Flatten component properties into parent entities
- `--dry-run` - Convert without uploading
- `--streaming` - Use memory-efficient mode for large files (>100MB)
- `--force-memory` - Skip memory safety checks for very large files

**See [COMMANDS.md](COMMANDS.md#unified-commands) for:**
- Complete command syntax and all options
- Component and command handling modes
- Streaming mode details for large files
- Advanced configuration examples
- Batch processing details

## DTDL to Fabric Mapping

The converter maps DTDL concepts to Fabric Ontology:

### Core Mappings

| DTDL Feature | Fabric Mapping | Support Level |
|--------------|----------------|---------------|
| Interface | EntityType | ✅ Full |
| Property | EntityTypeProperty | ✅ Full |
| Telemetry | timeseriesProperties | ✅ Full |
| Relationship | RelationshipType | ✅ Full |
| extends (single) | baseEntityTypeId | ✅ Full |
| Primitive schemas | valueType | ✅ Full |
| displayName | resolved to name | ✅ Full |
| description | metadata | ✅ Full |

### Type Mapping

DTDL primitive types map directly to Fabric types:
- **boolean** → Boolean
- **integer, long** → BigInt
- **double, float** → Double
- **string** → String
- **date, dateTime, time, duration** → DateTime
- **byte** (v4) → BigInt (with range validation)
- **uuid** (v4) → String (with format validation)

Complex types are serialized to JSON strings:
- **Object** → JSON String (nested structure preserved)
- **Array** → JSON String (array type information lost)
- **Map** → JSON String (key-value structure serialized)
- **Geospatial types** (v4) → JSON String (coordinates preserved)

### Configurable Features

#### Component Handling

Components can be handled in three ways via `dtdl.component_mode` configuration:

| Mode | Behavior | Use When |
|------|----------|----------|
| `skip` (default) | Components ignored | You don't need component data |
| `flatten` | Properties merged into parent entity with `{component}_` prefix | Simple component structures |
| `separate` | Component becomes separate EntityType with `has_{component}` relationship | Preserve component identity |

**Example:**
```json
{
  "dtdl": {
    "component_mode": "flatten"
  }
}
```

#### Command Handling

Commands can be handled in three ways via `dtdl.command_mode` configuration:

| Mode | Behavior | Use When |
|------|----------|----------|
| `skip` (default) | Commands ignored | Commands not needed in ontology |
| `property` | Creates `command_{name}` String property | Simple command tracking |
| `entity` | Creates `Command_{name}` EntityType with request/response properties | Full command modeling |

**Example with entity mode:**
```json
{
  "dtdl": {
    "command_mode": "entity"
  }
}
```

Creates:
- EntityType `Command_{name}` with:
  - `commandName` (String, identifier)
  - `requestSchema` (String, JSON)
  - `responseSchema` (String, JSON)
  - `request_{param}` properties for each request parameter
  - `response_{param}` properties for each response parameter
- RelationshipType `supports_{commandName}` linking interface to command

#### ScaledDecimal Handling (DTDL v4)

ScaledDecimal types can be handled in three ways via `dtdl.scaled_decimal_mode` configuration:

| Mode | Behavior | Use When |
|------|----------|----------|
| `json_string` (default) | Stored as JSON: `{"scale": 7, "value": "1234.56"}` | Preserve full precision |
| `structured` | Creates `{prop}_scale` (BigInt) and `{prop}_value` (String) properties | Queryable scale/value |
| `calculated` | Calculates `value × 10^scale` as Double | Direct numeric value needed |

**Example:**
```json
{
  "dtdl": {
    "scaled_decimal_mode": "structured"
  }
}
```

For a property with value `1234.56` and scale `7`, creates:
- `{property}_scale` (BigInt): `7`
- `{property}_value` (String): `"1234.56"`

## What Gets Converted?

### ✅ Fully Supported (DTDL v2/v3/v4)
- **Interfaces** → EntityType with name, description
- **Properties** → EntityTypeProperty with proper typing
- **Telemetry** → timeseriesProperties for sensor data
- **Relationships** → RelationshipType with source/target
- **Single inheritance** (extends) → baseEntityTypeId
- **Primitive types** → Direct mapping to Fabric types
- **DTDL v4 types** → byte (BigInt), uuid (String), geospatial (JSON)
- **Enums** → String type (enum values documented in description)
- **displayName, description** → name and metadata

### ⚠️ Configurable Features
- **Components:** Three modes available
  - `skip` (default): Components ignored
  - `flatten`: Properties merged with `{component}_` prefix
  - `separate`: New EntityType + `has_{component}` relationship
- **Commands:** Three modes available
  - `skip` (default): Commands ignored
  - `property`: Creates `command_{name}` String property
  - `entity`: Creates `Command_{name}` EntityType with full details
- **ScaledDecimal (v4):** Three modes available
  - `json_string` (default): JSON with scale and value
  - `structured`: Separate `_scale` and `_value` properties
  - `calculated`: Computed Double value

### ⚠️ Limited Support (Information Loss)
- **Multiple inheritance** → First parent only (DTDL allows multiple extends)
- **Complex schemas** → JSON strings
  - Object → JSON String (nested structure preserved)
  - Array → JSON String (array type information lost)
  - Map → JSON String (key-value structure serialized)
- **Enum** → String (enum values lost, documented in description)
- **@id (DTMI)** → Hashed to numeric ID (original DTMI preserved in mapping)
- **Relationship properties** → Not preserved (DTDL allows properties on relationships)

### ❌ Not Supported (Skipped)
- **request/response schemas** (in SKIP/PROPERTY command modes)
- **writable** → Mutability information lost
- **unit** → Metadata only, not queryable
- **semanticType** → Not preserved in Fabric model
- **minMultiplicity/maxMultiplicity** → Cardinality constraints not enforced
- **target** (Relationship) → External targets ignored
- **Custom @context extensions** → Only standard DTDL contexts supported

### Version-Specific Limits

The converter validates against DTDL specification limits per version:

| Limit | DTDL v2 | DTDL v3 | DTDL v4 |
|-------|---------|---------|---------|
| Max contents per interface | 300 | 100,000 | 100,000 |
| Max extends depth | 10 | 10 | 12 |
| Max complex schema depth | 5 | 5 | 8 |
| Max name length | 64 | 512 | 512 |
| Max description length | 512 | 512 | 512 |

## DTDL Validation Checks

The `validate --format dtdl` command performs comprehensive checks:

### Schema Validation
- **DTMI format** - Validates Digital Twin Model Identifier syntax
- **JSON-LD context** - Checks for valid DTDL v2/v3/v4 context URLs
- **Schema types** - Verifies all schema types are valid DTDL types
- **Required fields** - Ensures @id, @type, and required properties are present

### Semantic Validation
- **Inheritance cycles** - Detects circular `extends` chains
- **Relationship targets** - Warns about relationships pointing to undefined interfaces
- **Component schemas** - Warns about components referencing missing schemas
- **DTMI uniqueness** - Checks for duplicate @id values

### Best Practices
- **Large ontology warnings** - Alerts when >200 interfaces may cause performance issues
- **Deep inheritance** - Warns about inheritance chains >5 levels (DTDL allows up to 12 in v4)
- **Complex schemas** - Warns about deeply nested Object/Array schemas

## Examples

### Example 1: Simple Thermostat

**Input DTDL** (samples/dtdl/thermostat.json):
```json
{
  "@context": "dtmi:dtdl:context;3",
  "@id": "dtmi:com:example:Thermostat;1",
  "@type": "Interface",
  "displayName": "Thermostat",
  "description": "A smart thermostat device",
  "contents": [
    {
      "@type": "Property",
      "name": "targetTemperature",
      "schema": "double",
      "writable": true
    },
    {
      "@type": "Telemetry",
      "name": "temperature",
      "schema": "double"
    }
  ]
}
```

**Conversion:**
```powershell
python -m src.main upload --format dtdl samples/dtdl/thermostat.json --ontology-name "ThermostatOntology"
```

**Result:**
- EntityType: `Thermostat` with description
- Property: `targetTemperature` (Double, writable)
- TimeseriesProperty: `temperature` (Double)

### Example 2: Factory with Inheritance

**Input DTDL**:
```json
{
  "@context": "dtmi:dtdl:context;3",
  "@id": "dtmi:com:factory:Equipment;1",
  "@type": "Interface",
  "displayName": "Equipment",
  "contents": [
    {
      "@type": "Property",
      "name": "manufacturer",
      "schema": "string"
    }
  ]
}
```

```json
{
  "@context": "dtmi:dtdl:context;3",
  "@id": "dtmi:com:factory:Machine;1",
  "@type": "Interface",
  "displayName": "Machine",
  "extends": "dtmi:com:factory:Equipment;1",
  "contents": [
    {
      "@type": "Telemetry",
      "name": "rpm",
      "schema": "double"
    }
  ]
}
```

**Result:**
- EntityType: `Equipment` with property `manufacturer`
- EntityType: `Machine` extending `Equipment` with timeseries property `rpm`

### Example 3: RealEstateCore DTDL

The RealEstateCore DTDL ontology (~269 interfaces) has been successfully tested:

```powershell
# Import the full RealEstateCore DTDL ontology
python -m src.main upload --format dtdl path/to/RealEstateCore/ --recursive --ontology-name "RealEstateCore"
```

This demonstrates the tool's capability to handle large, complex DTDL ontologies with:
- Extensive inheritance hierarchies
- Complex relationship networks
- Components and semantic types
- Hundreds of interfaces

## Key Considerations

### Information Loss During Conversion

DTDL is designed for digital twins, while Fabric Ontology targets business data models. Some features don't translate directly:

| DTDL Feature | Impact | Recommendation |
|--------------|--------|----------------|
| **Commands** | Lost in skip mode | Use `command_mode=entity` for full modeling |
| **Complex schemas** (Object, Array, Map) | Serialized to JSON strings | Accept JSON representation or simplify schema |
| **Multiple inheritance** | First parent only | Refactor to single parent or accept limitation |
| **Relationship properties** | Not preserved | Model as intermediate entity |
| **request/response schemas** | Lost in SKIP/PROPERTY modes | Use `command_mode=entity` |
| **writable** | Mutability lost | Document field behavior separately |
| **unit** | Metadata only | Track units in separate documentation |
| **semanticType** | Not preserved | Document semantic types separately |
| **minMultiplicity/maxMultiplicity** | Cardinality lost | Validate in data layer |
| **target** (Relationship) | External targets ignored | Ensure targets in same conversion set |

### Fabric API Limits

> **📘 For complete API limits and constraints, see [API.md - Fabric API Limits](API.md#fabric-api-limits)**

Key limits that affect DTDL conversion:
- Max entity/property/relationship name length: **256 characters**
- Max properties per entity: **200**
- Max entity types per ontology: **1000**
- Max relationship types per ontology: **1000**

### Configuration Options

Customize conversion behavior via config.json or command parameters:

```json
{
  "dtdl": {
    "component_mode": "flatten",
    "command_mode": "skip",
    "scaled_decimal_mode": "json_string"
  }
}
```

**Configuration priority:** Command-line parameters > config.json > defaults

### Before You Convert

1. **Validate first:** `python -m src.main validate --format dtdl ./models/ --recursive --verbose`
2. **Choose configuration:** Decide how to handle Components, Commands, ScaledDecimals
3. **Review validation output:** Check for unsupported constructs
4. **Test with samples:** Try conversion on a subset before full upload
5. **Check version limits:** Ensure interface sizes match DTDL version (see table above)

### Best Practices for DTDL Sources

✅ **Use single inheritance** — Multi-extends will use only the first parent  
✅ **Simplify complex schemas** — Objects/Arrays serialize to JSON strings  
✅ **Include targets in conversion** — Ensure relationship targets are in the same set  
✅ **Configure Component handling** — Choose mode based on your needs  
✅ **Check version limits** — Ensure interface sizes match DTDL version  
✅ **Keep names under limits** — Entity/property names under 256 characters  
✅ **Limit properties per entity** — Stay under 200 properties  
✅ **Enable debug logging** — Set `logging.level` to `DEBUG` in config.json  

### Common Warnings & Fixes

| Warning | Fix |
|---------|-----|
| "Multiple inheritance not supported" | Refactor to single parent or accept first-parent-only behavior |
| "Complex schema serialized to JSON" | Accept JSON representation or simplify schema |
| "Entity name exceeds Fabric limit" | Shorten name or accept truncation |
| "Too many properties" | Split entity, use `component_mode=separate`, or remove properties |
| "Relationship target not found" | Include target interface in conversion set |
| "DTDL version limit exceeded" | Reduce interface size or split into multiple interfaces |

### Compliance Reports

Generate detailed reports showing conversion impact:

```python
from src.dtdl.dtdl_converter import DTDLToFabricConverter
from src.dtdl.dtdl_parser import DTDLParser

# Parse DTDL
parser = DTDLParser()
interfaces = parser.parse_file("samples/dtdl/thermostat.json")

# Convert with compliance report
converter = DTDLToFabricConverter()
result, report = converter.convert_with_compliance_report(interfaces, dtdl_version="v3")

# Access report data
if report:
    print(f"Total issues: {report.total_issues}")
    for warning in report.warnings:
        print(f"[{warning.impact.value}] {warning.feature}: {warning.message}")
```

The report shows:
1. **Source Compliance Issues** - DTDL specification violations
2. **Conversion Warnings** - Features preserved/limited/lost
3. **Fabric Compliance Issues** - API limit violations

## Related Resources

- [DTDL Language Specification](https://github.com/Azure/opendigitaltwins-dtdl)
- [RealEstateCore DTDL](https://github.com/Azure/opendigitaltwins-building) - Example large DTDL ontology
- [Microsoft Fabric Ontology REST API](https://learn.microsoft.com/rest/api/fabric/ontology/items)
