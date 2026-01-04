"""
Common Streaming Engine for RDF and DTDL Processing

This module provides a unified streaming infrastructure for memory-efficient
processing of large ontology files in both RDF (TTL) and DTDL (JSON) formats.

Architecture:
    - StreamConfig: Configuration for streaming behavior
    - StreamStats: Statistics collection during processing
    - ChunkProcessor: Abstract base for format-specific chunk handlers
    - StreamReader: Abstract base for format-specific file readers
    - StreamingEngine: Main orchestrator for streaming operations
    - RDFStreamAdapter: Adapter for RDF/TTL streaming (wraps existing StreamingRDFConverter)
    - DTDLStreamReader: Streaming JSON parser for DTDL files
    - DTDLChunkProcessor: Chunk processor for DTDL interfaces

Features:
    - Configurable chunk sizes and memory thresholds
    - Progress callbacks and cancellation support
    - Automatic streaming threshold detection
    - Format-agnostic interfaces with format-specific implementations

Usage:
    # For RDF files
    from core.streaming import StreamingEngine, RDFStreamAdapter
    
    engine = StreamingEngine()
    result = engine.process_file("large_ontology.ttl", 
                                  progress_callback=lambda n: print(f"Processed: {n}"))
    
    # For DTDL files  
    from core.streaming import StreamingEngine, DTDLStreamReader
    
    engine = StreamingEngine(reader=DTDLStreamReader())
    result = engine.process_file("large_models.json")
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import (
    Any, Callable, Dict, Generic, Iterator, List, 
    Optional, Protocol, Tuple, TypeVar, Union
)

logger = logging.getLogger(__name__)


# Type variables for generic streaming
T = TypeVar('T')  # Input chunk type
R = TypeVar('R')  # Result type


class StreamFormat(str, Enum):
    """Supported streaming formats."""
    RDF = "rdf"      # TTL/RDF files
    DTDL = "dtdl"    # JSON/JSON-LD DTDL files
    AUTO = "auto"    # Auto-detect from file extension


@dataclass
class StreamConfig:
    """
    Configuration for streaming operations.
    
    Attributes:
        chunk_size: Number of items to process per chunk (default: 10000)
        memory_threshold_mb: File size threshold for streaming mode (default: 100)
        max_memory_usage_mb: Maximum memory to use before pausing (default: 512)
        enable_progress: Enable progress callbacks (default: True)
        format: Expected file format (default: AUTO)
        buffer_size_bytes: Read buffer size for file I/O (default: 64KB)
    """
    chunk_size: int = 10000
    memory_threshold_mb: float = 100.0
    max_memory_usage_mb: float = 512.0
    enable_progress: bool = True
    format: StreamFormat = StreamFormat.AUTO
    buffer_size_bytes: int = 65536  # 64KB
    
    def should_use_streaming(self, file_size_mb: float) -> bool:
        """Determine if streaming mode should be used based on file size."""
        return file_size_mb > self.memory_threshold_mb


@dataclass 
class StreamStats:
    """
    Statistics collected during streaming operations.
    
    Attributes:
        chunks_processed: Number of chunks processed
        items_processed: Total items processed (e.g., triples, interfaces)
        bytes_read: Total bytes read from file
        errors_encountered: Number of recoverable errors
        warnings: List of warning messages
        peak_memory_mb: Peak memory usage during processing
        duration_seconds: Total processing time
    """
    chunks_processed: int = 0
    items_processed: int = 0
    bytes_read: int = 0
    errors_encountered: int = 0
    warnings: List[str] = field(default_factory=list)
    peak_memory_mb: float = 0.0
    duration_seconds: float = 0.0
    
    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)
        logger.warning(message)
    
    def get_summary(self) -> str:
        """Get human-readable summary."""
        lines = [
            "Streaming Statistics:",
            f"  Chunks processed: {self.chunks_processed}",
            f"  Items processed: {self.items_processed:,}",
            f"  Bytes read: {self.bytes_read:,} ({self.bytes_read / 1024 / 1024:.2f} MB)",
            f"  Errors: {self.errors_encountered}",
            f"  Warnings: {len(self.warnings)}",
        ]
        if self.duration_seconds > 0:
            rate = self.items_processed / self.duration_seconds
            lines.append(f"  Processing rate: {rate:.0f} items/sec")
        if self.peak_memory_mb > 0:
            lines.append(f"  Peak memory: {self.peak_memory_mb:.1f} MB")
        return "\n".join(lines)


class ProgressCallback(Protocol):
    """Protocol for progress callbacks."""
    def __call__(self, items_processed: int) -> None: ...


class CancellationProtocol(Protocol):
    """Protocol for cancellation tokens."""
    def throw_if_cancelled(self) -> None: ...


class ChunkProcessor(ABC, Generic[T, R]):
    """
    Abstract base class for processing chunks of data.
    
    Implementations handle format-specific chunk processing logic.
    Each chunk processor takes raw chunks and produces partial results
    that can be merged.
    """
    
    @abstractmethod
    def process_chunk(self, chunk: T, chunk_index: int) -> R:
        """
        Process a single chunk of data.
        
        Args:
            chunk: Raw chunk data (format-specific)
            chunk_index: Index of this chunk (0-based)
            
        Returns:
            Partial result from processing this chunk
        """
        pass
    
    @abstractmethod
    def merge_results(self, results: List[R]) -> R:
        """
        Merge partial results from multiple chunks.
        
        Args:
            results: List of partial results to merge
            
        Returns:
            Combined result
        """
        pass
    
    @abstractmethod
    def finalize(self, result: R) -> R:
        """
        Finalize the merged result (post-processing).
        
        Args:
            result: Merged result from all chunks
            
        Returns:
            Final processed result
        """
        pass


class StreamReader(ABC, Generic[T]):
    """
    Abstract base class for reading files in streaming fashion.
    
    Implementations handle format-specific file reading logic,
    yielding chunks of data that can be processed incrementally.
    """
    
    @abstractmethod
    def read_chunks(
        self, 
        file_path: str, 
        config: StreamConfig
    ) -> Iterator[Tuple[T, int]]:
        """
        Read file in chunks.
        
        Args:
            file_path: Path to file to read
            config: Streaming configuration
            
        Yields:
            Tuples of (chunk_data, bytes_read_in_chunk)
        """
        pass
    
    @abstractmethod
    def get_total_size(self, file_path: str) -> int:
        """
        Get total file size in bytes.
        
        Args:
            file_path: Path to file
            
        Returns:
            File size in bytes
        """
        pass
    
    @abstractmethod
    def supports_format(self, file_path: str) -> bool:
        """
        Check if this reader supports the given file format.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if format is supported
        """
        pass


@dataclass
class StreamResult(Generic[R]):
    """
    Result of a streaming operation.
    
    Attributes:
        data: The processed result data
        stats: Statistics from the streaming operation
        success: Whether processing completed successfully
        error_message: Error message if failed
    """
    data: Optional[R] = None
    stats: StreamStats = field(default_factory=StreamStats)
    success: bool = True
    error_message: Optional[str] = None


class StreamingEngine(Generic[T, R]):
    """
    Main orchestrator for streaming operations.
    
    Coordinates reading, processing, and result collection for
    large file processing with memory efficiency.
    
    Example:
        engine = StreamingEngine(reader=DTDLStreamReader(), 
                                  processor=DTDLChunkProcessor())
        result = engine.process_file("large_models.json", 
                                      progress_callback=print_progress)
    """
    
    def __init__(
        self,
        reader: Optional[StreamReader[T]] = None,
        processor: Optional[ChunkProcessor[T, R]] = None,
        config: Optional[StreamConfig] = None
    ):
        """
        Initialize the streaming engine.
        
        Args:
            reader: Format-specific stream reader (auto-selected if None)
            processor: Format-specific chunk processor (auto-selected if None)
            config: Streaming configuration (defaults used if None)
        """
        self.reader = reader
        self.processor = processor
        self.config = config or StreamConfig()
        self._stats = StreamStats()
    
    def process_file(
        self,
        file_path: str,
        progress_callback: Optional[ProgressCallback] = None,
        cancellation_token: Optional[CancellationProtocol] = None
    ) -> StreamResult[R]:
        """
        Process a file in streaming fashion.
        
        Args:
            file_path: Path to file to process
            progress_callback: Optional callback for progress updates
            cancellation_token: Optional token for cancellation support
            
        Returns:
            StreamResult with processed data and statistics
        """
        import time
        start_time = time.time()
        
        self._stats = StreamStats()
        result = StreamResult[R](stats=self._stats)
        
        # Validate inputs
        path = Path(file_path)
        if not path.exists():
            result.success = False
            result.error_message = f"File not found: {file_path}"
            return result
        
        # Auto-select reader if needed
        reader = self.reader
        if reader is None:
            reader = self._auto_select_reader(file_path)
            if reader is None:
                result.success = False
                result.error_message = f"No reader available for file: {file_path}"
                return result
        
        # Auto-select processor if needed
        processor = self.processor
        if processor is None:
            processor = self._auto_select_processor(file_path)
            if processor is None:
                result.success = False
                result.error_message = f"No processor available for file: {file_path}"
                return result
        
        # Check file size
        total_size = reader.get_total_size(file_path)
        file_size_mb = total_size / (1024 * 1024)
        logger.info(f"Processing file: {file_path} ({file_size_mb:.2f} MB)")
        
        try:
            # Process chunks
            partial_results: List[R] = []
            
            for chunk, bytes_read in reader.read_chunks(file_path, self.config):
                # Check for cancellation
                if cancellation_token:
                    cancellation_token.throw_if_cancelled()
                
                # Process chunk
                partial = processor.process_chunk(chunk, self._stats.chunks_processed)
                partial_results.append(partial)
                
                # Update stats
                self._stats.chunks_processed += 1
                self._stats.bytes_read += bytes_read
                
                # Progress callback
                if progress_callback and self.config.enable_progress:
                    progress_callback(self._stats.items_processed)
                
                # Memory check
                self._check_memory()
            
            # Merge and finalize results
            if partial_results:
                merged = processor.merge_results(partial_results)
                result.data = processor.finalize(merged)
            
            result.success = True
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            result.success = False
            result.error_message = str(e)
            self._stats.errors_encountered += 1
        
        # Finalize stats
        self._stats.duration_seconds = time.time() - start_time
        logger.info(self._stats.get_summary())
        
        return result
    
    def _auto_select_reader(self, file_path: str) -> Optional[StreamReader[T]]:
        """Auto-select appropriate reader based on file extension."""
        ext = Path(file_path).suffix.lower()
        
        # Import readers here to avoid circular imports
        if ext in {'.ttl', '.rdf', '.owl', '.n3'}:
            return RDFStreamReader()  # type: ignore
        elif ext in {'.json', '.dtdl'}:
            return DTDLStreamReader()  # type: ignore
        
        return None
    
    def _auto_select_processor(self, file_path: str) -> Optional[ChunkProcessor[T, R]]:
        """Auto-select appropriate processor based on file extension."""
        ext = Path(file_path).suffix.lower()
        
        if ext in {'.ttl', '.rdf', '.owl', '.n3'}:
            return RDFChunkProcessor()  # type: ignore
        elif ext in {'.json', '.dtdl'}:
            return DTDLChunkProcessor()  # type: ignore
        
        return None
    
    def _check_memory(self) -> None:
        """Check memory usage and pause if needed."""
        try:
            import psutil
            process = psutil.Process()
            current_mb = process.memory_info().rss / (1024 * 1024)
            self._stats.peak_memory_mb = max(self._stats.peak_memory_mb, current_mb)
            
            if current_mb > self.config.max_memory_usage_mb:
                logger.warning(f"High memory usage: {current_mb:.1f} MB")
                # Could implement memory pressure handling here
        except ImportError:
            pass


# ============================================================================
# RDF Streaming Implementation
# ============================================================================

@dataclass
class RDFChunk:
    """Chunk of RDF triples for processing."""
    triples: List[Tuple[Any, Any, Any]]
    chunk_index: int


@dataclass
class RDFPartialResult:
    """Partial result from processing RDF chunk."""
    classes: Dict[str, Any] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)
    relationships: Dict[str, Any] = field(default_factory=dict)
    triple_count: int = 0


class RDFStreamReader(StreamReader[RDFChunk]):
    """
    Stream reader for RDF/TTL files.
    
    Reads TTL files and yields chunks of triples for processing.
    Uses rdflib's incremental parsing capabilities.
    """
    
    SUPPORTED_EXTENSIONS = {'.ttl', '.rdf', '.owl', '.n3', '.nt'}
    
    def read_chunks(
        self, 
        file_path: str, 
        config: StreamConfig
    ) -> Iterator[Tuple[RDFChunk, int]]:
        """
        Read RDF file in chunks of triples.
        
        Note: RDFlib doesn't support true streaming parsing, so we load
        the graph and yield triples in batches. For very large files,
        consider using a dedicated streaming RDF parser.
        """
        from rdflib import Graph
        
        graph = Graph()
        graph.parse(file_path)
        
        triples = list(graph)
        total_bytes = os.path.getsize(file_path)
        bytes_per_triple = total_bytes / len(triples) if triples else 1
        
        chunk_size = config.chunk_size
        chunk_index = 0
        
        for i in range(0, len(triples), chunk_size):
            chunk_triples = triples[i:i + chunk_size]
            chunk = RDFChunk(
                triples=chunk_triples,
                chunk_index=chunk_index
            )
            bytes_read = int(len(chunk_triples) * bytes_per_triple)
            yield chunk, bytes_read
            chunk_index += 1
    
    def get_total_size(self, file_path: str) -> int:
        """Get file size in bytes."""
        return os.path.getsize(file_path)
    
    def supports_format(self, file_path: str) -> bool:
        """Check if file is a supported RDF format."""
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS


class RDFChunkProcessor(ChunkProcessor[RDFChunk, RDFPartialResult]):
    """
    Chunk processor for RDF triples.
    
    Processes chunks of triples, extracting classes, properties,
    and relationships incrementally.
    """
    
    def __init__(self):
        """Initialize the processor."""
        from rdflib import RDF, RDFS, OWL
        self.RDF = RDF
        self.RDFS = RDFS  
        self.OWL = OWL
    
    def process_chunk(
        self, 
        chunk: RDFChunk, 
        chunk_index: int
    ) -> RDFPartialResult:
        """Process a chunk of RDF triples."""
        result = RDFPartialResult(triple_count=len(chunk.triples))
        
        for subj, pred, obj in chunk.triples:
            # Extract classes
            if pred == self.RDF.type and obj in (self.OWL.Class, self.RDFS.Class):
                result.classes[str(subj)] = {"uri": str(subj)}
            
            # Extract properties
            if pred == self.RDF.type and obj in (
                self.OWL.DatatypeProperty, 
                self.OWL.ObjectProperty,
                self.RDF.Property
            ):
                result.properties[str(subj)] = {
                    "uri": str(subj),
                    "type": str(obj)
                }
        
        return result
    
    def merge_results(self, results: List[RDFPartialResult]) -> RDFPartialResult:
        """Merge partial results from all chunks."""
        merged = RDFPartialResult()
        
        for result in results:
            merged.classes.update(result.classes)
            merged.properties.update(result.properties)
            merged.relationships.update(result.relationships)
            merged.triple_count += result.triple_count
        
        return merged
    
    def finalize(self, result: RDFPartialResult) -> RDFPartialResult:
        """Finalize the merged result."""
        logger.info(
            f"RDF processing complete: {len(result.classes)} classes, "
            f"{len(result.properties)} properties, {result.triple_count} triples"
        )
        return result


# ============================================================================
# DTDL Streaming Implementation
# ============================================================================

@dataclass
class DTDLChunk:
    """Chunk of DTDL interfaces for processing."""
    interfaces: List[Dict[str, Any]]
    chunk_index: int
    file_path: Optional[str] = None


@dataclass
class DTDLPartialResult:
    """Partial result from processing DTDL chunk."""
    interfaces: List[Dict[str, Any]] = field(default_factory=list)
    interface_count: int = 0
    property_count: int = 0
    relationship_count: int = 0
    component_count: int = 0
    errors: List[str] = field(default_factory=list)
    source_files: List[str] = field(default_factory=list)


class DTDLStreamReader(StreamReader[DTDLChunk]):
    """
    Streaming reader for DTDL JSON files.
    
    Supports:
    - Single interface JSON files
    - Arrays of interfaces
    - Large JSON files with incremental parsing
    - Directory of JSON files (chunked by file)
    
    For very large JSON files (>100MB), uses ijson for incremental parsing
    if available, otherwise falls back to standard json with chunked reading.
    """
    
    SUPPORTED_EXTENSIONS = {'.json', '.dtdl'}
    
    def __init__(self, use_ijson: bool = True):
        """
        Initialize the reader.
        
        Args:
            use_ijson: Try to use ijson for incremental parsing (default: True)
        """
        self.use_ijson = use_ijson
        self._ijson_available = self._check_ijson()
    
    def _check_ijson(self) -> bool:
        """Check if ijson library is available."""
        if not self.use_ijson:
            return False
        try:
            import ijson
            return True
        except ImportError:
            logger.debug("ijson not available, using standard json parser")
            return False
    
    def read_chunks(
        self, 
        file_path: str, 
        config: StreamConfig
    ) -> Iterator[Tuple[DTDLChunk, int]]:
        """
        Read DTDL file(s) in chunks.
        
        For single files, yields interfaces in batches.
        For directories, yields one chunk per file.
        """
        path = Path(file_path)
        
        if path.is_dir():
            yield from self._read_directory_chunks(path, config)
        elif self._ijson_available and self._should_use_streaming(file_path, config):
            yield from self._read_streaming_chunks(file_path, config)
        else:
            yield from self._read_standard_chunks(file_path, config)
    
    def _should_use_streaming(self, file_path: str, config: StreamConfig) -> bool:
        """Check if streaming mode should be used for this file."""
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        return config.should_use_streaming(file_size_mb)
    
    def _read_directory_chunks(
        self, 
        dir_path: Path, 
        config: StreamConfig
    ) -> Iterator[Tuple[DTDLChunk, int]]:
        """Read all DTDL files in a directory."""
        json_files = list(dir_path.glob("**/*.json"))
        dtdl_files = list(dir_path.glob("**/*.dtdl"))
        all_files = json_files + dtdl_files
        
        chunk_index = 0
        interfaces_batch: List[Dict[str, Any]] = []
        bytes_batch = 0
        
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    bytes_read = len(content.encode('utf-8'))
                    data = json.loads(content)
                
                # Normalize to list of interfaces
                if isinstance(data, list):
                    interfaces_batch.extend(data)
                elif isinstance(data, dict):
                    if data.get("@type") == "Interface":
                        interfaces_batch.append(data)
                    elif "@graph" in data:
                        interfaces_batch.extend(data["@graph"])
                
                bytes_batch += bytes_read
                
                # Yield chunk when batch is full
                if len(interfaces_batch) >= config.chunk_size:
                    yield DTDLChunk(
                        interfaces=interfaces_batch,
                        chunk_index=chunk_index,
                        file_path=str(dir_path)
                    ), bytes_batch
                    interfaces_batch = []
                    bytes_batch = 0
                    chunk_index += 1
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse {file_path}: {e}")
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}")
        
        # Yield remaining interfaces
        if interfaces_batch:
            yield DTDLChunk(
                interfaces=interfaces_batch,
                chunk_index=chunk_index,
                file_path=str(dir_path)
            ), bytes_batch
    
    def _read_streaming_chunks(
        self, 
        file_path: str, 
        config: StreamConfig
    ) -> Iterator[Tuple[DTDLChunk, int]]:
        """Read large JSON file using ijson for incremental parsing."""
        import ijson
        
        interfaces: List[Dict[str, Any]] = []
        bytes_read = 0
        chunk_index = 0
        
        with open(file_path, 'rb') as f:
            # Try to parse as array of interfaces
            try:
                parser = ijson.items(f, 'item')
                for item in parser:
                    if isinstance(item, dict) and item.get("@type") == "Interface":
                        interfaces.append(item)
                        
                        if len(interfaces) >= config.chunk_size:
                            # Estimate bytes read
                            current_pos = f.tell()
                            yield DTDLChunk(
                                interfaces=interfaces,
                                chunk_index=chunk_index,
                                file_path=file_path
                            ), current_pos - bytes_read
                            bytes_read = current_pos
                            interfaces = []
                            chunk_index += 1
            except ijson.JSONError:
                # File might be a single interface or have different structure
                f.seek(0)
                content = f.read()
                data = json.loads(content)
                
                if isinstance(data, dict) and data.get("@type") == "Interface":
                    interfaces = [data]
                elif isinstance(data, dict) and "@graph" in data:
                    interfaces = data["@graph"]
                
                bytes_read = len(content)
        
        # Yield remaining interfaces
        if interfaces:
            yield DTDLChunk(
                interfaces=interfaces,
                chunk_index=chunk_index,
                file_path=file_path
            ), os.path.getsize(file_path) - bytes_read if bytes_read else os.path.getsize(file_path)
    
    def _read_standard_chunks(
        self, 
        file_path: str, 
        config: StreamConfig
    ) -> Iterator[Tuple[DTDLChunk, int]]:
        """Read JSON file using standard json library."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            bytes_read = len(content.encode('utf-8'))
        
        data = json.loads(content)
        interfaces: List[Dict[str, Any]] = []
        
        # Normalize to list of interfaces
        if isinstance(data, list):
            interfaces = [i for i in data if isinstance(i, dict) and i.get("@type") == "Interface"]
        elif isinstance(data, dict):
            if data.get("@type") == "Interface":
                interfaces = [data]
            elif "@graph" in data:
                interfaces = [i for i in data["@graph"] if isinstance(i, dict) and i.get("@type") == "Interface"]
        
        # Yield in chunks
        chunk_index = 0
        for i in range(0, len(interfaces), config.chunk_size):
            chunk_interfaces = interfaces[i:i + config.chunk_size]
            bytes_per_interface = bytes_read / len(interfaces) if interfaces else bytes_read
            
            yield DTDLChunk(
                interfaces=chunk_interfaces,
                chunk_index=chunk_index,
                file_path=file_path
            ), int(len(chunk_interfaces) * bytes_per_interface)
            chunk_index += 1
        
        # Handle empty file
        if not interfaces:
            yield DTDLChunk(
                interfaces=[],
                chunk_index=0,
                file_path=file_path
            ), bytes_read
    
    def get_total_size(self, file_path: str) -> int:
        """Get file or directory size in bytes."""
        path = Path(file_path)
        
        if path.is_dir():
            total = 0
            for f in path.glob("**/*.json"):
                total += f.stat().st_size
            for f in path.glob("**/*.dtdl"):
                total += f.stat().st_size
            return total
        
        return path.stat().st_size
    
    def supports_format(self, file_path: str) -> bool:
        """Check if file is a supported DTDL format."""
        path = Path(file_path)
        if path.is_dir():
            return True  # Directories are always checked for JSON files
        ext = path.suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS


