"""Format pipeline contracts used by the CLI and plugin layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.plugins.protocols import (
    ParserProtocol,
    ValidatorProtocol,
    ConverterProtocol,
    ExporterProtocol,
)


@dataclass(slots=True)
class FormatPipeline:
    """Container describing the core services required to process a format."""

    format_name: str
    parser: ParserProtocol
    validator: ValidatorProtocol
    converter: ConverterProtocol
    exporter: Optional[ExporterProtocol] = None

    def has_exporter(self) -> bool:
        return self.exporter is not None
