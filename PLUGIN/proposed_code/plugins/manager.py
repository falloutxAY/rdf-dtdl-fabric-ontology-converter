"""
Plugin Manager - Discovery, loading, and registration of plugins.

This module provides the PluginManager singleton that handles:
- Plugin discovery (built-in, entry points, directories)
- Plugin registration and lookup
- Extension-based format detection
- Plugin lifecycle management

Usage:
    from plugins.manager import PluginManager
    
    # Get manager instance
    manager = PluginManager.get_instance()
    
    # Discover and load plugins
    manager.discover_plugins()
    
    # Get a plugin by format name
    rdf_plugin = manager.get_plugin("rdf")
    
    # Get plugin for a file extension
    plugin = manager.get_plugin_for_extension(".ttl")
    
    # List all available formats
    formats = manager.list_formats()
"""

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type

from .base import OntologyPlugin

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Manages discovery, loading, and registration of ontology plugins.
    
    This is a singleton class - use get_instance() to get the manager.
    
    Supports plugin loading from:
    1. Built-in plugins (RDF, DTDL)
    2. Entry points (setuptools/pip installed packages)
    3. Custom plugin directories
    
    Example:
        >>> manager = PluginManager.get_instance()
        >>> manager.discover_plugins()
        >>> 
        >>> # Get plugin by format
        >>> rdf = manager.get_plugin("rdf")
        >>> converter = rdf.get_converter()
        >>> 
        >>> # Auto-detect format from file
        >>> plugin = manager.get_plugin_for_extension(".ttl")
        >>> validator = plugin.get_validator()
    
    Attributes:
        ENTRY_POINT_GROUP: Entry point group name for pip-installed plugins.
        PLUGIN_FILE_PATTERN: Glob pattern for plugin files in directories.
    """
    
    ENTRY_POINT_GROUP = "fabric_ontology.plugins"
    PLUGIN_FILE_PATTERN = "*_plugin.py"
    
    _instance: Optional['PluginManager'] = None
    
    def __init__(self) -> None:
        """
        Initialize the plugin manager.
        
        Note: Use get_instance() instead of creating directly.
        """
        self._plugins: Dict[str, OntologyPlugin] = {}
        self._extension_map: Dict[str, str] = {}  # extension -> format_name
        self._initialized = False
        self._callbacks: List[Callable[[OntologyPlugin], None]] = []
    
    @classmethod
    def get_instance(cls) -> 'PluginManager':
        """
        Get the singleton PluginManager instance.
        
        Returns:
            The global PluginManager instance.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset the singleton instance.
        
        Primarily for testing purposes.
        """
        if cls._instance is not None:
            cls._instance.cleanup_all()
            cls._instance = None
    
    # =========================================================================
    # Plugin Registration
    # =========================================================================
    
    def register_plugin(self, plugin: OntologyPlugin) -> None:
        """
        Register a plugin instance.
        
        Args:
            plugin: OntologyPlugin instance to register.
        
        Raises:
            ValueError: If plugin is invalid.
        """
        # Validate plugin
        if not isinstance(plugin, OntologyPlugin):
            raise ValueError(f"Expected OntologyPlugin, got {type(plugin)}")
        
        name = plugin.format_name.lower()
        
        # Check for duplicate
        if name in self._plugins:
            logger.warning(
                f"Overwriting existing plugin '{name}' "
                f"(old: {self._plugins[name].display_name}, "
                f"new: {plugin.display_name})"
            )
        
        # Check dependencies
        missing = plugin.check_dependencies()
        if missing:
            logger.warning(
                f"Plugin '{plugin.display_name}' has missing dependencies: {missing}"
            )
        
        # Initialize plugin
        try:
            plugin.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize plugin '{plugin.display_name}': {e}")
            raise
        
        # Register
        self._plugins[name] = plugin
        
        # Map extensions to format
        for ext in plugin.file_extensions:
            ext_lower = ext.lower()
            if ext_lower in self._extension_map:
                existing = self._extension_map[ext_lower]
                logger.warning(
                    f"Extension '{ext_lower}' already mapped to '{existing}', "
                    f"overwriting with '{name}'"
                )
            self._extension_map[ext_lower] = name
        
        # Register type mappings
        type_mappings = plugin.get_type_mappings()
        if type_mappings:
            try:
                from common.type_registry import get_type_registry
                registry = get_type_registry()
                registry.register_mappings(name, type_mappings)
            except ImportError:
                pass  # Type registry not available yet
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(plugin)
            except Exception as e:
                logger.warning(f"Plugin registration callback failed: {e}")
        
        logger.info(
            f"Registered plugin: {plugin.display_name} "
            f"(format={name}, version={plugin.version}, "
            f"extensions={plugin.file_extensions})"
        )
    
    def unregister_plugin(self, format_name: str) -> bool:
        """
        Unregister a plugin.
        
        Args:
            format_name: Format name of plugin to remove.
        
        Returns:
            True if plugin was removed, False if not found.
        """
        name = format_name.lower()
        if name not in self._plugins:
            return False
        
        plugin = self._plugins[name]
        
        # Cleanup
        try:
            plugin.cleanup()
        except Exception as e:
            logger.warning(f"Plugin cleanup failed: {e}")
        
        # Remove extension mappings
        for ext in plugin.file_extensions:
            ext_lower = ext.lower()
            if self._extension_map.get(ext_lower) == name:
                del self._extension_map[ext_lower]
        
        # Remove plugin
        del self._plugins[name]
        logger.info(f"Unregistered plugin: {name}")
        
        return True
    
    def on_plugin_registered(
        self,
        callback: Callable[[OntologyPlugin], None]
    ) -> None:
        """
        Register a callback for when plugins are registered.
        
        Args:
            callback: Function called with each new plugin.
        """
        self._callbacks.append(callback)
    
    # =========================================================================
    # Plugin Lookup
    # =========================================================================
    
    def get_plugin(self, format_name: str) -> Optional[OntologyPlugin]:
        """
        Get a plugin by format name.
        
        Args:
            format_name: Format identifier (e.g., "rdf", "dtdl").
        
        Returns:
            OntologyPlugin instance or None if not found.
        """
        return self._plugins.get(format_name.lower())
    
    def get_plugin_for_extension(
        self,
        extension: str
    ) -> Optional[OntologyPlugin]:
        """
        Get the plugin that handles a file extension.
        
        Args:
            extension: File extension (with or without leading dot).
        
        Returns:
            OntologyPlugin instance or None if not found.
        """
        ext = extension.lower()
        if not ext.startswith('.'):
            ext = f'.{ext}'
        
        format_name = self._extension_map.get(ext)
        return self._plugins.get(format_name) if format_name else None
    
    def get_plugin_for_file(self, file_path: str) -> Optional[OntologyPlugin]:
        """
        Get the plugin that can handle a file.
        
        Args:
            file_path: Path to the file.
        
        Returns:
            OntologyPlugin instance or None if not found.
        """
        ext = Path(file_path).suffix.lower()
        return self.get_plugin_for_extension(ext)
    
    def has_plugin(self, format_name: str) -> bool:
        """Check if a plugin is registered for a format."""
        return format_name.lower() in self._plugins
    
    def require_plugin(self, format_name: str) -> OntologyPlugin:
        """
        Get a plugin, raising error if not found.
        
        Args:
            format_name: Format identifier.
        
        Returns:
            OntologyPlugin instance.
        
        Raises:
            ValueError: If plugin not found.
        """
        plugin = self.get_plugin(format_name)
        if plugin is None:
            available = ", ".join(self.list_formats()) or "none"
            raise ValueError(
                f"No plugin found for format '{format_name}'. "
                f"Available formats: {available}"
            )
        return plugin
    
    # =========================================================================
    # Listing and Enumeration
    # =========================================================================
    
    def list_plugins(self) -> List[OntologyPlugin]:
        """
        List all registered plugins.
        
        Returns:
            List of OntologyPlugin instances.
        """
        return list(self._plugins.values())
    
    def list_formats(self) -> List[str]:
        """
        List all supported format names.
        
        Returns:
            List of format names (e.g., ["rdf", "dtdl"]).
        """
        return sorted(self._plugins.keys())
    
    def list_extensions(self) -> Set[str]:
        """
        List all supported file extensions.
        
        Returns:
            Set of extensions (e.g., {".ttl", ".json"}).
        """
        return set(self._extension_map.keys())
    
    def get_format_for_extension(self, extension: str) -> Optional[str]:
        """
        Get the format name for an extension.
        
        Args:
            extension: File extension.
        
        Returns:
            Format name or None.
        """
        ext = extension.lower()
        if not ext.startswith('.'):
            ext = f'.{ext}'
        return self._extension_map.get(ext)
    
    def get_all_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all plugins.
        
        Returns:
            Dict mapping format names to plugin info.
        """
        return {
            name: plugin.get_info()
            for name, plugin in self._plugins.items()
        }
    
    # =========================================================================
    # Plugin Discovery
    # =========================================================================
    
    def discover_plugins(
        self,
        plugin_dirs: Optional[List[Path]] = None,
        load_builtin: bool = True,
        load_entrypoints: bool = True,
    ) -> int:
        """
        Discover and load plugins from various sources.
        
        Args:
            plugin_dirs: Additional directories to search.
            load_builtin: Whether to load built-in plugins.
            load_entrypoints: Whether to load entry point plugins.
        
        Returns:
            Number of plugins loaded.
        """
        initial_count = len(self._plugins)
        
        # Load built-in plugins first
        if load_builtin:
            self._load_builtin_plugins()
        
        # Load from entry points
        if load_entrypoints:
            self._load_entrypoint_plugins()
        
        # Load from custom directories
        if plugin_dirs:
            for plugin_dir in plugin_dirs:
                self._load_directory_plugins(Path(plugin_dir))
        
        self._initialized = True
        loaded = len(self._plugins) - initial_count
        logger.info(f"Plugin discovery complete: {loaded} plugins loaded")
        
        return loaded
    
    def _load_builtin_plugins(self) -> None:
        """Load built-in RDF and DTDL plugins."""
        # Try to load RDF plugin
        try:
            from .builtin.rdf_plugin import RDFPlugin
            self.register_plugin(RDFPlugin())
        except ImportError as e:
            logger.debug(f"Could not load built-in RDF plugin: {e}")
        except Exception as e:
            logger.error(f"Failed to load RDF plugin: {e}")
        
        # Try to load DTDL plugin
        try:
            from .builtin.dtdl_plugin import DTDLPlugin
            self.register_plugin(DTDLPlugin())
        except ImportError as e:
            logger.debug(f"Could not load built-in DTDL plugin: {e}")
        except Exception as e:
            logger.error(f"Failed to load DTDL plugin: {e}")
    
    def _load_entrypoint_plugins(self) -> None:
        """Load plugins from setuptools entry points."""
        try:
            # Python 3.10+ compatible
            from importlib.metadata import entry_points
            
            # Get entry points (different API in Python versions)
            try:
                # Python 3.10+
                eps = entry_points(group=self.ENTRY_POINT_GROUP)
            except TypeError:
                # Python 3.9
                eps = entry_points().get(self.ENTRY_POINT_GROUP, [])
            
            for ep in eps:
                try:
                    plugin_class = ep.load()
                    if isinstance(plugin_class, type) and issubclass(plugin_class, OntologyPlugin):
                        self.register_plugin(plugin_class())
                    elif isinstance(plugin_class, OntologyPlugin):
                        self.register_plugin(plugin_class)
                    else:
                        logger.warning(
                            f"Entry point {ep.name} did not return an OntologyPlugin"
                        )
                except Exception as e:
                    logger.error(f"Failed to load plugin from entry point {ep.name}: {e}")
        
        except ImportError:
            logger.debug("importlib.metadata not available, skipping entry points")
        except Exception as e:
            logger.warning(f"Error loading entry point plugins: {e}")
    
    def _load_directory_plugins(self, plugin_dir: Path) -> None:
        """
        Load plugins from a directory.
        
        Args:
            plugin_dir: Directory to search for plugins.
        """
        if not plugin_dir.exists():
            logger.warning(f"Plugin directory does not exist: {plugin_dir}")
            return
        
        if not plugin_dir.is_dir():
            logger.warning(f"Plugin path is not a directory: {plugin_dir}")
            return
        
        logger.debug(f"Searching for plugins in: {plugin_dir}")
        
        for py_file in plugin_dir.glob(self.PLUGIN_FILE_PATTERN):
            self._load_plugin_file(py_file)
    
    def _load_plugin_file(self, file_path: Path) -> None:
        """
        Load a plugin from a Python file.
        
        Args:
            file_path: Path to Python file.
        """
        try:
            # Create module name from file
            module_name = f"fabric_ontology_plugin_{file_path.stem}"
            
            # Load module
            spec = importlib.util.spec_from_file_location(
                module_name,
                file_path
            )
            if spec is None or spec.loader is None:
                logger.warning(f"Could not create module spec for: {file_path}")
                return
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Find OntologyPlugin subclasses in module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type) and
                    issubclass(attr, OntologyPlugin) and
                    attr is not OntologyPlugin
                ):
                    try:
                        self.register_plugin(attr())
                        logger.debug(f"Loaded plugin {attr.__name__} from {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to instantiate plugin {attr.__name__}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to load plugin from {file_path}: {e}")
    
    # =========================================================================
    # Lifecycle Management
    # =========================================================================
    
    def cleanup_all(self) -> None:
        """Clean up all plugins."""
        for plugin in self._plugins.values():
            try:
                plugin.cleanup()
            except Exception as e:
                logger.warning(f"Plugin cleanup failed for {plugin.format_name}: {e}")
        
        self._plugins.clear()
        self._extension_map.clear()
        self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """Check if plugin discovery has been run."""
        return self._initialized


# =============================================================================
# Convenience Functions
# =============================================================================

def get_plugin_manager() -> PluginManager:
    """
    Get the global plugin manager instance.
    
    Convenience function for PluginManager.get_instance().
    
    Returns:
        PluginManager instance.
    """
    return PluginManager.get_instance()


def get_plugin(format_name: str) -> Optional[OntologyPlugin]:
    """
    Get a plugin by format name.
    
    Convenience function for manager.get_plugin().
    
    Args:
        format_name: Format identifier.
    
    Returns:
        OntologyPlugin or None.
    """
    return PluginManager.get_instance().get_plugin(format_name)


def list_formats() -> List[str]:
    """
    List all available format names.
    
    Convenience function for manager.list_formats().
    
    Returns:
        List of format names.
    """
    return PluginManager.get_instance().list_formats()
