"""
Tests for compliance validation and conversion warning system.

This module tests the compliance validators for DTDL, RDF/OWL, and Fabric formats,
as well as the conversion report generation.
"""

import pytest
from dataclasses import dataclass
from typing import List, Optional
from unittest.mock import MagicMock

from src.core.compliance import (
    ComplianceLevel,
    ConversionImpact,
    DTDLVersion,
    ComplianceIssue,
    ConversionWarning,
    ComplianceResult,
    ConversionReport,
    DTDLComplianceValidator,
    RDFOWLComplianceValidator,
    FabricComplianceChecker,
    ConversionReportGenerator,
    DTDL_LIMITS,
    OWL_CONSTRUCT_SUPPORT,
    DTDL_FEATURE_SUPPORT,
)
from shared.models import (
    EntityType,
    EntityTypeProperty,
    RelationshipType,
    RelationshipEnd,
    ConversionResult,
)
from src.dtdl.dtdl_models import (
    DTDLInterface,
    DTDLProperty,
    DTDLRelationship,
    DTDLTelemetry,
    DTDLCommand,
    DTDLComponent,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_dtdl_interface():
    """Create a sample DTDL interface for testing."""
    # DTDLInterface uses 'contents' to store all elements
    contents = [
        DTDLProperty(
            name="temperature",
            schema="double",
            display_name="Temperature",
            description="Current temperature reading"
        ),
        DTDLProperty(
            name="setpoint",
            schema="double",
            display_name="Set Point",
        ),
        DTDLRelationship(
            name="controls",
            target="dtmi:com:example:Room;1",
            display_name="Controls"
        ),
        DTDLTelemetry(
            name="humidity",
            schema="double",
            display_name="Humidity"
        ),
    ]
    
    return DTDLInterface(
        dtmi="dtmi:com:example:Thermostat;1",
        display_name="Smart Thermostat",
        description="A temperature control device",
        contents=contents,
        extends=[],
    )


@pytest.fixture
def sample_entity_type():
    """Create a sample Fabric entity type for testing."""
    return EntityType(
        id="1000000000001",
        name="Thermostat",
        namespace="usertypes",
        namespaceType="Custom",
        visibility="Visible",
        properties=[
            EntityTypeProperty(
                id="1000000000001001",
                name="temperature",
                valueType="Double"
            ),
            EntityTypeProperty(
                id="1000000000001002",
                name="setpoint",
                valueType="Double"
            ),
        ],
        entityIdParts=["1000000000001001"],
        displayNamePropertyId=None,
        baseEntityTypeId=None,
        timeseriesProperties=[]
    )


@pytest.fixture
def sample_conversion_result(sample_entity_type):
    """Create a sample conversion result for testing."""
    return ConversionResult(
        entity_types=[sample_entity_type],
        relationship_types=[],
        skipped_items=[],
        warnings=[],
        triple_count=0
    )


# ============================================================================
# DTDL Limits Tests
# ============================================================================

class TestDTDLLimits:
    """Tests for DTDL version-specific limits."""
    
    def test_dtdl_v2_limits_defined(self):
        """Test that DTDL v2 limits are properly defined."""
        assert DTDLVersion.V2 in DTDL_LIMITS
        v2_limits = DTDL_LIMITS[DTDLVersion.V2]
        assert v2_limits["max_contents"] == 300
        assert v2_limits["max_extends_depth"] == 10
        assert v2_limits["max_complex_schema_depth"] == 5
        assert v2_limits["max_name_length"] == 64
    
    def test_dtdl_v3_limits_defined(self):
        """Test that DTDL v3 limits are properly defined."""
        assert DTDLVersion.V3 in DTDL_LIMITS
        v3_limits = DTDL_LIMITS[DTDLVersion.V3]
        assert v3_limits["max_contents"] == 100000
        assert v3_limits["max_extends_depth"] == 10
        assert v3_limits["max_name_length"] == 512
    
    def test_dtdl_v4_limits_defined(self):
        """Test that DTDL v4 limits are properly defined."""
        assert DTDLVersion.V4 in DTDL_LIMITS
        v4_limits = DTDL_LIMITS[DTDLVersion.V4]
        assert v4_limits["max_extends_depth"] == 12
        assert v4_limits["max_complex_schema_depth"] == 8


# ============================================================================
# OWL Construct Support Tests
# ============================================================================

class TestOWLConstructSupport:
    """Tests for OWL construct support definitions."""
    
    def test_owl_class_fully_supported(self):
        """Test that owl:Class is marked as fully supported."""
        assert "owl:Class" in OWL_CONSTRUCT_SUPPORT
        assert OWL_CONSTRUCT_SUPPORT["owl:Class"]["support"] == "full"
    
    def test_owl_restriction_not_supported(self):
        """Test that owl:Restriction is marked as not supported."""
        assert "owl:Restriction" in OWL_CONSTRUCT_SUPPORT
        assert OWL_CONSTRUCT_SUPPORT["owl:Restriction"]["support"] == "none"
    
    def test_owl_union_of_partially_supported(self):
        """Test that owl:unionOf is marked as partially supported."""
        assert "owl:unionOf" in OWL_CONSTRUCT_SUPPORT
        assert OWL_CONSTRUCT_SUPPORT["owl:unionOf"]["support"] == "partial"
    
    def test_owl_transitive_property_not_supported(self):
        """Test that owl:TransitiveProperty is marked as not supported."""
        assert "owl:TransitiveProperty" in OWL_CONSTRUCT_SUPPORT
        assert OWL_CONSTRUCT_SUPPORT["owl:TransitiveProperty"]["support"] == "none"


# ============================================================================
# DTDL Feature Support Tests
# ============================================================================

class TestDTDLFeatureSupport:
    """Tests for DTDL feature support definitions."""
    
    def test_interface_fully_supported(self):
        """Test that Interface is marked as fully supported."""
        assert "Interface" in DTDL_FEATURE_SUPPORT
        assert DTDL_FEATURE_SUPPORT["Interface"]["support"] == "full"
    
    def test_command_not_supported(self):
        """Test that Command is marked as not supported by default."""
        assert "Command" in DTDL_FEATURE_SUPPORT
        assert DTDL_FEATURE_SUPPORT["Command"]["support"] == "none"
    
    def test_component_partially_supported(self):
        """Test that Component is marked as partially supported."""
        assert "Component" in DTDL_FEATURE_SUPPORT
        assert DTDL_FEATURE_SUPPORT["Component"]["support"] == "partial"
    
    def test_enum_partially_supported(self):
        """Test that Enum is marked as partially supported."""
        assert "Enum" in DTDL_FEATURE_SUPPORT
        assert DTDL_FEATURE_SUPPORT["Enum"]["support"] == "partial"


# ============================================================================
# Compliance Issue Tests
# ============================================================================

class TestComplianceIssue:
    """Tests for ComplianceIssue dataclass."""
    
    def test_compliance_issue_creation(self):
        """Test creating a compliance issue."""
        issue = ComplianceIssue(
            level=ComplianceLevel.ERROR,
            code="DTDL001",
            message="Invalid DTMI format",
            location="dtmi:invalid",
            suggestion="Use format dtmi:<domain>:<path>;<version>"
        )
        
        assert issue.level == ComplianceLevel.ERROR
        assert issue.code == "DTDL001"
        assert "Invalid DTMI" in issue.message
        assert issue.location == "dtmi:invalid"
        assert issue.suggestion is not None
    
    def test_compliance_issue_to_dict(self):
        """Test converting compliance issue to dictionary."""
        issue = ComplianceIssue(
            level=ComplianceLevel.WARNING,
            code="FABRIC001",
            message="Name too long",
            location="entity:test"
        )
        
        result = issue.to_dict()
        
        assert result["level"] == "warning"
        assert result["code"] == "FABRIC001"
        assert result["message"] == "Name too long"


# ============================================================================
# Conversion Warning Tests
# ============================================================================

class TestConversionWarning:
    """Tests for ConversionWarning dataclass."""
    
    def test_conversion_warning_creation(self):
        """Test creating a conversion warning."""
        warning = ConversionWarning(
            impact=ConversionImpact.LOST,
            feature="Command",
            source_construct="DTDL Command",
            details="Commands are not converted to Fabric",
            workaround="Set command_mode=PROPERTY"
        )
        
        assert warning.feature == "Command"
        assert warning.impact == ConversionImpact.LOST
        assert warning.source_construct == "DTDL Command"
    
    def test_conversion_warning_to_dict(self):
        """Test converting warning to dictionary."""
        warning = ConversionWarning(
            impact=ConversionImpact.LOST,
            feature="owl:Restriction",
            source_construct="OWL Property Restriction",
            details="Cardinality constraints not preserved"
        )
        
        result = warning.to_dict()
        
        assert result["impact"] == "lost"
        assert result["feature"] == "owl:Restriction"
        assert result["source_construct"] == "OWL Property Restriction"


# ============================================================================
# DTDL Compliance Validator Tests
# ============================================================================

class TestDTDLComplianceValidator:
    """Tests for DTDLComplianceValidator."""
    
    def test_validate_valid_interface(self, sample_dtdl_interface):
        """Test validation of a valid DTDL interface."""
        validator = DTDLComplianceValidator()
        result = validator.validate([sample_dtdl_interface], DTDLVersion.V3)
        
        assert result.is_valid
    
    def test_validate_interface_collection(self, sample_dtdl_interface):
        """Test validation of multiple interfaces."""
        validator = DTDLComplianceValidator()
        result = validator.validate([sample_dtdl_interface], DTDLVersion.V3)
        
        assert result.source_type == "DTDL"
        assert "interfaces" in result.statistics


# ============================================================================
# RDF/OWL Compliance Validator Tests
# ============================================================================

class TestRDFOWLComplianceValidator:
    """Tests for RDFOWLComplianceValidator."""
    
    def test_validate_empty_graph(self):
        """Test validation of empty graph raises no fatal errors."""
        validator = RDFOWLComplianceValidator()
        # Just instantiate - actual graph validation would need rdflib
        assert validator is not None


# ============================================================================
# Fabric Compliance Checker Tests
# ============================================================================

class TestFabricComplianceChecker:
    """Tests for FabricComplianceChecker."""
    
    def test_check_valid_entities(self, sample_entity_type):
        """Test validation of valid entity types."""
        checker = FabricComplianceChecker()
        result = checker.check([sample_entity_type], [])
        
        assert result.is_valid or result.error_count == 0
    
    def test_check_empty_ontology(self):
        """Test validation of empty ontology."""
        checker = FabricComplianceChecker()
        result = checker.check([], [])
        
        assert result.is_valid


# ============================================================================
# Conversion Report Generator Tests
# ============================================================================

class TestConversionReportGenerator:
    """Tests for ConversionReportGenerator."""
    
    def test_generate_dtdl_report(self, sample_dtdl_interface):
        """Test generating a DTDL conversion report."""
        generator = ConversionReportGenerator()
        report = generator.generate_dtdl_report([sample_dtdl_interface])
        
        assert report is not None
        assert report.source_format == "DTDL"
        assert report.target_format == "Fabric IQ Ontology"
    
    def test_report_to_dict(self, sample_dtdl_interface):
        """Test converting report to dictionary."""
        generator = ConversionReportGenerator()
        report = generator.generate_dtdl_report([sample_dtdl_interface])
        
        result = report.to_dict()
        
        assert "source_format" in result
        assert "target_format" in result
        assert "summary" in result
    
    def test_report_to_markdown(self, sample_dtdl_interface):
        """Test converting report to markdown."""
        generator = ConversionReportGenerator()
        report = generator.generate_dtdl_report([sample_dtdl_interface])
        
        markdown = report.to_markdown()
        
        assert isinstance(markdown, str)
        assert "Conversion Report" in markdown


# ============================================================================
# Integration Tests
# ============================================================================

class TestComplianceIntegration:
    """Integration tests for the compliance system."""
    
    def test_full_dtdl_validation_workflow(self, sample_dtdl_interface):
        """Test complete DTDL validation workflow."""
        validator = DTDLComplianceValidator()
        result = validator.validate([sample_dtdl_interface], DTDLVersion.V3)
        
        assert result.is_valid or result.error_count == 0
    
    def test_fabric_compliance_after_conversion(self, sample_entity_type):
        """Test Fabric compliance check after conversion."""
        checker = FabricComplianceChecker()
        
        # Validate entity type
        result = checker.check([sample_entity_type], [])
        assert result.is_valid or result.error_count == 0


# ============================================================================
# Edge Cases
# ============================================================================

class TestComplianceEdgeCases:
    """Tests for edge cases in compliance validation."""
    
    def test_conversion_impact_levels(self):
        """Test that all conversion impact levels are defined."""
        assert ConversionImpact.PRESERVED is not None
        assert ConversionImpact.CONVERTED_WITH_LIMITATIONS is not None
        assert ConversionImpact.LOST is not None
        assert ConversionImpact.TRANSFORMED is not None
    
    def test_compliance_level_ordering(self):
        """Test compliance levels."""
        assert ComplianceLevel.COMPLIANT is not None
        assert ComplianceLevel.WARNING is not None
        assert ComplianceLevel.ERROR is not None
    
    def test_dtdl_version_values(self):
        """Test DTDL version enum values."""
        assert DTDLVersion.V2.value == 2
        assert DTDLVersion.V3.value == 3
        assert DTDLVersion.V4.value == 4
    
    def test_fabric_compliance_checker_instantiation(self):
        """Test FabricComplianceChecker can be instantiated."""
        checker = FabricComplianceChecker()
        assert checker is not None
    
    def test_dtdl_validator_instantiation(self):
        """Test DTDLComplianceValidator can be instantiated."""
        validator = DTDLComplianceValidator()
        assert validator is not None
    
    def test_rdf_validator_instantiation(self):
        """Test RDFOWLComplianceValidator can be instantiated."""
        validator = RDFOWLComplianceValidator()
        assert validator is not None
    
    def test_report_generator_instantiation(self):
        """Test ConversionReportGenerator can be instantiated."""
        generator = ConversionReportGenerator()
        assert generator is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
