import json
from pathlib import Path

import faiss
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

EVIDENCE_PATH = (
    PROJECT_ROOT
    / "data"
    / "normalized"
    / "evidence_objects"
    / "vector_chunk_evidence.json"
)

FAISS_OUTPUT_DIR = PROJECT_ROOT / "storage" / "faiss"

INDEX_PATH = FAISS_OUTPUT_DIR / "index.faiss"
METADATA_PATH = FAISS_OUTPUT_DIR / "metadata.json"

EMBEDDING_MODEL = "text-embedding-3-small"


def load_vector_evidence():
    if not EVIDENCE_PATH.exists():
        raise FileNotFoundError(f"Missing vector evidence file: {EVIDENCE_PATH}")

    with open(EVIDENCE_PATH, "r", encoding="utf-8") as f:
        evidence_objects = json.load(f)

    chunks = []

    for obj in evidence_objects:
        text = (obj.get("text_excerpt") or "").strip()

        if not text:
            continue

        if "vector" not in obj.get("target_layers", []):
            continue

        metadata = obj.get("metadata", {})

        chunks.append({
            "evidence_id": obj.get("evidence_id"),
            "chunk_id": metadata.get("chunk_id", obj.get("evidence_id")),
            "text": text,
            "source_type": obj.get("source_type"),
            "source_name": obj.get("source_name"),
            "company": obj.get("company"),
            "year": obj.get("year"),
            "source_file": metadata.get("source_file"),
            "filing_type": metadata.get("filing_type"),
            "filing_year": metadata.get("filing_year"),
            "chunk_index": metadata.get("chunk_index"),
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

    print("Loading normalized vector evidence...")
    chunks = load_vector_evidence()

    if not chunks:
        raise ValueError("No vector-ready EvidenceObjects found.")

    print(f"Loaded {len(chunks)} vector evidence chunks")

    client = OpenAI()

    texts = [chunk["text"] for chunk in chunks]

    print("Generating embeddings...")
    embeddings = embed_texts(client, texts)

    print("Building FAISS index...")
    index = build_faiss_index(embeddings)

    print("Saving FAISS index...")
    faiss.write_index(index, str(INDEX_PATH))

    print("Saving FAISS metadata...")
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2)

    print("FAISS index build complete")
    print(f"Index saved to: {INDEX_PATH}")
    print(f"Metadata saved to: {METADATA_PATH}")


if __name__ == "__main__":
    main()