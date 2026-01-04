"""
Tests for the plugin system infrastructure.

Tests cover:
- Plugin base class
- Plugin protocols
- Plugin manager discovery and registration
- Built-in RDF and DTDL plugins
- CLI format.py integration
"""

import pytest
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

# Import plugin system components
from src.plugins import (
    OntologyPlugin,
    PluginManager,
    get_plugin_manager,
    ParserProtocol,
    ValidatorProtocol,
    ConverterProtocol,
    ExporterProtocol,
)
from src.plugins.protocols import is_parser, is_validator, is_converter, is_exporter
from src.common import (
    TypeMappingRegistry,
    get_type_registry,
    IDGenerator,
    get_id_generator,
    ValidationResult,
    ValidationIssue,
    Severity,
    IssueCategory,
)
from src.common.id_generator import DEFAULT_PREFIX


class TestOntologyPluginBase:
    """Tests for the OntologyPlugin abstract base class."""
    
    def test_cannot_instantiate_directly(self):
        """OntologyPlugin cannot be instantiated directly."""
        with pytest.raises(TypeError):
            OntologyPlugin()
    
    def test_concrete_plugin_implementation(self):
        """Test that concrete plugin implementations work."""
        class TestPlugin(OntologyPlugin):
            @property
            def format_name(self) -> str:
                return "test"
            
            @property
            def display_name(self) -> str:
                return "Test Format"
            
            @property
            def file_extensions(self) -> Set[str]:
                return {".test"}
            
            def get_parser(self) -> Any:
                return None
            
            def get_validator(self) -> Any:
                return None
            
            def get_converter(self) -> Any:
                return None
        
        plugin = TestPlugin()
        assert plugin.format_name == "test"
        assert plugin.display_name == "Test Format"
        assert plugin.file_extensions == {".test"}
        assert plugin.version == "1.0.0"  # default
        assert plugin.author == "Unknown"  # default
        assert plugin.dependencies == []  # default
    
    def test_plugin_info(self):
        """Test get_info() method."""
        class TestPlugin(OntologyPlugin):
            @property
            def format_name(self) -> str:
                return "info_test"
            
            @property
            def display_name(self) -> str:
                return "Info Test Format"
            
            @property
            def file_extensions(self) -> Set[str]:
                return {".info"}
            
            @property
            def version(self) -> str:
                return "2.0.0"
            
            def get_parser(self) -> Any:
                return None
            
            def get_validator(self) -> Any:
                return None
            
            def get_converter(self) -> Any:
                return None
        
        plugin = TestPlugin()
        info = plugin.get_info()
        
        assert info["format_name"] == "info_test"
        assert info["display_name"] == "Info Test Format"
        assert info["version"] == "2.0.0"
        assert ".info" in info["file_extensions"]


