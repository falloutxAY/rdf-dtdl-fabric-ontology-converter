"""
DTDL CLI commands.

This module contains commands for DTDL file operations:
- DTDLValidateCommand: Validate DTDL files
- DTDLConvertCommand: Convert DTDL to Fabric format
- DTDLImportCommand: Import DTDL to Fabric Ontology (validate + convert + upload)
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from src.core import (
    FabricConfig,
    create_client,
    StreamConfig,
    DTDLStreamAdapter,
)
from src.formats.dtdl import DTDLParser, DTDLToFabricConverter, DTDLValidator
from ..helpers import resolve_dtdl_converter_modes
from .base import BaseCommand, print_conversion_summary


logger = logging.getLogger(__name__)


def _get_converter_kwargs(args: argparse.Namespace) -> Dict[str, Any]:
    """Build keyword arguments for DTDLToFabricConverter from CLI args."""
    namespace = getattr(args, 'namespace', 'usertypes')
    component_mode, command_mode = resolve_dtdl_converter_modes(args)
    return {
        "namespace": namespace,
        "component_mode": component_mode,
        "command_mode": command_mode,
    }


class DTDLValidateCommand(BaseCommand):
    """Command to validate DTDL files."""
    
    def execute(self, args: argparse.Namespace) -> int:
        """Execute DTDL validation."""
        self.setup_logging_from_config()
        path = Path(args.path).expanduser()
        if not path.exists():
            print(f"Error: Path does not exist: {path}")
            return 2

        parser = DTDLParser()
        validator = DTDLValidator()

        print(f"Validating DTDL at: {path}")

        try:
            if path.is_file():
                result = parser.parse_file(str(path))
            elif path.is_dir():
                recursive = getattr(args, 'recursive', False)
                result = parser.parse_directory(str(path), recursive=recursive)
            else:
                print(f"Error: Path is neither file nor directory: {path}")
                return 2
        except Exception as exc:
            print(f"Unexpected error parsing DTDL: {exc}")
            return 2

        if result.errors:
            print(f"Found {len(result.errors)} parse errors:")
            for error in result.errors[:10]:
                print(f"  - {error}")
            if not getattr(args, 'continue_on_error', False):
                return 2

        print(f"Parsed {len(result.interfaces)} interfaces")

        validation_result = validator.validate(result.interfaces)
        
        # Build report data
        report_data = {
            "path": str(path),
            "interfaces_parsed": len(result.interfaces),
            "parse_errors": result.errors,
            "validation_errors": [
                {"level": e.level.value, "dtmi": e.dtmi, "message": e.message}
                for e in validation_result.errors
            ],
            "validation_warnings": [
                {"level": w.level.value, "dtmi": w.dtmi, "message": w.message}
                for w in validation_result.warnings
            ],
            "is_valid": len(validation_result.errors) == 0,
            "interfaces": [
                {
                    "name": i.name,
                    "dtmi": i.dtmi,
                    "properties": len(i.properties),
                    "telemetries": len(i.telemetries),
                    "relationships": len(i.relationships),
                    "commands": len(i.commands),
                    "components": len(i.components),
                }
                for i in result.interfaces
            ]
        }
        
        if validation_result.errors:
            print(f"Found {len(validation_result.errors)} validation errors:")
            for error in validation_result.errors[:10]:
                print(f"  - [{error.level.value}] {error.dtmi or 'unknown'}: {error.message}")
            exit_code = 1
        else:
            if validation_result.warnings:
                print(f"Found {len(validation_result.warnings)} warnings:")
                for warning in validation_result.warnings[:10]:
                    print(f"  - {warning.dtmi or 'unknown'}: {warning.message}")
            
            print("✓ Validation successful!")
            exit_code = 0
        
        if getattr(args, 'verbose', False):
            print("\nInterface Summary:")
            for interface in result.interfaces[:20]:
                print(f"  {interface.name} ({interface.dtmi})")
                print(f"    Properties: {len(interface.properties)}, "
                      f"Telemetries: {len(interface.telemetries)}, "
                      f"Relationships: {len(interface.relationships)}")
        
        # Save report if requested
        output_path = getattr(args, 'output', None)
        save_report = getattr(args, 'save_report', False)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2)
            print(f"\nValidation report saved to: {output_path}")
        elif save_report:
            auto_path = f"{path}.validation.json" if path.is_file() else f"{path.name}.validation.json"
            with open(auto_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2)
            print(f"\nValidation report saved to: {auto_path}")
        
        return exit_code


class DTDLConvertCommand(BaseCommand):
    """Command to convert DTDL to Fabric format."""
    
    def execute(self, args: argparse.Namespace) -> int:
        """Execute DTDL conversion."""
        self.setup_logging_from_config()
        path = Path(args.path).expanduser()
        if not path.exists():
            print(f"Error: Path does not exist: {path}")
            return 2

        use_streaming = getattr(args, 'streaming', False)
        force_memory = getattr(args, 'force_memory', False)

        if path.is_file():
            file_size_mb = path.stat().st_size / (1024 * 1024)
            if file_size_mb > 100 and not use_streaming and not force_memory:
                print(f"⚠️  Large file detected ({file_size_mb:.1f} MB). Consider using --streaming.")

        if use_streaming:
            return self._convert_with_streaming(args, path)

        print(f"Parsing DTDL files from: {path}")
        parser = DTDLParser()

        try:
            if path.is_file():
                result = parser.parse_file(str(path))
            elif path.is_dir():
                recursive = getattr(args, 'recursive', False)
                result = parser.parse_directory(str(path), recursive=recursive)
            else:
                print(f"Error: Path is neither file nor directory: {path}")
                return 2
        except Exception as exc:
            print(f"Parse error: {exc}")
            return 2

        if result.errors:
            print(f"Parse errors: {len(result.errors)}")
            for error in result.errors[:5]:
                print(f"  - {error}")
            return 2

        print(f"Parsed {len(result.interfaces)} interfaces")

        validator = DTDLValidator()
        validation_result = validator.validate(result.interfaces)

        if validation_result.errors:
            print(f"Validation errors: {len(validation_result.errors)}")
            for error in validation_result.errors[:5]:
                print(f"  - {error.message}")
            return 1

        converter = DTDLToFabricConverter(**_get_converter_kwargs(args))

        conversion_result = converter.convert(result.interfaces)
        ontology_name = getattr(args, 'ontology_name', None) or path.stem
        definition = converter.to_fabric_definition(conversion_result, ontology_name)

        output_path = Path(getattr(args, 'output', None) or f"{ontology_name}_fabric.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(definition, f, indent=2)

        print_conversion_summary(conversion_result, heading="CONVERSION SUMMARY")
        print(f"  Output: {output_path}")

        if getattr(args, 'save_mapping', False):
            mapping_path = output_path.with_suffix('.mapping.json')
            with open(mapping_path, 'w', encoding='utf-8') as f:
                json.dump(converter.get_dtmi_mapping(), f, indent=2)
            print(f"  DTMI mapping: {mapping_path}")

        return 0
    
    def _convert_with_streaming(self, args, path) -> int:
        """Convert DTDL files using streaming mode."""
        print("Using streaming mode for conversion...")

        converter_kwargs = _get_converter_kwargs(args)
        ontology_name = getattr(args, 'ontology_name', None) or path.stem

        config = StreamConfig(
            chunk_size=10000,
            memory_threshold_mb=100.0,
            enable_progress=True,
        )

        adapter = DTDLStreamAdapter(
            config=config,
            ontology_name=ontology_name,
            namespace=converter_kwargs["namespace"],
            component_mode=converter_kwargs["component_mode"],
            command_mode=converter_kwargs["command_mode"],
        )

        def progress_callback(items_processed: int) -> None:
            if items_processed % 1000 == 0:
                print(f"  Processed {items_processed:,} items...")

        try:
            result = adapter.convert_streaming(
                str(path),
                progress_callback=progress_callback,
            )
        except Exception as exc:
            print(f"Streaming conversion error: {exc}")
            return 1

        if not result.success:
            error_message = result.error_message or "unknown error"
            print(f"Streaming conversion failed: {error_message}")
            return 1

        payload = result.data or {}
        definition = payload.get("definition")
        conversion_result = payload.get("conversion_result")

        if definition is None or conversion_result is None:
            print("Streaming conversion returned no definition from adapter.")
            return 1

        output_path = Path(getattr(args, 'output', None) or f"{ontology_name}_fabric.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(definition, f, indent=2)

        print("Streaming conversion complete!")
        print_conversion_summary(conversion_result, heading="CONVERSION SUMMARY")
        print(result.stats.get_summary())
        print(f"  Output: {output_path}")

        if getattr(args, 'save_mapping', False) and payload.get("dtmi_mapping"):
            mapping_path = output_path.with_suffix('.mapping.json')
            with open(mapping_path, 'w', encoding='utf-8') as f:
                json.dump(payload["dtmi_mapping"], f, indent=2)
            print(f"  DTMI mapping: {mapping_path}")

        return 0


class DTDLImportCommand(BaseCommand):
    """Command to import DTDL to Fabric Ontology (validate + convert + upload)."""
    
    def execute(self, args: argparse.Namespace) -> int:
        """Execute DTDL import pipeline."""
        if getattr(args, 'config', None):
            self.config_path = args.config
        self.setup_logging_from_config()

        path = Path(args.path).expanduser()
        if not path.exists():
            print(f"Error: Path does not exist: {path}")
            return 2

        ontology_name = getattr(args, 'ontology_name', None) or path.stem
        use_streaming = getattr(args, 'streaming', False)
        force_memory = getattr(args, 'force_memory', False)

        print(f"=== DTDL Import: {path} ===")

        if path.is_file():
            file_size_mb = path.stat().st_size / (1024 * 1024)
            if file_size_mb > 100 and not use_streaming and not force_memory:
                print(f"⚠️  Large file detected ({file_size_mb:.1f} MB). Consider using --streaming.")

        if use_streaming:
            return self._import_with_streaming(args, path, ontology_name)

        print("\nStep 1: Parsing DTDL files...")
        parser = DTDLParser()

        try:
            if path.is_file():
                result = parser.parse_file(str(path))
            elif path.is_dir():
                recursive = getattr(args, 'recursive', False)
                result = parser.parse_directory(str(path), recursive=recursive)
            else:
                print(f"  ✗ Invalid path: {path}")
                return 2
        except Exception as exc:
            print(f"  ✗ Parse error: {exc}")
            return 2

        if result.errors:
            print(f"  ✗ Parse errors: {len(result.errors)}")
            for error in result.errors[:5]:
                print(f"    - {error}")
            return 2

        print(f"  ✓ Parsed {len(result.interfaces)} interfaces")

        print("\nStep 2: Validating...")
        validator = DTDLValidator()
        validation_result = validator.validate(result.interfaces)

        if validation_result.errors:
            print(f"  ✗ Validation errors: {len(validation_result.errors)}")
            for error in validation_result.errors[:5]:
                print(f"    - {error.message}")
            return 1

        print("  ✓ Validation passed")

        print("\nStep 3: Converting to Fabric format...")
        converter = DTDLToFabricConverter(**_get_converter_kwargs(args))

        conversion_result = converter.convert(result.interfaces)
        definition = converter.to_fabric_definition(conversion_result, ontology_name)

        print_conversion_summary(conversion_result, heading="CONVERSION SUMMARY")

        if getattr(args, 'dry_run', False):
            print("\nStep 4: Dry run - saving to file...")
            output_path = Path(getattr(args, 'output', None) or f"{ontology_name}_fabric.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(definition, f, indent=2)
            print(f"  ✓ Definition saved to: {output_path}")
        else:
            print("\nStep 4: Uploading to Fabric...")
            client = self._get_fabric_client(args)
            if client is None:
                return 1

            try:
                result = client.create_ontology(
                    display_name=ontology_name,
                    description=f"Imported from DTDL: {path.name}",
                    definition=definition
                )
                ontology_id = result.get('id') if isinstance(result, dict) else result
                print(f"  ✓ Upload successful! Ontology ID: {ontology_id}")
            except Exception as exc:
                print(f"  ✗ Upload failed: {exc}")
                return 1

        print("\n=== Import complete ===")
        return 0
    
    def _import_with_streaming(self, args, path, ontology_name: str) -> int:
        """Import DTDL files using streaming mode."""
        print("Using streaming mode for import...")

        converter_kwargs = _get_converter_kwargs(args)
        config = StreamConfig(
            chunk_size=10000,
            memory_threshold_mb=100.0,
            enable_progress=True,
        )

        adapter = DTDLStreamAdapter(
            config=config,
            ontology_name=ontology_name,
            namespace=converter_kwargs["namespace"],
            component_mode=converter_kwargs["component_mode"],
            command_mode=converter_kwargs["command_mode"],
        )

        def progress_callback(items_processed: int) -> None:
            if items_processed % 1000 == 0:
                print(f"  Processed {items_processed:,} items...")

        try:
            result = adapter.convert_streaming(
                str(path),
                progress_callback=progress_callback,
            )
        except Exception as exc:
            print(f"Streaming conversion error: {exc}")
            return 1

        if not result.success:
            error_message = result.error_message or "unknown error"
            print(f"Streaming conversion failed: {error_message}")
            return 1

        payload = result.data or {}
        definition = payload.get("definition")
        conversion_result = payload.get("conversion_result")

        if conversion_result is not None:
            print_conversion_summary(conversion_result, heading="CONVERSION SUMMARY")

        if definition is None:
            print("Streaming conversion returned no definition from adapter.")
            return 1

        print("Streaming conversion complete!")
        print(result.stats.get_summary())

        if getattr(args, 'dry_run', False):
            print("\nDry run - saving to file...")
            output_path = Path(getattr(args, 'output', None) or f"{ontology_name}_fabric.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(definition, f, indent=2)
            print(f"  ✓ Definition saved to: {output_path}")
        else:
            print("\nUploading to Fabric...")
            client = self._get_fabric_client(args)
            if client is None:
                return 1

            try:
                upload_result = client.create_ontology(
                    display_name=ontology_name,
                    description=f"Imported from DTDL: {path.name}",
                    definition=definition
                )
                ontology_id = upload_result.get('id') if isinstance(upload_result, dict) else upload_result
                print(f"  ✓ Upload successful! Ontology ID: {ontology_id}")
            except Exception as exc:
                print(f"  ✗ Upload failed: {exc}")
                return 1

        print("\n=== Import complete ===")
        return 0

    def _get_fabric_client(self, args: argparse.Namespace):
        """Resolve Fabric configuration and return a client instance.
        
        Uses create_client() factory which respects FABRIC_USE_SDK environment
        variable to select between SDK and legacy client.
        """
        if getattr(args, 'config', None):
            self.config_path = args.config

        try:
            config_data = self.config
        except (FileNotFoundError, PermissionError, ValueError, IOError) as exc:
            print(f"  ✗ {exc}")
            return None

        try:
            fabric_config = FabricConfig.from_dict(config_data)
        except Exception as exc:
            print(f"  ✗ Invalid Fabric configuration: {exc}")
            return None

        logger.debug("Loaded Fabric config from %s", self.config_path)

        if not fabric_config.workspace_id or fabric_config.workspace_id == "YOUR_WORKSPACE_ID":
            print("  ✗ Configuration Error: Please configure your Fabric workspace_id in config.json")
            return None

        return create_client(fabric_config)
