# Error Handling Improvements


## Remaining Work (Low Priority)

The following issues remain for future improvement:

- Type hints consistency improvements
- Concurrent log file access handling
- Additional input validation edge cases
- Performance optimizations for very large ontologies
- Enhanced error messages for specific scenarios
- Improved logging granularity
- Additional unit tests for error paths
- Documentation updates for error codes
- Telemetry/metrics for production monitoring

### Implemented Enhancements (Dec 2025)

- Domain/Range Resolution:
   - Added support for resolving blank-node class expressions via `owl:unionOf` when reading `rdfs:domain` and `rdfs:range`.
   - Relationship generation now supports multiple domain-range pairs (one relationship per pair).
- Datatype Coverage:
   - Added XSD mappings for `xsd:anyURI` (String), `xsd:dateTimeStamp` (DateTime), and `xsd:time` (String).
- Logging and CLI Robustness:
   - Fixed logging initialization and configuration loading for `export` and `roundtrip` commands.
   - Improved sample file discovery in `test` command to look in multiple locations.

These changes reduce drops for ontologies that use union-of class expressions (e.g., parts of FOAF) and improve CLI reliability.

### Remaining Gaps

- ⚠️ No memory limits for extremely large ontologies (>1GB)
- ⚠️ Limited telemetry for production monitoring
- ⚠️ Limited support for complex OWL constructs (e.g., `owl:Restriction`, property characteristics)
- ⚠️ Properties without explicit `rdfs:domain`/`rdfs:range` may be skipped unless instance usage provides strong inference

## Recommendations for Future Work

1. **Enhanced Monitoring** (Low Priority)
   - Add structured logging
   - Add metrics collection
   - Add performance tracking

2. **Performance Optimization** (Low Priority)
   - Streaming parsing for very large files
   - Chunked processing for large ontologies
   - Connection pooling for HTTP requests

3. **Ontology Semantics & Inference** (Medium Priority)
   - Add optional "loose inference" mode to heuristically attach properties without explicit domain/range (guarded by a flag)
   - Support common OWL constructs (restrictions, property characteristics) to preserve more semantics in round-trip
   - Configurable datatype mapping overrides for edge cases

## Strict Semantics Policy (Current Behavior)

The converter adheres to strict semantics by default:

- Properties and relationships are generated only when `rdfs:domain` and `rdfs:range` resolve to declared classes in the input TTL.
- Blank-node class expressions using `owl:unionOf` are supported and resolved; each domain–range pair yields a distinct relationship.
- Properties without explicit, resolvable `rdfs:domain`/`rdfs:range` are skipped with warnings; no heuristic attachment is performed.
- Expanded XSD mappings ensure common datatypes (e.g., `xsd:anyURI`, `xsd:dateTimeStamp`) are preserved; time-only values (`xsd:time`) are represented as String.

### FOAF Round‑Trip Considerations under Strict Semantics

FOAF and similar vocabularies may rely on property signatures that are not explicitly declared in the provided TTL or reference external class definitions.

- If a property lacks explicit `rdfs:domain`/`rdfs:range` in the TTL (or references classes not declared locally), it will be skipped.
- To achieve round‑trip equivalence:
   1. Include explicit `rdfs:domain` and `rdfs:range` for the properties you want preserved.
   2. Ensure referenced classes are declared within the same TTL (or merge in the needed vocabularies).
   3. Avoid OWL constructs not currently supported (e.g., complex restrictions) or extend support in future iterations.

An optional "loose inference" mode is planned (see Recommendations) to heuristically attach properties when signatures are missing; it is intentionally disabled by default to maintain predictable, standards‑aligned behavior.