class TestPluginManager:
    """Tests for the PluginManager singleton."""
    
    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """Reset plugin manager before each test."""
        PluginManager.reset_instance()
        yield
        PluginManager.reset_instance()
    
    def test_singleton_pattern(self):
        """Plugin manager follows singleton pattern."""
        manager1 = PluginManager.get_instance()
        manager2 = PluginManager.get_instance()
        assert manager1 is manager2
    
    def test_get_plugin_manager_function(self):
        """get_plugin_manager() returns singleton."""
        manager1 = get_plugin_manager()
        manager2 = PluginManager.get_instance()
        assert manager1 is manager2
    
    def test_register_plugin(self):
        """Test plugin registration."""
        class TestPlugin(OntologyPlugin):
            @property
            def format_name(self) -> str:
                return "registered"
            
            @property
            def display_name(self) -> str:
                return "Registered Plugin"
            
            @property
            def file_extensions(self) -> Set[str]:
                return {".reg"}
            
            def get_parser(self) -> Any:
                return None
            
            def get_validator(self) -> Any:
                return None
            
            def get_converter(self) -> Any:
                return None
        
        manager = PluginManager.get_instance()
        plugin = TestPlugin()
        manager.register_plugin(plugin)
        
        assert manager.has_plugin("registered")
        assert manager.get_plugin("registered") is plugin
        assert "registered" in manager.list_formats()
    
    def test_get_plugin_for_extension(self):
        """Test extension-based plugin lookup."""
        class TestPlugin(OntologyPlugin):
            @property
            def format_name(self) -> str:
                return "ext_test"
            
            @property
            def display_name(self) -> str:
                return "Extension Test"
            
            @property
            def file_extensions(self) -> Set[str]:
                return {".ext1", ".ext2"}
            
            def get_parser(self) -> Any:
                return None
            
            def get_validator(self) -> Any:
                return None
            
            def get_converter(self) -> Any:
                return None
        
        manager = PluginManager.get_instance()
        manager.register_plugin(TestPlugin())
        
        plugin1 = manager.get_plugin_for_extension(".ext1")
        plugin2 = manager.get_plugin_for_extension(".ext2")
        plugin3 = manager.get_plugin_for_extension("ext1")  # without dot
        
        assert plugin1 is not None
        assert plugin1.format_name == "ext_test"
        assert plugin2 is plugin1
        assert plugin3 is plugin1
    
    def test_get_plugin_for_file(self):
        """Test file path-based plugin lookup."""
        class TestPlugin(OntologyPlugin):
            @property
            def format_name(self) -> str:
                return "file_test"
            
            @property
            def display_name(self) -> str:
                return "File Test"
            
            @property
            def file_extensions(self) -> Set[str]:
                return {".xyz"}
            
            def get_parser(self) -> Any:
                return None
            
            def get_validator(self) -> Any:
                return None
            
            def get_converter(self) -> Any:
                return None
        
        manager = PluginManager.get_instance()
        manager.register_plugin(TestPlugin())
        
        plugin = manager.get_plugin_for_file("/path/to/file.xyz")
        assert plugin is not None
        assert plugin.format_name == "file_test"
    
    def test_require_plugin(self):
        """Test require_plugin raises on missing plugin."""
        manager = PluginManager.get_instance()
        
        with pytest.raises(ValueError) as exc_info:
            manager.require_plugin("nonexistent")
        
        assert "No plugin found for format" in str(exc_info.value)
    
    def test_unregister_plugin(self):
        """Test plugin unregistration."""
        class TestPlugin(OntologyPlugin):
            @property
            def format_name(self) -> str:
                return "unregister_test"
            
            @property
            def display_name(self) -> str:
                return "Unregister Test"
            
            @property
            def file_extensions(self) -> Set[str]:
                return {".unreg"}
            
            def get_parser(self) -> Any:
                return None
            
            def get_validator(self) -> Any:
                return None
            
            def get_converter(self) -> Any:
                return None
        
        manager = PluginManager.get_instance()
        manager.register_plugin(TestPlugin())
        
        assert manager.has_plugin("unregister_test")
        
        result = manager.unregister_plugin("unregister_test")
        assert result is True
        assert not manager.has_plugin("unregister_test")
        
        # Second unregister returns False
        result = manager.unregister_plugin("unregister_test")
        assert result is False


class TestBuiltinPlugins:
    """Tests for built-in RDF and DTDL plugins."""
    
    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """Reset plugin manager before each test."""
        PluginManager.reset_instance()
        yield
        PluginManager.reset_instance()
    
    def test_discover_builtin_plugins(self):
        """Built-in plugins are discovered."""
        manager = PluginManager.get_instance()
        count = manager.discover_plugins()
        
        assert count >= 2  # At least RDF and DTDL
        assert manager.has_plugin("rdf")
        assert manager.has_plugin("dtdl")
    
    def test_rdf_plugin_properties(self):
        """RDF plugin has correct properties."""
        manager = PluginManager.get_instance()
        manager.discover_plugins()
        
        rdf = manager.get_plugin("rdf")
        assert rdf is not None
        assert rdf.format_name == "rdf"
        assert ".ttl" in rdf.file_extensions
        assert ".rdf" in rdf.file_extensions
    
    def test_dtdl_plugin_properties(self):
        """DTDL plugin has correct properties."""
        manager = PluginManager.get_instance()
        manager.discover_plugins()
        
        dtdl = manager.get_plugin("dtdl")
        assert dtdl is not None
        assert dtdl.format_name == "dtdl"
        assert ".json" in dtdl.file_extensions
    
    def test_rdf_plugin_components(self):
        """RDF plugin provides working components."""
        manager = PluginManager.get_instance()
        manager.discover_plugins()
        
        rdf = manager.get_plugin("rdf")
        
        parser = rdf.get_parser()
        validator = rdf.get_validator()
        converter = rdf.get_converter()
        
        assert parser is not None
        assert validator is not None
        assert converter is not None
    
    def test_dtdl_plugin_components(self):
        """DTDL plugin provides working components."""
        manager = PluginManager.get_instance()
        manager.discover_plugins()
        
        dtdl = manager.get_plugin("dtdl")
        
        parser = dtdl.get_parser()
        validator = dtdl.get_validator()
        converter = dtdl.get_converter()
        
        assert parser is not None
        assert validator is not None
        assert converter is not None


