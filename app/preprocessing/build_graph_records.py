"""
DEPRECATED / LEGACY SCRIPT

This script created the original structural document graph:
Company -> Filing -> Chunk -> NEXT Chunk.

The current project direction is now semantic Neo4j GraphRAG.
Future graph construction should use app/graph/ instead.

Do not delete this file yet because it documents the initial baseline graph approach.
"""

from pathlib import Path
import json


VECTOR_RECORDS_DIR = Path("data/processed/vector_records")
GRAPH_RECORDS_DIR = Path("data/processed/graph_records")


def load_chunk_records(vector_records_dir: Path) -> list:
    """
    Load all chunk records from vector record JSON files.

    Args:
        vector_records_dir (Path): Directory containing chunk JSON files.

    Returns:
        list: Combined list of chunk records.
    """
    chunk_records = []

    json_files = list(vector_records_dir.rglob("*_chunks.json"))

    print(f"Found {len(json_files)} vector record file(s).")

    for json_file in json_files:
        print(f"Loading chunks from: {json_file}")

        with open(json_file, "r", encoding="utf-8") as file:
            records = json.load(file)
            chunk_records.extend(records)

    return chunk_records


def create_company_node(company_name: str) -> dict:
    return {
        "node_id": f"company_{company_name}",
        "label": "Company",
        "properties": {
            "company_name": company_name
        }
    }


def create_filing_node(company_name: str, filing_type: str, filing_year: str) -> dict:
    return {
        "node_id": f"filing_{company_name}_{filing_type}_{filing_year}",
        "label": "Filing",
        "properties": {
            "company_name": company_name,
            "filing_type": filing_type,
            "filing_year": filing_year
        }
    }


def create_chunk_node(chunk_record: dict) -> dict:
    return {
        "node_id": f"chunk_{chunk_record['chunk_id']}",
        "label": "Chunk",
        "properties": {
            "chunk_id": chunk_record["chunk_id"],
            "company_name": chunk_record["company_name"],
            "filing_type": chunk_record["filing_type"],
            "filing_year": chunk_record["filing_year"],
            "source_file": chunk_record["source_file"],
            "text": chunk_record["text"]
        }
    }


def create_relationship(start_id: str, end_id: str, relationship_type: str, properties: dict | None = None) -> dict:
    return {
        "start_node_id": start_id,
        "end_node_id": end_id,
        "relationship_type": relationship_type,
        "properties": properties or {}
    }


def build_graph_records(chunk_records: list) -> tuple[list, list]:
    """
    Build graph node and relationship records from chunk records.

    Args:
        chunk_records (list): Chunk records created by chunk_text.py.

    Returns:
        tuple: nodes list and relationships list.
    """
    nodes_by_id = {}
    relationships = []

    grouped_chunks = {}

    for chunk in chunk_records:
        company_name = chunk["company_name"]
        filing_type = chunk["filing_type"]
        filing_year = chunk["filing_year"]

        company_node = create_company_node(company_name)
        filing_node = create_filing_node(company_name, filing_type, filing_year)
        chunk_node = create_chunk_node(chunk)

        nodes_by_id[company_node["node_id"]] = company_node
        nodes_by_id[filing_node["node_id"]] = filing_node
        nodes_by_id[chunk_node["node_id"]] = chunk_node

        relationships.append(
            create_relationship(
                start_id=company_node["node_id"],
                end_id=filing_node["node_id"],
                relationship_type="FILED"
            )
        )

        relationships.append(
            create_relationship(
                start_id=filing_node["node_id"],
                end_id=chunk_node["node_id"],
                relationship_type="HAS_CHUNK"
            )
        )

        filing_key = (company_name, filing_type, filing_year)
        grouped_chunks.setdefault(filing_key, []).append(chunk)

    for filing_key, chunks in grouped_chunks.items():
        sorted_chunks = sorted(chunks, key=lambda record: record["chunk_id"])

        for index in range(len(sorted_chunks) - 1):
            current_chunk = sorted_chunks[index]
            next_chunk = sorted_chunks[index + 1]

            relationships.append(
                create_relationship(
                    start_id=f"chunk_{current_chunk['chunk_id']}",
                    end_id=f"chunk_{next_chunk['chunk_id']}",
                    relationship_type="NEXT",
                    properties={
                        "sequence_order": index
                    }
                )
            )

    unique_relationships = deduplicate_relationships(relationships)

    return list(nodes_by_id.values()), unique_relationships


def deduplicate_relationships(relationships: list) -> list:
    """
    Remove duplicate relationships.

    Args:
        relationships (list): Raw relationship records.

    Returns:
        list: Deduplicated relationship records.
    """
    seen = set()
    unique_relationships = []

    for relationship in relationships:
        key = (
            relationship["start_node_id"],
            relationship["end_node_id"],
            relationship["relationship_type"]
        )

        if key in seen:
            continue

        seen.add(key)
        unique_relationships.append(relationship)

    return unique_relationships


def save_json(output_path: Path, data: list) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def main() -> None:
    chunk_records = load_chunk_records(VECTOR_RECORDS_DIR)

    if not chunk_records:
        print("No chunk records found. Graph records were not created.")
        return

    nodes, relationships = build_graph_records(chunk_records)

    nodes_output_path = GRAPH_RECORDS_DIR / "nodes.json"
    relationships_output_path = GRAPH_RECORDS_DIR / "relationships.json"

    save_json(nodes_output_path, nodes)
    save_json(relationships_output_path, relationships)

    print(f"Created {len(nodes)} graph node record(s).")
    print(f"Created {len(relationships)} graph relationship record(s).")
    print(f"Saved nodes to: {nodes_output_path}")
    print(f"Saved relationships to: {relationships_output_path}")


if __name__ == "__main__":
    main()