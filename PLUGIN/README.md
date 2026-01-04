# Plugin System - Proposed Code Structure

This directory contains the proposed code structure for the plugin system.
These are reference implementations that can be used when implementing the actual plugin system.

## Directory Structure

```
PLUGIN/
├── PLUGIN_PLAN.md              # Main implementation plan
├── README.md                   # This file
├── proposed_code/
│   ├── common/                 # Common utilities to extract
│   │   ├── __init__.py
│   │   ├── type_registry.py    # Unified type mapping
│   │   ├── id_generator.py     # ID generation
│   │   └── validation.py       # Unified validation
│   │
│   ├── plugins/                # Plugin infrastructure
│   │   ├── __init__.py
│   │   ├── base.py             # OntologyPlugin ABC
│   │   ├── protocols.py        # Protocol definitions
│   │   ├── manager.py          # Plugin manager
│   │   └── builtin/
│   │       ├── __init__.py
│   │       ├── rdf_plugin.py   # RDF as plugin
│   │       ├── dtdl_plugin.py  # DTDL as plugin
│   │       └── jsonld_plugin.py # Sample JSON-LD plugin
│   │
│   └── cli_updates/            # CLI modifications
│       └── format_updated.py   # Updated format.py
│
├── samples/
│   ├── jsonld/                 # Sample JSON-LD files
│   │   ├── simple_person.jsonld
│   │   └── organization.jsonld
│   │
│   └── external_plugin/        # Example external plugin
│       ├── __init__.py
│       ├── shacl_plugin.py
│       └── setup.py
│
├── tests/
│   ├── test_plugin_base.py
│   ├── test_plugin_manager.py
│   └── test_jsonld_plugin.py
│
└── docs/
    └── PLUGIN_GUIDE.md         # Plugin development guide
```

## How to Use

1. Review `PLUGIN_PLAN.md` for the complete implementation strategy
2. Review proposed code in `proposed_code/` directory
3. Review sample files in `samples/` directory
4. Review test templates in `tests/` directory
5. Review documentation in `docs/` directory

## Implementation Order

1. **Phase 1**: Create `common/` module with extracted utilities
2. **Phase 2**: Create `plugins/` infrastructure
3. **Phase 3**: Refactor RDF and DTDL as plugins
4. **Phase 4**: Create JSON-LD sample plugin
5. **Phase 5**: Update CLI and documentation