class TestProtocols:
    """Tests for plugin protocols."""
    
    def test_parser_protocol_check(self):
        """Test ParserProtocol runtime checking."""
        class ValidParser:
            def parse(self, content: str, file_path=None):
                return {}
            
            def parse_file(self, file_path: str):
                return {}
        
        class InvalidParser:
            def parse_content(self, content: str):
                return {}
        
        assert is_parser(ValidParser())
        assert not is_parser(InvalidParser())
        assert not is_parser("not a parser")
    
    def test_validator_protocol_check(self):
        """Test ValidatorProtocol runtime checking."""
        class ValidValidator:
            def validate(self, content: str, file_path=None):
                return ValidationResult("test")
            
            def validate_file(self, file_path: str):
                return ValidationResult("test")
        
        assert is_validator(ValidValidator())
        assert not is_validator("not a validator")
    
    def test_converter_protocol_check(self):
        """Test ConverterProtocol runtime checking."""
        class ValidConverter:
            def convert(self, content: str, id_prefix: int = 1000000000000, **kwargs):
                return None
        
        assert is_converter(ValidConverter())
        assert not is_converter("not a converter")
    
    def test_exporter_protocol_check(self):
        """Test ExporterProtocol runtime checking."""
        class ValidExporter:
            def export(self, entity_types, relationship_types, **kwargs):
                return ""
            
            def export_to_file(self, entity_types, relationship_types, file_path, **kwargs):
                pass
        
        assert is_exporter(ValidExporter())
        assert not is_exporter("not an exporter")


class TestTypeRegistry:
    """Tests for the TypeMappingRegistry."""
    
    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        return TypeMappingRegistry()
    
    def test_register_and_retrieve_mapping(self, registry):
        """Test basic mapping registration and retrieval."""
        registry.register_mapping("test", "source_type", "String")
        
        result = registry.get_fabric_type("test", "source_type")
        assert result == "String"
    
    def test_bulk_register_mappings(self, registry):
        """Test bulk mapping registration."""
        mappings = {
            "type1": "String",
            "type2": "Boolean",
            "type3": "BigInt",
        }
        registry.register_mappings("bulk_test", mappings)
        
        assert registry.get_fabric_type("bulk_test", "type1") == "String"
        assert registry.get_fabric_type("bulk_test", "type2") == "Boolean"
        assert registry.get_fabric_type("bulk_test", "type3") == "BigInt"
    
    def test_default_type_fallback(self, registry):
        """Test default type when mapping not found."""
        result = registry.get_fabric_type("unknown", "unknown_type")
        assert result == "String"  # default
        
        result = registry.get_fabric_type("unknown", "unknown_type", default="BigInt")
        assert result == "BigInt"
    
    def test_invalid_fabric_type_raises(self, registry):
        """Test that invalid Fabric types raise error."""
        with pytest.raises(ValueError) as exc_info:
            registry.register_mapping("test", "type", "InvalidType")
        
        assert "Invalid Fabric type" in str(exc_info.value)
    
    def test_list_mappings(self, registry):
        """Test listing mappings for a format."""
        registry.register_mapping("list_test", "type1", "String")
        registry.register_mapping("list_test", "type2", "Boolean")
        
        mappings = registry.list_mappings("list_test")
        assert mappings == {"type1": "String", "type2": "Boolean"}
    
    def test_global_registry(self):
        """Test global registry singleton."""
        registry1 = get_type_registry()
        registry2 = get_type_registry()
        assert registry1 is registry2


class TestIDGenerator:
    """Tests for the IDGenerator."""
    
    @pytest.fixture
    def generator(self):
        """Create a fresh generator for each test."""
        return IDGenerator()
    
    def test_generates_13_digit_ids(self, generator):
        """Test that IDs are 13 digits."""
        id1 = generator.next_id()
        assert len(id1) == 13
        assert id1.isdigit()
    
    def test_sequential_ids(self, generator):
        """Test that IDs are sequential."""
        id1 = generator.next_id()
        id2 = generator.next_id()
        id3 = generator.next_id()
        
        assert int(id2) == int(id1) + 1
        assert int(id3) == int(id2) + 1
    
    def test_custom_prefix(self):
        """Test custom starting prefix."""
        generator = IDGenerator(prefix=2000000000000)
        
        id1 = generator.next_id()
        assert id1 == "2000000000000"
    
    def test_reset(self, generator):
        """Test reset functionality."""
        generator.next_id()
        generator.next_id()
        generator.reset()
        
        id1 = generator.next_id()
        assert id1 == str(DEFAULT_PREFIX)
    
    def test_namespace_ids(self, generator):
        """Test namespace-specific ID generation."""
        id1 = generator.next_id_for_namespace("ns1")
        id2 = generator.next_id_for_namespace("ns2")
        id3 = generator.next_id_for_namespace("ns1")
        
        # All IDs should be valid
        assert len(id1) == 13
        assert len(id2) == 13
        assert len(id3) == 13
    
    def test_global_generator(self):
        """Test global generator singleton."""
        gen1 = get_id_generator()
        gen2 = get_id_generator()
        assert gen1 is gen2


