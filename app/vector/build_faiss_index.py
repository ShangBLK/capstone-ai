import json
from pathlib import Path

import faiss
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

VECTOR_RECORDS_DIR = PROJECT_ROOT / "data" / "processed" / "vector_records"
FAISS_OUTPUT_DIR = PROJECT_ROOT / "storage" / "faiss"

INDEX_PATH = FAISS_OUTPUT_DIR / "index.faiss"
METADATA_PATH = FAISS_OUTPUT_DIR / "metadata.json"

EMBEDDING_MODEL = "text-embedding-3-small"


def load_chunks():
    chunks = []

    for json_file in VECTOR_RECORDS_DIR.glob("*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            records = json.load(f)

        for record in records:
            text = record.get("text", "").strip()

            if not text:
                continue

            chunks.append({
                "chunk_id": record.get("chunk_id"),
                "text": text,
                "company_name": record.get("company_name"),
                "filing_type": record.get("filing_type"),
                "filing_year": record.get("filing_year"),
                "source_file": record.get("source_file"),
            })

    return chunks


def embed_texts(client, texts, batch_size=50):
    embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]

        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch
        )

        batch_embeddings = [item.embedding for item in response.data]
        embeddings.extend(batch_embeddings)

        print(f"Embedded {min(i + batch_size, len(texts))}/{len(texts)} chunks")

    return np.array(embeddings, dtype="float32")


def build_faiss_index(embeddings):
    dimension = embeddings.shape[1]

    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    return index


def main():
    load_dotenv()

    FAISS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading vector chunks...")
    chunks = load_chunks()

    if not chunks:
        raise ValueError("No chunks found. Check data/processed/vector_records/")

    print(f"Loaded {len(chunks)} chunks")

    client = OpenAI()

    texts = [chunk["text"] for chunk in chunks]

    print("Generating embeddings...")
    embeddings = embed_texts(client, texts)

    print("Building FAISS index...")
    index = build_faiss_index(embeddings)

    print("Saving FAISS index...")
    faiss.write_index(index, str(INDEX_PATH))

    print("Saving metadata...")
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2)

    print("FAISS index build complete")
    print(f"Index saved to: {INDEX_PATH}")
    print(f"Metadata saved to: {METADATA_PATH}")


if __name__ == "__main__":
    main()