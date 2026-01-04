"""
Compliance validation and conversion warning system for DTDL, RDF/OWL, and Fabric IQ Ontology.

This module provides comprehensive compliance validation to:
1. Validate DTDL documents against v2/v3/v4 specifications
2. Validate RDF/OWL documents against OWL 2 and RDFS specifications
3. Detect and warn about information loss during Fabric IQ Ontology conversion
4. Generate detailed conversion reports

The compliance system helps users understand:
- What features are fully preserved in conversion
- What features are converted with limitations
- What information is lost and cannot be represented

Usage:
    from core.compliance import (
        DTDLComplianceValidator,
        RDFOWLComplianceValidator,
        FabricComplianceChecker,
        ConversionReport,
        ConversionReportGenerator,
    )
    
    # Validate DTDL compliance
    dtdl_validator = DTDLComplianceValidator()
    result = dtdl_validator.validate(interfaces)
    
    # Validate RDF/OWL compliance
    rdf_validator = RDFOWLComplianceValidator()
    result = rdf_validator.validate(graph)
    
    # Generate conversion report
    report_gen = ConversionReportGenerator()
    report = report_gen.generate_dtdl_report(interfaces)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class ComplianceLevel(Enum):
    """Compliance validation result levels."""
    COMPLIANT = "compliant"
    WARNING = "warning"
    ERROR = "error"


class ConversionImpact(Enum):
    """Impact level of conversion transformations."""
    PRESERVED = "preserved"  # Fully preserved in conversion
    CONVERTED_WITH_LIMITATIONS = "converted_with_limitations"  # Converted but with some loss
    LOST = "lost"  # Cannot be represented in target format
    TRANSFORMED = "transformed"  # Semantically changed during conversion


class DTDLVersion(Enum):
    """Supported DTDL versions."""
    V2 = 2
    V3 = 3
    V4 = 4


# DTDL Version-specific limits
DTDL_LIMITS = {
    DTDLVersion.V2: {
        "max_contents": 300,
        "max_extends": 2,
        "max_extends_depth": 10,
        "max_complex_schema_depth": 5,
        "max_name_length": 64,
        "max_enum_values": 100,
        "max_object_fields": 30,
        "max_relationship_multiplicity": 500,
        "supports_array_in_property": False,
        "supports_semantic_types": True,
    },
    DTDLVersion.V3: {
        "max_contents": 100000,  # Total elements in hierarchy
        "max_extends": 1024,  # In hierarchy
        "max_extends_depth": 10,
        "max_complex_schema_depth": 5,
        "max_name_length": 512,
        "max_enum_values": None,  # No explicit limit
        "max_object_fields": None,  # No explicit limit
        "max_relationship_multiplicity": None,  # No explicit limit
        "supports_array_in_property": True,
        "supports_semantic_types": False,  # Moved to extension
    },
    DTDLVersion.V4: {
        "max_contents": 100000,
        "max_extends": 1024,
        "max_extends_depth": 12,
        "max_complex_schema_depth": 8,
        "max_name_length": 512,
        "max_enum_values": None,
        "max_object_fields": None,
        "max_relationship_multiplicity": None,
        "supports_array_in_property": True,
        "supports_semantic_types": False,
        "supports_self_referential_schemas": True,
        "supports_scaled_decimal": True,
        "supports_nullable_commands": True,
    },
}


# RDF/OWL constructs and their Fabric support status
OWL_CONSTRUCT_SUPPORT = {
    # Classes
    "owl:Class": {"support": "full", "fabric": True, "notes": "Maps to EntityType"},
    "rdfs:Class": {"support": "full", "fabric": True, "notes": "Maps to EntityType"},
    "rdfs:subClassOf": {"support": "full", "fabric": True, "notes": "Maps to baseEntityTypeId"},
    
    # Properties
    "owl:DatatypeProperty": {"support": "full", "fabric": True, "notes": "Maps to EntityTypeProperty"},
    "owl:ObjectProperty": {"support": "full", "fabric": True, "notes": "Maps to RelationshipType"},
    "rdfs:domain": {"support": "full", "fabric": True, "notes": "Required for property mapping"},
    "rdfs:range": {"support": "full", "fabric": True, "notes": "Required for property mapping"},
    
    # Restrictions (NOT SUPPORTED)
    "owl:Restriction": {"support": "none", "fabric": False, "notes": "Constraints not enforced in Fabric"},
    "owl:allValuesFrom": {"support": "none", "fabric": False, "notes": "Universal restriction not supported"},
    "owl:someValuesFrom": {"support": "none", "fabric": False, "notes": "Existential restriction not supported"},
    "owl:hasValue": {"support": "none", "fabric": False, "notes": "Value restriction not supported"},
    "owl:cardinality": {"support": "none", "fabric": False, "notes": "Cardinality constraints not supported"},
    "owl:minCardinality": {"support": "none", "fabric": False, "notes": "Min cardinality not supported"},
    "owl:maxCardinality": {"support": "none", "fabric": False, "notes": "Max cardinality not supported"},
    "owl:qualifiedCardinality": {"support": "none", "fabric": False, "notes": "Qualified cardinality not supported"},
    
    # Property characteristics (NOT PRESERVED)
    "owl:FunctionalProperty": {"support": "none", "fabric": False, "notes": "Functional constraint not enforced"},
    "owl:InverseFunctionalProperty": {"support": "none", "fabric": False, "notes": "Inverse functional not supported"},
    "owl:TransitiveProperty": {"support": "none", "fabric": False, "notes": "Transitivity not materialized"},
    "owl:SymmetricProperty": {"support": "none", "fabric": False, "notes": "Symmetry not materialized"},
    "owl:AsymmetricProperty": {"support": "none", "fabric": False, "notes": "Asymmetry not enforced"},
    "owl:ReflexiveProperty": {"support": "none", "fabric": False, "notes": "Reflexivity not enforced"},
    "owl:IrreflexiveProperty": {"support": "none", "fabric": False, "notes": "Irreflexivity not enforced"},
    "owl:inverseOf": {"support": "none", "fabric": False, "notes": "Inverse relationships not created"},
    "owl:propertyChainAxiom": {"support": "none", "fabric": False, "notes": "Property chains not materialized"},
    
    # Class expressions (PARTIAL SUPPORT)
    "owl:unionOf": {"support": "partial", "fabric": True, "notes": "Union expanded to multiple relationships"},
    "owl:intersectionOf": {"support": "partial", "fabric": True, "notes": "Intersection flattened"},
    "owl:complementOf": {"support": "none", "fabric": False, "notes": "Complement not representable"},
    "owl:oneOf": {"support": "partial", "fabric": True, "notes": "Enum values extracted if applicable"},
    
    # Class axioms (NOT SUPPORTED)
    "owl:equivalentClass": {"support": "none", "fabric": False, "notes": "Class equivalence not preserved"},
    "owl:disjointWith": {"support": "none", "fabric": False, "notes": "Disjointness not enforced"},
    "owl:disjointUnionOf": {"support": "none", "fabric": False, "notes": "Disjoint union not supported"},
    
    # Property axioms (NOT SUPPORTED)
    "owl:equivalentProperty": {"support": "none", "fabric": False, "notes": "Property equivalence not preserved"},
    "owl:propertyDisjointWith": {"support": "none", "fabric": False, "notes": "Property disjointness not supported"},
    
    # Imports and annotations
    "owl:imports": {"support": "none", "fabric": False, "notes": "Must merge external ontologies manually"},
    "owl:versionInfo": {"support": "metadata", "fabric": False, "notes": "Preserved in metadata only"},
    "rdfs:label": {"support": "metadata", "fabric": True, "notes": "Used for display name"},
    "rdfs:comment": {"support": "metadata", "fabric": False, "notes": "Not preserved in Fabric"},
    
    # Individuals (OUT OF SCOPE)
    "owl:NamedIndividual": {"support": "none", "fabric": False, "notes": "Instance data not converted"},
    "owl:sameAs": {"support": "none", "fabric": False, "notes": "Instance identity not supported"},
    "owl:differentFrom": {"support": "none", "fabric": False, "notes": "Instance differentiation not supported"},
}


# DTDL features and their Fabric IQ Ontology support
DTDL_FEATURE_SUPPORT = {
    # Fully Supported
    "Interface": {"support": "full", "fabric": True, "notes": "Maps to EntityType"},
    "Property": {"support": "full", "fabric": True, "notes": "Maps to EntityTypeProperty"},
    "Relationship": {"support": "full", "fabric": True, "notes": "Maps to RelationshipType"},
    "extends": {"support": "full", "fabric": True, "notes": "Maps to baseEntityTypeId (single inheritance only)"},
    
    # Partially Supported
    "Telemetry": {"support": "partial", "fabric": True, "notes": "Maps to timeseriesProperties; complex schemas flattened"},
    "Component": {"support": "partial", "fabric": True, "notes": "Flattened into parent; reference semantics lost"},
    "displayName": {"support": "partial", "fabric": True, "notes": "Single language only; localization lost"},
    "description": {"support": "none", "fabric": False, "notes": "Not preserved in Fabric"},
    "comment": {"support": "none", "fabric": False, "notes": "Not preserved in Fabric"},
    
    # Complex Schemas
    "Object": {"support": "partial", "fabric": True, "notes": "Flattened to JSON String; nested structure lost"},
    "Array": {"support": "partial", "fabric": True, "notes": "Converted to JSON String; type safety lost"},
    "Enum": {"support": "partial", "fabric": True, "notes": "Converted to String/BigInt; named values lost"},
    "Map": {"support": "partial", "fabric": True, "notes": "Converted to JSON String; key-value typing lost"},
    
    # Not Supported
    "Command": {"support": "none", "fabric": False, "notes": "Operations not representable in Fabric"},
    "writable": {"support": "none", "fabric": False, "notes": "Read/write semantics not preserved"},
    "unit": {"support": "none", "fabric": False, "notes": "Semantic units not preserved"},
    "semanticType": {"support": "none", "fabric": False, "notes": "Semantic annotations not preserved"},
    "minMultiplicity": {"support": "none", "fabric": False, "notes": "Cardinality not enforced"},
    "maxMultiplicity": {"support": "none", "fabric": False, "notes": "Cardinality not enforced"},
    
    # Geospatial
    "point": {"support": "partial", "fabric": True, "notes": "Stored as GeoJSON String"},
    "lineString": {"support": "partial", "fabric": True, "notes": "Stored as GeoJSON String"},
    "polygon": {"support": "partial", "fabric": True, "notes": "Stored as GeoJSON String"},
    
    # DTDL v4 specific
    "scaledDecimal": {"support": "partial", "fabric": True, "notes": "Stored as JSON String with scale/value"},
    "nullable": {"support": "none", "fabric": False, "notes": "Nullability not enforced"},
}


# =============================================================================
# Data Classes for Results
# =============================================================================

@dataclass
class ComplianceIssue:
    """Represents a single compliance issue or warning."""
    level: ComplianceLevel
    code: str
    message: str
    location: Optional[str] = None  # File path, line number, or element identifier
    element_type: Optional[str] = None  # Interface, Property, Class, etc.
    element_name: Optional[str] = None
    suggestion: Optional[str] = None  # How to fix or workaround
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "level": self.level.value,
            "code": self.code,
            "message": self.message,
        }
        if self.location:
            result["location"] = self.location
        if self.element_type:
            result["element_type"] = self.element_type
        if self.element_name:
            result["element_name"] = self.element_name
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result


@dataclass
class ConversionWarning:
    """Represents a warning about information loss during conversion."""
    impact: ConversionImpact
    feature: str
    source_construct: str  # Original construct (e.g., "owl:Restriction", "Command")
    target_representation: Optional[str] = None  # How it's represented in target (or None if lost)
    details: Optional[str] = None
    affected_elements: List[str] = field(default_factory=list)
    workaround: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "impact": self.impact.value,
            "feature": self.feature,
            "source_construct": self.source_construct,
        }
        if self.target_representation:
            result["target_representation"] = self.target_representation
        if self.details:
            result["details"] = self.details
        if self.affected_elements:
            result["affected_elements"] = self.affected_elements
        if self.workaround:
            result["workaround"] = self.workaround
        return result


@dataclass
class ComplianceResult:
    """Result of compliance validation."""
    is_valid: bool
    source_type: str  # "DTDL" or "RDF/OWL"
    version: Optional[str] = None
    issues: List[ComplianceIssue] = field(default_factory=list)
    warnings: List[ConversionWarning] = field(default_factory=list)
    statistics: Dict[str, int] = field(default_factory=dict)
    
    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.level == ComplianceLevel.ERROR)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.level == ComplianceLevel.WARNING)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "source_type": self.source_type,
            "version": self.version,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [i.to_dict() for i in self.issues],
            "warnings": [w.to_dict() for w in self.warnings],
            "statistics": self.statistics,
        }


@dataclass
class ConversionReport:
    """Comprehensive report of a conversion process."""
    timestamp: str
    source_format: str
    target_format: str = "Fabric IQ Ontology"
    
    # Summary counts
    total_elements: int = 0
    preserved_count: int = 0
    converted_with_limitations_count: int = 0
    lost_count: int = 0
    
    # Detailed breakdowns
    preserved_features: List[str] = field(default_factory=list)
    limited_features: List[ConversionWarning] = field(default_factory=list)
    lost_features: List[ConversionWarning] = field(default_factory=list)
    
    # Source compliance
    compliance_result: Optional[ComplianceResult] = None
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "source_format": self.source_format,
            "target_format": self.target_format,
            "summary": {
                "total_elements": self.total_elements,
                "preserved": self.preserved_count,
                "converted_with_limitations": self.converted_with_limitations_count,
                "lost": self.lost_count,
            },
            "preserved_features": self.preserved_features,
            "limited_features": [w.to_dict() for w in self.limited_features],
            "lost_features": [w.to_dict() for w in self.lost_features],
            "compliance": self.compliance_result.to_dict() if self.compliance_result else None,
            "recommendations": self.recommendations,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def get_summary_text(self) -> str:
        """Get human-readable summary."""
        lines = [
            f"Conversion Report - {self.source_format} → {self.target_format}",
            f"Generated: {self.timestamp}",
            "",
            "Summary:",
            f"  Total elements: {self.total_elements}",
            f"  Fully preserved: {self.preserved_count}",
            f"  Converted with limitations: {self.converted_with_limitations_count}",
            f"  Information lost: {self.lost_count}",
            "",
        ]
        
        if self.limited_features:
            lines.append("Features converted with limitations:")
            for warning in self.limited_features:
                lines.append(f"  - {warning.feature}: {warning.details or warning.source_construct}")
            lines.append("")
        
        if self.lost_features:
            lines.append("Features lost in conversion:")
            for warning in self.lost_features:
                lines.append(f"  - {warning.feature}: {warning.details or warning.source_construct}")
                if warning.workaround:
                    lines.append(f"    Workaround: {warning.workaround}")
            lines.append("")
        
        if self.recommendations:
            lines.append("Recommendations:")
            for rec in self.recommendations:
                lines.append(f"  - {rec}")
        
        return "\n".join(lines)
    
    def to_markdown(self) -> str:
        """Convert report to Markdown format."""
        lines = [
            f"# Conversion Report",
            f"",
            f"**Source Format:** {self.source_format}",
            f"**Target Format:** {self.target_format}",
            f"**Generated:** {self.timestamp}",
            "",
            "## Summary",
            "",
            "| Metric | Count |",
            "|--------|-------|",
            f"| Total Elements | {self.total_elements} |",
            f"| Fully Preserved | {self.preserved_count} |",
            f"| Converted with Limitations | {self.converted_with_limitations_count} |",
            f"| Information Lost | {self.lost_count} |",
            "",
        ]
        
        if self.preserved_features:
            lines.extend([
                "## Preserved Features",
                "",
            ])
            for feat in self.preserved_features:
                lines.append(f"- {feat}")
            lines.append("")
        
        if self.limited_features:
            lines.extend([
                "## Features Converted with Limitations",
                "",
                "| Feature | Impact | Details |",
                "|---------|--------|---------|",
            ])
            for warning in self.limited_features:
                details = warning.details or warning.source_construct
                lines.append(f"| {warning.feature} | {warning.impact.value} | {details} |")
            lines.append("")
        
        if self.lost_features:
            lines.extend([
                "## Features Lost in Conversion",
                "",
                "| Feature | Details | Workaround |",
                "|---------|---------|------------|",
            ])
            for warning in self.lost_features:
                details = warning.details or warning.source_construct
                workaround = warning.workaround or "N/A"
                lines.append(f"| {warning.feature} | {details} | {workaround} |")
            lines.append("")
        
        if self.recommendations:
            lines.extend([
                "## Recommendations",
                "",
            ])
            for rec in self.recommendations:
                lines.append(f"- {rec}")
            lines.append("")
        
        return "\n".join(lines)


# =============================================================================
# DTDL Compliance Validator
# =============================================================================

class DTDLComplianceValidator:
    """
    Validates DTDL documents against v2/v3/v4 specifications.
    
    Checks for:
    - Valid DTMI format
    - Required fields presence
    - Value constraints (lengths, counts, types)
    - Version-specific features
    - Structural validity (inheritance depth, schema nesting)
    """
    
    def __init__(self, strict: bool = False):
        """
        Initialize validator.
        
        Args:
            strict: If True, treat warnings as errors
        """
        self.strict = strict
    
    def validate(
        self,
        interfaces: List[Any],
        version: Optional[DTDLVersion] = None
    ) -> ComplianceResult:
        """
        Validate a list of DTDL interfaces.
        
        Args:
            interfaces: List of DTDLInterface objects
            version: Expected DTDL version (auto-detected if None)
            
        Returns:
            ComplianceResult with validation findings
        """
        result = ComplianceResult(
            is_valid=True,
            source_type="DTDL",
            version=f"v{version.value}" if version else "auto",
            statistics={
                "interfaces": len(interfaces),
                "properties": 0,
                "relationships": 0,
                "telemetries": 0,
                "commands": 0,
                "components": 0,
            }
        )
        
        # Build interface map for reference validation
        interface_map = {}
        for iface in interfaces:
            if hasattr(iface, 'dtmi'):
                interface_map[iface.dtmi] = iface
        
        # Validate each interface
        for iface in interfaces:
            detected_version = self._detect_version(iface)
            if version is None:
                version = detected_version
            
            limits = DTDL_LIMITS.get(version or DTDLVersion.V3, DTDL_LIMITS[DTDLVersion.V3])
            
            # Validate DTMI
            self._validate_dtmi(iface, result)
            
            # Validate interface structure
            self._validate_interface_structure(iface, limits, result)
            
            # Validate inheritance
            self._validate_inheritance(iface, interface_map, limits, result)
            
            # Validate contents
            self._validate_contents(iface, limits, result)
            
            # Count elements for statistics
            self._count_elements(iface, result)
        
        # Check for any errors
        result.is_valid = result.error_count == 0
        if self.strict and result.warning_count > 0:
            result.is_valid = False
        
        return result
    
    def _detect_version(self, interface: Any) -> Optional[DTDLVersion]:
        """Detect DTDL version from interface context."""
        if hasattr(interface, 'context'):
            ctx = interface.context
            if hasattr(ctx, 'dtdl_version'):
                version_num = ctx.dtdl_version
                return DTDLVersion(version_num) if version_num in [2, 3, 4] else None
        return None
    
    def _validate_dtmi(self, interface: Any, result: ComplianceResult) -> None:
        """Validate DTMI format."""
        if not hasattr(interface, 'dtmi') or not interface.dtmi:
            result.issues.append(ComplianceIssue(
                level=ComplianceLevel.ERROR,
                code="DTDL001",
                message="Interface missing required @id (DTMI)",
                element_type="Interface",
                element_name=getattr(interface, 'name', 'unknown'),
            ))
            return
        
        dtmi = interface.dtmi
        
        # Basic DTMI format check
        if not dtmi.startswith("dtmi:"):
            result.issues.append(ComplianceIssue(
                level=ComplianceLevel.ERROR,
                code="DTDL002",
                message=f"Invalid DTMI format: must start with 'dtmi:' (got: {dtmi})",
                element_type="Interface",
                element_name=interface.dtmi,
            ))
        
        # Length check for Interface DTMIs
        if len(dtmi) > 128:
            result.issues.append(ComplianceIssue(
                level=ComplianceLevel.ERROR,
                code="DTDL003",
                message=f"Interface DTMI exceeds maximum length of 128 characters (length: {len(dtmi)})",
                element_type="Interface",
                element_name=interface.dtmi,
            ))
        
        # Check for system segments (segments starting with underscore)
        parts = dtmi.replace("dtmi:", "").split(";")[0].split(":")
        for part in parts:
            if part.startswith("_"):
                result.issues.append(ComplianceIssue(
                    level=ComplianceLevel.ERROR,
                    code="DTDL004",
                    message=f"DTMI contains system segment (starts with _): {part}",
                    element_type="Interface",
                    element_name=interface.dtmi,
                    suggestion="User DTMIs cannot contain segments starting with underscore",
                ))
    
    def _validate_interface_structure(
        self,
        interface: Any,
        limits: Dict,
        result: ComplianceResult
    ) -> None:
        """Validate interface structure against version limits."""
        # Validate name length
        name = getattr(interface, 'name', '') or getattr(interface, 'resolved_display_name', '')
        max_name = limits.get('max_name_length', 512)
        
        if len(name) > max_name:
            result.issues.append(ComplianceIssue(
                level=ComplianceLevel.ERROR,
                code="DTDL010",
                message=f"Interface name exceeds maximum length of {max_name} characters",
                element_type="Interface",
                element_name=interface.dtmi,
            ))
    
    def _validate_inheritance(
        self,
        interface: Any,
        interface_map: Dict,
        limits: Dict,
        result: ComplianceResult
    ) -> None:
        """Validate inheritance chain."""
        extends = getattr(interface, 'extends', []) or []
        
        # Check extends count
        max_extends = limits.get('max_extends', 2)
        if len(extends) > max_extends:
            result.issues.append(ComplianceIssue(
                level=ComplianceLevel.ERROR,
                code="DTDL020",
                message=f"Interface extends {len(extends)} interfaces, maximum is {max_extends}",
                element_type="Interface",
                element_name=interface.dtmi,
            ))
        
        # Check inheritance depth
        max_depth = limits.get('max_extends_depth', 10)
        depth = self._calculate_inheritance_depth(interface, interface_map)
        if depth > max_depth:
            result.issues.append(ComplianceIssue(
                level=ComplianceLevel.ERROR,
                code="DTDL021",
                message=f"Inheritance depth ({depth}) exceeds maximum ({max_depth})",
                element_type="Interface",
                element_name=interface.dtmi,
            ))
        
        # Warn about external references
        for parent_dtmi in extends:
            if parent_dtmi not in interface_map:
                result.issues.append(ComplianceIssue(
                    level=ComplianceLevel.WARNING,
                    code="DTDL022",
                    message=f"Interface extends external type not in model: {parent_dtmi}",
                    element_type="Interface",
                    element_name=interface.dtmi,
                    suggestion="Include the parent interface definition or remove the extends reference",
                ))
    
    def _calculate_inheritance_depth(
        self,
        interface: Any,
        interface_map: Dict,
        visited: Optional[Set[str]] = None
    ) -> int:
        """Calculate inheritance chain depth."""
        if visited is None:
            visited = set()
        
        dtmi = getattr(interface, 'dtmi', '')
        if dtmi in visited:
            return 0  # Cycle detected, stop
        
        visited.add(dtmi)
        extends = getattr(interface, 'extends', []) or []
        
        if not extends:
            return 1
        
        max_depth = 0
        for parent_dtmi in extends:
            if parent_dtmi in interface_map:
                parent = interface_map[parent_dtmi]
                depth = self._calculate_inheritance_depth(parent, interface_map, visited)
                max_depth = max(max_depth, depth)
        
        return max_depth + 1
    
    def _validate_contents(
        self,
        interface: Any,
        limits: Dict,
        result: ComplianceResult
    ) -> None:
        """Validate interface contents."""
        # Validate properties
        properties = getattr(interface, 'properties', []) or []
        for prop in properties:
            self._validate_content_element(prop, "Property", limits, result)
        
        # Validate relationships
        relationships = getattr(interface, 'relationships', []) or []
        for rel in relationships:
            self._validate_content_element(rel, "Relationship", limits, result)
        
        # Validate telemetries
        telemetries = getattr(interface, 'telemetries', []) or []
        for tel in telemetries:
            self._validate_content_element(tel, "Telemetry", limits, result)
        
        # Validate commands
        commands = getattr(interface, 'commands', []) or []
        for cmd in commands:
            self._validate_content_element(cmd, "Command", limits, result)
    
    def _validate_content_element(
        self,
        element: Any,
        element_type: str,
        limits: Dict,
        result: ComplianceResult
    ) -> None:
        """Validate a single content element."""
        name = getattr(element, 'name', '')
        max_name = limits.get('max_name_length', 512)
        
        if len(name) > max_name:
            result.issues.append(ComplianceIssue(
                level=ComplianceLevel.ERROR,
                code="DTDL030",
                message=f"{element_type} name '{name}' exceeds maximum length of {max_name}",
                element_type=element_type,
                element_name=name,
            ))
        
        # Validate name format (alphanumeric + underscore, starting with letter)
        if name and not name[0].isalpha():
            result.issues.append(ComplianceIssue(
                level=ComplianceLevel.ERROR,
                code="DTDL031",
                message=f"{element_type} name must start with a letter: '{name}'",
                element_type=element_type,
                element_name=name,
            ))
    
    def _count_elements(self, interface: Any, result: ComplianceResult) -> None:
        """Count interface elements for statistics."""
        result.statistics["properties"] += len(getattr(interface, 'properties', []) or [])
        result.statistics["relationships"] += len(getattr(interface, 'relationships', []) or [])
        result.statistics["telemetries"] += len(getattr(interface, 'telemetries', []) or [])
        result.statistics["commands"] += len(getattr(interface, 'commands', []) or [])
        result.statistics["components"] += len(getattr(interface, 'components', []) or [])


# =============================================================================
# RDF/OWL Compliance Validator
# =============================================================================

class RDFOWLComplianceValidator:
    """
    Validates RDF/OWL documents against OWL 2 and RDFS specifications.
    
    Checks for:
    - Valid URI formats
    - Required property signatures (domain/range)
    - Supported OWL constructs
    - Class hierarchy consistency
    """
    
    def __init__(self, strict: bool = False):
        """
        Initialize validator.
        
        Args:
            strict: If True, treat warnings as errors
        """
        self.strict = strict
    
    def validate(self, graph: Any) -> ComplianceResult:
        """
        Validate an RDF graph.
        
        Args:
            graph: RDFLib Graph object
            
        Returns:
            ComplianceResult with validation findings
        """
        from rdflib import RDF, RDFS, OWL, URIRef
        
        result = ComplianceResult(
            is_valid=True,
            source_type="RDF/OWL",
            version="OWL 2",
            statistics={
                "classes": 0,
                "datatype_properties": 0,
                "object_properties": 0,
                "restrictions": 0,
                "individuals": 0,
            }
        )
        
        # Collect all declared classes
        declared_classes: Set[str] = set()
        for s in graph.subjects(RDF.type, OWL.Class):
            declared_classes.add(str(s))
            result.statistics["classes"] += 1
        for s in graph.subjects(RDF.type, RDFS.Class):
            declared_classes.add(str(s))
        
        # Validate datatype properties
        for prop in graph.subjects(RDF.type, OWL.DatatypeProperty):
            result.statistics["datatype_properties"] += 1
            self._validate_property(prop, "DatatypeProperty", graph, declared_classes, result)
        
        # Validate object properties
        for prop in graph.subjects(RDF.type, OWL.ObjectProperty):
            result.statistics["object_properties"] += 1
            self._validate_property(prop, "ObjectProperty", graph, declared_classes, result)
        
        # Check for restrictions (warning - not supported)
        for restriction in graph.subjects(RDF.type, OWL.Restriction):
            result.statistics["restrictions"] += 1
            result.issues.append(ComplianceIssue(
                level=ComplianceLevel.WARNING,
                code="OWL001",
                message="owl:Restriction detected - constraints will not be preserved in Fabric",
                element_type="Restriction",
                element_name=str(restriction),
                suggestion="Consider expressing constraints as documentation or external validation rules",
            ))
        
        # Check for unsupported constructs
        self._check_unsupported_constructs(graph, result)
        
        # Count individuals
        for ind in graph.subjects(RDF.type, OWL.NamedIndividual):
            result.statistics["individuals"] += 1
        
        if result.statistics["individuals"] > 0:
            result.issues.append(ComplianceIssue(
                level=ComplianceLevel.WARNING,
                code="OWL010",
                message=f"Found {result.statistics['individuals']} individuals - instance data is not converted",
                element_type="Individual",
                suggestion="Individual/instance data must be loaded separately into Fabric",
            ))
        
        # Determine validity
        result.is_valid = result.error_count == 0
        if self.strict and result.warning_count > 0:
            result.is_valid = False
        
        return result
    
    def _validate_property(
        self,
        prop: Any,
        prop_type: str,
        graph: Any,
        declared_classes: Set[str],
        result: ComplianceResult
    ) -> None:
        """Validate a property has required domain and range."""
        from rdflib import RDFS
        
        prop_uri = str(prop)
        
        # Check domain
        domains = list(graph.objects(prop, RDFS.domain))
        if not domains:
            result.issues.append(ComplianceIssue(
                level=ComplianceLevel.WARNING,
                code="OWL020",
                message=f"Property missing rdfs:domain - will be skipped in conversion",
                element_type=prop_type,
                element_name=prop_uri,
                suggestion="Add explicit rdfs:domain pointing to a declared class",
            ))
        else:
            # Validate domain references declared class
            for domain in domains:
                domain_str = str(domain)
                if domain_str not in declared_classes and not self._is_blank_node(domain):
                    result.issues.append(ComplianceIssue(
                        level=ComplianceLevel.WARNING,
                        code="OWL021",
                        message=f"Property domain references undeclared class: {domain_str}",
                        element_type=prop_type,
                        element_name=prop_uri,
                        suggestion="Declare the domain class or import its definition",
                    ))
        
        # Check range
        ranges = list(graph.objects(prop, RDFS.range))
        if not ranges:
            result.issues.append(ComplianceIssue(
                level=ComplianceLevel.WARNING,
                code="OWL022",
                message=f"Property missing rdfs:range - will be skipped or use default String type",
                element_type=prop_type,
                element_name=prop_uri,
                suggestion="Add explicit rdfs:range",
            ))
    
    def _is_blank_node(self, node: Any) -> bool:
        """Check if node is a blank node."""
        from rdflib import BNode
        return isinstance(node, BNode)
    
    def _check_unsupported_constructs(self, graph: Any, result: ComplianceResult) -> None:
        """Check for OWL constructs that aren't supported."""
        from rdflib import OWL, RDF
        
        unsupported_checks = [
            (OWL.FunctionalProperty, "OWL030", "owl:FunctionalProperty"),
            (OWL.TransitiveProperty, "OWL031", "owl:TransitiveProperty"),
            (OWL.SymmetricProperty, "OWL032", "owl:SymmetricProperty"),
            (OWL.inverseOf, "OWL033", "owl:inverseOf"),
        ]
        
        for construct, code, name in unsupported_checks:
            # Check as type
            count = len(list(graph.subjects(RDF.type, construct)))
            if count > 0:
                result.issues.append(ComplianceIssue(
                    level=ComplianceLevel.WARNING,
                    code=code,
                    message=f"Found {count} uses of {name} - semantic behavior not preserved in Fabric",
                    suggestion="Document expected behavior externally",
                ))
            
            # Check as predicate
            count = len(list(graph.subject_objects(construct)))
            if count > 0:
                result.issues.append(ComplianceIssue(
                    level=ComplianceLevel.WARNING,
                    code=code,
                    message=f"Found {count} uses of {name} as predicate - not preserved in Fabric",
                ))
        
        # Check for owl:imports
        imports_count = len(list(graph.objects(None, OWL.imports)))
        if imports_count > 0:
            result.issues.append(ComplianceIssue(
                level=ComplianceLevel.WARNING,
                code="OWL040",
                message=f"Found {imports_count} owl:imports statements - external ontologies must be merged manually",
                suggestion="Use a tool like robot or rapper to merge imported ontologies before conversion",
            ))


