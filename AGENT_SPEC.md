# Agent Specification: RDF/DTDL to Microsoft Fabric Ontology Converter

**Version:** 2.0.0  
**Last Updated:** January 3, 2026  
**Purpose:** Forward-looking guide for AI agents to understand architecture, make decisions, and extend functionality

---

## 🎯 Quick Start for Agents

### What You Need to Know

This is a **plugin-based ontology converter** that transforms various formats (RDF, DTDL, JSON-LD) into Microsoft Fabric Ontology format.

**Core Architecture Pattern:**
```
User Input → CLI → Plugin System → Format Converter → Fabric Client → Fabric API
```

**Key Principles:**
1. **Plugin-based extensibility** - New formats added via plugin system, not core modifications
2. **Protocol-driven** - All components implement protocols (Parser, Validator, Converter)
3. **Shared models** - Single source of truth in `src/models/`
4. **Resilience-first** - Rate limiting, circuit breakers, graceful degradation
5. **Type safety** - Protocols and dataclasses throughout

### Essential Reading Order

1. **This document** - Decision framework and architecture overview
2. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Detailed system design
3. [docs/PLUGIN_GUIDE.md](docs/PLUGIN_GUIDE.md) - How to add new formats
4. **Source code** - Start with `src/plugins/base.py` and `src/models/base.py`

---

## 🧭 Agent Decision Framework

### When to Modify What

Use this decision tree when asked to make changes:

```
Question: What kind of change is needed?
│
├─ Add new ontology format (e.g., OBO, SKOS)
│  └─> Create new plugin → See "Adding New Format Plugin" below
│
├─ Add new CLI command
│  └─> Add to src/cli/commands/ → See "Adding CLI Command" below
│
├─ Modify conversion logic for existing format
│  └─> Modify format-specific converter (src/rdf/, src/dtdl/)
│
├─ Add new property type or validation rule
│  └─> Update type mapper + validator → See "Extending Type System" below
│
├─ Change API interaction or resilience
│  └─> Modify src/core/ (fabric_client, rate_limiter, circuit_breaker)
│
├─ Add new protocol/interface
│  └─> Add to src/plugins/protocols.py → See "Adding New Protocol" below
│
└─ Bug fix or optimization
   └─> Locate affected module → Follow existing patterns → Add tests
```

### Critical Decision Points

**Before Making ANY Change:**
1. ✅ Check if similar functionality exists elsewhere
2. ✅ Verify which existing protocol/interface applies
3. ✅ Ensure change aligns with plugin architecture
4. ✅ Write tests FIRST (TDD approach)
5. ✅ Update relevant documentation in `docs/`

**Red Flags - DO NOT:**
- ❌ Modify core converter logic for format-specific features
- ❌ Add format-specific code outside plugin boundaries
- ❌ Bypass protocol interfaces
- ❌ Duplicate validation or type mapping logic
- ❌ Skip tests or documentation updates

---

## 🏗️ Architecture Mental Model

