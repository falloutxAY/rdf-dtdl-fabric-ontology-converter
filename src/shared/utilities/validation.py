"""
Unified Validation Result Models.

This module provides standardized validation result structures used
across all format validators (RDF, DTDL, JSON-LD, etc.).

Replaces format-specific validation types:
- RDF: ValidationReport, ValidationIssue
- DTDL: ValidationResult, DTDLValidationError

Usage:
    from common.validation import ValidationResult, Severity, IssueCategory
    
    result = ValidationResult(format_name="rdf", source_path="ontology.ttl")
    result.add_error(IssueCategory.SYNTAX_ERROR, "Invalid syntax at line 10")
    result.add_warning(IssueCategory.UNSUPPORTED_CONSTRUCT, "owl:Restriction not supported")
    
    if result.can_convert:
        # Proceed with conversion
        pass
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Severity(Enum):
    """
    Severity levels for validation issues.
    
    - INFO: Informational message, no action required.
    - WARNING: Non-blocking issue, conversion may lose some information.
    - ERROR: Blocking issue, conversion cannot proceed.
    """
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class IssueCategory(Enum):
    """
    Standard issue categories across all formats.
    
    Provides consistent categorization for:
    - Filtering and grouping issues
    - Documentation and troubleshooting
    - Metrics and reporting
    """
    # Syntax and parsing issues
    SYNTAX_ERROR = "syntax_error"
    ENCODING_ERROR = "encoding_error"
    
    # Schema and structure issues
    MISSING_REQUIRED = "missing_required"
    INVALID_REFERENCE = "invalid_reference"
    INVALID_STRUCTURE = "invalid_structure"
    TYPE_MISMATCH = "type_mismatch"
    
    # Name validation issues
    NAME_TOO_LONG = "name_too_long"
    INVALID_CHARACTER = "invalid_character"
    
    # Constraint violations
    CONSTRAINT_VIOLATION = "constraint_violation"
    NAME_CONFLICT = "name_conflict"
    CIRCULAR_REFERENCE = "circular_reference"
    
    # Conversion limitations
    UNSUPPORTED_CONSTRUCT = "unsupported_construct"
    CONVERSION_LIMITATION = "conversion_limitation"
    PRECISION_LOSS = "precision_loss"
    
    # Fabric-specific issues
    FABRIC_COMPATIBILITY = "fabric_compatibility"
    
    # External dependencies
    EXTERNAL_DEPENDENCY = "external_dependency"
    UNRESOLVED_IMPORT = "unresolved_import"
    
    # Security
    SECURITY_CONCERN = "security_concern"
    
    # Custom/format-specific
    CUSTOM = "custom"


@dataclass
class ValidationIssue:
    """
    Represents a single validation issue.
    
    Attributes:
        severity: Issue severity (ERROR, WARNING, INFO).
        category: Issue category for grouping.
        message: Human-readable description.
        location: Where the issue occurred (URI, line number, identifier).
        details: Additional technical details.
        recommendation: Suggested action to resolve the issue.
        source_format: Original format-specific category (for compatibility).
    """
    severity: Severity
    category: IssueCategory
    message: str
    location: Optional[str] = None
    details: Optional[str] = None
    recommendation: Optional[str] = None
    source_format: Optional[str] = None  # Original format-specific category
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
        }
        if self.location:
            result["location"] = self.location
        if self.details:
            result["details"] = self.details
        if self.recommendation:
            result["recommendation"] = self.recommendation
        if self.source_format:
            result["source_format"] = self.source_format
        return result
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        icon = {"error": "✗", "warning": "⚠", "info": "ℹ"}[self.severity.value]
        parts = [f"{icon} [{self.category.value}] {self.message}"]
        if self.location:
            parts.append(f"  Location: {self.location}")
        if self.recommendation:
            parts.append(f"  Recommendation: {self.recommendation}")
        return "\n".join(parts)


@dataclass
class ValidationResult:
    """
    Unified validation result used across all format validators.
    
    Provides consistent structure for:
    - RDF/TTL validation
    - DTDL validation
    - JSON-LD validation
    - Future format validation
    
    Attributes:
        format_name: Name of the validated format.
        source_path: Path to the validated file (optional).
        timestamp: When validation occurred.
        is_valid: Overall validity (True if no errors).
        issues: List of validation issues.
        statistics: Format-specific statistics.
        metadata: Additional metadata.
    
    Example:
        >>> result = ValidationResult("rdf", "ontology.ttl")
        >>> result.add_error(IssueCategory.SYNTAX_ERROR, "Parse error")
        >>> result.add_warning(IssueCategory.UNSUPPORTED_CONSTRUCT, "owl:Restriction")
        >>> print(result.get_summary())
    """
    format_name: str
    source_path: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    is_valid: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_issue(
        self,
        severity: Severity,
        category: IssueCategory,
        message: str,
        location: Optional[str] = None,
        details: Optional[str] = None,
        recommendation: Optional[str] = None,
        source_format: Optional[str] = None,
    ) -> None:
        """
        Add a validation issue.
        
        Args:
            severity: Issue severity.
            category: Issue category.
            message: Human-readable description.
            location: Where the issue occurred.
            details: Additional technical details.
            recommendation: Suggested resolution.
            source_format: Original format-specific category.
        """
        issue = ValidationIssue(
            severity=severity,
            category=category,
            message=message,
            location=location,
            details=details,
            recommendation=recommendation,
            source_format=source_format,
        )
        self.issues.append(issue)
        
        # Update validity on error
        if severity == Severity.ERROR:
            self.is_valid = False
    
    def add_error(
        self,
        category: IssueCategory,
        message: str,
        **kwargs: Any,
    ) -> None:
        """Convenience method to add an error."""
        self.add_issue(Severity.ERROR, category, message, **kwargs)
    
    def add_warning(
        self,
        category: IssueCategory,
        message: str,
        **kwargs: Any,
    ) -> None:
        """Convenience method to add a warning."""
        self.add_issue(Severity.WARNING, category, message, **kwargs)
    
    def add_info(
        self,
        category: IssueCategory,
        message: str,
        **kwargs: Any,
    ) -> None:
        """Convenience method to add an info message."""
        self.add_issue(Severity.INFO, category, message, **kwargs)
    
    @property
    def error_count(self) -> int:
        """Count of ERROR severity issues."""
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)
    
    @property
    def warning_count(self) -> int:
        """Count of WARNING severity issues."""
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)
    
    @property
    def info_count(self) -> int:
        """Count of INFO severity issues."""
        return sum(1 for i in self.issues if i.severity == Severity.INFO)
    
    @property
    def total_issues(self) -> int:
        """Total count of all issues."""
        return len(self.issues)
    
    @property
    def can_convert(self) -> bool:
        """Check if conversion can proceed (no errors)."""
        return self.error_count == 0
    
    @property
    def issues_by_severity(self) -> Dict[str, int]:
        """Get issue counts grouped by severity."""
        return {
            "error": self.error_count,
            "warning": self.warning_count,
            "info": self.info_count,
        }
    
    @property
    def issues_by_category(self) -> Dict[str, int]:
        """Get issue counts grouped by category."""
        counts: Dict[str, int] = {}
        for issue in self.issues:
            cat = issue.category.value
            counts[cat] = counts.get(cat, 0) + 1
        return counts
    
    def get_issues_by_severity(self, severity: Severity) -> List[ValidationIssue]:
        """Get all issues of a specific severity."""
        return [i for i in self.issues if i.severity == severity]
    
    def get_issues_by_category(self, category: IssueCategory) -> List[ValidationIssue]:
        """Get all issues of a specific category."""
        return [i for i in self.issues if i.category == category]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "format": self.format_name,
            "source_path": self.source_path,
            "timestamp": self.timestamp,
            "is_valid": self.is_valid,
            "can_convert": self.can_convert,
            "summary": {
                "total_issues": self.total_issues,
                "errors": self.error_count,
                "warnings": self.warning_count,
                "info": self.info_count,
            },
            "issues_by_category": self.issues_by_category,
            "issues": [i.to_dict() for i in self.issues],
            "statistics": self.statistics,
            "metadata": self.metadata,
        }
    
    def save_to_file(self, path: str) -> None:
        """
        Save validation result to JSON file.
        
        Args:
            path: Output file path.
        """
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Validation result saved to: {path}")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidationResult':
        """
        Create ValidationResult from dictionary.
        
        Args:
            data: Dictionary representation.
        
        Returns:
            New ValidationResult instance.
        """
        result = cls(
            format_name=data.get("format", "unknown"),
            source_path=data.get("source_path"),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            statistics=data.get("statistics", {}),
            metadata=data.get("metadata", {}),
        )
        
        for issue_data in data.get("issues", []):
            result.add_issue(
                severity=Severity(issue_data["severity"]),
                category=IssueCategory(issue_data["category"]),
                message=issue_data["message"],
                location=issue_data.get("location"),
                details=issue_data.get("details"),
                recommendation=issue_data.get("recommendation"),
                source_format=issue_data.get("source_format"),
            )
        
        return result
    
    def get_summary(self) -> str:
        """
        Generate human-readable summary.
        
        Returns:
            Multi-line summary string.
        """
        lines = [
            "=" * 60,
            f"VALIDATION RESULT ({self.format_name.upper()})",
            "=" * 60,
        ]
        
        if self.source_path:
            lines.append(f"File: {self.source_path}")
        lines.append(f"Timestamp: {self.timestamp}")
        lines.append("")
        
        # Status
        if self.is_valid:
            lines.append("✓ STATUS: VALID")
            if self.warning_count > 0:
                lines.append(f"  (with {self.warning_count} warning(s))")
        else:
            lines.append("✗ STATUS: INVALID")
            lines.append(f"  {self.error_count} error(s) must be fixed")
        
        lines.append("")
        
        # Summary counts
        lines.append("SUMMARY:")
        lines.append(f"  Total Issues: {self.total_issues}")
        lines.append(f"    ✗ Errors:   {self.error_count}")
        lines.append(f"    ⚠ Warnings: {self.warning_count}")
        lines.append(f"    ℹ Info:     {self.info_count}")
        
        # Statistics
        if self.statistics:
            lines.append("")
            lines.append("STATISTICS:")
            for key, value in self.statistics.items():
                lines.append(f"  {key}: {value}")
        
        # Issues
        if self.issues:
            lines.append("")
            lines.append("-" * 60)
            lines.append("ISSUES:")
            lines.append("-" * 60)
            
            # Show errors first
            errors = self.get_issues_by_severity(Severity.ERROR)
            if errors:
                lines.append("\nErrors:")
                for issue in errors[:10]:
                    lines.append(f"  ✗ {issue.message}")
                    if issue.location:
                        lines.append(f"    Location: {issue.location}")
                if len(errors) > 10:
                    lines.append(f"  ... and {len(errors) - 10} more errors")
            
            # Show warnings
            warnings = self.get_issues_by_severity(Severity.WARNING)
            if warnings:
                lines.append("\nWarnings:")
                for issue in warnings[:5]:
                    lines.append(f"  ⚠ {issue.message}")
                if len(warnings) > 5:
                    lines.append(f"  ... and {len(warnings) - 5} more warnings")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def get_human_readable_summary(self) -> str:
        """Alias for get_summary() for backward compatibility."""
        return self.get_summary()
    
    def merge(self, other: 'ValidationResult') -> 'ValidationResult':
        """
        Merge another validation result into this one.
        
        Useful for combining results from multiple files.
        
        Args:
            other: Another ValidationResult to merge.
        
        Returns:
            Self for chaining.
        """
        self.issues.extend(other.issues)
        self.is_valid = self.is_valid and other.is_valid
        
        # Merge statistics
        for key, value in other.statistics.items():
            if key in self.statistics and isinstance(value, (int, float)):
                self.statistics[key] = self.statistics.get(key, 0) + value
            else:
                self.statistics[key] = value
        
        # Merge metadata
        self.metadata.update(other.metadata)
        
        return self


# =============================================================================
# Utility Functions
# =============================================================================

def create_validation_result(
    format_name: str,
    source_path: Optional[str] = None,
    **metadata: Any,
) -> ValidationResult:
    """
    Factory function to create a new ValidationResult.
    
    Args:
        format_name: Name of the format being validated.
        source_path: Path to the source file.
        **metadata: Additional metadata to include.
    
    Returns:
        New ValidationResult instance.
    """
    return ValidationResult(
        format_name=format_name,
        source_path=source_path,
        metadata=metadata,
    )


def combine_validation_results(
    results: List[ValidationResult],
    combined_name: str = "combined",
) -> ValidationResult:
    """
    Combine multiple validation results into one.
    
    Args:
        results: List of ValidationResult instances.
        combined_name: Name for the combined result.
    
    Returns:
        Combined ValidationResult.
    """
    if not results:
        return ValidationResult(format_name=combined_name)
    
    combined = ValidationResult(
        format_name=combined_name,
        statistics={"file_count": len(results)},
    )
    
    for result in results:
        combined.merge(result)
    
    return combined
