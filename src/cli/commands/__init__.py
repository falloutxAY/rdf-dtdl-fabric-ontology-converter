"""
CLI command implementations.

This package contains split command modules for better organization:
- base.py: Base command class and protocols
- unified.py: Unified commands (validate, convert, upload, export)
- common.py: Common commands (list, get, delete, test, compare)
"""

from .base import (
    BaseCommand,
    IValidator,
    IConverter,
    IFabricClient,
    print_conversion_summary,
)

from .common import (
    ListCommand,
    GetCommand,
    DeleteCommand,
    TestCommand,
    CompareCommand,
)

from .unified import (
    ValidateCommand,
    ConvertCommand,
    UploadCommand,
    ExportCommand,
)


__all__ = [
    # Base
    'BaseCommand',
    'IValidator',
    'IConverter',
    'IFabricClient',
    'print_conversion_summary',
    # Common
    'ListCommand',
    'GetCommand',
    'DeleteCommand',
    'TestCommand',
    'CompareCommand',
    # Unified
    'ValidateCommand',
    'ConvertCommand',
    'UploadCommand',
    'ExportCommand',
]
