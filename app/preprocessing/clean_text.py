from pathlib import Path
import re


def clean_text(text: str) -> str:
    """
    Clean extracted PDF text while preserving important financial content.

    Args:
        text (str): Raw extracted text.

    Returns:
        str: Cleaned text.
    """
    text = text.replace("\u25a1", " ")
    text = text.replace("\u25cf", " ")
    text = text.replace("\u2022", " ")
    text = text.replace("\uf0b7", " ")
    text = text.replace("\ufffd", " ")
    text = text.replace("☒", " ")
    text = text.replace("☐", " ")

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    return text


def clean_text_file(input_path: Path, output_path: Path) -> None:
    """
    Read a raw text file, clean it, and save the cleaned version.

    Args:
        input_path (Path): Path to raw text file.
        output_path (Path): Path to cleaned text file.
    """
    with open(input_path, "r", encoding="utf-8") as file:
        raw_text = file.read()

    cleaned = clean_text(raw_text)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(cleaned)


def process_all_text_files(input_dir: str, output_dir: str, overwrite: bool = False) -> None:
    """
    Clean all extracted text files in a directory.

    Args:
        input_dir (str): Directory containing raw extracted text files.
        output_dir (str): Directory to save cleaned text files.
        overwrite (bool): Whether to overwrite existing cleaned files.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    text_files = list(input_path.rglob("*.txt"))

    print(f"Found {len(text_files)} text file(s).")

    if not text_files:
        print("No text files found in the input directory.")
        return

    for text_file in text_files:
        output_file = output_path / f"clean_{text_file.name}"

        if output_file.exists() and not overwrite:
            print(f"Skipping existing cleaned file: {output_file}")
            continue

        print(f"Cleaning: {text_file}")

        try:
            clean_text_file(text_file, output_file)
            print(f"Saved: {output_file}")

        except Exception as error:
            print(f"Failed to clean {text_file.name}: {error}")


if __name__ == "__main__":
    process_all_text_files(
        input_dir="data/extracted/text",
        output_dir="data/processed/cleaned_text",
        overwrite=True #CHANGE TO TRUE OF YOU WANT TO OVERRIDE
    )