class DTDLChunkProcessor(ChunkProcessor[DTDLChunk, DTDLPartialResult]):
    """
    Chunk processor for DTDL interfaces.
    
    Processes chunks of DTDL interfaces, extracting properties,
    relationships, and components for conversion to Fabric format.
    """
    
    def process_chunk(
        self, 
        chunk: DTDLChunk, 
        chunk_index: int
    ) -> DTDLPartialResult:
        """Process a chunk of DTDL interfaces."""
        result = DTDLPartialResult()
        
        for interface in chunk.interfaces:
            try:
                result.interfaces.append(interface)
                source = chunk.file_path or "<stream>"
                result.source_files.append(source)
                result.interface_count += 1
                
                # Count contents
                contents = interface.get("contents", [])
                if isinstance(contents, list):
                    for content in contents:
                        content_type = content.get("@type", "")
                        if content_type == "Property":
                            result.property_count += 1
                        elif content_type == "Relationship":
                            result.relationship_count += 1
                        elif content_type == "Component":
                            result.component_count += 1
                            
            except Exception as e:
                result.errors.append(f"Error processing interface: {e}")
        
        return result
    
    def merge_results(self, results: List[DTDLPartialResult]) -> DTDLPartialResult:
        """Merge partial results from all chunks."""
        merged = DTDLPartialResult()
        
        for result in results:
            merged.interfaces.extend(result.interfaces)
            merged.source_files.extend(result.source_files)
            merged.interface_count += result.interface_count
            merged.property_count += result.property_count
            merged.relationship_count += result.relationship_count
            merged.component_count += result.component_count
            merged.errors.extend(result.errors)
        
        return merged
    
    def finalize(self, result: DTDLPartialResult) -> DTDLPartialResult:
        """Finalize the merged result."""
        logger.info(
            f"DTDL processing complete: {result.interface_count} interfaces, "
            f"{result.property_count} properties, {result.relationship_count} relationships, "
            f"{result.component_count} components"
        )
        return result


