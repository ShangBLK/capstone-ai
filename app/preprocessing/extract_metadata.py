from pathlib import Path
import json
import re


def parse_filename_metadata(file_name: str) -> dict:
    """
    Parse metadata from a cleaned text filename.

    Expected format:
        clean_<company>_<filing_type>_<year>.txt

    Example:
        clean_tesla_10k_2022.txt

    Args:
        file_name (str): Name of the cleaned text file.

    Returns:
        dict: Parsed metadata fields. Unknown values are used if parsing fails.
    """
    pattern = r"^clean_(?P<company>[a-zA-Z0-9]+)_(?P<filing_type>[a-zA-Z0-9]+)_(?P<year>20\d{2})\.txt$"
    match = re.match(pattern, file_name)

    if not match:
        return {
            "company_name": "unknown",
            "filing_type": "unknown",
            "filing_year": "unknown",
            "metadata_source": "filename_failed"
        }

    company_name = match.group("company").lower()
    filing_type_raw = match.group("filing_type").lower()
    filing_year = match.group("year")

    filing_type_map = {
        "10k": "10K",
        "10q": "10Q",
        "8k": "8K"
    }

    filing_type = filing_type_map.get(filing_type_raw, filing_type_raw.upper())

    return {
        "company_name": company_name,
        "filing_type": filing_type,
        "filing_year": filing_year,
        "metadata_source": "filename"
    }


def build_metadata_record(text_file: Path) -> dict:
    """
    Build a metadata dictionary for one cleaned text file.

    Args:
        text_file (Path): Path to cleaned text file.

    Returns:
        dict: Metadata record.
    """
    with open(text_file, "r", encoding="utf-8") as file:
        text = file.read()

    file_name = text_file.name
    base_name = text_file.stem
    parsed_metadata = parse_filename_metadata(file_name)

    metadata = {
        "cleaned_text_file": file_name,
        "original_pdf_guess": base_name.replace("clean_", "") + ".pdf",
        "company_name": parsed_metadata["company_name"],
        "filing_type": parsed_metadata["filing_type"],
        "filing_year": parsed_metadata["filing_year"],
        "metadata_source": parsed_metadata["metadata_source"],
        "character_count": len(text),
        "word_count": len(text.split()),
        "source_path": str(text_file)
    }

    return metadata


def save_metadata(output_path: Path, metadata: dict) -> None:
    """
    Save metadata to a JSON file.

    Args:
        output_path (Path): Output JSON path.
        metadata (dict): Metadata dictionary.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=4)


def process_all_cleaned_texts(input_dir: str, output_dir: str, overwrite: bool = False) -> None:
    """
    Process all cleaned text files and generate metadata JSON files.

    Args:
        input_dir (str): Directory containing cleaned text files.
        output_dir (str): Directory where metadata JSON files will be saved.
        overwrite (bool): Whether to overwrite existing metadata files.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    text_files = list(input_path.rglob("clean_*.txt"))

    print(f"Found {len(text_files)} cleaned text file(s).")

    if not text_files:
        print("No cleaned text files found in the input directory.")
        return

    for text_file in text_files:
        output_file = output_path / f"{text_file.stem}_metadata.json"

        if output_file.exists() and not overwrite:
            print(f"Skipping existing metadata file: {output_file}")
            continue

        print(f"Extracting metadata: {text_file}")

        try:
            metadata = build_metadata_record(text_file)
            save_metadata(output_file, metadata)
            print(f"Saved: {output_file}")

        except Exception as error:
            print(f"Failed to extract metadata from {text_file.name}: {error}")


if __name__ == "__main__":
    process_all_cleaned_texts(
        input_dir="data/processed/cleaned_text",
        output_dir="data/extracted/metadata",
        overwrite=True
    )