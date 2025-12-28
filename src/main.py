#!/usr/bin/env python3
"""
RDF TTL to Microsoft Fabric Ontology Uploader

This is the main entry point for uploading RDF TTL ontologies to Microsoft Fabric.

Usage:
    python main.py upload <ttl_file> [--config <config.json>] [--name <ontology_name>]
    python main.py validate <ttl_file> [--verbose]
    python main.py list [--config <config.json>]
    python main.py get <ontology_id> [--config <config.json>]
    python main.py delete <ontology_id> [--config <config.json>]
    python main.py test [--config <config.json>]
    python main.py convert <ttl_file> [--output <output.json>]
    python main.py export <ontology_id> [--output <output.ttl>]
    python main.py compare <ttl_file1> <ttl_file2>

Architecture:
    This module provides the main entry point and delegates to the cli/ module
    which implements clean separation of concerns:
    - cli/commands.py: Command handlers (thin orchestration layer)
    - cli/parsers.py: Argument parsing configuration
    - cli/helpers.py: Shared utilities (logging, config loading)
"""

import sys
from pathlib import Path

# Ensure the src directory is in the Python path for imports
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from cli import (
    create_argument_parser,
    ValidateCommand,
    UploadCommand,
    ListCommand,
    GetCommand,
    DeleteCommand,
    TestCommand,
    ConvertCommand,
    ExportCommand,
    CompareCommand,
)


# Command mapping from command name to Command class
COMMAND_MAP = {
    'validate': ValidateCommand,
    'upload': UploadCommand,
    'list': ListCommand,
    'get': GetCommand,
    'delete': DeleteCommand,
    'test': TestCommand,
    'convert': ConvertCommand,
    'export': ExportCommand,
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
