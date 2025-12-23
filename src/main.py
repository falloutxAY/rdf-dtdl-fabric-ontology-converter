#!/usr/bin/env python3
"""
RDF TTL to Microsoft Fabric Ontology Uploader

This is the main entry point for uploading RDF TTL ontologies to Microsoft Fabric.

Usage:
    python main.py upload <ttl_file> [--config <config.json>] [--name <ontology_name>]
    python main.py list [--config <config.json>]
    python main.py get <ontology_id> [--config <config.json>]
    python main.py delete <ontology_id> [--config <config.json>]
    python main.py test [--config <config.json>]
    python main.py convert <ttl_file> [--output <output.json>]
"""

import argparse
import json
import logging
import sys
import os
from pathlib import Path
from typing import Optional

from rdf_converter import parse_ttl_file, parse_ttl_content
from fabric_client import FabricConfig, FabricOntologyClient, FabricAPIError


# Setup logging
def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """Setup logging configuration."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        try:
            # Ensure directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
        except PermissionError:
            print(f"Warning: Permission denied creating log file: {log_file}")
            print("Logging to console only")
        except OSError as e:
            print(f"Warning: Failed to create log file {log_file}: {e}")
            print("Logging to console only")
        except Exception as e:
            print(f"Warning: Unexpected error setting up log file: {e}")
            print("Logging to console only")
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
    )


def load_config(config_path: str) -> dict:
    """Load configuration from file."""
    if not config_path:
        raise ValueError("config_path cannot be empty")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Please create a config.json file or specify one with --config"
        )
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON in configuration file {config_path} at line {e.lineno}, column {e.colno}: {e.msg}"
        )
    except UnicodeDecodeError as e:
        raise ValueError(f"File encoding error in {config_path}: {e}")
    except PermissionError:
        raise PermissionError(f"Permission denied reading {config_path}")
    except Exception as e:
        raise IOError(f"Error loading configuration file: {e}")
    
    if not isinstance(config, dict):
        raise ValueError(f"Configuration file must contain a JSON object, got {type(config)}")
    
    return config


def get_default_config_path() -> str:
    """Get the default configuration file path."""
    script_dir = Path(__file__).parent
    return str(script_dir / "config.json")


def cmd_upload(args):
    """Upload an RDF TTL file to Fabric Ontology."""
    logger = logging.getLogger(__name__)
    
    # Load configuration
    config_path = args.config or get_default_config_path()
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found: {config_path}")
        print("Please create a config.json file or specify one with --config")
        sys.exit(1)
    
    config_data = load_config(config_path)
    fabric_config = FabricConfig.from_dict(config_data)
    
    if not fabric_config.workspace_id or fabric_config.workspace_id == "YOUR_WORKSPACE_ID":
        print("Error: Please configure your Fabric workspace_id in config.json")
        sys.exit(1)
    
    # Setup logging from config
    log_config = config_data.get('logging', {})
    setup_logging(
        level=log_config.get('level', 'INFO'),
        log_file=log_config.get('file'),
    )
    
    # Parse the TTL file
    ttl_file = args.ttl_file
    if not os.path.exists(ttl_file):
        print(f"Error: TTL file not found: {ttl_file}")
        sys.exit(1)
    
    logger.info(f"Parsing TTL file: {ttl_file}")
    
    try:
        with open(ttl_file, 'r', encoding='utf-8') as f:
            ttl_content = f.read()
    except FileNotFoundError:
        print(f"Error: TTL file not found: {ttl_file}")
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"Error: Failed to read TTL file due to encoding issue: {e}")
        print("Try converting the file to UTF-8 encoding")
        sys.exit(1)
    except PermissionError:
        print(f"Error: Permission denied reading file: {ttl_file}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading TTL file: {e}")
        sys.exit(1)
    
    if not ttl_content.strip():
        print(f"Error: TTL file is empty: {ttl_file}")
        sys.exit(1)
    
    id_prefix = config_data.get('ontology', {}).get('id_prefix', 1000000000000)
    
    try:
        definition, extracted_name = parse_ttl_content(ttl_content, id_prefix)
    except ValueError as e:
        logger.error(f"Invalid TTL content: {e}")
        print(f"Error: Invalid RDF/TTL content: {e}")
        sys.exit(1)
    except MemoryError:
        logger.error("Insufficient memory to parse TTL file")
        print(f"Error: Insufficient memory to parse TTL file. File may be too large.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to parse TTL file: {e}", exc_info=True)
        print(f"Error parsing TTL file: {e}")
        sys.exit(1)
    
    if not definition or 'parts' not in definition:
        print("Error: Generated definition is invalid or empty")
        sys.exit(1)
    
    if not definition['parts']:
        print("Warning: No entity types or relationship types found in TTL file")
        logger.warning("Empty ontology definition generated")
    
    # Use provided name or extracted name
    ontology_name = args.name or extracted_name
    description = args.description or f"Imported from {os.path.basename(ttl_file)}"
    
    logger.info(f"Ontology name: {ontology_name}")
    logger.info(f"Definition has {len(definition['parts'])} parts")
    
    # Create Fabric client and upload
    client = FabricOntologyClient(fabric_config)
    
    try:
        # Use create_or_update for automatic incremental updates
        result = client.create_or_update_ontology(
            display_name=ontology_name,
            description=description,
            definition=definition,
            wait_for_completion=True,
        )
        
        print(f"Successfully processed ontology '{ontology_name}'")
        print(f"Ontology ID: {result.get('id', 'Unknown')}")
        print(f"Workspace ID: {result.get('workspaceId', fabric_config.workspace_id)}")
        
    except FabricAPIError as e:
        logger.error(f"Fabric API error: {e}")
        print(f"Error: {e.message}")
        if e.error_code == "ItemDisplayNameAlreadyInUse":
            print("Hint: Use --update to update an existing ontology, or choose a different name with --name")
        sys.exit(1)


def cmd_list(args):
    """List all ontologies in the workspace."""
    logger = logging.getLogger(__name__)
    
    config_path = args.config or get_default_config_path()
    config_data = load_config(config_path)
    fabric_config = FabricConfig.from_dict(config_data)
    
    log_config = config_data.get('logging', {})
    setup_logging(level=log_config.get('level', 'INFO'))
    
    client = FabricOntologyClient(fabric_config)
    
    try:
        ontologies = client.list_ontologies()
        
        if not ontologies:
            print("No ontologies found in the workspace.")
            return
        
        print(f"\nFound {len(ontologies)} ontologies:\n")
        print(f"{'ID':<40} {'Name':<30} {'Description':<40}")
        print("-" * 110)
        
        for ont in ontologies:
            ont_id = ont.get('id', 'Unknown')
            name = ont.get('displayName', 'Unknown')[:30]
            desc = (ont.get('description', '') or '')[:40]
            print(f"{ont_id:<40} {name:<30} {desc:<40}")
        
    except FabricAPIError as e:
        logger.error(f"Fabric API error: {e}")
        print(f"Error: {e.message}")
        sys.exit(1)


def cmd_get(args):
    """Get details of a specific ontology."""
    logger = logging.getLogger(__name__)
    
    config_path = args.config or get_default_config_path()
    config_data = load_config(config_path)
    fabric_config = FabricConfig.from_dict(config_data)
    
    log_config = config_data.get('logging', {})
    setup_logging(level=log_config.get('level', 'INFO'))
    
    client = FabricOntologyClient(fabric_config)
    
    try:
        ontology = client.get_ontology(args.ontology_id)
        print("\nOntology Details:")
        print(json.dumps(ontology, indent=2))
        
        if args.with_definition:
            print("\nOntology Definition:")
            definition = client.get_ontology_definition(args.ontology_id)
            print(json.dumps(definition, indent=2))
        
    except FabricAPIError as e:
        logger.error(f"Fabric API error: {e}")
        print(f"Error: {e.message}")
        sys.exit(1)


def cmd_delete(args):
    """Delete an ontology."""
    logger = logging.getLogger(__name__)
    
    config_path = args.config or get_default_config_path()
    config_data = load_config(config_path)
    fabric_config = FabricConfig.from_dict(config_data)
    
    log_config = config_data.get('logging', {})
    setup_logging(level=log_config.get('level', 'INFO'))
    
    client = FabricOntologyClient(fabric_config)
    
    if not args.force:
        confirm = input(f"Are you sure you want to delete ontology {args.ontology_id}? [y/N]: ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return
    
    try:
        client.delete_ontology(args.ontology_id)
        print(f"Successfully deleted ontology {args.ontology_id}")
        
    except FabricAPIError as e:
        logger.error(f"Fabric API error: {e}")
        print(f"Error: {e.message}")
        sys.exit(1)


def cmd_test(args):
    """Test the program with a sample ontology."""
    logger = logging.getLogger(__name__)
    
    config_path = args.config or get_default_config_path()
    if os.path.exists(config_path):
        config_data = load_config(config_path)
        log_config = config_data.get('logging', {})
        setup_logging(level=log_config.get('level', 'INFO'))
    else:
        setup_logging()
    
    # Find sample TTL file in samples folder
    script_dir = Path(__file__).parent
    sample_ttl = script_dir / "samples" / "sample_ontology.ttl"
    
    if not sample_ttl.exists():
        print(f"Error: Sample TTL file not found: {sample_ttl}")
        sys.exit(1)
    
    print(f"Testing with sample ontology: {sample_ttl}\n")
    
    # Parse the sample TTL
    with open(sample_ttl, 'r', encoding='utf-8') as f:
        ttl_content = f.read()
    
    definition, ontology_name = parse_ttl_content(ttl_content)
    
    print(f"Ontology Name: {ontology_name}")
    print(f"Number of definition parts: {len(definition['parts'])}")
    print("\nDefinition Parts:")
    
    for part in definition['parts']:
        print(f"  - {part['path']}")
    
    print("\n--- Full Definition (JSON) ---\n")
    print(json.dumps(definition, indent=2))
    
    # Test Fabric connection if config exists
    if os.path.exists(config_path):
        config_data = load_config(config_path)
        fabric_config = FabricConfig.from_dict(config_data)
        
        if fabric_config.workspace_id and fabric_config.workspace_id != "YOUR_WORKSPACE_ID":
            print("\n--- Testing Fabric Connection ---\n")
            client = FabricOntologyClient(fabric_config)
            
            try:
                ontologies = client.list_ontologies()
                print(f"Successfully connected to Fabric. Found {len(ontologies)} existing ontologies.")
                
                if args.upload_test:
                    print("\nUploading test ontology...")
                    result = client.create_ontology(
                        display_name="Test_Manufacturing_Ontology",
                        description="Test ontology from RDF import tool",
                        definition=definition,
                    )
                    print(f"Successfully created test ontology: {result.get('id')}")
                    
            except FabricAPIError as e:
                print(f"Fabric API error: {e.message}")
        else:
            print("\nNote: Configure workspace_id in config.json to test Fabric connection.")
    else:
        print(f"\nNote: Create {config_path} to test Fabric connection.")


def cmd_convert(args):
    """Convert TTL to Fabric Ontology definition without uploading."""
    logger = logging.getLogger(__name__)
    setup_logging()
    
    ttl_file = args.ttl_file
    if not os.path.exists(ttl_file):
        print(f"Error: TTL file not found: {ttl_file}")
        sys.exit(1)
    
    print(f"Converting TTL file: {ttl_file}")
    
    try:
        with open(ttl_file, 'r', encoding='utf-8') as f:
            ttl_content = f.read()
    except UnicodeDecodeError as e:
        print(f"Error: Failed to read TTL file due to encoding issue: {e}")
        print("Try converting the file to UTF-8 encoding")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading TTL file: {e}")
        sys.exit(1)
    
    try:
        definition, ontology_name = parse_ttl_content(ttl_content)
    except ValueError as e:
        print(f"Error: Invalid RDF/TTL content: {e}")
        sys.exit(1)
    except MemoryError:
        print(f"Error: Insufficient memory to parse TTL file. File may be too large.")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing TTL file: {e}")
        sys.exit(1)
    
    output = {
        "displayName": ontology_name,
        "description": f"Converted from {os.path.basename(ttl_file)}",
        "definition": definition,
    }
    
    if args.output:
        output_path = args.output
    else:
        output_path = str(Path(ttl_file).with_suffix('.json'))
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, indent=2, fp=f)
    except PermissionError:
        print(f"Error: Permission denied writing to {output_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)
    
    print(f"Saved Fabric Ontology definition to: {output_path}")
    print(f"Ontology Name: {ontology_name}")
    print(f"Definition Parts: {len(definition['parts'])}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="RDF TTL to Microsoft Fabric Ontology Uploader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s upload samples\\sample_ontology.ttl
    %(prog)s upload my_ontology.ttl --name MyOntology --update
  %(prog)s list
    %(prog)s get 12345678-1234-1234-1234-123456789012
    %(prog)s convert samples\\sample_ontology.ttl --output fabric_definition.json
  %(prog)s test
        """,
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload a TTL file to Fabric Ontology')
    upload_parser.add_argument('ttl_file', help='Path to the TTL file to upload')
    upload_parser.add_argument('--config', '-c', help='Path to configuration file')
    upload_parser.add_argument('--name', '-n', help='Override ontology name')
    upload_parser.add_argument('--description', '-d', help='Ontology description')
    upload_parser.add_argument('--update', '-u', action='store_true', 
                               help='Update if ontology with same name exists')
    upload_parser.set_defaults(func=cmd_upload)
    
    # List command
    list_parser = subparsers.add_parser('list', help='List ontologies in the workspace')
    list_parser.add_argument('--config', '-c', help='Path to configuration file')
    list_parser.set_defaults(func=cmd_list)
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get ontology details')
    get_parser.add_argument('ontology_id', help='Ontology ID')
    get_parser.add_argument('--config', '-c', help='Path to configuration file')
    get_parser.add_argument('--with-definition', action='store_true',
                            help='Also fetch the ontology definition')
    get_parser.set_defaults(func=cmd_get)
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete an ontology')
    delete_parser.add_argument('ontology_id', help='Ontology ID')
    delete_parser.add_argument('--config', '-c', help='Path to configuration file')
    delete_parser.add_argument('--force', '-f', action='store_true',
                               help='Skip confirmation prompt')
    delete_parser.set_defaults(func=cmd_delete)
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test with sample ontology')
    test_parser.add_argument('--config', '-c', help='Path to configuration file')
    test_parser.add_argument('--upload-test', action='store_true',
                             help='Also upload the test ontology to Fabric')
    test_parser.set_defaults(func=cmd_test)
    
    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert TTL to Fabric format without uploading')
    convert_parser.add_argument('ttl_file', help='Path to the TTL file to convert')
    convert_parser.add_argument('--output', '-o', help='Output JSON file path')
    convert_parser.set_defaults(func=cmd_convert)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == '__main__':
    main()
