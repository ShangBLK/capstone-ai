from app.router.query_router import route_query
from app.graph.graph_retriever import graph_search, get_metric_facts
from app.vector.vector_search import search_vector

def infer_metric(query):
    q = query.lower()
    if "gross profit" in q or "gross_profit" in q:
        return "gross_profit"
    if "net income" in q:
        return "net_income"
    if "operating income" in q:
        return "operating_income"
    if "revenue" in q:
        return "revenue"
    return "revenue"


def infer_company(query):
    q = query.lower()
    if "ford" in q:
        return "ford"
    return "tesla"


def retrieve_evidence(query):
    decision = route_query(query)
    company = infer_company(query)
    metric = infer_metric(query)

    evidence = {
        "query": query,
        "route": decision.route,
        "route_reason": decision.reason,
        "scope_note": (
            "This prototype is scoped to Tesla/Ford financial and EV-related "
            "analysis using the currently ingested SQL, Neo4j, and FAISS data."
        ),
        "sql_evidence": [],
        "graph_evidence": [],
        "vector_evidence": [],
    }

    if "sql" in decision.route:
        evidence["sql_evidence"] = get_metric_facts(company, metric)

    if "graph" in decision.route:
        evidence["graph_evidence"] = graph_search(query, company)["results"]

    # Vector left optional for now so the system works immediately.
    # We will connect FAISS after confirming this hybrid retriever works.
    if "vector" in decision.route:
        evidence["vector_evidence"] = search_vector(query, top_k=3)

    return evidence


def print_evidence(evidence):
    print("=" * 80)
    print("HYBRID RETRIEVAL RESULT")
    print("=" * 80)
    print(f"Query: {evidence['query']}")
    print(f"Route: {evidence['route']}")
    print(f"Reason: {evidence['route_reason']}")
    print(f"Scope: {evidence['scope_note']}")

    print("\nSQL Evidence:")
    for row in evidence["sql_evidence"]:
        print(row)

    print("\nGraph Evidence:")
    print(evidence["graph_evidence"])

    print("\nVector Evidence:")
    print(evidence["vector_evidence"])


if __name__ == "__main__":
    test_queries = [
        "What was Tesla revenue in 2022?",
        "What risks affect Tesla revenue?",
        "Why did Tesla revenue increase from 2022 to 2023?",
        "What could pressure Tesla gross profit?",
    ]

    for query in test_queries:
        result = retrieve_evidence(query)
        print_evidence(result)
        print("\n")