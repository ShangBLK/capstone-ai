import json
import re
from pathlib import Path

from neo4j_connection import get_neo4j_driver


PROJECT_ROOT = Path(__file__).resolve().parents[2]

GRAPH_RECORDS_DIR = PROJECT_ROOT / "data" / "processed" / "graph_records"

ENTITY_INPUT_PATH = GRAPH_RECORDS_DIR / "semantic_entities_test.json"
RELATIONSHIP_INPUT_PATH = GRAPH_RECORDS_DIR / "semantic_relationships_test.json"


def normalize_entity_id(name, label, company_name, filing_year):
    """
    Creates a stable entity ID for Neo4j MERGE operations.

    This prevents duplicate nodes when the same entity appears multiple times.
    """

    raw = f"{company_name}_{filing_year}_{label}_{name}".lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    return normalized


def load_json(path):
    """
    Loads a JSON file and returns its contents.
    """

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def create_constraints(driver):
    """
    Creates basic uniqueness constraints for test graph loading.
    """

    queries = [
        """
        CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
        FOR (e:Entity)
        REQUIRE e.entity_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
        FOR (c:Chunk)
        REQUIRE c.chunk_id IS UNIQUE
        """
    ]

    with driver.session() as session:
        for query in queries:
            session.run(query)


def load_entities(driver, entities):
    """
    Loads extracted entities into Neo4j.

    Each extracted entity receives:
    - generic Entity label
    - domain label such as Organization, ProductOrService, RiskFactor, etc.
    """

    query = """
    MERGE (e:Entity {entity_id: $entity_id})
    SET
        e.name = $name,
        e.description = $description,
        e.source_chunk_id = $source_chunk_id,
        e.company_name = $company_name,
        e.filing_type = $filing_type,
        e.filing_year = $filing_year,
        e.domain_label = $label

    WITH e
    CALL apoc.create.addLabels(e, [$label]) YIELD node
    RETURN node
    """

    fallback_query = """
    MERGE (e:Entity {entity_id: $entity_id})
    SET
        e.name = $name,
        e.description = $description,
        e.source_chunk_id = $source_chunk_id,
        e.company_name = $company_name,
        e.filing_type = $filing_type,
        e.filing_year = $filing_year,
        e.domain_label = $label
    RETURN e
    """

    with driver.session() as session:
        for entity in entities:
            entity_id = normalize_entity_id(
                entity.get("name", ""),
                entity.get("label", "Entity"),
                entity.get("company_name", ""),
                entity.get("filing_year", "")
            )

            params = {
                "entity_id": entity_id,
                "name": entity.get("name", ""),
                "label": entity.get("label", "Entity"),
                "description": entity.get("description", ""),
                "source_chunk_id": entity.get("source_chunk_id", ""),
                "company_name": entity.get("company_name", ""),
                "filing_type": entity.get("filing_type", ""),
                "filing_year": str(entity.get("filing_year", ""))
            }

            try:
                session.run(query, params)
            except Exception:
                session.run(fallback_query, params)


def create_chunk_placeholders(driver, entities, relationships):
    """
    Creates lightweight Chunk nodes so entities and relationships can be traced to evidence.

    Full chunk text loading can happen later.
    """

    chunk_ids = set()

    for entity in entities:
        if entity.get("source_chunk_id"):
            chunk_ids.add(entity["source_chunk_id"])

    for relationship in relationships:
        if relationship.get("source_chunk_id"):
            chunk_ids.add(relationship["source_chunk_id"])

    query = """
    MERGE (c:Chunk {chunk_id: $chunk_id})
    """

    with driver.session() as session:
        for chunk_id in chunk_ids:
            session.run(query, {"chunk_id": chunk_id})


def link_entities_to_chunks(driver, entities):
    """
    Connects each entity to the chunk that supports it.
    """

    query = """
    MATCH (e:Entity {entity_id: $entity_id})
    MATCH (c:Chunk {chunk_id: $chunk_id})
    MERGE (e)-[:SUPPORTED_BY_CHUNK]->(c)
    """

    with driver.session() as session:
        for entity in entities:
            entity_id = normalize_entity_id(
                entity.get("name", ""),
                entity.get("label", "Entity"),
                entity.get("company_name", ""),
                entity.get("filing_year", "")
            )

            session.run(
                query,
                {
                    "entity_id": entity_id,
                    "chunk_id": entity.get("source_chunk_id", "")
                }
            )


