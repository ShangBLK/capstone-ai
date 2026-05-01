from dataclasses import dataclass


@dataclass
class RouteDecision:
    query: str
    route: str
    reason: str


SQL_KEYWORDS = [
    "revenue",
    "net income",
    "income",
    "profit",
    "sales",
    "how much",
    "amount",
    "value",
    "increase",
    "decrease",
    "trend",
    "compare",
    "2022",
    "2023",
]

VECTOR_KEYWORDS = [
    "explain",
    "describe",
    "discussion",
    "risk",
    "risks",
    "strategy",
    "business factors",
    "management",
    "operations",
    "why",
    "context",
]

GRAPH_KEYWORDS = [
    "relationship",
    "relationships",
    "connected",
    "connect",
    "affects",
    "causes",
    "associated",
    "related",
    "entities",
    "concepts",
    "impacts",
]


def contains_any(query, keywords):
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in keywords)


def route_query(query):
    query_lower = query.lower()

    has_sql_signal = contains_any(query_lower, SQL_KEYWORDS)
    has_vector_signal = contains_any(query_lower, VECTOR_KEYWORDS)
    has_graph_signal = contains_any(query_lower, GRAPH_KEYWORDS)

    if has_sql_signal and has_vector_signal:
        return RouteDecision(
            query=query,
            route="hybrid_sql_vector",
            reason="Query asks for both financial values and explanatory context."
        )

    if has_sql_signal and has_graph_signal:
        return RouteDecision(
            query=query,
            route="hybrid_sql_graph",
            reason="Query asks for financial values and relationships between entities or concepts."
        )

    if has_vector_signal and has_graph_signal:
        return RouteDecision(
            query=query,
            route="hybrid_vector_graph",
            reason="Query asks for explanatory text and relationship-based context."
        )

    if has_sql_signal:
        return RouteDecision(
            query=query,
            route="sql",
            reason="Query asks for structured financial values, trends, or year-specific metrics."
        )

    if has_graph_signal:
        return RouteDecision(
            query=query,
            route="graph",
            reason="Query asks about relationships, connected entities, or concept links."
        )

    if has_vector_signal:
        return RouteDecision(
            query=query,
            route="vector",
            reason="Query asks for explanation or semantic context from the filing text."
        )

    return RouteDecision(
        query=query,
        route="vector",
        reason="No strong structured or graph signal detected; defaulting to semantic text retrieval."
    )


def print_route_decision(decision):
    print("-" * 80)
    print(f"Query: {decision.query}")
    print(f"Route: {decision.route}")
    print(f"Reason: {decision.reason}")


if __name__ == "__main__":
    test_queries = [
        "What was Tesla's revenue in 2022?",
        "What was Tesla's net income in 2022?",
        "Describe Tesla's business risks.",
        "What business factors affected Tesla in 2022?",
        "Why did Tesla revenue increase from 2022 to 2023?",
        "What entities are connected to Tesla?",
        "What risks are associated with Tesla?",
        "Explain Tesla's revenue trend from 2022 to 2023.",
    ]

    print("\nPHASE 4 ROUTER TEST RESULTS\n")

    for query in test_queries:
        decision = route_query(query)
        print_route_decision(decision)