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


def embed_query(client, query):
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query
    )

    return np.array([response.data[0].embedding], dtype="float32")


def search_vector(query, top_k=5):
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

        results.append({
            "rank": rank,
            "distance": float(distances[0][rank - 1]),
            "chunk_id": record.get("chunk_id"),
            "company_name": record.get("company_name"),
            "filing_type": record.get("filing_type"),
            "filing_year": record.get("filing_year"),
            "source_file": record.get("source_file"),
            "text_preview": record.get("text", "")[:700]
        })

    return results


def print_results(query, results):
    print("=" * 80)
    print(f"QUERY: {query}")
    print("=" * 80)

    for result in results:
        print(f"\nRank: {result['rank']}")
        print(f"Distance: {result['distance']}")
        print(f"Chunk ID: {result['chunk_id']}")
        print(f"Company: {result['company_name']}")
        print(f"Filing Type: {result['filing_type']}")
        print(f"Filing Year: {result['filing_year']}")
        print(f"Source File: {result['source_file']}")
        print("Text Preview:")
        print(result["text_preview"])
        print("-" * 80)


if __name__ == "__main__":
    test_queries = [
        "What risks did Tesla discuss in its filing?",
        "What does Ford say about revenue?",
        "What business factors affected Tesla in 2022?"
    ]

    for query in test_queries:
        results = search_vector(query, top_k=3)
        print_results(query, results)