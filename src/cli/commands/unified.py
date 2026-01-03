"""
Unified CLI command implementations.

This module provides format-agnostic command wrappers that delegate to
the appropriate RDF or DTDL handlers based on the --format flag.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Optional

# Ensure src directory is in path for late imports
_src_dir = str(Path(__file__).parent.parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from .base import BaseCommand, print_conversion_summary

try:
    from ..format import Format
except ImportError:
    from cli.format import Format

try:
    from ..helpers import (
        load_config,
        get_default_config_path,
        setup_logging,
        print_header,
        print_footer,
        confirm_action,
    )
except ImportError:
    from cli.helpers import (
        load_config,
        get_default_config_path,
        setup_logging,
        print_header,
        print_footer,
        confirm_action,
    )


logger = logging.getLogger(__name__)


# ============================================================================
# Unified Validate Command
# ============================================================================

class ValidateCommand(BaseCommand):
    """
    Unified validate command supporting both RDF and DTDL formats.
    
    Usage:
        validate --format rdf <path> [options]
        validate --format dtdl <path> [options]
    """
    
    def execute(self, args: argparse.Namespace) -> int:
        """Execute validation based on the specified format."""
        fmt = Format(args.format)
        
        if fmt == Format.RDF:
            return self._validate_rdf(args)
        elif fmt == Format.DTDL:
            return self._validate_dtdl(args)
        else:
            print(f"✗ Unsupported format: {fmt}")
            return 1
    
    def _validate_rdf(self, args: argparse.Namespace) -> int:
        """Delegate to RDF validation logic."""
        from rdf import InputValidator, validate_ttl_content
        import json
        
        self.setup_logging_from_config()
        
        path = Path(args.path)
        
        # Handle directory with --recursive
        if path.is_dir():
            if not getattr(args, 'recursive', False):
                print(f"✗ '{path}' is a directory. Use --recursive to process all TTL files.")
                return 1
            return self._validate_rdf_batch(args, path)
        
        # Single file validation
        try:
            allow_up = getattr(args, 'allow_relative_up', False)
            validated_path = InputValidator.validate_input_ttl_path(str(path), allow_relative_up=allow_up)
        except ValueError as e:
            print(f"✗ Invalid file path: {e}")
            return 1
        except FileNotFoundError:
            print(f"✗ File not found: {path}")
            return 1
        except PermissionError:
            print(f"✗ Permission denied: {path}")
            return 1
        
        print(f"✓ Validating RDF file: {validated_path}\n")
        
        try:
            with open(validated_path, 'r', encoding='utf-8') as f:
                ttl_content = f.read()
        except UnicodeDecodeError as e:
            print(f"✗ Encoding error: File is not valid UTF-8\n  {e}")
            return 1
        except Exception as e:
            print(f"✗ Error reading file: {e}")
            return 1
        
        report = validate_ttl_content(ttl_content, str(validated_path))
        
        # Display results
        if args.verbose:
            print(report.get_human_readable_summary())
        else:
            print_header("VALIDATION RESULT")
            if report.can_import_seamlessly:
                print("✓ This ontology can be imported SEAMLESSLY.")
            else:
                print("✗ Issues detected that may affect conversion quality.")
                print(f"\nTotal Issues: {report.total_issues}")
                print(f"  - Errors:   {report.issues_by_severity.get('error', 0)}")
                print(f"  - Warnings: {report.issues_by_severity.get('warning', 0)}")
                print(f"  - Info:     {report.issues_by_severity.get('info', 0)}")
            print_footer()
        
        # Save report if requested
        if args.output:
            report.save_to_file(args.output)
            print(f"\nReport saved to: {args.output}")
        elif args.save_report:
            output_path = str(Path(args.path).with_suffix('.validation.json'))
            report.save_to_file(output_path)
            print(f"\nReport saved to: {output_path}")
        
        if report.can_import_seamlessly:
            return 0
        elif report.issues_by_severity.get('error', 0) > 0:
            return 2
        else:
            return 1
    
    def _validate_rdf_batch(self, args: argparse.Namespace, directory: Path) -> int:
        """Validate all RDF files in a directory."""
        from rdf import InputValidator, validate_ttl_content
        import json
        
        pattern = "**/*.ttl" if args.recursive else "*.ttl"
        files = list(directory.glob(pattern))
        for ext in [".rdf", ".owl"]:
            ext_pattern = f"**/*{ext}" if args.recursive else f"*{ext}"
            files.extend(directory.glob(ext_pattern))
        files = sorted(set(files))
        
        if not files:
            print(f"✗ No RDF files found in '{directory}'")
            return 1
        
        print(f"Found {len(files)} RDF file(s) to validate\n")
        
        successes, failures = [], []
        all_reports = []
        
        for i, f in enumerate(files, 1):
            print(f"[{i}/{len(files)}] {f.name}")
            try:
                validated_path = InputValidator.validate_input_ttl_path(str(f))
                with open(validated_path, 'r', encoding='utf-8') as fp:
                    content = fp.read()
                report = validate_ttl_content(content, str(validated_path))
                all_reports.append((f.name, report))
                if report.can_import_seamlessly:
                    successes.append(str(f))
                    print("  ✓ Valid")
                else:
                    errors = report.issues_by_severity.get('error', 0)
                    if errors > 0:
                        failures.append((str(f), f"{errors} errors"))
                        print(f"  ✗ {errors} errors")
                    else:
                        successes.append(str(f))
                        print(f"  ⚠ warnings only")
            except Exception as e:
                failures.append((str(f), str(e)))
                print(f"  ✗ Error: {e}")
        
        print(f"\n{'='*60}")
        print(f"BATCH VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total: {len(files)}, Successful: {len(successes)}, Failed: {len(failures)}")
        
        if args.output:
            combined = {
                "total_files": len(files),
                "successful": len(successes),
                "failed": len(failures),
                "reports": [{"file": n, "summary": r.to_dict()} for n, r in all_reports]
            }
            with open(args.output, 'w', encoding='utf-8') as fp:
                json.dump(combined, fp, indent=2)
            print(f"\nCombined report saved to: {args.output}")
        
        return 0 if not failures else 1
    
    def _validate_dtdl(self, args: argparse.Namespace) -> int:
        """Delegate to DTDL validation logic."""
        import json
        
        try:
            from dtdl.dtdl_parser import DTDLParser, ParseError
            from dtdl.dtdl_validator import DTDLValidator
        except ImportError:
            print("✗ DTDL module not found. Ensure src/dtdl/ exists.")
            return 1
        
        path = Path(args.path)
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
                print(f"✗ Path does not exist: {path}")
                return 2
        except ParseError as e:
            print(f"✗ Parse error: {e}")
            return 2
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            return 2
        
        if result.errors:
            print(f"Found {len(result.errors)} parse errors:")
            for err in result.errors[:10]:
                print(f"  - {err}")
            if not getattr(args, 'continue_on_error', False):
                return 2
        
        print(f"Parsed {len(result.interfaces)} interfaces")
        
        validation_result = validator.validate(result.interfaces)
        
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
            for err in validation_result.errors[:10]:
                print(f"  - [{err.level.value}] {err.dtmi or 'unknown'}: {err.message}")
            exit_code = 1
        else:
            if validation_result.warnings:
                print(f"Found {len(validation_result.warnings)} warnings:")
                for w in validation_result.warnings[:10]:
                    print(f"  - {w.dtmi or 'unknown'}: {w.message}")
            print("✓ Validation successful!")
            exit_code = 0
        
        if getattr(args, 'verbose', False):
            print("\nInterface Summary:")
            for iface in result.interfaces[:20]:
                print(f"  {iface.name} ({iface.dtmi})")
                print(f"    Props: {len(iface.properties)}, Telemetry: {len(iface.telemetries)}, Rels: {len(iface.relationships)}")
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2)
            print(f"\nReport saved to: {args.output}")
        elif args.save_report:
            auto_path = f"{path}.validation.json" if path.is_file() else f"{path.name}.validation.json"
            with open(auto_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2)
            print(f"\nReport saved to: {auto_path}")
        
        return exit_code


# ============================================================================
# Unified Convert Command
# ============================================================================

class ConvertCommand(BaseCommand):
    """
    Unified convert command supporting both RDF and DTDL formats.
    
    Usage:
        convert --format rdf <path> [options]
        convert --format dtdl <path> [options]
    """
    
    def execute(self, args: argparse.Namespace) -> int:
        """Execute conversion based on the specified format."""
        fmt = Format(args.format)
        
        if fmt == Format.RDF:
            return self._convert_rdf(args)
        elif fmt == Format.DTDL:
            return self._convert_dtdl(args)
        else:
            print(f"✗ Unsupported format: {fmt}")
            return 1
    
    def _convert_rdf(self, args: argparse.Namespace) -> int:
        """Delegate to RDF conversion logic."""
        from rdf import InputValidator, parse_ttl_with_result, parse_ttl_streaming, StreamingRDFConverter
        import json
        
        self.setup_logging_from_config()
        
        path = Path(args.path)
        
        if path.is_dir():
            if not getattr(args, 'recursive', False):
                print(f"✗ '{path}' is a directory. Use --recursive to process all files.")
                return 1
            return self._convert_rdf_batch(args, path)
        
        try:
            allow_up = getattr(args, 'allow_relative_up', False)
            validated_path = InputValidator.validate_input_ttl_path(str(path), allow_relative_up=allow_up)
        except (ValueError, FileNotFoundError, PermissionError) as e:
            print(f"✗ Invalid file path: {e}")
            return 1
        
        print(f"✓ Converting RDF file: {validated_path}")
        
        force_memory = getattr(args, 'force_memory', False)
        use_streaming = getattr(args, 'streaming', False)
        
        file_size_mb = validated_path.stat().st_size / (1024 * 1024)
        if file_size_mb > StreamingRDFConverter.STREAMING_THRESHOLD_MB and not use_streaming:
            print(f"⚠️  Large file ({file_size_mb:.1f} MB). Consider using --streaming.")
        
        try:
            if use_streaming:
                print("Using streaming mode...")
                definition, ontology_name, conversion_result = parse_ttl_streaming(str(validated_path))
            else:
                with open(validated_path, 'r', encoding='utf-8') as f:
                    ttl_content = f.read()
                definition, ontology_name, conversion_result = parse_ttl_with_result(
                    ttl_content, force_large_file=force_memory
                )
        except ValueError as e:
            print(f"✗ Invalid RDF content: {e}")
            return 1
        except MemoryError as e:
            print(f"✗ {e}\n\nTip: Use --streaming for large files.")
            return 1
        except Exception as e:
            print(f"✗ Error parsing file: {e}")
            return 1
        
        print("\n" + conversion_result.get_summary())
        
        output = {
            "displayName": args.ontology_name or ontology_name,
            "description": args.description or f"Converted from {validated_path.name}",
            "definition": definition,
            "conversionResult": conversion_result.to_dict()
        }
        
        output_path = args.output or str(validated_path.with_suffix('.json'))
        
        try:
            validated_output = InputValidator.validate_output_file_path(output_path, allowed_extensions=['.json'])
            with open(validated_output, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2)
        except Exception as e:
            print(f"✗ Error writing output: {e}")
            return 1
        
        print(f"\nSaved to: {validated_output}")
        return 0
    
    def _convert_rdf_batch(self, args: argparse.Namespace, directory: Path) -> int:
        """Convert all RDF files in a directory."""
        from rdf import InputValidator, parse_ttl_with_result
        import json
        
        pattern = "**/*.ttl" if args.recursive else "*.ttl"
        files = list(directory.glob(pattern))
        for ext in [".rdf", ".owl"]:
            ext_pattern = f"**/*{ext}" if args.recursive else f"*{ext}"
            files.extend(directory.glob(ext_pattern))
        files = sorted(set(files))
        
        if not files:
            print(f"✗ No RDF files found in '{directory}'")
            return 1
        
        print(f"Found {len(files)} RDF file(s) to convert\n")
        
        successes, failures = [], []
        output_dir = Path(args.output) if args.output else directory
        if args.output:
            output_dir.mkdir(parents=True, exist_ok=True)
        
        for i, f in enumerate(files, 1):
            print(f"[{i}/{len(files)}] {f.name}")
            try:
                validated_path = InputValidator.validate_input_ttl_path(str(f))
                with open(validated_path, 'r', encoding='utf-8') as fp:
                    content = fp.read()
                definition, ontology_name, conversion_result = parse_ttl_with_result(content)
                output = {
                    "displayName": ontology_name,
                    "description": f"Converted from {f.name}",
                    "definition": definition,
                    "conversionResult": conversion_result.to_dict()
                }
                output_file = output_dir / f"{f.stem}.json"
                with open(output_file, 'w', encoding='utf-8') as fp:
                    json.dump(output, fp, indent=2)
                successes.append(str(f))
                print(f"  ✓ {output_file}")
            except Exception as e:
                failures.append((str(f), str(e)))
                print(f"  ✗ {e}")
        
        print(f"\n{'='*60}")
        print(f"BATCH CONVERSION SUMMARY")
        print(f"{'='*60}")
        print(f"Total: {len(files)}, Successful: {len(successes)}, Failed: {len(failures)}")
        
        return 0 if not failures else 1
    
    def _convert_dtdl(self, args: argparse.Namespace) -> int:
        """Delegate to DTDL conversion logic."""
        import json
        
        try:
            from dtdl.dtdl_parser import DTDLParser
            from dtdl.dtdl_validator import DTDLValidator
            from dtdl.dtdl_converter import DTDLToFabricConverter
        except ImportError:
            print("✗ DTDL module not found.")
            return 1
        
        path = Path(args.path)
        use_streaming = getattr(args, 'streaming', False)
        
        if use_streaming:
            return self._convert_dtdl_streaming(args, path)
        
        print(f"Parsing DTDL from: {path}")
        parser = DTDLParser()
        
        try:
            if path.is_file():
                result = parser.parse_file(str(path))
            else:
                recursive = getattr(args, 'recursive', False)
                result = parser.parse_directory(str(path), recursive=recursive)
        except Exception as e:
            print(f"✗ Parse error: {e}")
            return 2
        
        if result.errors:
            print(f"✗ Parse errors: {len(result.errors)}")
            return 2
        
        print(f"Parsed {len(result.interfaces)} interfaces")
        
        validator = DTDLValidator()
        validation_result = validator.validate(result.interfaces)
        
        if validation_result.errors:
            print(f"✗ Validation errors: {len(validation_result.errors)}")
            for err in validation_result.errors[:5]:
                print(f"  - {err.message}")
            return 1
        
        converter = DTDLToFabricConverter(
            namespace=getattr(args, 'namespace', 'usertypes'),
            flatten_components=getattr(args, 'flatten_components', False),
        )
        
        conversion_result = converter.convert(result.interfaces)
        ontology_name = args.ontology_name or path.stem
        definition = converter.to_fabric_definition(conversion_result, ontology_name)
        
        output_path = Path(args.output or f"{ontology_name}_fabric.json")
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
    
    def _convert_dtdl_streaming(self, args, path: Path) -> int:
        """Convert DTDL using streaming mode."""
        import json
        
        try:
            from core.streaming import StreamingEngine, DTDLStreamReader, DTDLChunkProcessor, StreamConfig
        except ImportError:
            print("✗ Streaming module not available.")
            return 1
        
        print("Using streaming mode...")
        
        config = StreamConfig(chunk_size=10000, memory_threshold_mb=100.0, enable_progress=True)
        engine = StreamingEngine(
            reader=DTDLStreamReader(),
            processor=DTDLChunkProcessor(
                namespace=getattr(args, 'namespace', 'usertypes'),
                flatten_components=getattr(args, 'flatten_components', False),
            ),
            config=config
        )
        
        def progress(n: int) -> None:
            if n % 1000 == 0:
                print(f"  Processed {n:,} items...")
        
        try:
            result = engine.process_file(str(path), progress_callback=progress)
            if not result.success:
                print(f"✗ Streaming failed: {result.error}")
                return 1
            
            ontology_name = args.ontology_name or path.stem
            output_path = Path(args.output or f"{ontology_name}_fabric.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result.data, f, indent=2)
            
            print("Streaming conversion complete!")
            print(result.stats.get_summary())
            print(f"  Output: {output_path}")
            return 0
        except Exception as e:
            print(f"✗ Streaming error: {e}")
            return 1


# ============================================================================
# Unified Upload Command
# ============================================================================

class UploadCommand(BaseCommand):
    """
    Unified upload command supporting both RDF and DTDL formats.
    
    Usage:
        upload --format rdf <path> [options]
        upload --format dtdl <path> [options]
    """
    
    def execute(self, args: argparse.Namespace) -> int:
        """Execute upload based on the specified format."""
        fmt = Format(args.format)
        
        if fmt == Format.RDF:
            return self._upload_rdf(args)
        elif fmt == Format.DTDL:
            return self._upload_dtdl(args)
        else:
            print(f"✗ Unsupported format: {fmt}")
            return 1
    
    def _upload_rdf(self, args: argparse.Namespace) -> int:
        """Delegate to RDF upload logic."""
        from rdf import (
            InputValidator, parse_ttl_with_result, parse_ttl_streaming,
            StreamingRDFConverter, validate_ttl_content, IssueSeverity
        )
        from core import FabricConfig, FabricOntologyClient, FabricAPIError
        from core import setup_cancellation_handler, restore_default_handler, OperationCancelledException
        import os
        
        cancellation_token = setup_cancellation_handler(message="\n⚠️  Cancellation requested...")
        
        try:
            config_path = args.config or get_default_config_path()
            try:
                config_data = load_config(config_path)
            except Exception as e:
                print(f"✗ {e}")
                return 1
            
            fabric_config = FabricConfig.from_dict(config_data)
            if not fabric_config.workspace_id or fabric_config.workspace_id == "YOUR_WORKSPACE_ID":
                print("✗ Please configure workspace_id in config.json")
                return 1
            
            setup_logging(config=config_data.get('logging', {}))
            
            path = Path(args.path)
            
            if path.is_dir():
                if not getattr(args, 'recursive', False):
                    print(f"✗ '{path}' is a directory. Use --recursive.")
                    return 1
                return self._upload_rdf_batch(args, path, config_data, fabric_config)
            
            try:
                allow_up = getattr(args, 'allow_relative_up', False)
                validated_path = InputValidator.validate_input_ttl_path(str(path), allow_relative_up=allow_up)
            except (ValueError, FileNotFoundError, PermissionError) as e:
                print(f"✗ {e}")
                return 1
            
            with open(validated_path, 'r', encoding='utf-8') as f:
                ttl_content = f.read()
            
            if not ttl_content.strip():
                print(f"✗ File is empty: {path}")
                return 1
            
            # Pre-flight validation
            validation_report = None
            if not args.skip_validation:
                print_header("PRE-FLIGHT VALIDATION")
                validation_report = validate_ttl_content(ttl_content, str(path))
                if validation_report.can_import_seamlessly:
                    print("✓ Ontology can be imported seamlessly.")
                else:
                    print(f"⚠ Issues detected: {validation_report.total_issues}")
                    if not args.force:
                        if not confirm_action("Proceed anyway?"):
                            print("Upload cancelled.")
                            return 0
                print_footer()
            
            # Convert
            id_prefix = config_data.get('ontology', {}).get('id_prefix', 1000000000000)
            force_memory = getattr(args, 'force_memory', False)
            use_streaming = getattr(args, 'streaming', False)
            
            if use_streaming:
                definition, extracted_name, conversion_result = parse_ttl_streaming(
                    str(validated_path), id_prefix=id_prefix, cancellation_token=cancellation_token
                )
            else:
                definition, extracted_name, conversion_result = parse_ttl_with_result(
                    ttl_content, id_prefix, force_large_file=force_memory
                )
            
            print_conversion_summary(conversion_result, heading="CONVERSION SUMMARY")
            
            if conversion_result.has_skipped_items and not args.force:
                print("⚠ Some items were skipped.")
                if not confirm_action("Proceed with upload?"):
                    print("Upload cancelled.")
                    return 0
            
            # Dry-run check
            if args.dry_run:
                import json
                output_path = args.output or f"{extracted_name or 'output'}_fabric.json"
                output = {
                    "displayName": args.ontology_name or extracted_name,
                    "description": args.description or f"Converted from {path.name}",
                    "definition": definition,
                }
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(output, f, indent=2)
                print(f"\n✓ Dry-run: saved to {output_path}")
                return 0
            
            # Upload
            ontology_name = args.ontology_name or extracted_name
            description = args.description or f"Imported from {os.path.basename(str(path))}"
            
            client = FabricOntologyClient(fabric_config)
            
            try:
                result = client.create_or_update_ontology(
                    display_name=ontology_name,
                    description=description,
                    definition=definition,
                    wait_for_completion=True,
                    cancellation_token=cancellation_token,
                )
                print(f"✓ Successfully uploaded '{ontology_name}'")
                print(f"  Ontology ID: {result.get('id', 'Unknown')}")
                return 0
            except FabricAPIError as e:
                print(f"✗ Fabric API error: {e.message}")
                if e.error_code == "ItemDisplayNameAlreadyInUse":
                    print("  Hint: Use --update to update existing ontology.")
                return 1
        
        except OperationCancelledException:
            print("\n✗ Upload cancelled.")
            return 130
        finally:
            restore_default_handler()
    
    def _upload_rdf_batch(self, args, directory: Path, config_data: dict, fabric_config) -> int:
        """Upload all RDF files in a directory."""
        from rdf import InputValidator, parse_ttl_with_result
        from core import FabricOntologyClient
        
        pattern = "**/*.ttl" if args.recursive else "*.ttl"
        files = list(directory.glob(pattern))
        for ext in [".rdf", ".owl"]:
            ext_pattern = f"**/*{ext}" if args.recursive else f"*{ext}"
            files.extend(directory.glob(ext_pattern))
        files = sorted(set(files))
        
        if not files:
            print(f"✗ No RDF files found in '{directory}'")
            return 1
        
        print(f"Found {len(files)} RDF file(s) to upload\n")
        
        if not args.force:
            if not confirm_action(f"Upload {len(files)} files to Fabric?"):
                print("Upload cancelled.")
                return 0
        
        successes, failures = [], []
        id_prefix = config_data.get('ontology', {}).get('id_prefix', 1000000000000)
        client = FabricOntologyClient(fabric_config)
        
        for i, f in enumerate(files, 1):
            print(f"[{i}/{len(files)}] {f.name}")
            try:
                validated_path = InputValidator.validate_input_ttl_path(str(f))
                with open(validated_path, 'r', encoding='utf-8') as fp:
                    content = fp.read()
                definition, extracted_name, _ = parse_ttl_with_result(content, id_prefix)
                ontology_name = args.ontology_name or extracted_name or f.stem
                description = args.description or f"Batch imported from {f.name}"
                result = client.create_or_update_ontology(
                    display_name=ontology_name,
                    description=description,
                    definition=definition,
                    wait_for_completion=True,
                )
                successes.append(str(f))
                print(f"  ✓ ID: {result.get('id', 'N/A')}")
            except Exception as e:
                failures.append((str(f), str(e)))
                print(f"  ✗ {e}")
        
        print(f"\n{'='*60}")
        print(f"BATCH UPLOAD SUMMARY")
        print(f"{'='*60}")
        print(f"Total: {len(files)}, Successful: {len(successes)}, Failed: {len(failures)}")
        
        return 0 if not failures else 1
    
    def _upload_dtdl(self, args: argparse.Namespace) -> int:
        """Delegate to DTDL upload logic."""
        import json
        
        try:
            from dtdl.dtdl_parser import DTDLParser
            from dtdl.dtdl_validator import DTDLValidator
            from dtdl.dtdl_converter import DTDLToFabricConverter
        except ImportError:
            print("✗ DTDL module not found.")
            return 1
        
        path = Path(args.path)
        ontology_name = args.ontology_name or path.stem
        
        print(f"=== DTDL Upload: {path} ===")
        
        # Parse
        print("\nStep 1: Parsing...")
        parser = DTDLParser()
        
        try:
            if path.is_file():
                result = parser.parse_file(str(path))
            else:
                recursive = getattr(args, 'recursive', False)
                result = parser.parse_directory(str(path), recursive=recursive)
        except Exception as e:
            print(f"  ✗ Parse error: {e}")
            return 2
        
        if result.errors:
            print(f"  ✗ Parse errors: {len(result.errors)}")
            return 2
        
        print(f"  ✓ Parsed {len(result.interfaces)} interfaces")
        
        # Validate
        print("\nStep 2: Validating...")
        validator = DTDLValidator()
        validation_result = validator.validate(result.interfaces)
        
        if validation_result.errors:
            print(f"  ✗ Validation errors: {len(validation_result.errors)}")
            if not args.force:
                return 1
        
        print("  ✓ Validation passed")
        
        # Convert
        print("\nStep 3: Converting...")
        converter = DTDLToFabricConverter(
            namespace=getattr(args, 'namespace', 'usertypes'),
            flatten_components=getattr(args, 'flatten_components', False),
        )
        
        conversion_result = converter.convert(result.interfaces)
        definition = converter.to_fabric_definition(conversion_result, ontology_name)
        
        print_conversion_summary(conversion_result, heading="CONVERSION SUMMARY")
        
        # Dry-run or upload
        if args.dry_run:
            print("\nStep 4: Dry run - saving to file...")
            output_path = Path(args.output or f"{ontology_name}_fabric.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(definition, f, indent=2)
            print(f"  ✓ Saved to: {output_path}")
        else:
            print("\nStep 4: Uploading...")
            
            try:
                from core import FabricOntologyClient, FabricConfig
            except ImportError:
                print("  ✗ Could not import FabricOntologyClient")
                return 1
            
            config_path = args.config or get_default_config_path()
            try:
                config = FabricConfig.from_file(config_path)
            except Exception as e:
                print(f"  ✗ Config error: {e}")
                return 1
            
            client = FabricOntologyClient(config)
            
            try:
                result = client.create_ontology(
                    display_name=ontology_name,
                    description=f"Imported from DTDL: {path.name}",
                    definition=definition
                )
                ontology_id = result.get('id') if isinstance(result, dict) else result
                print(f"  ✓ Upload successful! Ontology ID: {ontology_id}")
            except Exception as e:
                print(f"  ✗ Upload failed: {e}")
                return 1
        
        print("\n=== Upload complete ===")
        return 0


# ============================================================================
# Export Command (RDF only)
# ============================================================================

class ExportCommand(BaseCommand):
    """
    Export an ontology from Fabric to TTL format (RDF only).
    
    Usage:
        export <ontology_id> [options]
    """
    
    def execute(self, args: argparse.Namespace) -> int:
        """Execute the export command."""
        from rdf import InputValidator, FabricToTTLConverter
        from core import FabricConfig, FabricOntologyClient, FabricAPIError
        
        config_path = args.config or get_default_config_path()
        
        try:
            config_data = load_config(config_path)
            setup_logging(config=config_data.get('logging', {}))
        except Exception as e:
            print(f"✗ {e}")
            return 1
        
        try:
            fabric_config = FabricConfig.from_dict(config_data)
        except Exception as e:
            print(f"✗ Configuration error: {e}")
            return 1
        
        client = FabricOntologyClient(fabric_config)
        ontology_id = args.ontology_id
        
        print(f"✓ Exporting ontology {ontology_id} to TTL...")
        
        try:
            ontology_info = client.get_ontology(ontology_id)
            definition = client.get_ontology_definition(ontology_id)
            
            if not definition:
                print("✗ Failed to get ontology definition")
                return 1
            
            fabric_definition = {
                "displayName": ontology_info.get("displayName", "exported_ontology"),
                "description": ontology_info.get("description", ""),
                "definition": definition
            }
            
            converter = FabricToTTLConverter()
            ttl_content = converter.convert(fabric_definition)
            
            if args.output:
                output_path = args.output
            else:
                safe_name = ontology_info.get("displayName", ontology_id).replace(" ", "_")
                output_path = f"{safe_name}_exported.ttl"
            
            try:
                validated_output = InputValidator.validate_output_file_path(
                    output_path, allowed_extensions=['.ttl', '.rdf', '.owl']
                )
            except Exception as e:
                print(f"✗ Invalid output path: {e}")
                return 1
            
            with open(validated_output, 'w', encoding='utf-8') as f:
                f.write(ttl_content)
            
            print(f"✓ Exported to: {validated_output}")
            print(f"  Ontology Name: {ontology_info.get('displayName', 'Unknown')}")
            print(f"  Parts: {len(definition.get('parts', []))}")
            
            return 0
            
        except FabricAPIError as e:
            print(f"✗ API Error: {e}")
            return 1
        except Exception as e:
            print(f"✗ Export failed: {e}")
            return 1