# =============================================================================
# Fabric Compliance Checker
# =============================================================================

class FabricComplianceChecker:
    """
    Checks Fabric IQ Ontology compliance and detects potential issues.
    
    Validates generated Fabric definitions against API requirements.
    """
    
    def check(
        self,
        entity_types: List[Any],
        relationship_types: List[Any]
    ) -> ComplianceResult:
        """
        Check Fabric ontology definition compliance.
        
        Args:
            entity_types: List of EntityType objects
            relationship_types: List of RelationshipType objects
            
        Returns:
            ComplianceResult with findings
        """
        result = ComplianceResult(
            is_valid=True,
            source_type="Fabric IQ Ontology",
            statistics={
                "entity_types": len(entity_types),
                "relationship_types": len(relationship_types),
                "total_properties": 0,
            }
        )
        
        # Import Fabric limits
        from constants import FabricLimits
        
        entity_ids = {e.id for e in entity_types}
        
        for entity in entity_types:
            # Check name length
            if len(entity.name) > FabricLimits.MAX_ENTITY_NAME_LENGTH:
                result.issues.append(ComplianceIssue(
                    level=ComplianceLevel.ERROR,
                    code="FAB001",
                    message=f"Entity name exceeds {FabricLimits.MAX_ENTITY_NAME_LENGTH} characters",
                    element_type="EntityType",
                    element_name=entity.name,
                ))
            
            # Check parent reference validity
            if entity.baseEntityTypeId and entity.baseEntityTypeId not in entity_ids:
                result.issues.append(ComplianceIssue(
                    level=ComplianceLevel.ERROR,
                    code="FAB002",
                    message=f"Entity references non-existent parent: {entity.baseEntityTypeId}",
                    element_type="EntityType",
                    element_name=entity.name,
                ))
            
            # Check property count
            prop_count = len(entity.properties) + len(getattr(entity, 'timeseriesProperties', []))
            result.statistics["total_properties"] += prop_count
            
            if prop_count > FabricLimits.MAX_PROPERTIES_PER_ENTITY:
                result.issues.append(ComplianceIssue(
                    level=ComplianceLevel.WARNING,
                    code="FAB003",
                    message=f"Entity has {prop_count} properties, exceeds recommended {FabricLimits.MAX_PROPERTIES_PER_ENTITY}",
                    element_type="EntityType",
                    element_name=entity.name,
                ))
            
            # Validate properties
            for prop in entity.properties:
                if len(prop.name) > FabricLimits.MAX_PROPERTY_NAME_LENGTH:
                    result.issues.append(ComplianceIssue(
                        level=ComplianceLevel.ERROR,
                        code="FAB010",
                        message=f"Property name exceeds {FabricLimits.MAX_PROPERTY_NAME_LENGTH} characters",
                        element_type="Property",
                        element_name=prop.name,
                    ))
        
        # Check totals
        if len(entity_types) > FabricLimits.MAX_ENTITY_TYPES:
            result.issues.append(ComplianceIssue(
                level=ComplianceLevel.WARNING,
                code="FAB020",
                message=f"Ontology has {len(entity_types)} entity types, exceeds recommended {FabricLimits.MAX_ENTITY_TYPES}",
            ))
        
        if len(relationship_types) > FabricLimits.MAX_RELATIONSHIP_TYPES:
            result.issues.append(ComplianceIssue(
                level=ComplianceLevel.WARNING,
                code="FAB021",
                message=f"Ontology has {len(relationship_types)} relationships, exceeds recommended {FabricLimits.MAX_RELATIONSHIP_TYPES}",
            ))
        
        result.is_valid = result.error_count == 0
        return result


