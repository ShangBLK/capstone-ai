import json
from pathlib import Path

import faiss
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FAISS_DIR = PROJECT_ROOT / "storage" / "faiss"
INDEX_PATH = FAISS_DIR / "index.faiss"
METADATA_PATH = FAISS_DIR / "metadata.json"

EMBEDDING_MODEL = "text-embedding-3-small"


def load_index_and_metadata():
    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"Missing FAISS index: {INDEX_PATH}")

    if not METADATA_PATH.exists():
        raise FileNotFoundError(f"Missing metadata file: {METADATA_PATH}")

    index = faiss.read_index(str(INDEX_PATH))

    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    return index, metadata


def embed_query(client, query: str):
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query,
    )

    return np.array([response.data[0].embedding], dtype="float32")


def search_vector(query: str, top_k: int = 5):
    load_dotenv()

    client = OpenAI()
    index, metadata = load_index_and_metadata()

    query_embedding = embed_query(client, query)

    distances, indices = index.search(query_embedding, top_k)

    results = []

    for rank, idx in enumerate(indices[0], start=1):
        if idx == -1:
            continue

        record = metadata[idx]
        text = record.get("text", "")

        results.append({
            "rank": rank,
            "distance": float(distances[0][rank - 1]),
            "evidence_id": record.get("evidence_id"),
            "chunk_id": record.get("chunk_id"),
            "source_type": record.get("source_type"),
            "source_name": record.get("source_name"),
            "company": record.get("company"),
            "year": record.get("year"),
            "source_file": record.get("source_file"),
            "filing_type": record.get("filing_type"),
            "filing_year": record.get("filing_year"),
            "chunk_index": record.get("chunk_index"),
            "text_preview": text[:700],
            "text": text,
        })

    return results


def print_results(query: str, results: list[dict]) -> None:
    print("=" * 80)
    print(f"QUERY: {query}")
    print("=" * 80)

    for result in results:
        print(f"\nRank: {result['rank']}")
        print(f"Distance: {result['distance']}")
        print(f"Evidence ID: {result['evidence_id']}")
        print(f"Chunk ID: {result['chunk_id']}")
        print(f"Source Type: {result['source_type']}")
        print(f"Source Name: {result['source_name']}")
        print(f"Company: {result['company']}")
        print(f"Year: {result['year']}")
        print(f"Filing Type: {result['filing_type']}")
        print(f"Source File: {result['source_file']}")
        print("Text Preview:")
        print(result["text_preview"])
        print("-" * 80)


if __name__ == "__main__":
    test_queries = [
        "What risks did the company discuss in its filing?",
        "What business factors affected the company in 2022?",
        "What does the filing say about revenue?",
    ]

    for query in test_queries:
        results = search_vector(query, top_k=3)
        print_results(query, results)