# ============================================================================
# Adapter for existing StreamingRDFConverter
# ============================================================================

class RDFStreamAdapter:
    """
    Adapter that wraps the existing StreamingRDFConverter.
    
    Provides a bridge between the new streaming engine architecture
    and the existing RDF conversion implementation.
    
    Usage:
        adapter = RDFStreamAdapter(id_prefix=1000000000000)
        result = adapter.convert_streaming("large_ontology.ttl")
    """
    
    def __init__(
        self,
        id_prefix: int = 1000000000000,
        batch_size: int = 10000,
        loose_inference: bool = False
    ):
        """
        Initialize the adapter.
        
        Args:
            id_prefix: Base prefix for generating unique IDs
            batch_size: Number of triples to process per batch
            loose_inference: Apply heuristic inference for missing domain/range
        """
        self.id_prefix = id_prefix
        self.batch_size = batch_size
        self.loose_inference = loose_inference
    
    def convert_streaming(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[int], None]] = None,
        cancellation_token: Optional[Any] = None
    ) -> Any:
        """
        Convert RDF file using streaming mode.
        
        Args:
            file_path: Path to TTL file
            progress_callback: Optional progress callback
            cancellation_token: Optional cancellation token
            
        Returns:
            ConversionResult from StreamingRDFConverter
        """
        # Import here to avoid circular imports
        try:
            from ..rdf import StreamingRDFConverter
        except ImportError:
            from rdf import StreamingRDFConverter
        
        converter = StreamingRDFConverter(
            id_prefix=self.id_prefix,
            batch_size=self.batch_size,
            loose_inference=self.loose_inference
        )
        
        return converter.parse_ttl_streaming(
            file_path,
            progress_callback=progress_callback,
            cancellation_token=cancellation_token
        )


