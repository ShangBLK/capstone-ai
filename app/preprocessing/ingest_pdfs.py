from pathlib import Path

def get_pdf_files(base_path: str):
    """
    Recursively find all PDF files in a directory.

    Args:
        base_path (str): Path to root folder containing PDFs

    Returns:
        list[Path]: List of PDF file paths
    """
    base = Path(base_path)
    pdf_files = list(base.rglob("*.pdf"))
    return pdf_files


if __name__ == "__main__":
    pdfs = get_pdf_files("data/raw_pdfs")

    print(f"Found {len(pdfs)} PDF files:")
    for pdf in pdfs:
        print(pdf)