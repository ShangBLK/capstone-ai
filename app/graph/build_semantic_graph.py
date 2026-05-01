import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

from graph_schema import EXTRACTION_SCHEMA, RELEVANT_KEYWORDS


PROJECT_ROOT = Path(__file__).resolve().parents[2]

VECTOR_RECORDS_DIR = PROJECT_ROOT / "data" / "processed" / "vector_records"
GRAPH_RECORDS_DIR = PROJECT_ROOT / "data" / "processed" / "graph_records"

ENTITY_OUTPUT_PATH = GRAPH_RECORDS_DIR / "semantic_entities_test.json"
RELATIONSHIP_OUTPUT_PATH = GRAPH_RECORDS_DIR / "semantic_relationships_test.json"

MAX_CHUNKS_TO_PROCESS = 5


def load_chunk_records():
    """
    Loads chunk records from data/processed/vector_records.

    Expected input:
    JSON files created earlier by chunk_text.py.
    """

    chunk_records = []

    for json_path in VECTOR_RECORDS_DIR.glob("*.json"):
        with open(json_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            chunk_records.extend(data)
        else:
            raise ValueError(f"Expected list in {json_path}, but found {type(data)}")

    return chunk_records


def select_relevant_chunks(chunks, max_chunks):
    """
    Selects business-relevant chunks instead of simply using the first chunks.

    This avoids cover-page, SEC checkbox, and legal boilerplate sections.
    """

    selected_chunks = []

    for chunk in chunks:
        text = chunk.get("text", "").lower()

        if any(keyword.lower() in text for keyword in RELEVANT_KEYWORDS):
            selected_chunks.append(chunk)

        if len(selected_chunks) >= max_chunks:
            break

    return selected_chunks


def build_extraction_prompt(chunk):
    """
    Builds a strict extraction prompt for one chunk.

    The LLM should extract semantic financial entities and relationships.
    It should not invent facts or extract exact numerical truth.
    """

    allowed_entities = ", ".join(EXTRACTION_SCHEMA["entities"])
    allowed_relationships = ", ".join(EXTRACTION_SCHEMA["relationships"])

    chunk_id = chunk.get("chunk_id", "")
    company_name = chunk.get("company_name", "")
    filing_type = chunk.get("filing_type", "")
    filing_year = chunk.get("filing_year", "")
    text = chunk.get("text", "")

    prompt = f"""
You are extracting a semantic financial knowledge graph from SEC filing text.

Important rules:
1. Return JSON only.
2. Do not include markdown.
3. Do not invent facts.
4. Only extract information explicitly supported by the chunk text.
5. Do not extract exact financial values as truth. Exact numerical facts belong in SQL.
6. Every entity must include source_chunk_id.
7. Every relationship must include source_chunk_id and evidence.
8. Use only the allowed entity labels and relationship types.
9. Prioritize business meaning over legal filing boilerplate.
10. If no meaningful relationship exists between entities, return an empty relationships list.
11. Do NOT force relationships if they do not clearly exist in the text.
12. Avoid structural/legal relationships (e.g., filing metadata, incorporation details) unless they have business significance.

Allowed entity labels:
{allowed_entities}

Allowed relationship types:
{allowed_relationships}

Chunk metadata:
chunk_id: {chunk_id}
company_name: {company_name}
filing_type: {filing_type}
filing_year: {filing_year}

Chunk text:
{text}

Return JSON in exactly this structure:

{{
  "entities": [
    {{
      "name": "entity name",
      "label": "one allowed entity label",
      "description": "brief description grounded in the chunk",
      "source_chunk_id": "{chunk_id}",
      "company_name": "{company_name}",
      "filing_type": "{filing_type}",
      "filing_year": "{filing_year}"
    }}
  ],
  "relationships": [
    {{
      "source": "source entity name",
      "relationship": "one allowed relationship type",
      "target": "target entity name",
      "evidence": "brief evidence from the chunk",
      "source_chunk_id": "{chunk_id}",
      "company_name": "{company_name}",
      "filing_type": "{filing_type}",
      "filing_year": "{filing_year}"
    }}
  ]
}}
"""

    return prompt


def extract_from_chunk(client, chunk):
    """
    Sends one chunk to the LLM and parses the JSON response.
    """

    prompt = build_extraction_prompt(chunk)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You extract financial knowledge graph entities and relationships from SEC filing chunks."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    content = response.choices[0].message.content
    return json.loads(content)


def main():
    """
    Runs a small semantic graph extraction test.

    This does not write to Neo4j yet.
    It only creates JSON outputs for inspection.
    """

    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is missing from .env")

    GRAPH_RECORDS_DIR.mkdir(parents=True, exist_ok=True)

    client = OpenAI()

    chunks = load_chunk_records()
    selected_chunks = select_relevant_chunks(chunks, MAX_CHUNKS_TO_PROCESS)

    print(f"Loaded {len(chunks)} chunks.")
    print(f"Selected {len(selected_chunks)} business-relevant chunks.")
    print(f"Processing {len(selected_chunks)} chunks only.")

    if not selected_chunks:
        raise ValueError("No relevant chunks were selected. Review RELEVANT_KEYWORDS in graph_schema.py.")

    all_entities = []
    all_relationships = []

    for index, chunk in enumerate(selected_chunks, start=1):
        chunk_id = chunk.get("chunk_id", "unknown")

        print(f"Processing chunk {index}/{len(selected_chunks)}: {chunk_id}")

        result = extract_from_chunk(client, chunk)

        entities = result.get("entities", [])
        relationships = result.get("relationships", [])

        all_entities.extend(entities)
        all_relationships.extend(relationships)

    with open(ENTITY_OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(all_entities, file, indent=2, ensure_ascii=False)

    with open(RELATIONSHIP_OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(all_relationships, file, indent=2, ensure_ascii=False)

    print(f"Saved entities to: {ENTITY_OUTPUT_PATH}")
    print(f"Saved relationships to: {RELATIONSHIP_OUTPUT_PATH}")
    print("Semantic extraction test complete.")


if __name__ == "__main__":
    main()