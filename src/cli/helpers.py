"""
CLI helper utilities.

This module provides shared utilities for CLI commands including:
- Configuration loading
- Logging setup
- Path resolution
"""

import io
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, Literal

# Type alias for log levels
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def _ensure_utf8_stdout() -> None:
    """Ensure stdout can handle UTF-8 characters on Windows."""
    if sys.platform == 'win32':
        # Try to set console to UTF-8 mode
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, TypeError):
            # Fallback for older Python versions
            try:
                sys.stdout = io.TextIOWrapper(
                    sys.stdout.buffer, encoding='utf-8', errors='replace'
                )
            except AttributeError:
                pass  # Not a TTY, let it be


# Initialize UTF-8 output on module load
_ensure_utf8_stdout()


def get_default_config_path() -> str:
    """Get the default configuration file path.
    
    Returns:
        Path to the default config.json file in the src directory.
    """
    # Look for config.json in the src directory (where CLI modules live)
    cli_dir = Path(__file__).parent
    src_dir = cli_dir.parent
    return str(src_dir / "config.json")


def setup_logging(
    level: LogLevel = "INFO",
    log_file: Optional[str] = None
) -> Optional[str]:
    """
    Setup logging configuration with fallback locations.
    
    If the primary log file location fails (permission denied, disk full, etc.),
    attempts to write to fallback locations in order:
    1. Requested location
    2. System temp directory
    3. User home directory
    4. Console-only (final fallback)
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path. If None, logs to console only.
        
    Returns:
        The actual log file path used, or None if logging to console only.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    handlers = [logging.StreamHandler(sys.stdout)]
    actual_log_file = None
    
    if log_file:
        # Define fallback locations
        log_filename = os.path.basename(log_file) or "rdf_converter.log"
        fallback_locations = [
            log_file,  # Primary location
            os.path.join(tempfile.gettempdir(), log_filename),  # System temp
            os.path.join(Path.home(), log_filename),  # User home
        ]
        
        file_handler = None
        for fallback_path in fallback_locations:
            try:
                # Ensure directory exists
                log_dir = os.path.dirname(fallback_path)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
                
                # Try to create/open the file
                file_handler = logging.FileHandler(fallback_path, encoding='utf-8')
                handlers.append(file_handler)
                actual_log_file = fallback_path
                
                if fallback_path != log_file:
                    print(f"Note: Using fallback log file: {fallback_path}")
                break
                
            except PermissionError:
                print(f"  Could not create log at {fallback_path}: Permission denied")
                continue
            except OSError as e:
                print(f"  Could not create log at {fallback_path}: {e}")
                continue
            except Exception as e:
                print(f"  Unexpected error creating log at {fallback_path}: {e}")
                continue
        
        if not file_handler:
            print(f"Warning: Could not write log file to any location")
            print(f"  Requested: {log_file}")
            print(f"  Attempted fallbacks: {', '.join(fallback_locations[1:])}")
            print(f"  Logging to console only")
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
    )
    
    logger = logging.getLogger(__name__)
    if actual_log_file:
        logger.info(f"Logging to: {actual_log_file}")
    
    return actual_log_file


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a JSON file with path validation.
    
    Args:
        config_path: Path to the configuration file.
        
    Returns:
        Dictionary containing the configuration.
        
    Raises:
        ValueError: If config_path is empty or file contains invalid JSON.
        FileNotFoundError: If the configuration file doesn't exist.
        PermissionError: If the file cannot be read.
        IOError: If there's an error reading the file.
    """
    # Import InputValidator here to avoid circular imports
    from rdf_converter import InputValidator
    
    if not config_path:
        raise ValueError("config_path cannot be empty")
    
    # Validate config path (allow .json extension)
    try:
        validated_path = InputValidator.validate_file_path(
            config_path,
            allowed_extensions=['.json'],
            check_exists=True,
            check_readable=True
        )
    except (ValueError, FileNotFoundError, PermissionError) as e:
        # Re-raise with more context for config files
        if isinstance(e, FileNotFoundError):
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                f"Please create a config.json file or specify one with --config"
            )
        raise
    
    try:
        with open(validated_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON in configuration file {validated_path} at line {e.lineno}, column {e.colno}: {e.msg}"
        )
    except UnicodeDecodeError as e:
        raise ValueError(f"File encoding error in {validated_path}: {e}")
    except Exception as e:
        raise IOError(f"Error loading configuration file: {e}")
    
    if not isinstance(config, dict):
        raise ValueError(f"Configuration file must contain a JSON object, got {type(config)}")
    
    return config


def print_header(title: str, width: int = 60) -> None:
    """Print a formatted header with the given title.
    
    Args:
        title: The title to display in the header.
        width: Total width of the header line.
    """
    print("\n" + "=" * width)
    print(title)
    print("=" * width)


def print_footer(width: int = 60) -> None:
    """Print a footer line.
    
    Args:
        width: Total width of the footer line.
    """
    print("=" * width + "\n")


def format_count_summary(
    items: Dict[str, int],
    prefix: str = "  "
) -> str:
    """Format a dictionary of counts for display.
    
    Args:
        items: Dictionary mapping item names to counts.
        prefix: Prefix string for each line.
        
    Returns:
        Formatted multi-line string.
    """
    lines = []
    for name, count in sorted(items.items(), key=lambda x: -x[1]):
        lines.append(f"{prefix}{name}: {count}")
    return "\n".join(lines)


def confirm_action(
    prompt: str,
    default: bool = False
) -> bool:
    """
    Prompt the user for confirmation.
    
    Args:
        prompt: The prompt message to display.
        default: Default value if user just presses Enter.
        
    Returns:
        True if user confirmed, False otherwise.
    """
    suffix = "[Y/n]" if default else "[y/N]"
    response = input(f"{prompt} {suffix}: ").strip().lower()
    
    if not response:
        return default
    
    return response in ('y', 'yes')
