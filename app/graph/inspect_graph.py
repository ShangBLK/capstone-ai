from dotenv import load_dotenv
from neo4j import GraphDatabase
import os

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")


def get_driver():
    return GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
    )


def run_query(cypher):
    with get_driver() as driver:
        with driver.session() as session:
            result = session.run(cypher)
            return [record.data() for record in result]


def print_section(title, rows):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    if not rows:
        print("No results.")
        return

    for row in rows:
        print(row)


if __name__ == "__main__":
    print_section(
        "NODE LABEL COUNTS",
        run_query("""
        MATCH (n)
        RETURN labels(n) AS labels, count(*) AS count
        ORDER BY count DESC
        """)
    )

    print_section(
        "RELATIONSHIP TYPE COUNTS",
        run_query("""
        MATCH ()-[r]->()
        RETURN type(r) AS relationship_type, count(*) AS count
        ORDER BY count DESC
        """)
    )

    print_section(
        "SAMPLE NODES",
        run_query("""
        MATCH (n)
        RETURN labels(n) AS labels, properties(n) AS properties
        LIMIT 10
        """)
    )

    print_section(
        "SAMPLE RELATIONSHIPS",
        run_query("""
        MATCH (a)-[r]->(b)
        RETURN
            labels(a) AS start_labels,
            properties(a) AS start_properties,
            type(r) AS relationship,
            properties(r) AS relationship_properties,
            labels(b) AS end_labels,
            properties(b) AS end_properties
        LIMIT 10
        """)
    )