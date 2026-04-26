from pathlib import Path
import json


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200):
    """
    Split text into overlapping chunks.

    Args:
        text (str): Cleaned text.
        chunk_size (int): Number of words per chunk.
        overlap (int): Number of overlapping words.

    Returns:
        list[str]: List of text chunks.
    """
    words = text.split()
    chunks = []

    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk = " ".join(chunk_words)
        chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


def load_metadata(metadata_path: Path):
    with open(metadata_path, "r", encoding="utf-8") as file:
        return json.load(file)


def create_chunk_records(text_file: Path, metadata_file: Path):
    """
    Create chunk records with metadata.

    Args:
        text_file (Path): Path to cleaned text file.
        metadata_file (Path): Path to metadata JSON.

    Returns:
        list[dict]: List of chunk records.
    """
    with open(text_file, "r", encoding="utf-8") as file:
        text = file.read()

    metadata = load_metadata(metadata_file)

    chunks = chunk_text(text)

    records = []
    base_name = text_file.stem.replace("clean_", "")

    for i, chunk in enumerate(chunks):
        record = {
            "chunk_id": f"{base_name}_chunk_{i:04d}",
            "company_name": metadata["company_name"],
            "filing_type": metadata["filing_type"],
            "filing_year": metadata["filing_year"],
            "text": chunk,
            "source_file": text_file.name
        }
        records.append(record)

    return records


def save_chunks(output_path: Path, records: list):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=4)


def process_all_cleaned_files(
    text_dir: str,
    metadata_dir: str,
    output_dir: str,
    overwrite: bool = False
):
    text_path = Path(text_dir)
    metadata_path = Path(metadata_dir)
    output_path = Path(output_dir)

    text_files = list(text_path.rglob("clean_*.txt"))

    print(f"Found {len(text_files)} cleaned text file(s).")

    for text_file in text_files:
        metadata_file = metadata_path / f"{text_file.stem}_metadata.json"
        output_file = output_path / f"{text_file.stem}_chunks.json"

        if output_file.exists() and not overwrite:
            print(f"Skipping existing file: {output_file}")
            continue

        if not metadata_file.exists():
            print(f"Missing metadata for {text_file.name}, skipping.")
            continue

        print(f"Chunking: {text_file}")

        try:
            records = create_chunk_records(text_file, metadata_file)
            save_chunks(output_file, records)
            print(f"Saved: {output_file}")

        except Exception as error:
            print(f"Failed to process {text_file.name}: {error}")


if __name__ == "__main__":
    process_all_cleaned_files(
        text_dir="data/processed/cleaned_text",
        metadata_dir="data/extracted/metadata",
        output_dir="data/processed/vector_records",
        overwrite=True
    )