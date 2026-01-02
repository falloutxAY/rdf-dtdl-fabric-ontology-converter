"""
CLI module for RDF to Fabric Ontology Converter.

This module provides a clean separation of concerns for the CLI:
- commands.py: Command handlers (thin orchestration layer)
- parsers.py: Argument parsing configuration
- helpers.py: Shared CLI utilities
"""

from .commands import (
    UploadCommand,
    ValidateCommand,
    ListCommand,
    GetCommand,
    DeleteCommand,
    TestCommand,
    ConvertCommand,
    ExportCommand,
    CompareCommand,
    # DTDL commands
    DTDLValidateCommand,
    DTDLConvertCommand,
    DTDLImportCommand,
)

from .parsers import create_argument_parser

from .helpers import (
    load_config,
    get_default_config_path,
    setup_logging,
)

__all__ = [
    # Commands
    'UploadCommand',
    'ValidateCommand',
    'ListCommand',
    'GetCommand',
    'DeleteCommand',
    'TestCommand',
    'ConvertCommand',
    'ExportCommand',
    'CompareCommand',
    # DTDL Commands
    'DTDLValidateCommand',
    'DTDLConvertCommand',
    'DTDLImportCommand',
    # Parsers
    'create_argument_parser',
    # Helpers
    'load_config',
    'get_default_config_path',
    'setup_logging',
]