### Component Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLI Layer (src/cli/)                         │
│  Entry point → Argument parsing → Command dispatch              │
│  📄 Key: parsers.py, commands/*.py                              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                  Plugin Layer (src/plugins/)                     │
│  PluginManager discovers/loads → Returns Parser/Validator/Conv  │
│  📄 Key: manager.py, base.py, protocols.py                      │
└─────────────────────────┬───────────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
┌────────▼────────┐ ┌─────▼──────┐ ┌──────▼──────┐
│  RDF Pipeline   │ │DTDL Pipeline│ │JSON-LD Pipe │
│  (src/rdf/)     │ │(src/dtdl/)  │ │             │
│  📄 Key:        │ │📄 Key:      │ │             │
│  rdf_converter  │ │dtdl_convert │ │             │
└────────┬────────┘ └─────┬──────┘ └──────┬──────┘
         │                │                │
         └────────────────┼────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                Shared Models (src/models/)                       │
│  EntityType, RelationshipType, ConversionResult                 │
│  📄 Key: fabric_types.py, conversion.py, base.py               │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│               Core Infrastructure (src/core/)                    │
│  FabricClient, RateLimiter, CircuitBreaker, Validators          │
│  📄 Key: fabric_client.py, rate_limiter.py                     │
└─────────────────────────────────────────────────────────────────┘
```

**📚 Detailed Architecture:** See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## 📂 Repository Navigation

### Essential Directories

| Directory | Purpose | When to Modify |
|-----------|---------|----------------|
| `src/plugins/` | Plugin system core | Adding new protocols or plugin discovery logic |
| `src/plugins/builtin/` | Built-in format plugins | Adding new ontology format |
| `src/models/` | Shared data models | Adding new data structures used across formats |
| `src/core/` | Fabric client & resilience | Changing API interaction, rate limiting, auth |
| `src/cli/` | Command-line interface | Adding new commands or modifying CLI behavior |
| `src/common/` | Shared utilities | Adding validation, type registry, ID generation |
| `tests/` | Test suites | Every code change requires corresponding tests |
| `docs/` | Documentation | Every user-facing or architectural change |

### Key Files by Task

| Task | Primary Files | Secondary Files |
|------|---------------|-----------------|
| **Add format plugin** | `plugins/builtin/myformat_plugin.py` | `plugins/__init__.py` |
| **Add CLI command** | `cli/commands/mycommand.py` | `cli/parsers.py`, `main.py` |
| **Modify type mapping** | `rdf/type_mapper.py` or `dtdl/dtdl_type_mapper.py` | `common/type_registry.py` |
| **Add validation rule** | Format validator (e.g., `rdf/preflight_validator.py`) | `common/validation.py` |
| **Change API behavior** | `core/fabric_client.py` | `core/rate_limiter.py`, `core/circuit_breaker.py` |

**📚 Complete Structure:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Module Structure section

---

## 🔌 Protocol System (Critical for Extensions)

### What are Protocols?

Protocols are **interface contracts** that all components must implement. Think of them as TypeScript interfaces or Java interfaces.

**Location:** `src/plugins/protocols.py`

### Core Protocols

```python
# Every format needs these three
ParserProtocol      → parse(content) → Dict[str, Any]
ValidatorProtocol   → validate(content) → ValidationResult  
ConverterProtocol   → convert(content) → ConversionResult

# Optional for reverse conversion
ExporterProtocol    → export(fabric_def) → str
```

### Adding a New Protocol

**Scenario:** You need formats to support a new capability (e.g., schema merging, diff generation)

**Steps:**

1. **Define Protocol in `src/plugins/protocols.py`:**
```python
from typing import Protocol, Dict, Any, List

class MergerProtocol(Protocol):
    """Protocol for merging multiple ontology files."""
    
    def merge(
        self,
        sources: List[str],
        strategy: str = "union"
    ) -> Dict[str, Any]:
        """
        Merge multiple ontology sources.
        
        Args:
            sources: List of file paths or content strings
            strategy: Merge strategy ("union", "intersection")
            
        Returns:
            Merged ontology as intermediate representation
        """
        ...
```

2. **Add to Plugin Base Class (`src/plugins/base.py`):**
```python
class OntologyPlugin(ABC):
    # ... existing methods ...
    
    def get_merger(self) -> Optional[MergerProtocol]:
        """
        Return merger implementation if supported.
        
        Returns:
            Merger instance or None if not supported
        """
        return None  # Default: not supported
```

3. **Implement in Plugins (e.g., `src/plugins/builtin/rdf_plugin.py`):**
```python
class RDFPlugin(OntologyPlugin):
    # ... existing methods ...
    
    def get_merger(self) -> Optional[MergerProtocol]:
        from rdf.rdf_merger import RDFMerger  # Create this
        return RDFMerger()
```

4. **Create Implementation (e.g., `src/rdf/rdf_merger.py`):**
```python
class RDFMerger:
    """Merge multiple RDF/TTL files."""
    
    def merge(self, sources: List[str], strategy: str = "union") -> Dict[str, Any]:
        # Implementation here
        pass
```

5. **Add CLI Support (`src/cli/commands/unified.py`):**
```python
class UnifiedMergeCommand(BaseCommand):
    """Merge multiple ontology files."""
    
    def run(self) -> int:
        plugin = PluginManager.get_instance().get_plugin(self.args.format)
        merger = plugin.get_merger()
        
        if merger is None:
            self.error(f"Format '{self.args.format}' does not support merging")
            return 1
        
        result = merger.merge(self.args.sources, self.args.strategy)
        # ... rest of implementation
```

6. **Write Tests (`tests/plugins/test_merger_protocol.py`):**
```python
@pytest.mark.unit
def test_rdf_plugin_provides_merger():
    plugin = RDFPlugin()
    merger = plugin.get_merger()
    assert merger is not None
    assert hasattr(merger, 'merge')

@pytest.mark.integration  
def test_rdf_merger_combines_files():
    merger = RDFMerger()
    result = merger.merge(['file1.ttl', 'file2.ttl'], strategy='union')
    assert 'entities' in result
    # More assertions...
```

7. **Update Documentation:**
   - Add to [docs/PLUGIN_GUIDE.md](docs/PLUGIN_GUIDE.md) - New protocol section
   - Add to [docs/CLI_COMMANDS.md](docs/CLI_COMMANDS.md) - New merge command
   - Update [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Protocol list

**Key Principle:** All plugins implement the protocol, but return `None` if unsupported. CLI gracefully handles unsupported features.

---

## 🎨 Design Patterns in Use

Understanding these patterns is critical for making architectural decisions:

| Pattern | Location | Purpose | When to Use |
|---------|----------|---------|-------------|
| **Protocol (Structural)** | `plugins/protocols.py` | Define component interfaces | Adding new required behavior for all formats |
| **Plugin (Behavioral)** | `plugins/base.py` | Extensible format support | Adding new ontology format |
| **Singleton** | `plugins/manager.py` | Single plugin registry | Never - already implemented |
| **Facade** | `rdf/rdf_converter.py` | Simplify complex subsystems | Orchestrating multiple specialized components |
| **Factory** | `cli/format.py` | Create format-specific services | Adding format-specific CLI variations |
| **Strategy** | All converters | Swap algorithms at runtime | Different conversion strategies |
| **Circuit Breaker** | `core/circuit_breaker.py` | Fault tolerance | Protecting external API calls |
| **Token Bucket** | `core/rate_limiter.py` | Rate limiting | Controlling API request rate |

**📚 Pattern Details:** See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Design Patterns section

---

## 🚀 Common Extension Scenarios

### Scenario 1: Adding New Ontology Format Plugin

**Decision Point:** User wants to support OBO (Open Biological Ontology) format

**Agent Checklist:**
- [ ] Does this require modifying core code? → No, use plugin system
- [ ] What protocols are needed? → Parser, Validator, Converter (all formats need these)
- [ ] Are there similar formats? → Yes, check RDF plugin for inspiration
- [ ] What dependencies needed? → Research OBO libraries (e.g., `pronto`)

**Implementation Steps:**

1. **Create plugin file:** `src/plugins/builtin/obo_plugin.py`
2. **Implement OntologyPlugin interface** with all required properties
3. **Create parser, validator, converter** following existing patterns
4. **Add type mappings** (OBO → Fabric types)
5. **Write tests:** `tests/plugins/test_obo_plugin.py`
6. **Add sample files:** `samples/obo/sample_ontology.obo`
7. **Update docs:** [docs/PLUGIN_GUIDE.md](docs/PLUGIN_GUIDE.md)

**📚 Complete Guide:** [docs/PLUGIN_GUIDE.md](docs/PLUGIN_GUIDE.md)

### Scenario 2: Adding New CLI Command

**Decision Point:** User wants `compare` command to diff two ontologies

**Agent Checklist:**
- [ ] Is this format-specific? → No, works on Fabric definitions
- [ ] Does it use existing protocol? → No, creates new operation
- [ ] Where does it fit? → `src/cli/commands/common.py` (workspace operations)

**Implementation Steps:**

1. **Create command class:** `CompareCommand` in `src/cli/commands/common.py`
2. **Add parser:** `add_compare_parser()` in `src/cli/parsers.py`
3. **Register in main:** Import and add to `src/main.py`
4. **Implement logic:** Fetch two ontologies, generate diff
5. **Write tests:** `tests/cli/test_compare_command.py`
6. **Update docs:** [docs/CLI_COMMANDS.md](docs/CLI_COMMANDS.md)

**📚 CLI Reference:** [docs/CLI_COMMANDS.md](docs/CLI_COMMANDS.md)

### Scenario 3: Extending Type System

**Decision Point:** Fabric adds support for `GeoPoint` type

**Agent Checklist:**
- [ ] Is this a new Fabric type? → Yes, update all type mappers
- [ ] Do all formats support it? → Check source format capabilities
- [ ] What's the conversion logic? → Coordinate parsing/validation

**Implementation Steps:**

1. **Update RDF type mapper:** `src/rdf/type_mapper.py` → Add XSD to GeoPoint mapping
2. **Update DTDL type mapper:** `src/dtdl/dtdl_type_mapper.py` → Add DTDL to GeoPoint mapping
3. **Update validators:** Add GeoPoint validation rules
4. **Add tests:** Test conversion from all formats
5. **Update docs:** Add type to mapping tables in format guides

**Files to Modify:**
- `src/rdf/type_mapper.py`
- `src/dtdl/dtdl_type_mapper.py`
- `tests/rdf/test_converter.py` (add test cases)
- `tests/dtdl/test_dtdl.py` (add test cases)
- [docs/RDF_GUIDE.md](docs/RDF_GUIDE.md) (update type mapping table)
- [docs/DTDL_GUIDE.md](docs/DTDL_GUIDE.md) (update type mapping table)

### Scenario 4: Modifying Resilience Behavior

**Decision Point:** Rate limit needs to be per-endpoint instead of global

**Agent Checklist:**
- [ ] Does this break existing API? → Yes, RateLimiter interface changes
- [ ] Are there tests? → Yes, extensive in `tests/core/test_resilience.py`
- [ ] Who uses it? → Only `fabric_client.py`

**Implementation Steps:**

1. **Modify rate limiter:** `src/core/rate_limiter.py` → Add endpoint tracking
2. **Update fabric client:** `src/core/fabric_client.py` → Pass endpoint to rate limiter
3. **Update configuration:** `config.sample.json` → Add per-endpoint limits
4. **Modify tests:** `tests/core/test_resilience.py` → Test per-endpoint limits
5. **Update docs:** [docs/CONFIGURATION.md](docs/CONFIGURATION.md) → Document new settings

**⚠️ Breaking Change:** Requires version bump and migration guide

---

## 📊 Data Models Quick Reference

### Core Types (`src/models/fabric_types.py`)

```python
@dataclass
class EntityType:
    id: str
    name: str  # Max 256 chars
    namespace: str
    properties: List[EntityTypeProperty]
    base_type_ids: List[str] = []  # Inheritance

@dataclass
class RelationshipType:
    id: str
    name: str  # Max 256 chars
    source_type_id: str
    target_type_id: str
    cardinality: str  # "one-to-one", "one-to-many", "many-to-many"
```

### Result Types (`src/models/conversion.py`)

```python
@dataclass
class ConversionResult:
    entity_types: List[EntityType]
    relationship_types: List[RelationshipType]
    success: bool
    errors: List[str]
    warnings: List[str]

@dataclass
class ValidationResult:
    format_name: str
    is_valid: bool
    can_convert: bool
    issues: List[ValidationIssue]
```

**📚 Complete Type Definitions:** See `src/models/` directory

**📚 Type Mapping Tables:** 
- RDF: [docs/RDF_GUIDE.md](docs/RDF_GUIDE.md) - Type Mapping section
- DTDL: [docs/DTDL_GUIDE.md](docs/DTDL_GUIDE.md) - Type Mapping section

---

## 🧪 Testing Quick Reference

### Test Markers

```bash
pytest -m unit           # Fast unit tests (~200)
pytest -m integration    # Integration tests (~100)
pytest -m samples        # Sample file tests (~50)
pytest -m resilience     # Resilience tests (~107)
pytest -m security       # Security tests (~20)
pytest -m slow           # Long-running tests (~10)
```

### Test Template for New Features

```python
# tests/plugins/test_my_feature.py
import pytest
from src.plugins.manager import PluginManager

@pytest.mark.unit
def test_new_protocol_added_to_plugin_interface():
    """Verify new protocol method exists on plugin base."""
    from src.plugins.base import OntologyPlugin
    assert hasattr(OntologyPlugin, 'get_my_new_protocol')

@pytest.mark.integration
def test_rdf_plugin_implements_new_protocol():
    """Verify RDF plugin implements (or returns None for) new protocol."""
    manager = PluginManager.get_instance()
    plugin = manager.get_plugin("rdf")
    protocol_impl = plugin.get_my_new_protocol()
    
    # Either implements or explicitly returns None
    assert protocol_impl is not None or plugin.get_my_new_protocol() is None
```

**📚 Complete Testing Guide:** [docs/TESTING.md](docs/TESTING.md)

---

## ⚙️ Configuration Quick Reference

**Location:** `src/config.json` (gitignored, copy from `config.sample.json`)

**Environment Variables (override config file):**
- `FABRIC_CLIENT_SECRET` - Service principal secret
- `AZURE_TENANT_ID`, `AZURE_CLIENT_ID` - Azure AD auth
- `PLUGIN_DIR` - Custom plugin directory

**📚 Complete Configuration Guide:** [docs/CONFIGURATION.md](docs/CONFIGURATION.md)

---

## 🚀 Workflow Quick Reference

### Convert RDF → Fabric
```bash
python -m src.main validate --format rdf ontology.ttl
python -m src.main upload --format rdf ontology.ttl --ontology-name MyOntology
```

### Convert DTDL → Fabric
```bash
python -m src.main upload --format dtdl models/ --recursive --ontology-name SmartBuilding
```

### Export Fabric → TTL
```bash
python -m src.main export --format rdf --ontology-id <id> --output exported.ttl
```

**📚 Complete CLI Reference:** [docs/CLI_COMMANDS.md](docs/CLI_COMMANDS.md)

---

## 🔐 Security & Best Practices

### Path Safety
- All paths validated in `src/core/validators.py`
- Symlinks checked to prevent directory escape
- `--allow-relative-up` required for `..` in paths

### Secret Management  
- Never commit `config.json` (gitignored)
- Use environment variables in CI/CD
- Azure Key Vault for production

### Code Quality
```bash
ruff check src/ --fix          # Lint
ruff format src/               # Format
mypy src/                      # Type check
pytest tests/ -m "not slow"    # Test
```

**📚 Complete Security Guide:** [docs/CONFIGURATION.md](docs/CONFIGURATION.md) - Security section

---

## 🧠 Agent Mental Model Summary

### When Asked to Make Changes

1. **Identify change type** (use decision tree above)
2. **Check existing patterns** (look for similar code)
3. **Verify protocol compliance** (does it fit existing interfaces?)
4. **Plan in layers** (which layer does this affect?)
5. **Test-first** (write tests before implementation)
6. **Document** (update relevant `docs/*.md`)

### Red Flags

- ❌ Modifying core for format-specific logic
- ❌ Duplicating validation/type mapping code
- ❌ Bypassing plugin system
- ❌ Skipping tests or docs
- ❌ Hardcoding values instead of using config

### Green Lights

- ✅ Following existing plugin patterns
- ✅ Using shared models and protocols
- ✅ Adding comprehensive tests
- ✅ Documenting changes
- ✅ Preserving backward compatibility

---

## 📚 Documentation Reference

| Document | When to Read |
|----------|--------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Understanding system design, data flow, patterns |
| [PLUGIN_GUIDE.md](docs/PLUGIN_GUIDE.md) | Adding new ontology format |
| [CLI_COMMANDS.md](docs/CLI_COMMANDS.md) | Adding/modifying CLI commands |
| [CONFIGURATION.md](docs/CONFIGURATION.md) | Modifying config, auth, or limits |
| [RDF_GUIDE.md](docs/RDF_GUIDE.md) | Working with RDF/OWL conversion |
| [DTDL_GUIDE.md](docs/DTDL_GUIDE.md) | Working with DTDL conversion |
| [TESTING.md](docs/TESTING.md) | Writing tests, running test suites |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Debugging common issues |
| [API.md](docs/API.md) | Understanding Fabric API interactions |

---

## ✅ Agent Self-Check Questions

Before completing any task, verify you can answer:

1. ✅ Which layer does this change affect? (CLI/Plugin/Converter/Core/Model)
2. ✅ Does this follow the plugin architecture pattern?
3. ✅ Which existing protocol does this implement or extend?
4. ✅ Have I written tests that cover this change?
5. ✅ Which documentation needs updating?
6. ✅ Does this break backward compatibility?
7. ✅ Have I checked similar code for patterns to follow?
8. ✅ Are all dependencies in the correct layer?
9. ✅ Does this require configuration changes?
10. ✅ Will this affect CLI interface or user workflows?

If you can't answer these, review the relevant documentation section above.

---

## 🔄 Version History

- **v2.0.0** (2026-01-03): Forward-looking restructure, removed duplications, added decision framework, protocol guidance
- **v1.0.0** (2026-01-03): Initial comprehensive specification

---

**End of Agent Specification**

**Remember:** This is a guide for making *informed decisions*. When in doubt, examine existing code patterns, consult the detailed documentation in `docs/`, and follow the principle of least surprise.
