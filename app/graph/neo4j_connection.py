import os
from dotenv import load_dotenv
from neo4j import GraphDatabase


def get_neo4j_driver():
    """
    Creates and returns a Neo4j driver using credentials stored in the .env file.

    This function does not run queries directly.
    It only establishes the reusable connection object.
    """

    load_dotenv()

    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri:
        raise ValueError("NEO4J_URI is missing from .env")

    if not username:
        raise ValueError("NEO4J_USERNAME is missing from .env")

    if not password:
        raise ValueError("NEO4J_PASSWORD is missing from .env")

    driver = GraphDatabase.driver(
        uri,
        auth=(username, password)
    )

    return driver


def test_neo4j_connection():
    """
    Verifies that the Neo4j connection works.

    This is used as a safe checkpoint before building or loading the graph.
    """

    driver = get_neo4j_driver()

    try:
        driver.verify_connectivity()
        print("Neo4j connection passed from app/graph/neo4j_connection.py")
    finally:
        driver.close()


if __name__ == "__main__":
    test_neo4j_connection()