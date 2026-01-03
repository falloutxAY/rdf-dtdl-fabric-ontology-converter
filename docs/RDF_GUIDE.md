# RDF/OWL to Fabric Ontology Guide

This guide provides comprehensive information about importing **RDF/OWL ontologies** (Turtle/TTL format) into Microsoft Fabric Ontology.

## Table of Contents

- [What is RDF/OWL?](#what-is-rdfowl)
- [RDF Commands](#rdf-commands)
- [RDF to Fabric Mapping](#rdf-to-fabric-mapping)
  - [Fully Supported Constructs](#-fully-supported-constructs)
  - [XSD Type Mapping](#xsd-type-mapping)
  - [Partially Supported Constructs](#-partially-supported-constructs)
  - [Unsupported Constructs](#-unsupported-constructs)
- [What Gets Converted?](#what-gets-converted)
  - [Fully Supported](#-fully-supported)
  - [Limited Support](#-limited-support-simplified)
  - [Not Supported](#-not-supported-skipped-with-warnings)
- [RDF Validation Checks](#rdf-validation-checks)
  - [Syntax Validation](#syntax-validation)
  - [Semantic Validation](#semantic-validation)
  - [Fabric Compatibility](#fabric-compatibility)
- [Examples](#examples)
- [Key Considerations](#key-considerations)
  - [Information Loss During Conversion](#information-loss-during-conversion)
  - [Fabric API Limits](#fabric-api-limits)
  - [Before You Convert](#before-you-convert)
  - [Best Practices for RDF Sources](#best-practices-for-rdf-sources)
  - [Common Warnings & Fixes](#common-warnings--fixes)
  - [Compliance Reports](#compliance-reports)
- [Related Resources](#related-resources)

## What is RDF/OWL?

[RDF (Resource Description Framework)](https://www.w3.org/RDF/) and [OWL (Web Ontology Language)](https://www.w3.org/OWL/) are W3C standards for representing knowledge and ontologies. RDF provides the foundation for expressing graph-based data, while OWL adds rich semantics for defining classes, properties, and relationships.

**Key concepts:**
- **Classes** (`owl:Class`, `rdfs:Class`) - Types of resources
- **Properties** (`owl:DatatypeProperty`, `owl:ObjectProperty`) - Attributes and relationships
- **Inheritance** (`rdfs:subClassOf`) - Class hierarchies
- **Domains and Ranges** (`rdfs:domain`, `rdfs:range`) - Property constraints
- **Restrictions** (`owl:Restriction`) - Complex property constraints

RDF/OWL is widely used for semantic web applications, knowledge graphs, and data integration scenarios.

## RDF Commands

> **📘 For complete command reference, see [COMMANDS.md](COMMANDS.md#rdf-commands)**

This section shows the typical workflow for working with RDF/TTL ontologies.

### Quick Workflow

```powershell
# 1. Validate your TTL file
python -m src.main validate --format rdf ontology.ttl --verbose

# 2. Convert to Fabric JSON (optional - for inspection)
python -m src.main convert --format rdf ontology.ttl --output fabric_output.json

# 3. Upload to Fabric
python -m src.main upload --format rdf ontology.ttl --ontology-name "MyOntology"

# 4. Export back to TTL (optional - for verification)
python -m src.main export <ontology-id> --output exported.ttl
```

### Available Commands

| Command | Purpose |
|---------|----------|
| `validate --format rdf` | Validate TTL syntax and Fabric compatibility |
| `convert --format rdf` | Convert TTL to Fabric JSON (no upload) |
| `upload --format rdf` | Full pipeline: validate → convert → upload |
| `export` | Export Fabric ontology to TTL format |

### Common Options

- `--format rdf` - Specify RDF format (required for unified commands)
- `--recursive` - Process directories recursively
- `--verbose` - Show detailed output
- `--output` - Specify output file path
- `--streaming` - Use memory-efficient mode for large files (>100MB)
- `--force-memory` - Skip memory safety checks for very large files
- `--config` - Use custom configuration file

**See [COMMANDS.md](COMMANDS.md#unified-commands) for:**
- Complete command syntax and all options
- Batch processing examples
- Streaming mode details
- Advanced configuration

## RDF to Fabric Mapping

The converter maps RDF/OWL concepts to Fabric Ontology with the following support levels:

### ✅ Fully Supported Constructs

| OWL/RDF Construct | Fabric Mapping | Notes |
|-------------------|----------------|-------|
| `owl:Class` | EntityType | Named classes become entity types |
| `rdfs:Class` | EntityType | RDF Schema classes supported |
| `rdfs:subClassOf` (simple) | baseEntityTypeId | Single parent inheritance |
| `owl:DatatypeProperty` | EntityTypeProperty | Attributes with primitive types |
| `owl:ObjectProperty` | RelationshipType | Relationships between entities |
| `rdfs:domain` | Property assignment | Property assigned to entity |
| `rdfs:range` (datatype) | valueType | Property type from XSD datatype |
| `rdfs:range` (class) | Relationship target | Target entity for relationships |
| `rdfs:label` | name, displayName | Entity/property display names |
| `rdfs:comment` | description | Entity/property descriptions |

### XSD Type Mapping

Standard XSD types are mapped to equivalent Fabric property types:

| XSD Type | Fabric Type | Notes |
|----------|-------------|-------|
| `xsd:string` | String | Default for unknown types |
| `xsd:boolean` | Boolean | |
| `xsd:integer` | BigInt | |
| `xsd:int` | BigInt | |
| `xsd:long` | BigInt | |
| `xsd:decimal` | Decimal | |
| `xsd:double` | Double | |
| `xsd:float` | Double | |
| `xsd:date` | DateTime | |
| `xsd:dateTime` | DateTime | |
| `xsd:time` | DateTime | |
| `xsd:anyURI` | String | URIs stored as strings |
| Other XSD types | String | Defaults to String with warning |

### ⚠️ Partially Supported Constructs

| OWL/RDF Construct | Fabric Mapping | Notes |
|-------------------|----------------|-------|
| `owl:unionOf` (classes) | Multiple relationships | Creates separate relationships for each union member |
| `owl:unionOf` (datatypes) | Most restrictive type | Multiple types unified to single Fabric type (e.g., int + double → double) |
| `owl:intersectionOf` | Class extraction | Extracts named classes, ignores complex restrictions |
| `rdfs:subClassOf` (complex) | Flattened | Restrictions and expressions simplified to named class |
| `owl:equivalentClass` | Skipped | Entity ID mapping not preserved |
| `owl:sameAs` | Instance scope | Out of converter scope (operates on instances, not schema) |

### ❌ Unsupported Constructs

These OWL/RDF features are not supported and will be skipped with warnings:

#### Property Restrictions
- `owl:Restriction` - Cardinality/value constraints lost
- `owl:allValuesFrom` - Universal restriction not enforced
- `owl:someValuesFrom` - Existential restriction not enforced
- `owl:hasValue` - Value restriction not enforced
- `owl:minCardinality`, `owl:maxCardinality`, `owl:exactCardinality` - Cardinality constraints not enforced

#### Property Characteristics
- `owl:TransitiveProperty` - Transitivity not enforced
- `owl:SymmetricProperty` - Symmetry not enforced
- `owl:FunctionalProperty` - Uniqueness not enforced
- `owl:InverseFunctionalProperty` - Uniqueness not enforced
- `owl:ReflexiveProperty` - Reflexivity not enforced
- `owl:IrreflexiveProperty` - Irreflexivity not enforced
- `owl:AsymmetricProperty` - Asymmetry not enforced

#### Class Operations
- `owl:disjointWith` - Disjointness not enforced
- `owl:complementOf` - Negation lost
- `owl:oneOf` - Enumeration extracted as separate entities
- `owl:propertyChainAxiom` - Property chains not preserved
- `owl:inverseOf` - Inverse relationships not auto-created

#### Other Features
- `owl:imports` - External imports not resolved (merge ontologies first)
- `owl:AnnotationProperty` - Stored as metadata only
- `owl:deprecated` - Metadata only, not enforced
- `owl:versionInfo` - Metadata only
- `rdf:List` - Flattened, list structure lost
- `SHACL shapes` - Constraints lost

## What Gets Converted?

### ✅ Fully Supported
- **Classes** (`owl:Class`, `rdfs:Class`) → EntityType with description
- **Datatype Properties** (`owl:DatatypeProperty`) → EntityTypeProperty with proper typing
- **Object Properties** (`owl:ObjectProperty`) → RelationshipType
- **Simple inheritance** (`rdfs:subClassOf` to named class) → baseEntityTypeId
- **Domain/range declarations** → Property assignment and typing
- **Labels, comments** (`rdfs:label`, `rdfs:comment`) → name, displayName, description
- **Standard XSD types** → Direct mapping to Fabric types (see table above)

### ⚠️ Limited Support (Simplified)
- **Multiple inheritance** → First parent only (Fabric supports single inheritance)
- **Complex class expressions** → Simplified to named classes
  - `owl:unionOf` (classes) → Multiple separate relationships
  - `owl:intersectionOf` → Named classes extracted, restrictions ignored
- **Complex subClassOf** → Flattened (restrictions and expressions simplified)
- **Property characteristics** → Metadata only (transitivity, symmetry, etc. not enforced)
- **owl:oneOf** → Enumeration extracted as separate entities

### ❌ Not Supported (Skipped with Warnings)
- **OWL Restrictions** (cardinality, value constraints, allValuesFrom, someValuesFrom)
- **Property chains** (`owl:propertyChainAxiom`)
- **Inverse properties** (`owl:inverseOf`) - not auto-created
- **External imports** (`owl:imports`) - must merge ontologies first
- **Class operations** (disjointWith, complementOf)
- **Reasoning/inference** - not performed
- **SHACL shapes** - validation constraints lost
- **RDF Lists** - flattened, structure lost

## RDF Validation Checks

The `validate --format rdf` command performs comprehensive checks:

### Syntax Validation
- **TTL format** - Validates Turtle syntax
- **Prefix declarations** - Ensures all prefixes are declared
- **URI resolution** - Checks for malformed URIs
- **Triple structure** - Validates subject-predicate-object patterns

### Semantic Validation
- **Class declarations** - Warns about undeclared classes used in domain/range
- **Property signatures** - Checks for missing domain/range declarations
- **Type consistency** - Validates range values match declared types
- **Inheritance cycles** - Detects circular subClassOf chains

### Fabric Compatibility
- **Entity name length** - Warns if names exceed 256 characters
- **Property count** - Alerts when entities have >200 properties
- **Large ontologies** - Warns when >1000 entity types detected
- **Unsupported constructs** - Lists OWL features that will be skipped

## Examples

### Example 1: Simple Product Ontology

**Input TTL** (samples/rdf/sample_supply_chain_ontology.ttl):
```turtle
@prefix : <http://example.com/supply#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

:Product a owl:Class ;
    rdfs:label "Product" ;
    rdfs:comment "A product in the supply chain" .

:hasName a owl:DatatypeProperty ;
    rdfs:label "has name" ;
    rdfs:domain :Product ;
    rdfs:range xsd:string .

:hasPrice a owl:DatatypeProperty ;
    rdfs:label "has price" ;
    rdfs:domain :Product ;
    rdfs:range xsd:decimal .
```

**Conversion:**
```powershell
python -m src.main upload --format rdf samples/rdf/sample_supply_chain_ontology.ttl --ontology-name "SupplyChain"
```

**Result:**
- EntityType: `Product` with description
- Property: `hasName` (String)
- Property: `hasPrice` (Decimal)

### Example 2: IoT Device Ontology with Relationships

**Input TTL** (samples/rdf/sample_iot_ontology.ttl):
```turtle
@prefix : <http://example.com/iot#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

:Device a owl:Class ;
    rdfs:label "Device" ;
    rdfs:comment "An IoT device" .

:Sensor a owl:Class ;
    rdfs:label "Sensor" ;
    rdfs:subClassOf :Device ;
    rdfs:comment "A sensor device" .

:locatedIn a owl:ObjectProperty ;
    rdfs:label "located in" ;
    rdfs:domain :Device ;
    rdfs:range :Location .

:Location a owl:Class ;
    rdfs:label "Location" ;
    rdfs:comment "A physical location" .
```

**Result:**
- EntityType: `Device` with description
- EntityType: `Sensor` extending `Device`
- EntityType: `Location` with description
- RelationshipType: `locatedIn` from `Device` to `Location`

### Example 3: FOAF Ontology

The Friend of a Friend (FOAF) ontology has been successfully tested:

```powershell
# Import the FOAF ontology
python -m src.main upload --format rdf samples/rdf/sample_foaf_ontology.ttl --ontology-name "FOAF"
```

This demonstrates conversion of a standard semantic web vocabulary with:
- Person, Agent, Document classes
- Social relationships (knows, friend)
- Properties for names, emails, homepages
- Complex class hierarchies

## Key Considerations

### Information Loss During Conversion

RDF/OWL has rich semantics that may not fully translate to Fabric Ontology. Understanding what is preserved and what is lost is crucial for successful conversion.

#### What is Preserved
✅ Class hierarchies (single inheritance)  
✅ Property signatures (domain/range)  
✅ Basic typing (XSD datatypes)  
✅ Labels and descriptions  
✅ Object relationships  

#### What is Lost or Simplified

| OWL/RDF Feature | Impact | Recommendation |
|-----------------|--------|----------------|
| **OWL Restrictions** | Cardinality/value constraints not enforced | Document constraints separately, validate in data layer |
| **Property characteristics** | Transitivity, symmetry, etc. metadata only | Pre-compute transitive closure, create inverse relationships |
| **Multiple inheritance** | First parent only | Refactor to single parent or accept limitation |
| **Complex expressions** | Flattened to named classes | Use explicit class declarations |
| **External imports** | Not resolved | Merge external ontologies before conversion |
| **Reasoning/inference** | Not performed | Pre-compute inferred relationships |
| **Property chains** | Not preserved | Pre-compute derived relationships |
| **Inverse properties** | Not auto-created | Manually create inverse relationships |
| **Class operations** | Disjointness, complement lost | Validate data separately |
| **SHACL shapes** | Validation constraints lost | Document validation rules separately |
| **RDF Lists** | Structure lost | Use explicit properties or arrays |

### Fabric API Limits

> **📘 For complete API limits and constraints, see [API.md - Fabric API Limits](API.md#fabric-api-limits)**

Key limits that affect RDF conversion:
- Max entity/property/relationship name length: **256 characters**
- Max properties per entity: **200**
- Max entity types per ontology: **1000**
- Max relationship types per ontology: **1000**

### Before You Convert

1. **Validate first:** `python -m src.main validate --format rdf your_file.ttl --verbose`
2. **Review the validation report:** Check for unsupported constructs
3. **Merge external ontologies:** Ensure all referenced classes are declared locally
4. **Document constraints:** Keep track of restrictions that won't be preserved
5. **Flatten restrictions:** Convert property restrictions to explicit typed properties
6. **Check size limits:** Ensure names under 256 chars, properties per entity under 200

### Best Practices for RDF Sources

✅ **Provide explicit signatures** — Always declare `rdfs:domain` and `rdfs:range`  
✅ **Declare all referenced classes** — Don't rely on external ontologies unless merged  
✅ **Use supported XSD types** — string, boolean, integer, decimal, date, dateTime, anyURI  
✅ **Flatten restrictions** — Convert property restrictions to explicit typed properties  
✅ **Merge imports** — Combine external ontologies before conversion  
✅ **Keep names under limits** — Entity/property names under 256 characters  
✅ **Limit properties per entity** — Stay under 200 properties  
✅ **Use single inheritance** — Refactor if multiple parents  
✅ **Enable debug logging** — Set `logging.level` to `DEBUG` in config.json  

### Common Warnings & Fixes

| Warning | Fix |
|---------|-----|
| "Skipping property due to unresolved domain/range" | Add explicit `rdfs:domain`/`rdfs:range` and declare all referenced classes locally |
| "Unresolved class target" | Declare the class in your TTL or merge the external vocabulary |
| "Unknown XSD datatype, defaulting to String" | Use supported XSD types or accept String fallback |
| "Unsupported OWL construct: owl:Restriction" | Flatten restrictions to explicit properties with signatures |
| "Multiple inheritance not supported" | Refactor to single parent or accept first-parent-only behavior |
| "Entity name exceeds Fabric limit" | Shorten name or accept truncation |
| "Too many properties" | Split entity or remove less important properties |
| "External import not resolved" | Merge external ontology files before conversion |

### Compliance Reports

Generate detailed reports showing what will be preserved, limited, or lost:

```python
from src.rdf.rdf_converter import RDFToFabricConverter

converter = RDFToFabricConverter()
with open("ontology.ttl") as f:
    result, report = converter.parse_ttl_with_compliance_report(f.read())

if report:
    print(f"⚠️  Warnings: {len(report.warnings)}")
    for warning in report.warnings:
        print(f"[{warning.severity}] {warning.message}")
```

The report shows:
1. **Syntax Validation** - TTL format and structure issues
2. **Semantic Validation** - Missing declarations, type consistency
3. **Conversion Warnings** - Features preserved/limited/lost
4. **Fabric Compliance** - API limit violations

## Related Resources

- [RDF 1.1 Turtle Specification](https://www.w3.org/TR/turtle/)
- [OWL 2 Web Ontology Language Primer](https://www.w3.org/TR/owl2-primer/)
- [RDFLib Python Library](https://github.com/RDFLib/rdflib)
- [Schema.org Vocabularies](https://schema.org/) - Example RDF vocabularies
- [DBpedia Ontology](https://www.dbpedia.org/resources/ontology/) - Large RDF ontology example
