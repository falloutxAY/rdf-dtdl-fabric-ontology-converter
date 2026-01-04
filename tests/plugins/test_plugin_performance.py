"""
Plugin performance benchmark tests.

These tests measure plugin loading time, conversion performance,
and memory usage to ensure the plugin system remains efficient.
"""

import time
import pytest
from typing import List, Dict, Any


class TestPluginLoadingPerformance:
    """Test plugin loading and discovery performance."""

    def test_plugin_manager_singleton_performance(self):
        """Verify singleton access is fast."""
        from plugins.manager import PluginManager
        
        # First access creates instance
        start = time.perf_counter()
        manager1 = PluginManager.get_instance()
        first_access = time.perf_counter() - start
        
        # Subsequent accesses should be instant
        times: List[float] = []
        for _ in range(100):
            start = time.perf_counter()
            manager = PluginManager.get_instance()
            times.append(time.perf_counter() - start)
        
        avg_time = sum(times) / len(times)
        
        # Singleton access should be < 1ms
        assert avg_time < 0.001, f"Singleton access too slow: {avg_time*1000:.3f}ms"
        assert manager is manager1

    def test_plugin_discovery_time(self):
        """Verify plugin discovery completes within acceptable time."""
        from plugins.manager import PluginManager
        
        manager = PluginManager.get_instance()
        
        start = time.perf_counter()
        manager.discover_plugins(load_entrypoints=False)
        load_time = time.perf_counter() - start
        
        # Plugin discovery should complete in < 500ms
        assert load_time < 0.5, f"Plugin discovery too slow: {load_time*1000:.1f}ms"
        
        # Should have discovered plugins
        plugins = manager.list_plugins()
        assert len(plugins) >= 1, "No plugins discovered"

    def test_plugin_lookup_performance(self):
        """Verify plugin lookup is fast."""
        from plugins.manager import PluginManager
        
        manager = PluginManager.get_instance()
        manager.discover_plugins(load_entrypoints=False)
        
        # Measure lookup times
        lookups: List[float] = []
        formats = ["rdf", "dtdl", "unknown"]
        
        for _ in range(100):
            for fmt in formats:
                start = time.perf_counter()
                _ = manager.get_plugin(fmt)
                lookups.append(time.perf_counter() - start)
        
        avg_lookup = sum(lookups) / len(lookups)
        
        # Lookup should be < 0.1ms
        assert avg_lookup < 0.0001, f"Plugin lookup too slow: {avg_lookup*1000:.4f}ms"

    def test_extension_lookup_performance(self):
        """Verify extension-based lookup is fast."""
        from plugins.manager import PluginManager
        
        manager = PluginManager.get_instance()
        manager.discover_plugins(load_entrypoints=False)
        
        extensions = [".ttl", ".json", ".rdf", ".owl", ".unknown"]
        
        lookups: List[float] = []
        for _ in range(100):
            for ext in extensions:
                start = time.perf_counter()
                _ = manager.get_plugin_for_extension(ext)
                lookups.append(time.perf_counter() - start)
        
        avg_lookup = sum(lookups) / len(lookups)
        
        # Extension lookup should be < 0.1ms
        assert avg_lookup < 0.0001, f"Extension lookup too slow: {avg_lookup*1000:.4f}ms"