# ============================================================================
# Adapter for DTDL conversion with streaming
# ============================================================================

class DTDLStreamAdapter:
    """
    Adapter that provides streaming DTDL conversion.
    
    Uses the streaming engine with DTDLStreamReader and DTDLChunkProcessor
    to process large DTDL files efficiently, then converts to Fabric format.
    
    Usage:
        adapter = DTDLStreamAdapter()
        result = adapter.convert_streaming("./large_models/")
    """
    
    def __init__(
        self,
        config: Optional[StreamConfig] = None,
        ontology_name: Optional[str] = None,
        namespace: str = "usertypes",
        component_mode: Optional[Any] = None,
        command_mode: Optional[Any] = None,
        scaled_decimal_mode: Optional[Any] = None,
    ):
        """
        Initialize the adapter.
        
        Args:
            config: Streaming configuration
            ontology_name: Name for the ontology
            namespace: Namespace for entity types
        """
        self.config = config or StreamConfig()
        self.ontology_name = ontology_name
        self.namespace = namespace
        self.component_mode = component_mode
        self.command_mode = command_mode
        self.scaled_decimal_mode = scaled_decimal_mode
    
    def convert_streaming(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[int], None]] = None,
        cancellation_token: Optional[Any] = None
    ) -> Any:
        """
        Convert DTDL files using streaming mode.
        
        Args:
            file_path: Path to DTDL file or directory
            progress_callback: Optional progress callback
            cancellation_token: Optional cancellation token
            
        Returns:
            ConversionResult with Fabric definition
        """
        # Use streaming engine to read and chunk interfaces
        engine: StreamingEngine[DTDLChunk, DTDLPartialResult] = StreamingEngine(
            reader=DTDLStreamReader(),
            processor=DTDLChunkProcessor(),
            config=self.config
        )
        
        stream_result = engine.process_file(
            file_path,
            progress_callback=progress_callback,
            cancellation_token=cancellation_token
        )
        
        if not stream_result.success:
            return stream_result

        partial = stream_result.data
        if partial is None or not partial.interfaces:
            stream_result.success = False
            stream_result.error_message = "No DTDL interfaces found in stream"
            return stream_result

        try:
            from formats.dtdl import (
                DTDLParser,
                DTDLToFabricConverter,
                ComponentMode,
                CommandMode,
                ScaledDecimalMode,
            )
        except ImportError as exc:  # pragma: no cover - dependency issue
            raise ImportError("formats.dtdl module not available") from exc

        parser = DTDLParser()
        parsed_interfaces = []
        sources = partial.source_files or []

        for index, interface_dict in enumerate(partial.interfaces):
            source = sources[index] if index < len(sources) else "<stream>"
            try:
                parsed = parser.parse_interface_dict(interface_dict, source)
                if parsed:
                    parsed_interfaces.append(parsed)
            except Exception as exc:
                logger.warning(f"Failed to parse interface during streaming: {exc}")

        component_mode = self.component_mode or ComponentMode.SKIP
        if isinstance(component_mode, str):
            component_mode = ComponentMode(component_mode)
        command_mode = self.command_mode or CommandMode.SKIP
        if isinstance(command_mode, str):
            command_mode = CommandMode(command_mode)
        scaled_decimal_mode = self.scaled_decimal_mode or ScaledDecimalMode.JSON_STRING
        if isinstance(scaled_decimal_mode, str):
            scaled_decimal_mode = ScaledDecimalMode(scaled_decimal_mode)

        converter = DTDLToFabricConverter(
            namespace=self.namespace,
            component_mode=component_mode,
            command_mode=command_mode,
            scaled_decimal_mode=scaled_decimal_mode,
        )

        conversion_result = converter.convert(parsed_interfaces)
        ontology_name = self.ontology_name or self._infer_ontology_name(file_path)
        definition = converter.to_fabric_definition(conversion_result, ontology_name)

        stream_result.data = {
            "definition": definition,
            "conversion_result": conversion_result,
            "ontology_name": ontology_name,
            "dtmi_mapping": converter.get_dtmi_mapping(),
        }

        return stream_result

    @staticmethod
    def _infer_ontology_name(file_path: str) -> str:
        """Infer ontology name from file or directory path."""
        path = Path(file_path)
        if path.is_file():
            return path.stem or "dtdl_stream"
        return path.name or "dtdl_stream"