# =============================================================================
# Conversion Report Generator
# =============================================================================

class ConversionReportGenerator:
    """
    Generates comprehensive conversion reports detailing what is preserved,
    converted with limitations, or lost during conversion to Fabric IQ Ontology.
    """
    
    def generate_dtdl_report(self, interfaces: List[Any]) -> ConversionReport:
        """
        Generate a conversion report for DTDL to Fabric conversion.
        
        Args:
            interfaces: List of DTDLInterface objects
            
        Returns:
            ConversionReport with detailed findings
        """
        report = ConversionReport(
            timestamp=datetime.now().isoformat(),
            source_format="DTDL",
        )
        
        # Validate DTDL compliance first
        validator = DTDLComplianceValidator()
        report.compliance_result = validator.validate(interfaces)
        
        # Analyze features
        feature_counts: Dict[str, int] = {}
        
        for iface in interfaces:
            report.total_elements += 1
            
            # Properties (full support)
            props = getattr(iface, 'properties', []) or []
            feature_counts["Property"] = feature_counts.get("Property", 0) + len(props)
            
            # Relationships (full support)
            rels = getattr(iface, 'relationships', []) or []
            feature_counts["Relationship"] = feature_counts.get("Relationship", 0) + len(rels)
            
            # Telemetry (partial support)
            tels = getattr(iface, 'telemetries', []) or []
            feature_counts["Telemetry"] = feature_counts.get("Telemetry", 0) + len(tels)
            
            # Commands (not supported)
            cmds = getattr(iface, 'commands', []) or []
            feature_counts["Command"] = feature_counts.get("Command", 0) + len(cmds)
            
            # Components (partial support)
            comps = getattr(iface, 'components', []) or []
            feature_counts["Component"] = feature_counts.get("Component", 0) + len(comps)
            
            # Check for complex schemas
            for prop in props:
                schema = getattr(prop, 'schema', None)
                if schema and not isinstance(schema, str):
                    schema_type = type(schema).__name__
                    feature_counts[schema_type] = feature_counts.get(schema_type, 0) + 1
        
        # Categorize features
        for feature, count in feature_counts.items():
            if count == 0:
                continue
            
            support_info = DTDL_FEATURE_SUPPORT.get(feature, {})
            support_level = support_info.get("support", "partial")
            
            if support_level == "full":
                report.preserved_count += count
                if feature not in report.preserved_features:
                    report.preserved_features.append(f"{feature} ({count})")
            
            elif support_level == "partial":
                report.converted_with_limitations_count += count
                report.limited_features.append(ConversionWarning(
                    impact=ConversionImpact.CONVERTED_WITH_LIMITATIONS,
                    feature=feature,
                    source_construct=feature,
                    target_representation=support_info.get("notes", "Converted with modifications"),
                    details=f"{count} {feature}(s) converted with limitations",
                ))
            
            else:  # none
                report.lost_count += count
                report.lost_features.append(ConversionWarning(
                    impact=ConversionImpact.LOST,
                    feature=feature,
                    source_construct=feature,
                    details=f"{count} {feature}(s) cannot be represented in Fabric",
                    workaround=support_info.get("notes"),
                ))
        
        # Add recommendations
        if feature_counts.get("Command", 0) > 0:
            report.recommendations.append(
                "Commands are not supported in Fabric IQ Ontology. "
                "Consider implementing command logic in your application layer."
            )
        
        if feature_counts.get("Component", 0) > 0:
            report.recommendations.append(
                "Components are flattened into parent entities. "
                "Component reference semantics are lost."
            )
        
        return report
    
    def generate_rdf_report(self, graph: Any) -> ConversionReport:
        """
        Generate a conversion report for RDF/OWL to Fabric conversion.
        
        Args:
            graph: RDFLib Graph object
            
        Returns:
            ConversionReport with detailed findings
        """
        from rdflib import RDF, RDFS, OWL
        
        report = ConversionReport(
            timestamp=datetime.now().isoformat(),
            source_format="RDF/OWL",
        )
        
        # Validate RDF/OWL compliance first
        validator = RDFOWLComplianceValidator()
        report.compliance_result = validator.validate(graph)
        
        # Count constructs
        construct_counts: Dict[str, int] = {}
        
        # Classes
        for _ in graph.subjects(RDF.type, OWL.Class):
            construct_counts["owl:Class"] = construct_counts.get("owl:Class", 0) + 1
            report.total_elements += 1
        
        # Properties
        for _ in graph.subjects(RDF.type, OWL.DatatypeProperty):
            construct_counts["owl:DatatypeProperty"] = construct_counts.get("owl:DatatypeProperty", 0) + 1
            report.total_elements += 1
        
        for _ in graph.subjects(RDF.type, OWL.ObjectProperty):
            construct_counts["owl:ObjectProperty"] = construct_counts.get("owl:ObjectProperty", 0) + 1
            report.total_elements += 1
        
        # Restrictions
        for _ in graph.subjects(RDF.type, OWL.Restriction):
            construct_counts["owl:Restriction"] = construct_counts.get("owl:Restriction", 0) + 1
        
        # Property characteristics
        for char in [OWL.FunctionalProperty, OWL.TransitiveProperty, OWL.SymmetricProperty]:
            for _ in graph.subjects(RDF.type, char):
                char_name = str(char).split("#")[-1]
                construct_counts[f"owl:{char_name}"] = construct_counts.get(f"owl:{char_name}", 0) + 1
        
        # Categorize by support level
        for construct, count in construct_counts.items():
            if count == 0:
                continue
            
            support_info = OWL_CONSTRUCT_SUPPORT.get(construct, {})
            support_level = support_info.get("support", "none")
            
            if support_level == "full":
                report.preserved_count += count
                report.preserved_features.append(f"{construct} ({count})")
            
            elif support_level in ["partial", "metadata"]:
                report.converted_with_limitations_count += count
                report.limited_features.append(ConversionWarning(
                    impact=ConversionImpact.CONVERTED_WITH_LIMITATIONS,
                    feature=construct,
                    source_construct=construct,
                    target_representation=support_info.get("notes", ""),
                    details=f"{count} occurrence(s)",
                ))
            
            else:  # none
                report.lost_count += count
                report.lost_features.append(ConversionWarning(
                    impact=ConversionImpact.LOST,
                    feature=construct,
                    source_construct=construct,
                    details=f"{count} occurrence(s) - {support_info.get('notes', 'Not supported')}",
                    workaround=self._get_workaround(construct),
                ))
        
        # Add recommendations
        if construct_counts.get("owl:Restriction", 0) > 0:
            report.recommendations.append(
                "OWL Restrictions are not supported. Consider expressing constraints "
                "as explicit properties or external validation rules."
            )
        
        if any(k.startswith("owl:") and "Property" in k and k != "owl:DatatypeProperty" and k != "owl:ObjectProperty" 
               for k in construct_counts.keys()):
            report.recommendations.append(
                "Property characteristics (transitive, symmetric, etc.) are not materialized. "
                "If you need these semantics, implement them in your application logic."
            )
        
        return report
    
    def _get_workaround(self, construct: str) -> Optional[str]:
        """Get workaround suggestion for unsupported construct."""
        workarounds = {
            "owl:Restriction": "Express constraints as documentation or use SHACL for validation before import",
            "owl:FunctionalProperty": "Enforce functional constraint in application logic",
            "owl:TransitiveProperty": "Materialize transitive closure before import or query dynamically",
            "owl:SymmetricProperty": "Create inverse relationships explicitly",
            "owl:inverseOf": "Create both relationship types explicitly",
            "owl:equivalentClass": "Merge equivalent classes or use explicit mappings",
            "owl:imports": "Use ontology merge tools (robot, rapper) before conversion",
        }
        return workarounds.get(construct)


