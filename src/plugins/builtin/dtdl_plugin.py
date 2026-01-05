"""
DTDL Plugin wrapper.

This wraps the existing DTDL converter as a plugin to provide
it through the unified plugin interface.
"""

import json
from typing import Any, Dict, List, Optional, Set

from ..base import OntologyPlugin


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
        try:
            from src.dtdl import DTDLParser
            return DTDLParser()
        except ImportError:
            raise ImportError("DTDL modules not available")
    
    def get_validator(self) -> Any:
        """Return DTDL validator."""
        try:
            from src.dtdl import DTDLValidator
            return DTDLValidator()
        except ImportError:
            raise ImportError("DTDL modules not available")
    
    def get_converter(self) -> Any:
        """Return DTDL converter."""
        try:
            from src.dtdl import DTDLToFabricConverter
            return DTDLToFabricConverter()
        except ImportError:
            raise ImportError("DTDL modules not available")
    
    def get_type_mappings(self) -> Dict[str, str]:
        """Return DTDL to Fabric type mappings."""
        try:
            from src.dtdl import PRIMITIVE_TYPE_MAP
            # Convert FabricValueType enum values to string
            return {k: v.value if hasattr(v, 'value') else str(v) 
                    for k, v in PRIMITIVE_TYPE_MAP.items()}
        except ImportError:
            return {}
    
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
