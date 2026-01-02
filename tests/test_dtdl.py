"""
Tests for DTDL Import Module

Tests cover:
- Parsing single files and directories
- Validation of DTDL structure
- Conversion to Fabric Ontology format
- Type mapping
"""

import json
import pytest
import tempfile
from pathlib import Path

from src.dtdl import (
    DTDLParser,
    DTDLValidator,
    DTDLToFabricConverter,
    DTDLTypeMapper,
    DTDLInterface,
    DTDLProperty,
    DTDLTelemetry,
    DTDLRelationship,
    DTDLEnum,
    DTDLEnumValue,
    DTDLObject,
    DTDLArray,
    FabricValueType,
)


class TestDTDLParser:
    """Tests for DTDL parsing functionality."""
    
    @pytest.fixture
    def parser(self):
        return DTDLParser()
    
    @pytest.fixture
    def simple_interface_json(self):
        return {
            "@context": "dtmi:dtdl:context;4",
            "@id": "dtmi:com:example:Thermostat;1",
            "@type": "Interface",
            "displayName": "Thermostat",
            "contents": [
                {
                    "@type": "Property",
                    "name": "targetTemperature",
                    "schema": "double"
                },
                {
                    "@type": "Telemetry",
                    "name": "currentTemperature",
                    "schema": "double"
                }
            ]
        }
    
    def test_parse_simple_interface(self, parser, simple_interface_json):
        """Test parsing a simple interface JSON string."""
        json_str = json.dumps(simple_interface_json)
        result = parser.parse_string(json_str)
        
        assert len(result.interfaces) == 1
        assert len(result.errors) == 0
        
        interface = result.interfaces[0]
        assert interface.dtmi == "dtmi:com:example:Thermostat;1"
        assert interface.resolved_display_name == "Thermostat"
        assert len(interface.properties) == 1
        assert len(interface.telemetries) == 1
    
    def test_parse_interface_with_relationship(self, parser):
        """Test parsing an interface with a relationship."""
        json_data = {
            "@context": "dtmi:dtdl:context;4",
            "@id": "dtmi:com:example:Room;1",
            "@type": "Interface",
            "displayName": "Room",
            "contents": [
                {
                    "@type": "Relationship",
                    "name": "hasThermostat",
                    "target": "dtmi:com:example:Thermostat;1"
                }
            ]
        }
        
        result = parser.parse_string(json.dumps(json_data))
        
        assert len(result.interfaces) == 1
        interface = result.interfaces[0]
        assert len(interface.relationships) == 1
        
        rel = interface.relationships[0]
        assert rel.name == "hasThermostat"
        assert rel.target == "dtmi:com:example:Thermostat;1"
    
    def test_parse_interface_with_enum(self, parser):
        """Test parsing an interface with enum schema."""
        json_data = {
            "@context": "dtmi:dtdl:context;4",
            "@id": "dtmi:com:example:Device;1",
            "@type": "Interface",
            "contents": [
                {
                    "@type": "Property",
                    "name": "status",
                    "schema": {
                        "@type": "Enum",
                        "valueSchema": "string",
                        "enumValues": [
                            {"name": "online", "enumValue": "ONLINE"},
                            {"name": "offline", "enumValue": "OFFLINE"}
                        ]
                    }
                }
            ]
        }
        
        result = parser.parse_string(json.dumps(json_data))
        
        assert len(result.interfaces) == 1
        prop = result.interfaces[0].properties[0]
        assert isinstance(prop.schema, DTDLEnum)
        assert len(prop.schema.enum_values) == 2
    
    def test_parse_file(self, parser, simple_interface_json):
        """Test parsing a DTDL file."""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False
        ) as f:
            json.dump(simple_interface_json, f)
            f.flush()
            
            result = parser.parse_file(f.name)
            
            assert len(result.interfaces) == 1
            assert result.interfaces[0].dtmi == "dtmi:com:example:Thermostat;1"
    
    def test_parse_directory(self, parser):
        """Test parsing a directory of DTDL files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple DTDL files
            files = [
                {
                    "@context": "dtmi:dtdl:context;4",
                    "@id": "dtmi:com:example:Device1;1",
                    "@type": "Interface",
                    "contents": []
                },
                {
                    "@context": "dtmi:dtdl:context;4",
                    "@id": "dtmi:com:example:Device2;1",
                    "@type": "Interface",
                    "contents": []
                }
            ]
            
            for i, data in enumerate(files):
                path = Path(tmpdir) / f"device{i}.json"
                with open(path, 'w') as f:
                    json.dump(data, f)
            
            result = parser.parse_directory(tmpdir)
            
            assert len(result.interfaces) == 2


class TestDTDLValidator:
    """Tests for DTDL validation functionality."""
    
    @pytest.fixture
    def validator(self):
        return DTDLValidator()
    
    def test_valid_interface(self, validator):
        """Test validation of a valid interface."""
        interface = DTDLInterface(
            dtmi="dtmi:com:example:Thermostat;1",
            type="Interface",
            display_name="Thermostat",
            contents=[
                {
                    "@type": "Property",
                    "name": "temperature",
                    "schema": "double"
                }
            ]
        )
        interface.properties = [
            DTDLProperty(name="temperature", schema="double")
        ]
        
        result = validator.validate([interface])
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_invalid_dtmi(self, validator):
        """Test validation catches invalid DTMI format."""
        interface = DTDLInterface(
            dtmi="invalid:format",  # Invalid DTMI
            type="Interface"
        )
        
        result = validator.validate([interface])
        
        assert not result.is_valid
        assert any("DTMI" in str(e.message) for e in result.errors)
    
    def test_missing_extends_reference(self, validator):
        """Test validation catches missing extends reference."""
        interface = DTDLInterface(
            dtmi="dtmi:com:example:Child;1",
            type="Interface",
            extends=["dtmi:com:example:NonExistent;1"]  # Reference doesn't exist
        )
        
        result = validator.validate([interface])
        
        # Should produce warning about unresolved reference
        assert len(result.warnings) > 0 or len(result.errors) > 0


class TestDTDLToFabricConverter:
    """Tests for DTDL to Fabric conversion functionality."""
    
    @pytest.fixture
    def converter(self):
        return DTDLToFabricConverter()
    
    def test_convert_simple_interface(self, converter):
        """Test converting a simple interface to EntityType."""
        interface = DTDLInterface(
            dtmi="dtmi:com:example:Thermostat;1",
            type="Interface",
            display_name="Thermostat"
        )
        interface.properties = [
            DTDLProperty(name="temperature", schema="double"),
            DTDLProperty(name="serialNumber", schema="string"),
        ]
        interface.telemetries = [
            DTDLTelemetry(name="currentTemp", schema="double")
        ]
        
        result = converter.convert([interface])
        
        assert len(result.entity_types) == 1
        entity = result.entity_types[0]
        
        assert entity.name == "Thermostat"
        assert len(entity.properties) == 2
        assert len(entity.timeseriesProperties) == 1
    
    def test_convert_interface_with_relationship(self, converter):
        """Test converting interfaces with relationships."""
        room = DTDLInterface(
            dtmi="dtmi:com:example:Room;1",
            type="Interface",
            display_name="Room"
        )
        room.relationships = [
            DTDLRelationship(
                name="hasThermostat",
                target="dtmi:com:example:Thermostat;1"
            )
        ]
        
        thermostat = DTDLInterface(
            dtmi="dtmi:com:example:Thermostat;1",
            type="Interface",
            display_name="Thermostat"
        )
        
        result = converter.convert([room, thermostat])
        
        assert len(result.entity_types) == 2
        assert len(result.relationship_types) == 1
        
        rel = result.relationship_types[0]
        assert rel.name == "hasThermostat"
    
    def test_convert_type_mapping(self, converter):
        """Test DTDL to Fabric type mapping."""
        interface = DTDLInterface(
            dtmi="dtmi:com:example:Test;1",
            type="Interface"
        )
        interface.properties = [
            DTDLProperty(name="boolProp", schema="boolean"),
            DTDLProperty(name="intProp", schema="integer"),
            DTDLProperty(name="doubleProp", schema="double"),
            DTDLProperty(name="stringProp", schema="string"),
            DTDLProperty(name="dateProp", schema="dateTime"),
        ]
        
        result = converter.convert([interface])
        entity = result.entity_types[0]
        
        type_map = {p.name: p.valueType for p in entity.properties}
        
        assert type_map["boolProp"] == "Boolean"
        assert type_map["intProp"] == "BigInt"
        assert type_map["doubleProp"] == "Double"
        assert type_map["stringProp"] == "String"
        assert type_map["dateProp"] == "DateTime"
    
    def test_to_fabric_definition(self, converter):
        """Test generating Fabric API definition format."""
        interface = DTDLInterface(
            dtmi="dtmi:com:example:Test;1",
            type="Interface",
            display_name="Test"
        )
        
        result = converter.convert([interface])
        definition = converter.to_fabric_definition(result, "TestOntology")
        
        assert "parts" in definition
        parts = definition["parts"]
        
        # Should have .platform, definition.json, and entity type
        assert len(parts) >= 3
        
        # Check .platform part
        platform_part = next(p for p in parts if p["path"] == ".platform")
        assert platform_part["payloadType"] == "InlineBase64"


class TestDTDLTypeMapper:
    """Tests for type mapping functionality."""
    
    @pytest.fixture
    def mapper(self):
        return DTDLTypeMapper()
    
    def test_map_primitive_types(self, mapper):
        """Test mapping primitive DTDL types to Fabric types."""
        assert mapper.map_schema("boolean").fabric_type == FabricValueType.BOOLEAN
        assert mapper.map_schema("integer").fabric_type == FabricValueType.BIG_INT
        assert mapper.map_schema("long").fabric_type == FabricValueType.BIG_INT
        assert mapper.map_schema("double").fabric_type == FabricValueType.DOUBLE
        assert mapper.map_schema("float").fabric_type == FabricValueType.DOUBLE
        assert mapper.map_schema("string").fabric_type == FabricValueType.STRING
        assert mapper.map_schema("dateTime").fabric_type == FabricValueType.DATE_TIME
    
    def test_map_enum_type(self, mapper):
        """Test mapping enum schema to Fabric type."""
        enum = DTDLEnum(
            value_schema="string",
            enum_values=[
                DTDLEnumValue(name="a", value="A"),
                DTDLEnumValue(name="b", value="B")
            ]
        )
        
        result = mapper.map_schema(enum)
        
        assert result.fabric_type == FabricValueType.STRING
        assert result.is_complex
        assert result.json_schema is not None
    
    def test_map_array_type(self, mapper):
        """Test mapping array schema to Fabric type."""
        array = DTDLArray(element_schema="integer")
        
        result = mapper.map_schema(array)
        
        assert result.fabric_type == FabricValueType.STRING  # JSON encoded
        assert result.is_complex
        assert result.is_array
    
    def test_map_with_semantic_type(self, mapper):
        """Test mapping with semantic type annotation."""
        result = mapper.map_schema(
            "double",
            semantic_type="Temperature",
            unit="degreeCelsius"
        )
        
        assert result.fabric_type == FabricValueType.DOUBLE
        assert result.semantic_type == "Temperature"
        assert result.unit == "degreeCelsius"


class TestIntegration:
    """Integration tests using sample DTDL files."""
    
    def test_parse_convert_thermostat_sample(self):
        """Test full pipeline with thermostat sample."""
        sample_path = Path(__file__).parent.parent / "samples" / "dtdl" / "thermostat.json"
        
        if not sample_path.exists():
            pytest.skip("Sample file not found")
        
        parser = DTDLParser()
        validator = DTDLValidator()
        converter = DTDLToFabricConverter()
        
        # Parse
        result = parser.parse_file(str(sample_path))
        assert len(result.interfaces) == 1
        assert len(result.errors) == 0
        
        # Validate
        validation = validator.validate(result.interfaces)
        assert validation.is_valid
        
        # Convert
        conversion = converter.convert(result.interfaces)
        assert len(conversion.entity_types) == 1
        
        entity = conversion.entity_types[0]
        assert entity.name == "Thermostat"
    
    def test_parse_convert_manufacturing_samples(self):
        """Test full pipeline with manufacturing samples."""
        samples_dir = Path(__file__).parent.parent / "samples" / "dtdl"
        
        if not samples_dir.exists():
            pytest.skip("Samples directory not found")
        
        parser = DTDLParser()
        validator = DTDLValidator()
        converter = DTDLToFabricConverter()
        
        # Parse all files
        result = parser.parse_directory(str(samples_dir))
        
        if len(result.interfaces) == 0:
            pytest.skip("No interfaces found in samples")
        
        # Validate
        validation = validator.validate(result.interfaces)
        
        # Convert
        conversion = converter.convert(result.interfaces)
        
        # Should have multiple entities and relationships
        assert len(conversion.entity_types) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
