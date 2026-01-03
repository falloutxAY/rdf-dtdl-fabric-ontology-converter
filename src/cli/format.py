"""
Format enumeration and dispatch helpers.

Provides a single point for branching between RDF and DTDL logic
in the unified CLI commands.
"""

from enum import Enum
from typing import Any, Callable, Dict, Type


class Format(str, Enum):
    """Supported ontology formats."""
    RDF = "rdf"
    DTDL = "dtdl"

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Service factory registry
# ---------------------------------------------------------------------------

_VALIDATOR_FACTORIES: Dict[Format, Callable[[], Any]] = {}
_CONVERTER_FACTORIES: Dict[Format, Callable[[], Any]] = {}
_UPLOADER_FACTORIES: Dict[Format, Callable[[], Any]] = {}


def register_validator(fmt: Format, factory: Callable[[], Any]) -> None:
    """Register a validator factory for a format."""
    _VALIDATOR_FACTORIES[fmt] = factory


def register_converter(fmt: Format, factory: Callable[[], Any]) -> None:
    """Register a converter factory for a format."""
    _CONVERTER_FACTORIES[fmt] = factory


def register_uploader(fmt: Format, factory: Callable[[], Any]) -> None:
    """Register an uploader factory for a format."""
    _UPLOADER_FACTORIES[fmt] = factory


def get_validator(fmt: Format) -> Any:
    """
    Return a validator instance for the given format.
    
    Raises:
        ValueError: If no validator is registered for the format.
    """
    factory = _VALIDATOR_FACTORIES.get(fmt)
    if factory is None:
        raise ValueError(f"No validator registered for format: {fmt}")
    return factory()


def get_converter(fmt: Format) -> Any:
    """
    Return a converter instance for the given format.
    
    Raises:
        ValueError: If no converter is registered for the format.
    """
    factory = _CONVERTER_FACTORIES.get(fmt)
    if factory is None:
        raise ValueError(f"No converter registered for format: {fmt}")
    return factory()


def get_uploader(fmt: Format) -> Any:
    """
    Return an uploader instance for the given format.
    
    Raises:
        ValueError: If no uploader is registered for the format.
    """
    factory = _UPLOADER_FACTORIES.get(fmt)
    if factory is None:
        raise ValueError(f"No uploader registered for format: {fmt}")
    return factory()


# ---------------------------------------------------------------------------
# Default registrations (lazy imports to avoid circular deps)
# ---------------------------------------------------------------------------

def _register_defaults() -> None:
    """Register default factories for RDF and DTDL."""
    # RDF validators/converters
    def rdf_validator():
        from rdf import PreflightValidator
        return PreflightValidator()

    def rdf_converter():
        from rdf import RDFConverter
        return RDFConverter()

    register_validator(Format.RDF, rdf_validator)
    register_converter(Format.RDF, rdf_converter)

    # DTDL validators/converters
    def dtdl_validator():
        from dtdl.dtdl_validator import DTDLValidator
        return DTDLValidator()

    def dtdl_converter():
        from dtdl.dtdl_converter import DTDLToFabricConverter
        return DTDLToFabricConverter()

    register_validator(Format.DTDL, dtdl_validator)
    register_converter(Format.DTDL, dtdl_converter)


# Auto-register on module load
_register_defaults()


# ---------------------------------------------------------------------------
# File extension helpers
# ---------------------------------------------------------------------------

RDF_EXTENSIONS = {".ttl", ".rdf", ".owl"}
DTDL_EXTENSIONS = {".json"}


def infer_format_from_path(path: str) -> Format:
    """
    Attempt to infer the format from a file path extension.
    
    Args:
        path: File or directory path.
        
    Returns:
        Inferred Format.
        
    Raises:
        ValueError: If format cannot be inferred.
    """
    from pathlib import Path
    ext = Path(path).suffix.lower()
    if ext in RDF_EXTENSIONS:
        return Format.RDF
    if ext in DTDL_EXTENSIONS:
        return Format.DTDL
    raise ValueError(
        f"Cannot infer format from extension '{ext}'. "
        f"Use --format to specify explicitly."
    )
