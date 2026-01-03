#!/usr/bin/env python3
"""
RDF TTL to Microsoft Fabric Ontology Uploader

This is the main entry point for uploading RDF TTL and DTDL ontologies to Microsoft Fabric.

Usage:
    # Run as a module (recommended)
    python -m src.main <command> [options]
    
    # Or from the src directory
    cd src && python main.py <command> [options]
    
    # Unified Commands (use --format to specify input type)
    python -m src.main validate --format rdf <ttl_file> [--verbose]
    python -m src.main validate --format dtdl <path> [--recursive]
    python -m src.main convert --format rdf <ttl_file> [--output <output.json>]
    python -m src.main convert --format dtdl <path> [--ontology-name <name>]
    python -m src.main upload --format rdf <ttl_file> [--ontology-name <name>]
    python -m src.main upload --format dtdl <path> [--ontology-name <name>]
    python -m src.main export <ontology_id> [--output <output.ttl>]
    
    # Workspace Commands
    python -m src.main list [--config <config.json>]
    python -m src.main get <ontology_id> [--config <config.json>]
    python -m src.main delete <ontology_id> [--config <config.json>]
    python -m src.main test [--config <config.json>]
    python -m src.main compare <ttl_file1> <ttl_file2>

Architecture:
    This module provides the main entry point and delegates to the cli/ module
    which implements clean separation of concerns:
    - cli/commands/unified.py: Unified command handlers (validate, convert, upload, export)
    - cli/commands/common.py: Common command handlers (list, get, delete, test, compare)
    - cli/parsers.py: Argument parsing configuration
    - cli/helpers.py: Shared utilities (logging, config loading)
    - cli/format.py: Format enum and dispatch helpers
"""

import sys

# Use try/except for imports to support both module and direct execution
try:
    # When running as module: python -m src.main
    from .cli import (
        create_argument_parser,
        ValidateCommand,
        ConvertCommand,
        UploadCommand,
        ExportCommand,
        ListCommand,
        GetCommand,
        DeleteCommand,
        TestCommand,
        CompareCommand,
    )
except ImportError:
    # When running directly: python src/main.py (from project root)
    from cli import (
        create_argument_parser,
        ValidateCommand,
        ConvertCommand,
        UploadCommand,
        ExportCommand,
        ListCommand,
        GetCommand,
        DeleteCommand,
        TestCommand,
        CompareCommand,
    )


# Command mapping from command name to Command class
COMMAND_MAP = {
    # Unified commands (require --format)
    'validate': ValidateCommand,
    'convert': ConvertCommand,
    'upload': UploadCommand,
    'export': ExportCommand,
    
    # Common commands (no format needed)
    'list': ListCommand,
    'get': GetCommand,
    'delete': DeleteCommand,
    'test': TestCommand,
    'compare': CompareCommand,
}


def main():
    """
    Main entry point for the CLI.
    
    Parses command-line arguments and dispatches to the appropriate
    command handler. Uses the Command pattern for clean separation
    of concerns.
    """
    parser = create_argument_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Get the command class and instantiate it
    command_class = COMMAND_MAP.get(args.command)
    
    if command_class is None:
        print(f"Error: Unknown command '{args.command}'")
        parser.print_help()
        sys.exit(1)
    
    # Create and execute the command
    # Pass config_path if available in args
    config_path = getattr(args, 'config', None)
    command = command_class(config_path=config_path)
    
    exit_code = command.execute(args)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