# =============================================================================
# Convenience Functions
# =============================================================================

def validate_dtdl_compliance(interfaces: List[Any], strict: bool = False) -> ComplianceResult:
    """
    Validate DTDL interfaces for compliance.
    
    Args:
        interfaces: List of DTDLInterface objects
        strict: If True, treat warnings as errors
        
    Returns:
        ComplianceResult
    """
    validator = DTDLComplianceValidator(strict=strict)
    return validator.validate(interfaces)


def validate_rdf_compliance(graph: Any, strict: bool = False) -> ComplianceResult:
    """
    Validate RDF/OWL graph for compliance.
    
    Args:
        graph: RDFLib Graph object
        strict: If True, treat warnings as errors
        
    Returns:
        ComplianceResult
    """
    validator = RDFOWLComplianceValidator(strict=strict)
    return validator.validate(graph)


def generate_conversion_report(
    source: Any,
    source_type: str = "auto"
) -> ConversionReport:
    """
    Generate a conversion report for the given source.
    
    Args:
        source: Either a list of DTDLInterface objects or an RDFLib Graph
        source_type: "dtdl", "rdf", or "auto" to detect
        
    Returns:
        ConversionReport
    """
    generator = ConversionReportGenerator()
    
    if source_type == "auto":
        # Try to detect source type
        if isinstance(source, list) and len(source) > 0:
            if hasattr(source[0], 'dtmi'):
                source_type = "dtdl"
            else:
                source_type = "rdf"
        else:
            source_type = "rdf"
    
    if source_type == "dtdl":
        return generator.generate_dtdl_report(source)
    else:
        return generator.generate_rdf_report(source)
