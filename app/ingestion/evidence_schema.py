from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from datetime import date
import uuid


VALID_TARGET_LAYERS = {"sql", "neo4j", "vector"}


@dataclass
class EvidenceObject:
    """
    Normalized evidence unit used as the shared input for SQLite, Neo4j,
    and FAISS/vector retrieval.

    This object should be created by source adapters before any data is
    written into downstream storage systems.
    """

    evidence_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Source information
    source_type: str = ""
    source_name: str = ""
    source_url: Optional[str] = None
    publication_date: Optional[str] = None

    # Entity context
    company: Optional[str] = None
    vehicle_model: Optional[str] = None
    quarter: Optional[str] = None
    year: Optional[int] = None

    # Structured metric information
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    metric_unit: Optional[str] = None

    # Event / semantic information
    event_type: Optional[str] = None
    event_description: Optional[str] = None

    # Text evidence
    text_excerpt: Optional[str] = None

    # Quality / routing
    confidence_score: float = 1.0
    target_layers: List[str] = field(default_factory=list)

    # Flexible extension field
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """
        Validate the EvidenceObject before saving or routing it.
        Raises ValueError if the object is malformed.
        """

        if not self.source_type:
            raise ValueError("EvidenceObject requires source_type.")

        if not self.source_name:
            raise ValueError("EvidenceObject requires source_name.")

        if self.confidence_score < 0 or self.confidence_score > 1:
            raise ValueError("confidence_score must be between 0 and 1.")

        invalid_layers = set(self.target_layers) - VALID_TARGET_LAYERS
        if invalid_layers:
            raise ValueError(f"Invalid target_layers found: {invalid_layers}")

        if not self.target_layers:
            raise ValueError("EvidenceObject requires at least one target layer.")

        if self.metric_value is not None and self.metric_name is None:
            raise ValueError("metric_value was provided without metric_name.")

        if self.year is not None and self.year < 1900:
            raise ValueError("year appears invalid.")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert EvidenceObject to dictionary for JSON serialization.
        """

        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceObject":
        """
        Create EvidenceObject from dictionary data.
        """

        obj = cls(**data)
        obj.validate()
        return obj