def load_relationships(driver, relationships):
    """
    Loads semantic relationships between extracted entities.

    Relationship type is created dynamically from the LLM output.
    Evidence is stored as a relationship property.
    """

    with driver.session() as session:
        for relationship in relationships:
            source_name = relationship.get("source", "")
            target_name = relationship.get("target", "")
            rel_type = relationship.get("relationship", "ASSOCIATED_WITH")

            company_name = relationship.get("company_name", "")
            filing_year = str(relationship.get("filing_year", ""))
            source_chunk_id = relationship.get("source_chunk_id", "")

            source_id = None
            target_id = None

            source_lookup = """
            MATCH (e:Entity)
            WHERE toLower(e.name) = toLower($name)
              AND e.company_name = $company_name
              AND e.filing_year = $filing_year
            RETURN e.entity_id AS entity_id
            LIMIT 1
            """

            target_lookup = """
            MATCH (e:Entity)
            WHERE toLower(e.name) = toLower($name)
              AND e.company_name = $company_name
              AND e.filing_year = $filing_year
            RETURN e.entity_id AS entity_id
            LIMIT 1
            """

            source_result = session.run(
                source_lookup,
                {
                    "name": source_name,
                    "company_name": company_name,
                    "filing_year": filing_year
                }
            ).single()

            target_result = session.run(
                target_lookup,
                {
                    "name": target_name,
                    "company_name": company_name,
                    "filing_year": filing_year
                }
            ).single()

            if source_result:
                source_id = source_result["entity_id"]

            if target_result:
                target_id = target_result["entity_id"]

            if not source_id or not target_id:
                continue

            query = f"""
            MATCH (source:Entity {{entity_id: $source_id}})
            MATCH (target:Entity {{entity_id: $target_id}})
            MERGE (source)-[r:{rel_type}]->(target)
            SET
                r.evidence = $evidence,
                r.source_chunk_id = $source_chunk_id,
                r.company_name = $company_name,
                r.filing_type = $filing_type,
                r.filing_year = $filing_year
            """

            session.run(
                query,
                {
                    "source_id": source_id,
                    "target_id": target_id,
                    "evidence": relationship.get("evidence", ""),
                    "source_chunk_id": source_chunk_id,
                    "company_name": company_name,
                    "filing_type": relationship.get("filing_type", ""),
                    "filing_year": filing_year
                }
            )


def print_graph_summary(driver):
    """
    Prints basic graph size and relationship-type counts.
    """

    queries = {
        "Entity count": "MATCH (e:Entity) RETURN count(e) AS count",
        "Chunk count": "MATCH (c:Chunk) RETURN count(c) AS count",
        "Relationship count": "MATCH ()-[r]->() RETURN count(r) AS count"
    }

    with driver.session() as session:
        for label, query in queries.items():
            result = session.run(query).single()
            print(f"{label}: {result['count']}")

        print("\nRelationship types:")
        rel_results = session.run(
            """
            MATCH ()-[r]->()
            RETURN type(r) AS relationship_type, count(r) AS count
            ORDER BY count DESC
            """
        )

        for record in rel_results:
            print(f"{record['relationship_type']}: {record['count']}")


def main():
    """
    Loads the semantic test graph into Neo4j Aura.
    """

    entities = load_json(ENTITY_INPUT_PATH)
    relationships = load_json(RELATIONSHIP_INPUT_PATH)

    print(f"Loaded {len(entities)} entities from JSON.")
    print(f"Loaded {len(relationships)} relationships from JSON.")

    driver = get_neo4j_driver()

    try:
        create_constraints(driver)
        create_chunk_placeholders(driver, entities, relationships)
        load_entities(driver, entities)
        link_entities_to_chunks(driver, entities)
        load_relationships(driver, relationships)
        print_graph_summary(driver)
        print("\nSemantic test graph loaded into Neo4j.")
    finally:
        driver.close()


if __name__ == "__main__":
    main()