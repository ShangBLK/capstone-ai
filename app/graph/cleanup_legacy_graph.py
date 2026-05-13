"""
Cleanup Legacy/Test Graph Data

Removes old Entity/Chunk-based semantic extraction artifacts while preserving
the structured financial backbone.
"""

from .neo4j_connection import get_neo4j_driver


def main():
    driver = get_neo4j_driver()

    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (n)
                WHERE n:Entity OR n:Chunk
                DETACH DELETE n
                RETURN count(n) AS deleted_count
                """
            ).single()

            print(f"Deleted {result['deleted_count']} legacy nodes.")
            print("Structured financial graph preserved.")

    finally:
        driver.close()


if __name__ == "__main__":
    main()