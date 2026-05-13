from __future__ import annotations

import json
from pathlib import Path
from typing import List

from app.ingestion.evidence_schema import EvidenceObject


def save_evidence_objects(
    evidence_objects: List[EvidenceObject],
    output_path: str | Path
) -> None:
    """
    Save a list of EvidenceObject instances to a JSON file.
    """

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = [obj.to_dict() for obj in evidence_objects]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_evidence_objects(
    input_path: str | Path
) -> List[EvidenceObject]:
    """
    Load EvidenceObject instances from a JSON file.
    """

    input_path = Path(input_path)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    evidence_objects = []

    for item in data:
        obj = EvidenceObject.from_dict(item)
        evidence_objects.append(obj)

    return evidence_objects


def validate_evidence_objects(
    evidence_objects: List[EvidenceObject]
) -> None:
    """
    Validate all EvidenceObjects in a collection.
    """

    for obj in evidence_objects:
        obj.validate()