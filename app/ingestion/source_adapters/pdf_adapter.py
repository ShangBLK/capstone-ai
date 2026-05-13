from pathlib import Path
from typing import List, Optional

from app.preprocessing.ingest_pdfs import get_pdf_files
from app.ingestion.evidence_schema import EvidenceObject
from app.ingestion.normalize_evidence import save_evidence_objects


def infer_source_type(pdf_path: Path) -> str:
    """
    Infer a broad document type from the PDF filename.

    This only classifies the source document. It should not be treated as
    semantic extraction.
    """

    name = pdf_path.name.lower()

    if "10k" in name or "10-k" in name or "10q" in name or "10-q" in name:
        return "sec_pdf"

    if "shareholder" in name or "deck" in name or "presentation" in name:
        return "shareholder_deck"

    if "earnings" in name or "transcript" in name:
        return "earnings_transcript"

    return "pdf_document"


def create_pdf_evidence_objects(
    pdf_directory: str = "data/raw_pdfs",
    company: Optional[str] = "Tesla",
) -> List[EvidenceObject]:
    """
    Register PDF files as document-level EvidenceObjects.

    These objects identify PDF sources that can later be processed for
    vector retrieval. They do not contain extracted facts, metrics, or
    semantic relationships.
    """

    pdf_files = get_pdf_files(pdf_directory)
    evidence_objects = []

    for pdf_path in pdf_files:
        pdf_path = Path(pdf_path)

        evidence = EvidenceObject(
            source_type=infer_source_type(pdf_path),
            source_name=pdf_path.stem,
            source_url=None,
            publication_date=None,
            company=company,
            text_excerpt=f"PDF source document: {pdf_path.name}",
            confidence_score=1.0,
            target_layers=["vector"],
            metadata={
                "file_path": str(pdf_path),
                "file_name": pdf_path.name,
                "file_size_bytes": pdf_path.stat().st_size,
            },
        )

        evidence.validate()
        evidence_objects.append(evidence)

    return evidence_objects


def main() -> None:
    output_path = "data/normalized/evidence_objects/pdf_evidence.json"

    evidence_objects = create_pdf_evidence_objects()
    save_evidence_objects(evidence_objects, output_path)

    print(f"Created {len(evidence_objects)} PDF EvidenceObject(s).")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()