"""
CLI module for RDF to Fabric Ontology Converter.

This module provides a clean separation of concerns for the CLI:
- commands/: Command implementations split by format
  - base.py: Base command class and protocols
  - unified.py: Unified commands (validate, convert, upload, export)
  - common.py: Common commands (list, get, delete, test, compare)
- parsers.py: Argument parsing configuration
- helpers.py: Shared CLI utilities
- format.py: Format enum and dispatch helpers
"""

from .commands import (
    # Base
    BaseCommand,
    IValidator,
    IConverter,
    IFabricClient,
    print_conversion_summary,
    # Common
    ListCommand,
    GetCommand,
    DeleteCommand,
    TestCommand,
    CompareCommand,
    # Unified
    ValidateCommand,
    ConvertCommand,
    UploadCommand,
    ExportCommand,
)

from .parsers import create_argument_parser

from .helpers import (
    load_config,
    get_default_config_path,
    setup_logging,
)

from .format import Format

__all__ = [
    # Base
    'BaseCommand',
    'IValidator',
    'IConverter',
    'IFabricClient',
    'print_conversion_summary',
    # Common Commands
    'ListCommand',
    'GetCommand',
    'DeleteCommand',
    'TestCommand',
    'CompareCommand',
    # Unified Commands
    'ValidateCommand',
    'ConvertCommand',
    'UploadCommand',
    'ExportCommand',
    # Parsers
    'create_argument_parser',
    # Helpers
    'load_config',
    'get_default_config_path',
    'setup_logging',
    # Format
    'Format',
]
