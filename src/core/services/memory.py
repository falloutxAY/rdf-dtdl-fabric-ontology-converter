"""
Memory management utilities for resource-constrained operations.

This module provides memory monitoring and pre-flight checks to prevent
out-of-memory crashes when processing large files like RDF ontologies.

Example:
    ```python
    from core.memory import MemoryManager
    
    # Check if we have enough memory before loading a large file
    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    can_proceed, message = MemoryManager.check_memory_available(file_size_mb)
    
    if not can_proceed:
        print(f"Error: {message}")
        sys.exit(1)
    
    # Proceed with file loading
    data = load_large_file(filepath)
    ```
"""

import logging
from typing import Tuple

# Optional dependency for memory monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


# Import centralized constants - fallback to hardcoded if not available
try:
    from ..constants import MemoryLimits
    _MIN_AVAILABLE_MB = MemoryLimits.MIN_AVAILABLE_MEMORY_MB // 2  # 256MB minimum
    _MAX_SAFE_FILE_MB = MemoryLimits.MAX_SAFE_FILE_MB
    _MEMORY_MULTIPLIER = MemoryLimits.MEMORY_MULTIPLIER
except ImportError:
    # Fallback values if constants module not available
    _MIN_AVAILABLE_MB = 256
    _MAX_SAFE_FILE_MB = 500
    _MEMORY_MULTIPLIER = 3.5


