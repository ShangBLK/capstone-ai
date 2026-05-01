from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
import os


load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")


def get_driver():
    if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
        raise ValueError("Missing Neo4j environment variables.")

    return GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
    )


def run_query(cypher, parameters=None):
    parameters = parameters or {}

    with get_driver() as driver:
        with driver.session() as session:
            result = session.run(cypher, parameters)
            return [record.data() for record in result]


def get_entities_connected_to_company(company_name="tesla", limit=25):
    cypher = """
    MATCH (c:Entity)
    WHERE toLower(c.name) CONTAINS toLower($company_name)
    MATCH path = (c)-[r]-(n)
    RETURN
        c.name AS source_entity,
        type(r) AS relationship,
        n.name AS connected_entity,
        labels(n) AS connected_labels
    LIMIT $limit
    """

    return run_query(cypher, {
        "company_name": company_name,
        "limit": limit
    })


def get_relationships_involving_company(company_name="tesla", limit=25):
    cypher = """
    MATCH (c:Entity)
    WHERE toLower(c.name) CONTAINS toLower($company_name)
    MATCH (c)-[r]-(n)
    RETURN
        c.name AS entity_1,
        type(r) AS relationship,
        n.name AS entity_2,
        r.evidence AS evidence
    LIMIT $limit
    """

    return run_query(cypher, {
        "company_name": company_name,
        "limit": limit
    })


def get_risk_relationships(limit=25):
    cypher = """
    MATCH (a:Entity)-[r]-(b:Entity)
    WHERE
        toLower(a.name) CONTAINS "risk"
        OR toLower(b.name) CONTAINS "risk"
        OR type(r) CONTAINS "RISK"
        OR type(r) = "FACES_RISK"
    RETURN
        a.name AS entity_1,
        type(r) AS relationship,
        b.name AS entity_2,
        r.evidence AS evidence
    LIMIT $limit
    """

    return run_query(cypher, {"limit": limit})


def get_supported_chunks_for_entity(entity_name, limit=10):
    cypher = """
    MATCH (e:Entity)-[r:SUPPORTED_BY_CHUNK]->(ch:Chunk)
    WHERE toLower(e.name) CONTAINS toLower($entity_name)
    RETURN
        e.name AS entity,
        ch.chunk_id AS chunk_id,
        ch.text AS chunk_text
    LIMIT $limit
    """

    return run_query(cypher, {
        "entity_name": entity_name,
        "limit": limit
    })


def graph_search(query):
    query_lower = query.lower()

    if "risk" in query_lower or "risks" in query_lower:
        route = "risk_relationships"
        results = get_risk_relationships()

    elif "connected" in query_lower or "entities" in query_lower or "relationship" in query_lower:
        route = "company_connections"
        results = get_entities_connected_to_company("tesla")

    elif "tesla" in query_lower:
        route = "tesla_relationships"
        results = get_relationships_involving_company("tesla")

    else:
        route = "default_company_connections"
        results = get_entities_connected_to_company("tesla")

    return {
        "query": query,
        "graph_route": route,
        "results": results
    }


def print_graph_results(output):
    print("=" * 80)
    print(f"QUERY: {output['query']}")
    print(f"GRAPH ROUTE: {output['graph_route']}")
    print("=" * 80)

    if not output["results"]:
        print("No graph results found.")
        return

    for i, row in enumerate(output["results"], start=1):
        print(f"\nResult {i}")
        for key, value in row.items():
            print(f"{key}: {value}")
        print("-" * 80)


if __name__ == "__main__":
    test_queries = [
        "What entities are connected to Tesla?",
        "What risks are associated with Tesla?",
        "What relationships involve Tesla?"
    ]

    for q in test_queries:
        output = graph_search(q)
        print_graph_results(output)