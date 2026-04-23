from pathlib import Path
import fitz  # PyMuPDF


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract text from a single PDF file.

    Args:
        pdf_path (Path): Path to the PDF file.

    Returns:
        str: Combined text from all pages in the PDF.
    """
    full_text = []

    with fitz.open(pdf_path) as doc:
        for page_number, page in enumerate(doc, start=1):
            page_text = page.get_text()
            full_text.append(f"\n--- PAGE {page_number} ---\n")
            full_text.append(page_text)

    return "".join(full_text)


def save_text_file(output_path: Path, text: str) -> None:
    """
    Save extracted text to a UTF-8 text file.

    Args:
        output_path (Path): Destination .txt file path.
        text (str): Extracted text to save.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(text)


def process_all_pdfs(input_dir: str, output_dir: str) -> None:
    """
    Find all PDFs inside the input directory and extract their text.

    Args:
        input_dir (str): Folder containing raw PDF files.
        output_dir (str): Folder where extracted .txt files will be saved.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    pdf_files = list(input_path.rglob("*.pdf"))

    print(f"Found {len(pdf_files)} PDF file(s).")

    if not pdf_files:
        print("No PDFs found in the input directory.")
        return

    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file}")

        try:
            extracted_text = extract_text_from_pdf(pdf_file)

            output_file = output_path / f"{pdf_file.stem}.txt"
            save_text_file(output_file, extracted_text)

            print(f"Saved: {output_file}")

        except Exception as error:
            print(f"Failed to process {pdf_file.name}: {error}")


if __name__ == "__main__":
    process_all_pdfs(
        input_dir="data/raw_pdfs",
        output_dir="data/extracted/text"
    )