class MemoryManager:
    """
    Manage memory usage during file parsing to prevent out-of-memory crashes.
    
    Provides pre-flight memory checks before loading large files
    to fail gracefully with helpful error messages instead of crashing.
    
    The memory estimation is based on RDFlib parsing characteristics,
    which typically use 3-4x the file size during graph construction.
    
    Attributes:
        MIN_AVAILABLE_MB: Minimum free memory required (256MB default)
        MAX_SAFE_FILE_MB: Maximum safe file size without --force (500MB)
        MEMORY_MULTIPLIER: Estimated memory/file size ratio (3.5x)
        LOAD_FACTOR: Fraction of available memory to use as safe threshold (0.7)
    
    Example:
        ```python
        # Basic usage
        file_mb = 100.0
        can_proceed, msg = MemoryManager.check_memory_available(file_mb)
        
        # Force proceed for large files (with warning)
        can_proceed, msg = MemoryManager.check_memory_available(600.0, force=True)
        
        # Monitor current usage
        current_mb = MemoryManager.get_memory_usage_mb()
        available_mb = MemoryManager.get_available_memory_mb()
        ```
    """
    
    MIN_AVAILABLE_MB = _MIN_AVAILABLE_MB
    MAX_SAFE_FILE_MB = _MAX_SAFE_FILE_MB
    MEMORY_MULTIPLIER = _MEMORY_MULTIPLIER
    LOAD_FACTOR = 0.7  # Only use 70% of available memory as safe threshold
    
    @staticmethod
    def get_available_memory_mb() -> float:
        """
        Get available system memory in MB.
        
        Uses psutil to query the operating system for current available
        memory. If psutil is not installed, returns infinity to allow
        operations to proceed (with a warning logged).
        
        Returns:
            Available memory in MB, or float('inf') if detection fails.
        """
        if not PSUTIL_AVAILABLE:
            logger.warning(
                "psutil not available - cannot check memory. "
                "Install with: pip install psutil"
            )
            return float('inf')  # Assume unlimited if we can't check
        
        try:
            mem_info = psutil.virtual_memory()
            available_mb = mem_info.available / (1024 * 1024)
            return available_mb
        except Exception as e:
            logger.warning(f"Could not determine available memory: {e}")
            return MemoryManager.MIN_AVAILABLE_MB
    
    @staticmethod
    def get_memory_usage_mb() -> float:
        """
        Get current process memory usage in MB.
        
        Returns the Resident Set Size (RSS) of the current process,
        which represents the actual physical memory being used.
        
        Returns:
            Current memory usage in MB, or 0.0 if detection fails.
        """
        if not PSUTIL_AVAILABLE:
            return 0.0
        
        try:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0
    
    @staticmethod
    def get_memory_percent() -> float:
        """
        Get current memory usage as percentage of total.
        
        Returns:
            Memory usage percentage (0-100), or 0.0 if detection fails.
        """
        if not PSUTIL_AVAILABLE:
            return 0.0
        
        try:
            mem_info = psutil.virtual_memory()
            return mem_info.percent
        except Exception:
            return 0.0
    
    @classmethod
    def check_memory_available(
        cls, 
        file_size_mb: float, 
        force: bool = False
    ) -> Tuple[bool, str]:
        """
        Check if enough memory is available to parse a file.
        
        Performs multiple checks:
        1. File size against hard limit (unless force=True)
        2. Available system memory against minimum threshold
        3. Estimated memory usage against safe threshold
        
        Args:
            file_size_mb: Size of the file in MB.
            force: If True, skip safety checks and allow large files
                   (still warns if limits exceeded).
            
        Returns:
            Tuple of (can_proceed: bool, message: str) where:
            - can_proceed: True if it's safe to proceed
            - message: Description of the check result or error
        
        Example:
            ```python
            # Check a 50MB file
            ok, msg = MemoryManager.check_memory_available(50.0)
            print(msg)  # "Memory OK: File 50.0MB, estimated usage ~175MB of 8000MB available"
            
            # Force a large file
            ok, msg = MemoryManager.check_memory_available(600.0, force=True)
            print(msg)  # "WARNING: File may exceed safe memory limits..."
            ```
        """
        # Estimate memory required (RDFlib uses ~3-4x file size)
        estimated_usage_mb = file_size_mb * cls.MEMORY_MULTIPLIER
        
        # Check against hard limit unless forced
        if not force and file_size_mb > cls.MAX_SAFE_FILE_MB:
            return False, (
                f"File size ({file_size_mb:.1f}MB) exceeds safe limit "
                f"({cls.MAX_SAFE_FILE_MB}MB). "
                f"Estimated memory required: ~{estimated_usage_mb:.0f}MB. "
                f"To process anyway, use --force flag or split into smaller files."
            )
        
        # Check available system memory
        available_mb = cls.get_available_memory_mb()
        
        if available_mb == float('inf'):
            # Can't check memory, proceed with warning
            return True, (
                f"Memory check unavailable. "
                f"Proceeding with {file_size_mb:.1f}MB file."
            )
        
        # Check minimum available memory
        if available_mb < cls.MIN_AVAILABLE_MB:
            return False, (
                f"Insufficient free memory. "
                f"Available: {available_mb:.0f}MB, "
                f"Minimum required: {cls.MIN_AVAILABLE_MB}MB. "
                f"Close other applications or increase available memory."
            )
        
        # Check if estimated usage exceeds safe threshold
        safe_threshold_mb = available_mb * cls.LOAD_FACTOR
        
        if estimated_usage_mb > safe_threshold_mb:
            if force:
                return True, (
                    f"WARNING: File may exceed safe memory limits. "
                    f"File: {file_size_mb:.1f}MB, "
                    f"Estimated usage: ~{estimated_usage_mb:.0f}MB, "
                    f"Safe threshold: {safe_threshold_mb:.0f}MB. "
                    f"Proceeding due to --force flag."
                )
            return False, (
                f"Ontology may be too large for available memory. "
                f"File size: {file_size_mb:.1f}MB, "
                f"Estimated parsing memory: ~{estimated_usage_mb:.0f}MB, "
                f"Safe threshold: {safe_threshold_mb:.0f}MB "
                f"(Available: {available_mb:.0f}MB). "
                f"Recommendation: Split into smaller files, "
                f"increase available memory, or use --force to proceed anyway."
            )
        
        return True, (
            f"Memory OK: File {file_size_mb:.1f}MB, "
            f"estimated usage ~{estimated_usage_mb:.0f}MB "
            f"of {available_mb:.0f}MB available"
        )
    
    @classmethod
    def format_memory_status(cls) -> str:
        """
        Get formatted string of current memory status.
        
        Useful for logging and diagnostics.
        
        Returns:
            Human-readable memory status string.
        """
        if not PSUTIL_AVAILABLE:
            return "Memory status: psutil not available"
        
        try:
            mem_info = psutil.virtual_memory()
            process = psutil.Process()
            proc_mem = process.memory_info()
            
            return (
                f"Memory status: "
                f"System {mem_info.percent:.1f}% used "
                f"({mem_info.available / (1024**3):.1f}GB available), "
                f"Process using {proc_mem.rss / (1024**2):.1f}MB"
            )
        except Exception as e:
            return f"Memory status: Error - {e}"
