"""Integration tests for DTDL to Fabric conversion pipeline.

These tests verify the complete DTDL conversion workflow using sample models.
They do NOT require a live Fabric connection - they test the conversion logic only.
"""

import json
import pytest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLES_DTDL_DIR = ROOT_DIR / "samples" / "dtdl"

from src.dtdl import DTDLParser, DTDLValidator, DTDLToFabricConverter


class TestDTDLConversionPipeline:
    """Test end-to-end DTDL conversion workflows."""

    @pytest.fixture
    def dtdl_samples_dir(self) -> Path:
        """Get the DTDL samples directory path."""
        return SAMPLES_DTDL_DIR

    @pytest.fixture
    def parser(self) -> DTDLParser:
        """Create a DTDL parser instance."""
        return DTDLParser()

    @pytest.fixture
    def validator(self) -> DTDLValidator:
        """Create a DTDL validator instance."""
        return DTDLValidator(allow_external_references=True)

    @pytest.fixture
    def converter(self) -> DTDLToFabricConverter:
        """Create a DTDL to Fabric converter instance."""
        return DTDLToFabricConverter(namespace="usertypes")

    def test_thermostat_model_conversion(
        self, dtdl_samples_dir: Path, parser: DTDLParser, converter: DTDLToFabricConverter
    ):
        """Test converting the thermostat DTDL model."""
        model_path = dtdl_samples_dir / "thermostat.json"
        if not model_path.exists():
            pytest.skip("Thermostat model not found")

        # Parse
        parse_result = parser.parse_file(str(model_path))
        assert parse_result.success, f"Parse failed: {parse_result.errors}"
        assert len(parse_result.interfaces) > 0

        # Convert
        result = converter.convert(parse_result.interfaces)
        assert len(result.entity_types) > 0

        # Verify entity structure
        for entity in result.entity_types:
            assert entity.id
            assert entity.name
            assert entity.namespace == "usertypes"

    def test_factory_models_conversion(
        self, dtdl_samples_dir: Path, parser: DTDLParser, converter: DTDLToFabricConverter
    ):
        """Test converting factory-related DTDL models."""
        factory_models = ["factory.json", "machine.json", "product.json", "production_line.json"]
        interfaces = []

        for model_name in factory_models:
            model_path = dtdl_samples_dir / model_name
            if model_path.exists():
                parse_result = parser.parse_file(str(model_path))
                if parse_result.success:
                    interfaces.extend(parse_result.interfaces)

        if not interfaces:
            pytest.skip("No factory models found")

        # Convert all interfaces together
        result = converter.convert(interfaces)

        # Verify conversions
        assert len(result.entity_types) > 0
        entity_names = [e.name for e in result.entity_types]

        # Verify some expected entities exist
        # (Names may vary based on model definitions)
        assert len(entity_names) > 0

    def test_directory_parsing(
        self, dtdl_samples_dir: Path, parser: DTDLParser, converter: DTDLToFabricConverter
    ):
        """Test parsing an entire directory of DTDL files."""
        if not dtdl_samples_dir.exists():
            pytest.skip("DTDL samples directory not found")

        parse_result = parser.parse_directory(str(dtdl_samples_dir), recursive=False)
        assert parse_result.success or len(parse_result.interfaces) > 0

        if parse_result.interfaces:
            result = converter.convert(parse_result.interfaces)
            assert len(result.entity_types) >= len(parse_result.interfaces)

    def test_validation_before_conversion(
        self, dtdl_samples_dir: Path, parser: DTDLParser, validator: DTDLValidator
    ):
        """Test that validation passes before conversion."""
        model_path = dtdl_samples_dir / "thermostat.json"
        if not model_path.exists():
            pytest.skip("Thermostat model not found")

        # Parse
        parse_result = parser.parse_file(str(model_path))
        assert parse_result.success

        # Validate
        validation_result = validator.validate(parse_result.interfaces)

        # With allow_external_references=True, should pass
        assert validation_result.is_valid, f"Validation failed: {validation_result.errors}"

    def test_fabric_definition_output(
        self, dtdl_samples_dir: Path, parser: DTDLParser, converter: DTDLToFabricConverter
    ):
        """Test that output matches Fabric definition format."""
        model_path = dtdl_samples_dir / "thermostat.json"
        if not model_path.exists():
            pytest.skip("Thermostat model not found")

        parse_result = parser.parse_file(str(model_path))
        result = converter.convert(parse_result.interfaces)

        # Convert to Fabric definition (API format with parts)
        definition = converter.to_fabric_definition(result, "test_ontology")

        # Verify API structure - parts format
        assert "parts" in definition
        assert isinstance(definition["parts"], list)
        assert len(definition["parts"]) > 0  # At least platform file

        # Verify result has entity types
        assert len(result.entity_types) > 0

        # Verify JSON serializable
        json_str = json.dumps(definition)
        parsed = json.loads(json_str)
        assert parsed == definition

    def test_relationship_extraction(
        self, dtdl_samples_dir: Path, parser: DTDLParser, converter: DTDLToFabricConverter
    ):
        """Test that DTDL relationships are converted to Fabric relationships."""
        # Parse all models to get relationships
        parse_result = parser.parse_directory(str(dtdl_samples_dir), recursive=False)
        if not parse_result.interfaces:
            pytest.skip("No DTDL models found")

        result = converter.convert(parse_result.interfaces)

        # If there are relationships in DTDL, they should be converted
        for rel in result.relationship_types:
            assert rel.id
            assert rel.name
            assert rel.source is not None
            assert rel.target is not None

    def test_property_type_mapping(
        self, dtdl_samples_dir: Path, parser: DTDLParser, converter: DTDLToFabricConverter
    ):
        """Test that DTDL property types are mapped correctly."""
        model_path = dtdl_samples_dir / "thermostat.json"
        if not model_path.exists():
            pytest.skip("Thermostat model not found")

        parse_result = parser.parse_file(str(model_path))
        result = converter.convert(parse_result.interfaces)

        # Verify properties exist and have valid types
        for entity in result.entity_types:
            for prop in entity.properties + entity.timeseriesProperties:
                assert prop.valueType in [
                    "String", "Boolean", "BigInt", "Double", "DateTime"
                ], f"Invalid type: {prop.valueType}"

    def test_all_dtdl_samples_convert_without_crash(
        self, dtdl_samples_dir: Path, parser: DTDLParser, converter: DTDLToFabricConverter
    ):
        """Smoke test: verify all DTDL sample files convert without crashing."""
        if not dtdl_samples_dir.exists():
            pytest.skip("DTDL samples directory not found")

        json_files = list(dtdl_samples_dir.glob("*.json"))

        for json_file in json_files:
            try:
                parse_result = parser.parse_file(str(json_file))
                if parse_result.success and parse_result.interfaces:
                    result = converter.convert(parse_result.interfaces)
                    assert result is not None, f"Conversion returned None: {json_file.name}"
            except Exception as e:
                pytest.fail(f"Conversion crashed for {json_file.name}: {e}")

    def test_conversion_result_to_dict(
        self, dtdl_samples_dir: Path, parser: DTDLParser, converter: DTDLToFabricConverter
    ):
        """Test ConversionResult attributes and methods."""
        model_path = dtdl_samples_dir / "thermostat.json"
        if not model_path.exists():
            pytest.skip("Thermostat model not found")

        parse_result = parser.parse_file(str(model_path))
        result = converter.convert(parse_result.interfaces)

        # ConversionResult from DTDL converter uses shared model
        # Verify it has the expected attributes
        assert hasattr(result, "entity_types")
        assert hasattr(result, "relationship_types")
        assert hasattr(result, "skipped_items")
        assert hasattr(result, "warnings")
        assert hasattr(result, "success_rate")

        # Verify entity types are present
        assert len(result.entity_types) > 0

        # If to_dict exists, verify its structure (may have different key names)
        if hasattr(result, "to_dict"):
            result_dict = result.to_dict()
            # Accept either entity_types or entity_types_count
            has_entity_info = ("entity_types" in result_dict or 
                              "entity_types_count" in result_dict)
            assert has_entity_info, f"Missing entity info, got keys: {result_dict.keys()}"
