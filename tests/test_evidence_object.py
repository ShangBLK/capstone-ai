from pathlib import Path

from app.ingestion.evidence_schema import EvidenceObject
from app.ingestion.normalize_evidence import (
    save_evidence_objects,
    load_evidence_objects,
    validate_evidence_objects,
)


def main():
    output_path = Path("data/normalized/evidence_objects/test_evidence_objects.json")

    evidence = EvidenceObject(
        source_type="sec_pdf",
        source_name="Tesla 2022 10-K",
        source_url=None,
        publication_date="2023-01-31",
        company="Tesla",
        vehicle_model=None,
        year=2022,
        metric_name="automotive_revenue",
        metric_value=67210000000.0,
        metric_unit="USD",
        text_excerpt="Automotive revenues increased primarily due to growth in vehicle deliveries.",
        confidence_score=0.95,
        target_layers=["sql", "neo4j", "vector"],
        metadata={
            "filing_type": "10-K",
            "test_record": True,
        },
    )

    validate_evidence_objects([evidence])
    save_evidence_objects([evidence], output_path)

    loaded = load_evidence_objects(output_path)

    assert len(loaded) == 1
    assert loaded[0].source_type == "sec_pdf"
    assert loaded[0].source_name == "Tesla 2022 10-K"
    assert loaded[0].metric_name == "automotive_revenue"
    assert loaded[0].metric_value == 67210000000.0
    assert "sql" in loaded[0].target_layers
    assert "neo4j" in loaded[0].target_layers
    assert "vector" in loaded[0].target_layers

    print("EvidenceObject test passed.")
    print(f"Saved test evidence to: {output_path}")


if __name__ == "__main__":
    main()