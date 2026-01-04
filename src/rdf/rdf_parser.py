"""
RDF Parser Module

This module handles TTL/RDF parsing with memory management and graph operations.
Extracted from rdf_converter.py for better maintainability.

Components:
- MemoryManager: Pre-flight memory checks before parsing large files
- RDFGraphParser: TTL parsing and graph creation with validation
"""

import logging
from pathlib import Path
from typing import Optional, Tuple, Union

from rdflib import Graph, ConjunctiveGraph
from rdflib.util import guess_format

logger = logging.getLogger(__name__)

# Check for psutil availability
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class MemoryManager:
    """
    Manage memory usage during RDF parsing to prevent out-of-memory crashes.
    
    Provides pre-flight memory checks before loading large ontology files
    to fail gracefully with helpful error messages instead of crashing.
    """
    
    # Import centralized constants - fallback to hardcoded if not available
    try:
        from constants import MemoryLimits
        MIN_AVAILABLE_MB = MemoryLimits.MIN_AVAILABLE_MEMORY_MB // 2  # 256MB minimum
        MAX_SAFE_FILE_MB = MemoryLimits.MAX_SAFE_FILE_MB
        MEMORY_MULTIPLIER = MemoryLimits.MEMORY_MULTIPLIER
    except ImportError:
        # Fallback values if constants module not available
        MIN_AVAILABLE_MB = 256
        MAX_SAFE_FILE_MB = 500
        MEMORY_MULTIPLIER = 3.5
    
    LOAD_FACTOR = 0.7  # Only use 70% of available memory as safe threshold
    
    @staticmethod
    def get_available_memory_mb() -> float:
        """
        Get available system memory in MB.
        
        Returns:
            Available memory in MB, or infinity if detection fails.
        """
        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available - cannot check memory. Install with: pip install psutil")
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
        
        Returns:
            Current memory usage in MB.
        """
        if not PSUTIL_AVAILABLE:
            return 0.0
        
        try:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0
    
    @classmethod
    def check_memory_available(cls, file_size_mb: float, force: bool = False) -> Tuple[bool, str]:
        """
        Check if enough memory is available to parse a file.
        
        Args:
            file_size_mb: Size of the file in MB.
            force: If True, skip safety checks and allow large files.
            
        Returns:
            Tuple of (can_proceed: bool, message: str)
        """
        # Estimate memory required (RDFlib uses ~3-4x file size)
        estimated_usage_mb = file_size_mb * cls.MEMORY_MULTIPLIER
        
        # Check against hard limit unless forced
        if not force and file_size_mb > cls.MAX_SAFE_FILE_MB:
            return False, (
                f"File size ({file_size_mb:.1f}MB) exceeds safe limit ({cls.MAX_SAFE_FILE_MB}MB). "
                f"Estimated memory required: ~{estimated_usage_mb:.0f}MB. "
                f"To process anyway, use --force flag or split into smaller files."
            )
        
        # Check available system memory
        available_mb = cls.get_available_memory_mb()
        
        if available_mb == float('inf'):
            # Can't check memory, proceed with warning
            return True, f"Memory check unavailable. Proceeding with {file_size_mb:.1f}MB file."
        
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
                f"Recommendation: Split into smaller files, increase available memory, or use --force to proceed anyway."
            )
        
        return True, (
            f"Memory OK: File {file_size_mb:.1f}MB, "
            f"estimated usage ~{estimated_usage_mb:.0f}MB of {available_mb:.0f}MB available"
        )
    
    @classmethod
    def log_memory_status(cls, context: str = "") -> None:
        """
        Log current memory status for debugging.
        
        Args:
            context: Optional context string to include in log message.
        """
        if not PSUTIL_AVAILABLE:
            return
        
        try:
            process_mb = cls.get_memory_usage_mb()
            available_mb = cls.get_available_memory_mb()
            prefix = f"[{context}] " if context else ""
            logger.debug(
                f"{prefix}Memory status: Process using {process_mb:.0f}MB, "
                f"System available: {available_mb:.0f}MB"
            )
        except Exception as e:
            logger.debug(f"Could not log memory status: {e}")


class RDFGraphParser:
    """
    Handles RDF parsing with memory management and validation.

    This class encapsulates the graph parsing logic, including:
    - Pre-flight memory checks
    - RDF content validation
    - Graph creation and parsing for multiple serializations
    - Error handling with helpful messages
    """

    SUPPORTED_FORMATS = {
        "turtle",
        "xml",       # RDF/XML & OWL
        "nt",        # N-Triples
        "n3",        # Notation3
        "trig",      # TriG dataset
        "nquads",    # N-Quads dataset
        "trix",      # TriX dataset
        "json-ld",   # JSON-LD
        "hext",      # HexTuples dataset
        "rdfa",      # RDFa embedded in HTML/XHTML
        "microdata", # HTML microdata
    }

    DATASET_FORMATS = {
        "trig",
        "nquads",
        "trix",
        "hext",
    }

    FORMAT_ALIASES = {
        "ttl": "turtle",
        "turtle": "turtle",
        "rdf": "xml",
        "rdfxml": "xml",
        "rdf-xml": "xml",
        "owl": "xml",
        "xml": "xml",
        "nt": "nt",
        "ntriples": "nt",
        "n-triples": "nt",
        "n3": "n3",
        "trig": "trig",
        "nq": "nquads",
        "nquad": "nquads",
        "nquads": "nquads",
        "trix": "trix",
        "jsonld": "json-ld",
        "json_ld": "json-ld",
        "json-ld": "json-ld",
        "hext": "hext",
        "hextuples": "hext",
        "rdfa": "rdfa",
        "html": "rdfa",
        "xhtml": "rdfa",
        "htm": "rdfa",
        "microdata": "microdata",
    }

    DEFAULT_FORMAT = "turtle"

    @classmethod
    def normalize_format(cls, rdf_format: Optional[str]) -> Optional[str]:
        """Normalize user-provided format/alias to an rdflib format."""
        if not rdf_format:
            return None
        fmt = rdf_format.strip().lower()
        return cls.FORMAT_ALIASES.get(fmt, fmt)

    @classmethod
    def infer_format_from_path(cls, file_path: Union[str, Path]) -> Optional[str]:
        """Infer RDF format from file extension using rdflib's guess_format."""
        try:
            inferred = guess_format(str(file_path))
        except Exception:
            inferred = None
        return cls.normalize_format(inferred)

    @classmethod
    def resolve_format(
        cls,
        rdf_format: Optional[str],
        file_path: Optional[Union[str, Path]] = None
    ) -> str:
        """Resolve the effective RDF format using explicit input or file hints."""
        normalized = cls.normalize_format(rdf_format)
        if not normalized and file_path is not None:
            normalized = cls.infer_format_from_path(file_path)
        if not normalized:
            normalized = cls.DEFAULT_FORMAT
        if normalized not in cls.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported RDF serialization format '{rdf_format or normalized}'. "
                f"Supported formats: {sorted(cls.SUPPORTED_FORMATS)}"
            )
        return normalized

    @classmethod
    def _is_dataset_format(cls, format_name: str) -> bool:
        """Return True when the serialization may contain multiple named graphs."""
        return format_name in cls.DATASET_FORMATS

    @classmethod
    def _create_graph(cls, format_name: str) -> Graph:
        """Instantiate the correct rdflib graph implementation for a format."""
        if cls._is_dataset_format(format_name):
            return ConjunctiveGraph()
        return Graph()
    
    @staticmethod
    def parse_ttl_content(
        ttl_content: str,
        force_large_file: bool = False,
        rdf_format: Optional[str] = None,
        source_path: Optional[Union[str, Path]] = None,
    ) -> Tuple[Graph, int, float]:
        """
        Parse RDF content into an RDF graph with memory safety checks.
        
        Args:
            ttl_content: The RDF content as a string
            force_large_file: If True, skip memory safety checks for large files
            rdf_format: Optional explicit serialization name/alias
            source_path: Optional source path used for format inference
            
        Returns:
            Tuple of (parsed Graph, triple count, content size in MB)
            
        Raises:
            ValueError: If TTL content is empty or has invalid syntax
            MemoryError: If insufficient memory is available to parse the file
        """
        logger.info("Parsing RDF content%s...", f" ({rdf_format})" if rdf_format else "")
        
        if not ttl_content or not ttl_content.strip():
            raise ValueError("Empty TTL content provided")
        
        # Check size before parsing
        content_size_mb = len(ttl_content.encode('utf-8')) / (1024 * 1024)
        logger.info(f"RDF content size: {content_size_mb:.2f} MB")
        
        # Pre-flight memory check to prevent crashes
        can_proceed, memory_message = MemoryManager.check_memory_available(
            content_size_mb, 
            force=force_large_file
        )
        
        if not can_proceed:
            logger.error(f"Memory check failed: {memory_message}")
            raise MemoryError(memory_message)
        
        logger.info(f"Memory check: {memory_message}")
        
        if content_size_mb > 100:
            logger.warning(
                f"Large RDF content detected ({content_size_mb:.1f} MB). "
                "Parsing may take several minutes."
            )
        
        # Log memory before parsing
        MemoryManager.log_memory_status("Before parsing")
        
        # Determine serialization format
        format_name = RDFGraphParser.resolve_format(rdf_format, source_path)

        # Parse the RDF content
        graph = RDFGraphParser._create_graph(format_name)
        try:
            graph.parse(data=ttl_content, format=format_name)
        except MemoryError as e:
            MemoryManager.log_memory_status("After MemoryError")
            raise MemoryError(
                f"Insufficient memory while parsing RDF content ({content_size_mb:.1f} MB). "
                f"Try splitting the ontology into smaller files or increasing available memory. "
                f"Original error: {e}"
            )
        except Exception as e:
            logger.error(f"Failed to parse RDF content: {e}")
            raise ValueError(f"Invalid RDF/TTL syntax: {e}")
        
        # Log memory after parsing
        MemoryManager.log_memory_status("After parsing")
        
        triple_count = len(graph)
        if RDFGraphParser._is_dataset_format(format_name):
            try:
                context_count = len({ctx.identifier for ctx in graph.contexts()})
            except Exception:
                context_count = 0
            logger.info(
                f"Successfully parsed dataset with {triple_count} quads "
                f"across {context_count or 'unknown'} graph contexts "
                f"({content_size_mb:.1f} MB)"
            )
        else:
            logger.info(
                f"Successfully parsed {triple_count} triples ({content_size_mb:.1f} MB)"
            )
        if triple_count == 0:
            logger.warning("Parsed graph is empty - no triples found")
            raise ValueError("No RDF triples found in the provided content")

        if triple_count > 100000:
            logger.warning(
                f"Large ontology detected ({triple_count} triples). "
                "Processing may take several minutes."
            )
        
        return graph, triple_count, content_size_mb
    
    @staticmethod
    def parse_ttl_file(
        file_path: str,
        force_large_file: bool = False,
        rdf_format: Optional[str] = None,
    ) -> Tuple[Graph, int, float]:
        """
        Parse an RDF file into an RDF graph with memory safety checks.
        
        Args:
            file_path: Path to the RDF file
            force_large_file: If True, skip memory safety checks for large files
            rdf_format: Optional explicit serialization name/alias
            
        Returns:
            Tuple of (parsed Graph, triple count, file size in MB)
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file has invalid syntax
            MemoryError: If insufficient memory is available
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size_mb = path.stat().st_size / (1024 * 1024)
        logger.info(f"File size: {file_size_mb:.2f} MB")
        
        # Pre-flight memory check
        can_proceed, memory_message = MemoryManager.check_memory_available(
            file_size_mb, 
            force=force_large_file
        )
        
        if not can_proceed:
            logger.error(f"Memory check failed: {memory_message}")
            raise MemoryError(memory_message)
        
        logger.info(f"Memory check: {memory_message}")
        
        # Log memory before parsing
        MemoryManager.log_memory_status("Before parsing")
        
        # Resolve serialization format
        format_name = RDFGraphParser.resolve_format(rdf_format, path)

        # Parse the RDF file
        graph = RDFGraphParser._create_graph(format_name)
        try:
            graph.parse(file_path, format=format_name)
        except MemoryError as e:
            MemoryManager.log_memory_status("After MemoryError")
            raise MemoryError(
                f"Insufficient memory while parsing RDF file ({file_size_mb:.1f} MB). "
                f"Try splitting the ontology into smaller files or increasing available memory. "
                f"Original error: {e}"
            )
        except Exception as e:
            logger.error(f"Failed to parse RDF file: {e}")
            raise ValueError(f"Invalid RDF/TTL syntax: {e}")
        
        # Log memory after parsing
        MemoryManager.log_memory_status("After parsing")
        
        triple_count = len(graph)
        if RDFGraphParser._is_dataset_format(format_name):
            try:
                context_count = len({ctx.identifier for ctx in graph.contexts()})
            except Exception:
                context_count = 0
            logger.info(
                f"Successfully parsed dataset with {triple_count} quads "
                f"across {context_count or 'unknown'} graph contexts "
                f"({file_size_mb:.1f} MB)"
            )
        else:
            logger.info(
                f"Successfully parsed {triple_count} triples ({file_size_mb:.1f} MB)"
            )
        
        return graph, triple_count, file_size_mb
