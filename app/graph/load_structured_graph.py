"""
Load Structured Financial Graph into Neo4j

Purpose:
Builds the trusted Neo4j graph backbone from SQLite canonical_financials.

SQL remains the source of exact numerical truth.
Neo4j represents the semantic structure around those trusted facts.
"""

import json
import sqlite3
from pathlib import Path

from .neo4j_connection import get_neo4j_driver


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQLITE_DB_PATH = PROJECT_ROOT / "storage" / "sqlite" / "financials.db"


def fetch_canonical_financials():
    """
    Reads canonical financial facts from SQLite.
    """

    if not SQLITE_DB_PATH.exists():
        raise FileNotFoundError(f"SQLite database not found: {SQLITE_DB_PATH}")

    connection = sqlite3.connect(SQLITE_DB_PATH)
    connection.row_factory = sqlite3.Row

    query = """
    SELECT
        canonical_id,
        company_name,
        ticker,
        cik,
        filing_year,
        metric,
        value,
        unit,
        selected_evidence_id,
        selected_source_type,
        source_count,
        conflict_status,
        max_percent_difference,
        confidence_score,
        metadata_json
    FROM canonical_financials
    ORDER BY company_name, filing_year, metric
    """

    rows = connection.execute(query).fetchall()
    connection.close()

    return [dict(row) for row in rows]


def safe_json_load(value):
    """
    Safely parses JSON metadata from SQLite.
    """

    if not value:
        return {}

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def create_constraints(driver):
    """
    Creates uniqueness constraints for structured graph nodes.
    """

    constraints = [
        """
        CREATE CONSTRAINT company_name_unique IF NOT EXISTS
        FOR (c:Company)
        REQUIRE c.name IS UNIQUE
        """,
        """
        CREATE CONSTRAINT metric_name_unique IF NOT EXISTS
        FOR (m:Metric)
        REQUIRE m.name IS UNIQUE
        """,
        """
        CREATE CONSTRAINT financial_fact_id_unique IF NOT EXISTS
        FOR (f:FinancialFact)
        REQUIRE f.canonical_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT year_unique IF NOT EXISTS
        FOR (y:Year)
        REQUIRE y.year IS UNIQUE
        """,
        """
        CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS
        FOR (e:Evidence)
        REQUIRE e.evidence_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT source_name_unique IF NOT EXISTS
        FOR (s:Source)
        REQUIRE s.name IS UNIQUE
        """
    ]

    with driver.session() as session:
        for constraint in constraints:
            session.run(constraint)


def load_financial_fact(driver, record):
    """
    Loads one canonical financial fact and its graph neighborhood.
    """

    metadata = safe_json_load(record.get("metadata_json"))

    source_name = record.get("selected_source_type") or "unknown_source"
    evidence_id = record.get("selected_evidence_id") or f"missing_evidence_{record['canonical_id']}"

    query = """
    MERGE (company:Company {name: $company_name})
    SET
        company.ticker = $ticker,
        company.cik = $cik

    MERGE (metric:Metric {name: $metric})
    SET
        metric.unit = $unit

    MERGE (year:Year {year: $filing_year})

    MERGE (fact:FinancialFact {canonical_id: $canonical_id})
    SET
        fact.value = $value,
        fact.unit = $unit,
        fact.filing_year = $filing_year,
        fact.confidence_score = $confidence_score,
        fact.conflict_status = $conflict_status,
        fact.source_count = $source_count,
        fact.max_percent_difference = $max_percent_difference,
        fact.selected_source_type = $selected_source_type,
        fact.selected_evidence_id = $selected_evidence_id,
        fact.metadata_json = $metadata_json

    MERGE (evidence:Evidence {evidence_id: $evidence_id})
    SET
        evidence.source_type = $selected_source_type,
        evidence.confidence_score = $confidence_score

    MERGE (source:Source {name: $source_name})
    SET
        source.source_type = $selected_source_type

    MERGE (company)-[:REPORTED]->(fact)
    MERGE (fact)-[:MEASURES]->(metric)
    MERGE (fact)-[:FOR_YEAR]->(year)
    MERGE (fact)-[:SUPPORTED_BY]->(evidence)
    MERGE (evidence)-[:FROM_SOURCE]->(source)
    """

    params = {
        "canonical_id": record["canonical_id"],
        "company_name": record["company_name"],
        "ticker": record.get("ticker"),
        "cik": record.get("cik"),
        "filing_year": int(record["filing_year"]),
        "metric": record["metric"],
        "value": float(record["value"]),
        "unit": record.get("unit"),
        "selected_evidence_id": record.get("selected_evidence_id"),
        "selected_source_type": record.get("selected_source_type"),
        "source_count": record.get("source_count"),
        "conflict_status": record.get("conflict_status"),
        "max_percent_difference": record.get("max_percent_difference"),
        "confidence_score": record.get("confidence_score"),
        "metadata_json": json.dumps(metadata),
        "evidence_id": evidence_id,
        "source_name": source_name,
    }

    with driver.session() as session:
        session.run(query, params)


def print_graph_summary(driver):
    """
    Prints structured graph summary.
    """

    queries = {
        "Company nodes": "MATCH (n:Company) RETURN count(n) AS count",
        "Metric nodes": "MATCH (n:Metric) RETURN count(n) AS count",
        "FinancialFact nodes": "MATCH (n:FinancialFact) RETURN count(n) AS count",
        "Year nodes": "MATCH (n:Year) RETURN count(n) AS count",
        "Evidence nodes": "MATCH (n:Evidence) RETURN count(n) AS count",
        "Source nodes": "MATCH (n:Source) RETURN count(n) AS count",
        "Relationships": "MATCH ()-[r]->() RETURN count(r) AS count",
    }

    with driver.session() as session:
        for label, query in queries.items():
            result = session.run(query).single()
            print(f"{label}: {result['count']}")

        print("\nRelationship types:")
        result = session.run(
            """
            MATCH ()-[r]->()
            RETURN type(r) AS relationship_type, count(r) AS count
            ORDER BY relationship_type
            """
        )

        for row in result:
            print(f"{row['relationship_type']}: {row['count']}")


def main():
    """
    Main loader entry point.
    """

    records = fetch_canonical_financials()

    print(f"Loaded {len(records)} canonical financial records from SQLite.")

    driver = get_neo4j_driver()

    try:
        create_constraints(driver)

        for record in records:
            load_financial_fact(driver, record)

        print_graph_summary(driver)
        print("\nStructured financial graph loaded successfully.")

    finally:
        driver.close()


if __name__ == "__main__":
    main()