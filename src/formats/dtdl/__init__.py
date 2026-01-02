"""
DTDL (Digital Twins Definition Language) Format Support Package

This package provides comprehensive support for DTDL v2, v3, and v4 formats,
including parsing, validation, and conversion to Microsoft Fabric Ontology.

Components:
- parser: DTDLParser for parsing DTDL JSON/JSON-LD files
- validator: DTDLValidator for validating DTDL structure
- converter: DTDLToFabricConverter for converting to Fabric Ontology
- models: Data classes for DTDL interfaces, properties, etc.
- type_mapper: DTDL schema to Fabric type mapping
- cli: DTDL-specific CLI commands

DTDL Version Support:
- v2: Basic interfaces, properties, telemetry, commands
- v3: Extended semantic types, unit support
- v4: New primitives (byte, uuid, etc.), scaledDecimal, geospatial types,
      extended limits (12 inheritance levels, 8 complex schema depth)

Usage:
    from src.formats.dtdl import (
        DTDLParser,
        DTDLValidator,
        DTDLToFabricConverter,
    )
    
    # Parse DTDL files
    parser = DTDLParser()
    result = parser.parse_directory("./models/", recursive=True)
    
    # Validate DTDL interfaces
    validator = DTDLValidator()
    errors = validator.validate(result.interfaces)
    
    # Convert to Fabric format
    converter = DTDLToFabricConverter()
    fabric_result = converter.convert(result.interfaces)
"""

# Import main classes - these re-export from the legacy dtdl module for backward compatibility
try:
    # When imported as part of src package
    from ...dtdl import (
        # Models
        DTDLInterface,
        DTDLProperty,
        DTDLTelemetry,
        DTDLRelationship,
        DTDLComponent,
        DTDLCommand,
        DTDLCommandPayload,
        DTDLEnum,
        DTDLEnumValue,
        DTDLObject,
        DTDLArray,
        DTDLMap,
        DTDLContext,
        DTDLScaledDecimal,
        DTDLPrimitiveSchema,
        # Schema DTMIs
        GEOSPATIAL_SCHEMA_DTMIS,
        SCALED_DECIMAL_SCHEMA_DTMI,
        # Core classes
        DTDLParser,
        DTDLValidator,
        DTDLValidationError,
        DTDLToFabricConverter,
        DTDL_TO_FABRIC_TYPE,
        # Converter modes
        ComponentMode,
        CommandMode,
        ScaledDecimalMode,
        ScaledDecimalValue,
        # Type Mapper
        DTDLTypeMapper,
        TypeMappingResult,
        FabricValueType,
        PRIMITIVE_TYPE_MAP,
        flatten_object_fields,
        get_semantic_type_info,
    )
except ImportError:
    # When imported directly or in different context
    from src.dtdl import (
        # Models
        DTDLInterface,
        DTDLProperty,
        DTDLTelemetry,
        DTDLRelationship,
        DTDLComponent,
        DTDLCommand,
        DTDLCommandPayload,
        DTDLEnum,
        DTDLEnumValue,
        DTDLObject,
        DTDLArray,
        DTDLMap,
        DTDLContext,
        DTDLScaledDecimal,
        DTDLPrimitiveSchema,
        # Schema DTMIs
        GEOSPATIAL_SCHEMA_DTMIS,
        SCALED_DECIMAL_SCHEMA_DTMI,
        # Core classes
        DTDLParser,
        DTDLValidator,
        DTDLValidationError,
        DTDLToFabricConverter,
        DTDL_TO_FABRIC_TYPE,
        # Converter modes
        ComponentMode,
        CommandMode,
        ScaledDecimalMode,
        ScaledDecimalValue,
        # Type Mapper
        DTDLTypeMapper,
        TypeMappingResult,
        FabricValueType,
        PRIMITIVE_TYPE_MAP,
        flatten_object_fields,
        get_semantic_type_info,
    )


__all__ = [
    # Models
    'DTDLInterface',
    'DTDLProperty',
    'DTDLTelemetry',
    'DTDLRelationship',
    'DTDLComponent',
    'DTDLCommand',
    'DTDLCommandPayload',
    'DTDLEnum',
    'DTDLEnumValue',
    'DTDLObject',
    'DTDLArray',
    'DTDLMap',
    'DTDLContext',
    'DTDLScaledDecimal',
    'DTDLPrimitiveSchema',
    # Schema DTMIs
    'GEOSPATIAL_SCHEMA_DTMIS',
    'SCALED_DECIMAL_SCHEMA_DTMI',
    # Core classes
    'DTDLParser',
    'DTDLValidator',
    'DTDLValidationError',
    'DTDLToFabricConverter',
    'DTDL_TO_FABRIC_TYPE',
    # Converter modes
    'ComponentMode',
    'CommandMode',
    'ScaledDecimalMode',
    'ScaledDecimalValue',
    # Type Mapper
    'DTDLTypeMapper',
    'TypeMappingResult',
    'FabricValueType',
    'PRIMITIVE_TYPE_MAP',
    'flatten_object_fields',
    'get_semantic_type_info',
]