# ============================================================================
# Utility functions
# ============================================================================

def should_use_streaming(file_path: str, threshold_mb: float = 100.0) -> bool:
    """
    Check if streaming mode should be used for a file.
    
    Args:
        file_path: Path to file
        threshold_mb: Size threshold in MB (default: 100)
        
    Returns:
        True if streaming is recommended
    """
    try:
        path = Path(file_path)
        if path.is_dir():
            # For directories, sum all relevant files
            total_size = 0
            for ext in ['.json', '.dtdl', '.ttl', '.rdf']:
                for f in path.glob(f"**/*{ext}"):
                    total_size += f.stat().st_size
            file_size_mb = total_size / (1024 * 1024)
        else:
            file_size_mb = path.stat().st_size / (1024 * 1024)
        
        return file_size_mb > threshold_mb
    except Exception:
        return False


def get_streaming_threshold() -> float:
    """
    Get the recommended streaming threshold from configuration.
    
    Returns:
        Threshold in MB
    """
    try:
        from ..constants import ProcessingLimits
        return ProcessingLimits.STREAMING_THRESHOLD_MB
    except (ImportError, AttributeError):
        return 100.0  # Default 100MB


__all__ = [
    # Configuration
    'StreamFormat',
    'StreamConfig',
    'StreamStats',
    'StreamResult',
    
    # Base classes
    'ChunkProcessor',
    'StreamReader',
    'StreamingEngine',
    
    # RDF implementation  
    'RDFChunk',
    'RDFPartialResult',
    'RDFStreamReader',
    'RDFChunkProcessor',
    'RDFStreamAdapter',
    
    # DTDL implementation
    'DTDLChunk',
    'DTDLPartialResult',
    'DTDLStreamReader',
    'DTDLChunkProcessor',
    'DTDLStreamAdapter',
    
    # Utilities
    'should_use_streaming',
    'get_streaming_threshold',
]
