"""
Inspect Neo4j Graph

Purpose:
Provides a clear diagnostic view of the current Neo4j database.

This separates:
1. Structured financial graph backbone
2. Semantic/LLM graph relationships
3. Legacy/test contamination
"""

from .neo4j_connection import get_neo4j_driver


STRUCTURED_NODE_LABELS = [
    "Company",
    "Metric",
    "FinancialFact",
    "Year",
    "Evidence",
    "Source",
]

STRUCTURED_RELATIONSHIPS = [
    "REPORTED",
    "MEASURES",
    "FOR_YEAR",
    "SUPPORTED_BY",
    "FROM_SOURCE",
]


def run_query(cypher, params=None):
    driver = get_neo4j_driver()

    try:
        with driver.session() as session:
            result = session.run(cypher, params or {})
            return [record.data() for record in result]
    finally:
        driver.close()


def print_section(title, rows):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    if not rows:
        print("No results.")
        return

    for row in rows:
        print(row)


def inspect_node_counts():
    print_section(
        "ALL NODE LABEL COUNTS",
        run_query(
            """
            MATCH (n)
            UNWIND labels(n) AS label
            RETURN label, count(*) AS count
            ORDER BY count DESC
            """
        ),
    )


def inspect_relationship_counts():
    print_section(
        "ALL RELATIONSHIP TYPE COUNTS",
        run_query(
            """
            MATCH ()-[r]->()
            RETURN type(r) AS relationship_type, count(*) AS count
            ORDER BY count DESC
            """
        ),
    )


def inspect_structured_backbone():
    print_section(
        "STRUCTURED FINANCIAL BACKBONE",
        run_query(
            """
            MATCH (c:Company)-[:REPORTED]->(f:FinancialFact)
                  -[:MEASURES]->(m:Metric)
            MATCH (f)-[:FOR_YEAR]->(y:Year)
            RETURN
                c.name AS company,
                c.ticker AS ticker,
                y.year AS year,
                m.name AS metric,
                f.value AS value,
                f.unit AS unit,
                f.conflict_status AS conflict_status,
                f.confidence_score AS confidence_score
            ORDER BY company, year, metric
            LIMIT 25
            """
        ),
    )


def inspect_conflicted_facts():
    print_section(
        "CONFLICTED OR MINOR-DIFFERENCE FACTS",
        run_query(
            """
            MATCH (c:Company)-[:REPORTED]->(f:FinancialFact)
                  -[:MEASURES]->(m:Metric)
            MATCH (f)-[:FOR_YEAR]->(y:Year)
            WHERE f.conflict_status IN ["conflict", "minor_difference"]
            RETURN
                c.name AS company,
                y.year AS year,
                m.name AS metric,
                f.value AS selected_value,
                f.unit AS unit,
                f.conflict_status AS conflict_status,
                f.max_percent_difference AS max_percent_difference,
                f.selected_source_type AS selected_source_type,
                f.selected_evidence_id AS selected_evidence_id
            ORDER BY company, year, metric
            """
        ),
    )


def inspect_provenance_paths():
    print_section(
        "SAMPLE PROVENANCE PATHS",
        run_query(
            """
            MATCH (c:Company)-[:REPORTED]->(f:FinancialFact)
                  -[:SUPPORTED_BY]->(e:Evidence)
                  -[:FROM_SOURCE]->(s:Source)
            MATCH (f)-[:MEASURES]->(m:Metric)
            MATCH (f)-[:FOR_YEAR]->(y:Year)
            RETURN
                c.name AS company,
                y.year AS year,
                m.name AS metric,
                f.value AS value,
                e.evidence_id AS evidence_id,
                s.name AS source
            ORDER BY company, year, metric
            LIMIT 20
            """
        ),
    )


def inspect_possible_legacy_data():
    print_section(
        "POSSIBLE LEGACY / TEST DATA",
        run_query(
            """
            MATCH (n)
            WHERE any(label IN labels(n) WHERE NOT label IN $structured_labels)
            RETURN labels(n) AS labels, count(*) AS count
            ORDER BY count DESC
            """,
            {"structured_labels": STRUCTURED_NODE_LABELS},
        ),
    )

    print_section(
        "POSSIBLE LEGACY / TEST RELATIONSHIPS",
        run_query(
            """
            MATCH ()-[r]->()
            WHERE NOT type(r) IN $structured_relationships
            RETURN type(r) AS relationship_type, count(*) AS count
            ORDER BY count DESC
            """,
            {"structured_relationships": STRUCTURED_RELATIONSHIPS},
        ),
    )


def inspect_sample_semantic_relationships():
    print_section(
        "SAMPLE NON-STRUCTURED RELATIONSHIPS",
        run_query(
            """
            MATCH (a)-[r]->(b)
            WHERE NOT type(r) IN $structured_relationships
            RETURN
                labels(a) AS start_labels,
                properties(a) AS start_properties,
                type(r) AS relationship,
                properties(r) AS relationship_properties,
                labels(b) AS end_labels,
                properties(b) AS end_properties
            LIMIT 10
            """,
            {"structured_relationships": STRUCTURED_RELATIONSHIPS},
        ),
    )


def main():
    inspect_node_counts()
    inspect_relationship_counts()
    inspect_structured_backbone()
    inspect_conflicted_facts()
    inspect_provenance_paths()
    inspect_possible_legacy_data()
    inspect_sample_semantic_relationships()


if __name__ == "__main__":
    main()