class TestValidationResult:
    """Tests for the ValidationResult model."""
    
    def test_create_valid_result(self):
        """Test creating a valid result."""
        result = ValidationResult(format_name="test")
        
        assert result.is_valid
        assert result.error_count == 0
        assert result.warning_count == 0
    
    def test_add_error_invalidates(self):
        """Test that adding error invalidates result."""
        result = ValidationResult(format_name="test")
        result.add_error(IssueCategory.SYNTAX_ERROR, "Test error")
        
        assert not result.is_valid
        assert result.error_count == 1
        assert not result.can_convert
    
    def test_add_warning_keeps_valid(self):
        """Test that warnings don't invalidate."""
        result = ValidationResult(format_name="test")
        result.add_warning(IssueCategory.UNSUPPORTED_CONSTRUCT, "Test warning")
        
        assert result.is_valid
        assert result.warning_count == 1
        assert result.can_convert
    
    def test_to_dict(self):
        """Test serialization to dict."""
        result = ValidationResult(format_name="test", source_path="/test/path")
        result.add_error(IssueCategory.SYNTAX_ERROR, "Error message")
        result.add_warning(IssueCategory.CUSTOM, "Warning message")
        
        data = result.to_dict()
        
        assert data["format"] == "test"
        assert data["source_path"] == "/test/path"
        assert data["is_valid"] is False
        assert data["summary"]["errors"] == 1
        assert data["summary"]["warnings"] == 1
        assert len(data["issues"]) == 2
    
    def test_get_summary(self):
        """Test summary generation."""
        result = ValidationResult(format_name="test")
        result.add_error(IssueCategory.SYNTAX_ERROR, "Error 1")
        result.add_warning(IssueCategory.CUSTOM, "Warning 1")
        
        summary = result.get_summary()
        
        assert "TEST" in summary or "test" in summary.lower()  # Format name in summary
        assert "Invalid" in summary or "INVALID" in summary
        assert "Error 1" in summary
    
    def test_merge_results(self):
        """Test merging validation results."""
        result1 = ValidationResult(format_name="test")
        result1.add_error(IssueCategory.SYNTAX_ERROR, "Error 1")
        
        result2 = ValidationResult(format_name="test")
        result2.add_warning(IssueCategory.CUSTOM, "Warning 1")
        
        merged = result1.merge(result2)
        
        assert merged.error_count == 1
        assert merged.warning_count == 1
        assert not merged.is_valid


class TestCLIFormatIntegration:
    """Tests for CLI format.py plugin integration."""
    
    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """Reset plugin manager and format module state before each test."""
        PluginManager.reset_instance()
        # Reset the module-level plugin manager cache in format.py
        import src.cli.format as format_module
        format_module._plugin_manager = None
        yield
        PluginManager.reset_instance()
        format_module._plugin_manager = None
    
    def test_get_validator_uses_plugin(self):
        """Test that get_validator uses plugin system."""
        from src.cli.format import Format, get_validator
        
        validator = get_validator(Format.RDF)
        assert validator is not None
    
    def test_get_converter_uses_plugin(self):
        """Test that get_converter uses plugin system."""
        from src.cli.format import Format, get_converter
        
        converter = get_converter(Format.RDF)
        assert converter is not None
    
    def test_infer_format_from_path(self):
        """Test format inference from file path."""
        from src.cli.format import infer_format_from_path, Format
        
        assert infer_format_from_path("test.ttl") == Format.RDF
        assert infer_format_from_path("test.rdf") == Format.RDF
        assert infer_format_from_path("test.json") == Format.DTDL
    
    def test_list_supported_formats(self):
        """Test listing supported formats."""
        from src.cli.format import list_supported_formats
        
        formats = list_supported_formats()
        
        # Should have at least RDF and DTDL from plugins or fallback
        assert len(formats) >= 2 or "rdf" in formats or "dtdl" in formats
    
    def test_list_supported_extensions(self):
        """Test listing supported extensions."""
        from src.cli.format import list_supported_extensions
        
        extensions = list_supported_extensions()
        
        # Should have extensions from plugins or fallback
        assert len(extensions) > 0
        assert ".ttl" in extensions or ".json" in extensions
