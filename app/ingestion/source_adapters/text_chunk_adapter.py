from pathlib import Path
from typing import List

from app.preprocessing.chunk_text import chunk_text, load_metadata
from app.ingestion.evidence_schema import EvidenceObject
from app.ingestion.normalize_evidence import save_evidence_objects


def create_text_chunk_evidence_objects(
    text_dir: str = "data/processed/cleaned_text",
    metadata_dir: str = "data/extracted/metadata",
) -> List[EvidenceObject]:
    """
    Create vector-ready EvidenceObjects from cleaned text chunks.

    These EvidenceObjects represent retrievable text passages.
    They are intended for FAISS/vector indexing only.
    """

    text_path = Path(text_dir)
    metadata_path = Path(metadata_dir)

    text_files = list(text_path.rglob("clean_*.txt"))
    evidence_objects = []

    for text_file in text_files:
        metadata_file = metadata_path / f"{text_file.stem}_metadata.json"

        if not metadata_file.exists():
            print(f"Missing metadata for {text_file.name}, skipping.")
            continue

        metadata = load_metadata(metadata_file)

        with open(text_file, "r", encoding="utf-8") as file:
            text = file.read()

        chunks = chunk_text(text)

        base_name = text_file.stem.replace("clean_", "")

        for index, chunk in enumerate(chunks):
            evidence = EvidenceObject(
                evidence_id=f"{base_name}_chunk_{index:04d}",
                source_type="text_chunk",
                source_name=base_name,
                company=metadata.get("company_name"),
                year=int(metadata["filing_year"])
                if str(metadata.get("filing_year")).isdigit()
                else None,
                text_excerpt=chunk,
                confidence_score=1.0,
                target_layers=["vector"],
                metadata={
                    "chunk_id": f"{base_name}_chunk_{index:04d}",
                    "chunk_index": index,
                    "source_file": text_file.name,
                    "filing_type": metadata.get("filing_type"),
                    "filing_year": metadata.get("filing_year"),
                },
            )

            evidence.validate()
            evidence_objects.append(evidence)

    return evidence_objects


def main() -> None:
    output_path = "data/normalized/evidence_objects/vector_chunk_evidence.json"

    evidence_objects = create_text_chunk_evidence_objects()
    save_evidence_objects(evidence_objects, output_path)

    print(f"Created {len(evidence_objects)} text chunk EvidenceObject(s).")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()