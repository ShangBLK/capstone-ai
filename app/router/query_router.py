"""
Query Router for Hybrid Explainable RAG

Purpose:
Determines which retrieval layers should be used for a given question.

Retrieval layers:
- SQL: exact numerical facts and trends
- Graph: semantic relationships and multi-hop reasoning
- Vector: supporting narrative text and explanations

Most important route:
- hybrid_sql_graph_vector
  Used for analytical "why" questions that require:
    1. Financial metrics
    2. Semantic relationships
    3. Supporting textual evidence
"""

from dataclasses import dataclass


@dataclass
class RouteDecision:
    query: str
    route: str
    reason: str


# ============================================================================
# KEYWORD SIGNALS
# ============================================================================

SQL_KEYWORDS = [
    "revenue",
    "net income",
    "income",
    "profit",
    "gross profit",
    "operating income",
    "ebit",
    "ebitda",
    "eps",
    "sales",
    "how much",
    "amount",
    "value",
    "trend",
    "compare",
    "increase",
    "decrease",
    "grew",
    "declined",
    "2021",
    "2022",
    "2023",
    "2024",
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
    "drivers",
    "drives",
    "risk",
    "risks",
    "technology",
    "technologies",
    "event",
    "events",
    "model",
    "models",
    "vehicle",
    "vehicles",
]

VECTOR_KEYWORDS = [
    "explain",
    "describe",
    "discussion",
    "strategy",
    "management",
    "operations",
    "context",
    "evidence",
    "supporting text",
    "according to",
]

ANALYTICAL_KEYWORDS = [
    "why",
    "what caused",
    "what explains",
    "how did",
    "what drove",
    "what drives",
    "what factors",
    "what impacted",
    "what affected",
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def contains_any(query, keywords):
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in keywords)


# ============================================================================
# ROUTER
# ============================================================================

def route_query(query):
    """
    Returns the best retrieval route for a user question.
    """

    query_lower = query.lower()

    has_sql_signal = contains_any(query_lower, SQL_KEYWORDS)
    has_graph_signal = contains_any(query_lower, GRAPH_KEYWORDS)
    has_vector_signal = contains_any(query_lower, VECTOR_KEYWORDS)
    has_analytical_signal = contains_any(query_lower, ANALYTICAL_KEYWORDS)

    # ----------------------------------------------------------------------
    # Highest-value route:
    # Analytical "why" questions should use all three retrieval systems.
    # ----------------------------------------------------------------------
    if has_analytical_signal and has_sql_signal:
        return RouteDecision(
            query=query,
            route="hybrid_sql_graph_vector",
            reason=(
                "Analytical question requires financial metrics, semantic "
                "relationships, and supporting narrative evidence."
            ),
        )

    # ----------------------------------------------------------------------
    # Three-way hybrid if all signals are present.
    # ----------------------------------------------------------------------
    if has_sql_signal and has_graph_signal and has_vector_signal:
        return RouteDecision(
            query=query,
            route="hybrid_sql_graph_vector",
            reason=(
                "Query contains structured, graph, and explanatory signals."
            ),
        )

    # ----------------------------------------------------------------------
    # Two-way hybrids
    # ----------------------------------------------------------------------
    if has_sql_signal and has_graph_signal:
        return RouteDecision(
            query=query,
            route="hybrid_sql_graph",
            reason=(
                "Query requires financial facts and semantic relationships."
            ),
        )

    if has_sql_signal and has_vector_signal:
        return RouteDecision(
            query=query,
            route="hybrid_sql_vector",
            reason=(
                "Query requires financial values and explanatory text."
            ),
        )

    if has_graph_signal and has_vector_signal:
        return RouteDecision(
            query=query,
            route="hybrid_graph_vector",
            reason=(
                "Query requires semantic relationships and narrative context."
            ),
        )

    # ----------------------------------------------------------------------
    # Single-system routes
    # ----------------------------------------------------------------------
    if has_sql_signal:
        return RouteDecision(
            query=query,
            route="sql",
            reason=(
                "Query asks for exact financial metrics or trends."
            ),
        )

    if has_graph_signal:
        return RouteDecision(
            query=query,
            route="graph",
            reason=(
                "Query asks about relationships, risks, models, events, "
                "or technologies."
            ),
        )

    if has_vector_signal:
        return RouteDecision(
            query=query,
            route="vector",
            reason=(
                "Query asks for explanatory text or supporting evidence."
            ),
        )

    # ----------------------------------------------------------------------
    # Default route
    # ----------------------------------------------------------------------
    return RouteDecision(
        query=query,
        route="hybrid_sql_graph_vector",
        reason=(
            "No dominant signal detected; defaulting to full hybrid retrieval."
        ),
    )


# ============================================================================
# PRINTING
# ============================================================================

def print_route_decision(decision):
    print("-" * 80)
    print(f"Query:  {decision.query}")
    print(f"Route:  {decision.route}")
    print(f"Reason: {decision.reason}")


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    test_queries = [
        "What was Tesla revenue in 2022?",
        "What risks affect Tesla revenue?",
        "What technologies are connected to Tesla?",
        "Why did Tesla revenue increase from 2022 to 2023?",
        "What drove Tesla gross profit changes?",
        "Explain Tesla's business strategy.",
        "How did price cuts affect Tesla margins?",
    ]

    print("\nHYBRID QUERY ROUTER TEST RESULTS\n")

    for query in test_queries:
        decision = route_query(query)
        print_route_decision(decision)