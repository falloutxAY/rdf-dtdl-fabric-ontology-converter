"""
DTDL Plugin wrapper.

This wraps the existing DTDL converter as a plugin to demonstrate
how existing converters integrate with the plugin system.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Plugin base
import sys
_plugin_dir = Path(__file__).parent.parent
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))

from base import OntologyPlugin

# Existing DTDL modules (adjust imports as needed)
try:
    from dtdl.dtdl_parser import DTDLParser
    from dtdl.dtdl_validator import DTDLValidator
    from dtdl.dtdl_converter import DTDLConverter
    from dtdl.dtdl_type_mapper import DTDL_TO_FABRIC_TYPE
except ImportError:
    # Fallback for standalone reference
    DTDLParser = None
    DTDLValidator = None
    DTDLConverter = None
    DTDL_TO_FABRIC_TYPE = {}


class DTDLPlugin(OntologyPlugin):
    """
    Digital Twins Definition Language (DTDL) plugin.
    
    Wraps the existing DTDL converter components as a plugin.
    
    Supported versions:
    - DTDL v2
    - DTDL v3
    - DTDL v4
    """
    
    @property
    def format_name(self) -> str:
        return "dtdl"
    
    @property
    def display_name(self) -> str:
        return "DTDL (Digital Twins Definition Language)"
    
    @property
    def file_extensions(self) -> Set[str]:
        return {".json"}
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def author(self) -> str:
        return "Fabric Ontology Converter Team"
    
    @property
    def dependencies(self) -> List[str]:
        return []  # Standard library JSON
    
    def get_parser(self) -> Any:
        """Return DTDL parser."""
        if DTDLParser is None:
            raise ImportError("DTDL modules not available")
        return DTDLParser()
    
    def get_validator(self) -> Any:
        """Return DTDL validator."""
        if DTDLValidator is None:
            raise ImportError("DTDL modules not available")
        return DTDLValidator()
    
    def get_converter(self) -> Any:
        """Return DTDL converter."""
        if DTDLConverter is None:
            raise ImportError("DTDL modules not available")
        return DTDLConverter()
    
    def get_type_mappings(self) -> Dict[str, str]:
        """Return DTDL to Fabric type mappings."""
        return DTDL_TO_FABRIC_TYPE
    
    def register_cli_arguments(self, parser: Any) -> None:
        """Add DTDL-specific CLI arguments."""
        parser.add_argument(
            "--dtdl-version",
            type=int,
            choices=[2, 3, 4],
            help="DTDL version (auto-detected by default)"
        )
        parser.add_argument(
            "--include-components",
            action="store_true",
            default=True,
            help="Include DTDL components as relationships"
        )
        parser.add_argument(
            "--flatten-extends",
            action="store_true",
            help="Flatten extends hierarchy into single entities"
        )
    
    def detect_dtdl_version(self, content: str) -> Optional[int]:
        """
        Detect DTDL version from content.
        
        Args:
            content: JSON string content
            
        Returns:
            DTDL version (2, 3, 4) or None if not detected
        """
        import json
        try:
            data = json.loads(content)
            if isinstance(data, list) and data:
                data = data[0]
            
            if isinstance(data, dict):
                context = data.get("@context", "")
                if isinstance(context, str):
                    if "dtdl/dtmi/v2" in context.lower():
                        return 2
                    elif "dtdl/dtmi/v3" in context.lower():
                        return 3
                    elif "dtdl/dtmi/v4" in context.lower():
                        return 4
        except (json.JSONDecodeError, KeyError):
            pass
        return None


# Export
__all__ = ["DTDLPlugin"]
