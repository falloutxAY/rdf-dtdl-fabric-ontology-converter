"""
Conversion result data types.

This module defines data structures for tracking conversion results,
including successful conversions, skipped items, and warnings.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .fabric_types import EntityType, RelationshipType


@dataclass
class SkippedItem:
    """
    Represents an item that was skipped during conversion.
    
    Items may be skipped for various reasons:
    - Unsupported constructs (e.g., OWL restrictions)
    - Missing required information
    - Validation failures
    
    Attributes:
        item_type: Category of the skipped item ("class", "property", "relationship").
        name: Human-readable name or identifier.
        reason: Explanation of why the item was skipped.
        uri: Original URI or identifier from the source format.
    
    Example:
        >>> skipped = SkippedItem(
        ...     item_type="class",
        ...     name="AnonymousRestriction",
        ...     reason="OWL restrictions are not supported",
        ...     uri="_:b0"
        ... )
    """
    item_type: str
    name: str
    reason: str
    uri: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format for serialization."""
        return {
            "type": self.item_type,
            "name": self.name,
            "reason": self.reason,
            "uri": self.uri,
        }


@dataclass
class ConversionResult:
    """
    Results of ontology conversion with detailed tracking.
    
    Provides comprehensive information about the conversion process,
    including successful conversions, skipped items, and warnings.
    This class is used by both RDF and DTDL converters.
    
    Attributes:
        entity_types: Successfully converted entity types.
        relationship_types: Successfully converted relationship types.
        skipped_items: Items that could not be converted.
        warnings: Non-fatal issues encountered during conversion.
        triple_count: Number of RDF triples processed (RDF only).
        interface_count: Number of DTDL interfaces processed (DTDL only).
    
    Example:
        >>> result = ConversionResult(
        ...     entity_types=[entity1, entity2],
        ...     relationship_types=[rel1],
        ...     warnings=["Property 'foo' has unknown type, defaulting to String"]
        ... )
        >>> print(f"Success rate: {result.success_rate:.1f}%")
        Success rate: 100.0%
    """
    entity_types: List[Any] = field(default_factory=list)  # List[EntityType]
    relationship_types: List[Any] = field(default_factory=list)  # List[RelationshipType]
    skipped_items: List[SkippedItem] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    triple_count: int = 0
    interface_count: int = 0
    
    @property
    def success_rate(self) -> float:
        """
        Calculate success rate as percentage of items successfully converted.
        
        Returns:
            Percentage (0-100) of items that were successfully converted.
            Returns 100.0 if no items were processed.
        """
        total = (
            len(self.entity_types) + 
            len(self.relationship_types) + 
            len(self.skipped_items)
        )
        if total == 0:
            return 100.0
        successful = len(self.entity_types) + len(self.relationship_types)
        return (successful / total) * 100
    
    @property
    def has_skipped_items(self) -> bool:
        """Check if any items were skipped during conversion."""
        return len(self.skipped_items) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if any warnings were generated during conversion."""
        return len(self.warnings) > 0
    
    @property
    def skipped_by_type(self) -> Dict[str, int]:
        """Get a count of skipped items grouped by their type."""
        counts: Dict[str, int] = {}
        for item in self.skipped_items:
            counts[item.item_type] = counts.get(item.item_type, 0) + 1
        return counts
    
    def get_summary(self) -> str:
        """
        Get a human-readable summary of the conversion results.
        
        Returns:
            Summary string with entity and relationship counts.
        """
        lines = [
            "Conversion Summary:",
            f"  ✓ Entity Types: {len(self.entity_types)}",
            f"  ✓ Relationships: {len(self.relationship_types)}",
        ]
        
        if self.skipped_items:
            lines.append(f"  ⚠ Skipped: {len(self.skipped_items)}")
            for item_type, count in self.skipped_by_type.items():
                lines.append(f"      - {item_type}s: {count}")
            lines.append("    Details (first 5):")
            for item in self.skipped_items[:5]:
                lines.append(f"      - {item.item_type}: {item.name}")
                lines.append(f"        Reason: {item.reason}")
            if len(self.skipped_items) > 5:
                lines.append(f"      ... and {len(self.skipped_items) - 5} more")
        
        if self.warnings:
            lines.append(f"  ⚠ Warnings: {len(self.warnings)}")
            for warning in self.warnings[:3]:
                lines.append(f"      - {warning}")
            if len(self.warnings) > 3:
                lines.append(f"      ... and {len(self.warnings) - 3} more")
        
        lines.append(f"  Success Rate: {self.success_rate:.1f}%")
        if self.triple_count > 0:
            lines.append(f"  Total RDF Triples: {self.triple_count}")
        if self.interface_count > 0:
            lines.append(f"  Total DTDL Interfaces: {self.interface_count}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize conversion result to dictionary format."""
        return {
            "entity_types_count": len(self.entity_types),
            "relationship_types_count": len(self.relationship_types),
            "skipped_items_count": len(self.skipped_items),
            "skipped_items": [item.to_dict() for item in self.skipped_items],
            "warnings": self.warnings,
            "success_rate": self.success_rate,
            "triple_count": self.triple_count,
            "interface_count": self.interface_count,
        }
    
    def merge(self, other: "ConversionResult") -> "ConversionResult":
        """
        Merge another ConversionResult into this one.
        
        Useful when processing multiple files or batches.
        
        Args:
            other: Another ConversionResult to merge.
            
        Returns:
            A new ConversionResult with combined data.
        """
        return ConversionResult(
            entity_types=self.entity_types + other.entity_types,
            relationship_types=self.relationship_types + other.relationship_types,
            skipped_items=self.skipped_items + other.skipped_items,
            warnings=self.warnings + other.warnings,
            triple_count=self.triple_count + other.triple_count,
            interface_count=self.interface_count + other.interface_count,
        )
