"""
Load Curated Semantic Graph into Neo4j

Purpose:
Adds deterministic semantic relationships from curated Tesla data.

This avoids hallucinated graph creation from raw SEC chunks.
"""

import json
from pathlib import Path

from .neo4j_connection import get_neo4j_driver


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CURATED_PATH = PROJECT_ROOT / "data" / "curated" / "tesla_semantic_seed.json"


def load_seed_data():
    if not CURATED_PATH.exists():
        raise FileNotFoundError(f"Missing curated seed file: {CURATED_PATH}")

    with open(CURATED_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def create_constraints(driver):
    queries = [
        """
        CREATE CONSTRAINT vehicle_model_name_unique IF NOT EXISTS
        FOR (v:VehicleModel)
        REQUIRE v.name IS UNIQUE
        """,
        """
        CREATE CONSTRAINT business_segment_name_unique IF NOT EXISTS
        FOR (b:BusinessSegment)
        REQUIRE b.name IS UNIQUE
        """,
        """
        CREATE CONSTRAINT technology_name_unique IF NOT EXISTS
        FOR (t:Technology)
        REQUIRE t.name IS UNIQUE
        """,
        """
        CREATE CONSTRAINT risk_factor_name_unique IF NOT EXISTS
        FOR (r:RiskFactor)
        REQUIRE r.name IS UNIQUE
        """,
        """
        CREATE CONSTRAINT event_name_unique IF NOT EXISTS
        FOR (e:Event)
        REQUIRE e.name IS UNIQUE
        """
    ]

    with driver.session() as session:
        for query in queries:
            session.run(query)


def load_vehicle_models(driver, company, models):
    query = """
    MATCH (c:Company {name: $company_name})

    MERGE (v:VehicleModel {name: $model_name})
    SET
        v.segment = $segment,
        v.status = $status,
        v.description = $description

    MERGE (s:BusinessSegment {name: $segment})
    SET s.description = $segment_description

    MERGE (c)-[:MANUFACTURES]->(v)
    MERGE (v)-[:BELONGS_TO_SEGMENT]->(s)
    MERGE (c)-[:HAS_SEGMENT]->(s)
    """

    with driver.session() as session:
        for model in models:
            session.run(
                query,
                {
                    "company_name": company["name"],
                    "model_name": model["name"],
                    "segment": model["segment"],
                    "status": model["status"],
                    "description": model["description"],
                    "segment_description": f"Vehicle segment: {model['segment']}",
                },
            )


def load_business_segments(driver, company, segments):
    query = """
    MATCH (c:Company {name: $company_name})

    MERGE (s:BusinessSegment {name: $segment_name})
    SET s.description = $description

    MERGE (c)-[:HAS_SEGMENT]->(s)
    """

    with driver.session() as session:
        for segment in segments:
            session.run(
                query,
                {
                    "company_name": company["name"],
                    "segment_name": segment["name"],
                    "description": segment["description"],
                },
            )


def load_technologies(driver, company, technologies):
    query = """
    MATCH (c:Company {name: $company_name})

    MERGE (t:Technology {name: $technology_name})
    SET t.description = $description

    MERGE (c)-[:USES_TECHNOLOGY]->(t)
    """

    with driver.session() as session:
        for tech in technologies:
            session.run(
                query,
                {
                    "company_name": company["name"],
                    "technology_name": tech["name"],
                    "description": tech["description"],
                },
            )


def load_risks(driver, company, risks):
    query = """
    MATCH (c:Company {name: $company_name})

    MERGE (r:RiskFactor {name: $risk_name})
    SET r.description = $description

    MERGE (c)-[:FACES_RISK]->(r)
    """

    with driver.session() as session:
        for risk in risks:
            session.run(
                query,
                {
                    "company_name": company["name"],
                    "risk_name": risk["name"],
                    "description": risk["description"],
                },
            )


def load_events(driver, company, events):
    query = """
    MATCH (c:Company {name: $company_name})

    MERGE (e:Event {name: $event_name})
    SET
        e.year = $year,
        e.description = $description

    MERGE (c)-[:EXPERIENCED_EVENT]->(e)
    """

    with driver.session() as session:
        for event in events:
            session.run(
                query,
                {
                    "company_name": company["name"],
                    "event_name": event["name"],
                    "year": event["year"],
                    "description": event["description"],
                },
            )


def load_reasoning_edges(driver):
    """
    Adds deterministic high-value semantic reasoning edges.
    These are curated rules, not LLM guesses.
    """

    queries = [
        """
        MATCH (r:RiskFactor {name: "Price Cuts"})
        MATCH (m:Metric {name: "gross_profit"})
        MERGE (r)-[:MAY_PRESSURE]->(m)
        """,
        """
        MATCH (r:RiskFactor {name: "Price Cuts"})
        MATCH (m:Metric {name: "revenue"})
        MERGE (r)-[:MAY_SUPPORT]->(m)
        """,
        """
        MATCH (r:RiskFactor {name: "Supply Chain Constraints"})
        MATCH (m:Metric {name: "revenue"})
        MERGE (r)-[:MAY_IMPACT]->(m)
        """,
        """
        MATCH (r:RiskFactor {name: "EV Competition"})
        MATCH (m:Metric {name: "revenue"})
        MERGE (r)-[:MAY_IMPACT]->(m)
        """,
        """
        MATCH (s:BusinessSegment {name: "Automotive"})
        MATCH (m:Metric {name: "revenue"})
        MERGE (s)-[:CONTRIBUTES_TO]->(m)
        """,
        """
        MATCH (v:VehicleModel {name: "Model Y"})
        MATCH (s:BusinessSegment {name: "Automotive"})
        MERGE (v)-[:CONTRIBUTES_TO]->(s)
        """,
        """
        MATCH (v:VehicleModel {name: "Model 3"})
        MATCH (s:BusinessSegment {name: "Automotive"})
        MERGE (v)-[:CONTRIBUTES_TO]->(s)
        """,
        """
        MATCH (e:Event {name: "Cybertruck Launch"})
        MATCH (v:VehicleModel {name: "Cybertruck"})
        MERGE (e)-[:RELATED_TO]->(v)
        """,
        """
        MATCH (e:Event {name: "Vehicle Price Reductions"})
        MATCH (r:RiskFactor {name: "Price Cuts"})
        MERGE (e)-[:RELATED_TO]->(r)
        """
    ]

    with driver.session() as session:
        for query in queries:
            session.run(query)


def print_summary(driver):
    with driver.session() as session:
        print("\nNode labels:")
        result = session.run(
            """
            MATCH (n)
            UNWIND labels(n) AS label
            RETURN label, count(*) AS count
            ORDER BY count DESC
            """
        )
        for row in result:
            print(f"{row['label']}: {row['count']}")

        print("\nRelationship types:")
        result = session.run(
            """
            MATCH ()-[r]->()
            RETURN type(r) AS relationship_type, count(*) AS count
            ORDER BY count DESC
            """
        )
        for row in result:
            print(f"{row['relationship_type']}: {row['count']}")


def main():
    data = load_seed_data()
    company = data["company"]

    driver = get_neo4j_driver()

    try:
        create_constraints(driver)
        load_business_segments(driver, company, data["business_segments"])
        load_vehicle_models(driver, company, data["vehicle_models"])
        load_technologies(driver, company, data["technologies"])
        load_risks(driver, company, data["risk_factors"])
        load_events(driver, company, data["events"])
        load_reasoning_edges(driver)

        print("Curated semantic graph loaded successfully.")
        print_summary(driver)

    finally:
        driver.close()


if __name__ == "__main__":
    main()