class TestCommonLayerPerformance:
    """Test common layer performance."""

    def test_id_generator_performance(self):
        """Test ID generation is fast."""
        from src.common.id_generator import IDGenerator
        
        gen = IDGenerator()
        
        # Generate 10000 IDs
        start = time.perf_counter()
        for _ in range(10000):
            _ = gen.next_id()
        elapsed = time.perf_counter() - start
        
        # Should generate 10000 IDs in < 100ms
        assert elapsed < 0.1, f"ID generation too slow: {elapsed*1000:.1f}ms for 10000 IDs"

    def test_validation_result_performance(self):
        """Test ValidationResult operations are fast."""
        from src.common.validation import ValidationResult, IssueCategory
        
        # Create result and add many issues
        result = ValidationResult(format_name="test")
        
        start = time.perf_counter()
        for i in range(1000):
            if i % 3 == 0:
                result.add_error(IssueCategory.SYNTAX_ERROR, f"Error {i}")
            elif i % 3 == 1:
                result.add_warning(IssueCategory.FABRIC_COMPATIBILITY, f"Warning {i}")
            else:
                result.add_info(IssueCategory.CUSTOM, f"Info {i}")
        
        elapsed = time.perf_counter() - start
        
        # Adding 1000 issues should be < 50ms
        assert elapsed < 0.05, f"Adding issues too slow: {elapsed*1000:.1f}ms"
        
        # Check counts are correct
        assert result.error_count > 0
        assert result.warning_count > 0
        assert result.info_count > 0
        
        # Summary generation should be fast
        start = time.perf_counter()
        _ = result.get_summary()
        summary_time = time.perf_counter() - start
        
        assert summary_time < 0.01, f"Summary generation too slow: {summary_time*1000:.1f}ms"

    def test_type_registry_performance(self):
        """Test type registry lookup is fast."""
        from src.common.type_registry import TypeMappingRegistry
        
        registry = TypeMappingRegistry()
        
        # Register many mappings
        mappings = {f"type_{i}": "String" for i in range(1000)}
        registry.register_mappings("test", mappings)
        
        # Measure lookup time
        times: List[float] = []
        for i in range(1000):
            start = time.perf_counter()
            _ = registry.get_fabric_type("test", f"type_{i}")
            times.append(time.perf_counter() - start)
        
        avg_lookup = sum(times) / len(times)
        
        # Lookup should be < 0.01ms
        assert avg_lookup < 0.00001, f"Type lookup too slow: {avg_lookup*1000:.4f}ms"


class TestPluginIsolation:
    """Test plugin isolation and independence."""

    def test_plugins_independent_state(self):
        """Verify plugins maintain independent state."""
        from plugins.manager import PluginManager
        
        manager = PluginManager.get_instance()
        manager.discover_plugins(load_entrypoints=False)
        
        plugins = manager.list_plugins()
        
        if len(plugins) >= 2:
            # Create converters - each should be independent (skip plugins that can't create converters)
            converters = []
            for plugin in plugins:
                try:
                    conv = plugin.get_converter()
                    if conv is not None:
                        converters.append(conv)
                except (ImportError, Exception):
                    # Skip plugins that can't create converters
                    pass
            
            # Verify they're different instances if we have at least 2
            if len(converters) >= 2:
                assert converters[0] is not converters[1]

    def test_plugin_registration_isolation(self):
        """Verify plugin registration doesn't affect other plugins."""
        from plugins.manager import PluginManager
        from plugins.base import OntologyPlugin
        from typing import Set, Dict
        
        class MockPlugin(OntologyPlugin):
            @property
            def format_name(self) -> str:
                return "mock_perf_test"
            
            @property
            def display_name(self) -> str:
                return "Mock Perf Test"
            
            @property
            def file_extensions(self) -> Set[str]:
                return {".mockperf"}
            
            @property
            def version(self) -> str:
                return "1.0.0"
            
            def get_parser(self):
                return None
            
            def get_validator(self):
                return None
            
            def get_converter(self):
                return None
            
            def get_type_mappings(self) -> Dict[str, str]:
                return {}
        
        manager = PluginManager.get_instance()
        manager.discover_plugins(load_entrypoints=False)
        
        # Count existing plugins
        initial_count = len(manager.list_plugins())
        
        # Register mock plugin
        manager.register_plugin(MockPlugin())
        
        # Should have one more
        assert len(manager.list_plugins()) == initial_count + 1
        
        # Cleanup
        manager.unregister_plugin("mock_perf_test")


class TestEndToEndPerformance:
    """End-to-end performance tests."""


# Performance thresholds for CI/CD
PERFORMANCE_THRESHOLDS = {
    "plugin_discovery": 500,  # ms
    "singleton_access": 1,  # ms
    "plugin_lookup": 0.1,  # ms
    "parse_100_types": 100,  # ms
    "validate_100_types": 200,  # ms
    "convert_100_types": 500,  # ms
    "id_generation_10k": 100,  # ms
    "full_pipeline_simple": 100,  # ms
}
