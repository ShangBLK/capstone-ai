"""
Graph Retriever for Neo4j Financial GraphRAG

Purpose:
Provides clean retrieval functions for the structured + semantic Neo4j graph.

Used by:
- query_router.py
- hybrid_retriever.py
- future LangChain agent
"""

from .neo4j_connection import get_neo4j_driver


def run_query(cypher, parameters=None):
    parameters = parameters or {}
    driver = get_neo4j_driver()

    try:
        with driver.session() as session:
            result = session.run(cypher, parameters)
            return [record.data() for record in result]
    finally:
        driver.close()


def get_company_models(company_name="tesla"):
    cypher = """
    MATCH (c:Company)-[:MANUFACTURES]->(v:VehicleModel)
    WHERE toLower(c.name) = toLower($company_name)
    OPTIONAL MATCH (v)-[:BELONGS_TO_SEGMENT]->(s:BusinessSegment)
    RETURN
        c.name AS company,
        v.name AS vehicle_model,
        v.description AS description,
        v.status AS status,
        s.name AS segment
    ORDER BY vehicle_model
    """

    return run_query(cypher, {"company_name": company_name})


def get_company_risks(company_name="tesla"):
    cypher = """
    MATCH (c:Company)-[:FACES_RISK]->(r:RiskFactor)
    WHERE toLower(c.name) = toLower($company_name)
    OPTIONAL MATCH (r)-[impact]->(m:Metric)
    RETURN
        c.name AS company,
        r.name AS risk,
        r.description AS description,
        type(impact) AS impact_relationship,
        m.name AS impacted_metric
    ORDER BY risk, impacted_metric
    """

    return run_query(cypher, {"company_name": company_name})


def get_company_technologies(company_name="tesla"):
    cypher = """
    MATCH (c:Company)-[:USES_TECHNOLOGY]->(t:Technology)
    WHERE toLower(c.name) = toLower($company_name)
    RETURN
        c.name AS company,
        t.name AS technology,
        t.description AS description
    ORDER BY technology
    """

    return run_query(cypher, {"company_name": company_name})


def get_company_events(company_name="tesla"):
    cypher = """
    MATCH (c:Company)-[:EXPERIENCED_EVENT]->(e:Event)
    WHERE toLower(c.name) = toLower($company_name)
    OPTIONAL MATCH (e)-[rel]->(target)
    RETURN
        c.name AS company,
        e.name AS event,
        e.year AS year,
        e.description AS description,
        type(rel) AS related_relationship,
        labels(target) AS related_labels,
        target.name AS related_entity
    ORDER BY year, event
    """

    return run_query(cypher, {"company_name": company_name})


def get_metric_facts(company_name="tesla", metric_name="revenue"):
    cypher = """
    MATCH (c:Company)-[:REPORTED]->(f:FinancialFact)-[:MEASURES]->(m:Metric)
    MATCH (f)-[:FOR_YEAR]->(y:Year)
    WHERE toLower(c.name) = toLower($company_name)
      AND toLower(m.name) = toLower($metric_name)
    OPTIONAL MATCH (f)-[:SUPPORTED_BY]->(e:Evidence)-[:FROM_SOURCE]->(s:Source)
    RETURN
        c.name AS company,
        y.year AS year,
        m.name AS metric,
        f.value AS value,
        f.unit AS unit,
        f.conflict_status AS conflict_status,
        f.confidence_score AS confidence_score,
        e.evidence_id AS evidence_id,
        s.name AS source
    ORDER BY year
    """

    return run_query(
        cypher,
        {
            "company_name": company_name,
            "metric_name": metric_name,
        },
    )


def get_metric_drivers(company_name="tesla", metric_name="revenue"):
    cypher = """
    MATCH (m:Metric)
    WHERE toLower(m.name) = toLower($metric_name)

    OPTIONAL MATCH (s:BusinessSegment)-[sr:CONTRIBUTES_TO]->(m)
    OPTIONAL MATCH (v:VehicleModel)-[vr:CONTRIBUTES_TO]->(s)
    OPTIONAL MATCH (r:RiskFactor)-[rr]->(m)
    WHERE type(rr) IN ["MAY_IMPACT", "MAY_PRESSURE", "MAY_SUPPORT"]

    OPTIONAL MATCH (c:Company)
    WHERE toLower(c.name) = toLower($company_name)

    RETURN
        m.name AS metric,
        collect(DISTINCT {
            segment: s.name,
            relationship: type(sr)
        }) AS contributing_segments,
        collect(DISTINCT {
            vehicle_model: v.name,
            relationship: type(vr),
            segment: s.name
        }) AS contributing_models,
        collect(DISTINCT {
            risk: r.name,
            relationship: type(rr),
            description: r.description
        }) AS risk_or_event_drivers
    """

    return run_query(
        cypher,
        {
            "company_name": company_name,
            "metric_name": metric_name,
        },
    )


def get_company_semantic_profile(company_name="tesla"):
    return {
        "company": company_name,
        "models": get_company_models(company_name),
        "risks": get_company_risks(company_name),
        "technologies": get_company_technologies(company_name),
        "events": get_company_events(company_name),
    }


def graph_search(query, company_name="tesla"):
    query_lower = query.lower()

    if "model" in query_lower or "vehicle" in query_lower or "car" in query_lower:
        route = "company_models"
        results = get_company_models(company_name)

    elif "risk" in query_lower or "pressure" in query_lower or "impact" in query_lower:
        route = "company_risks"
        results = get_company_risks(company_name)

    elif "technology" in query_lower or "battery" in query_lower or "charging" in query_lower:
        route = "company_technologies"
        results = get_company_technologies(company_name)

    elif "event" in query_lower or "launch" in query_lower or "price cut" in query_lower:
        route = "company_events"
        results = get_company_events(company_name)

    elif "revenue" in query_lower:
        route = "metric_drivers_revenue"
        results = get_metric_drivers(company_name, "revenue")

    elif "gross profit" in query_lower or "gross_profit" in query_lower:
        route = "metric_drivers_gross_profit"
        results = get_metric_drivers(company_name, "gross_profit")

    else:
        route = "company_semantic_profile"
        results = get_company_semantic_profile(company_name)

    return {
        "query": query,
        "company": company_name,
        "graph_route": route,
        "results": results,
    }


def print_graph_results(output):
    print("=" * 80)
    print(f"QUERY: {output['query']}")
    print(f"COMPANY: {output['company']}")
    print(f"GRAPH ROUTE: {output['graph_route']}")
    print("=" * 80)

    results = output["results"]

    if not results:
        print("No graph results found.")
        return

    if isinstance(results, dict):
        for key, value in results.items():
            print(f"\n{key.upper()}")
            print(value)
    else:
        for i, row in enumerate(results, start=1):
            print(f"\nResult {i}")
            for key, value in row.items():
                print(f"{key}: {value}")
            print("-" * 80)


if __name__ == "__main__":
    test_queries = [
        "What vehicle models does Tesla manufacture?",
        "What risks could affect Tesla revenue?",
        "What technologies are connected to Tesla?",
        "What events are connected to Tesla?",
        "What drives Tesla revenue?",
        "What could pressure Tesla gross profit?",
    ]

    for q in test_queries:
        output = graph_search(q)
        print_graph_results(output)
        print("\n")