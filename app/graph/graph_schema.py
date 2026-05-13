"""
Graph Schema for Financial GraphRAG

Purpose:
Defines the official Neo4j ontology used by the project.

Core rule:
- SQL owns exact numerical truth.
- Neo4j owns semantic relationships and multi-hop reasoning.
- FAISS owns raw document context.
- LLMs may extract semantic relationships, but should not invent financial values.
"""

# =============================================================================
# NODE LABELS
# =============================================================================

NODE_LABELS = [
    # Core business entities
    "Company",
    "Year",
    "Source",
    "Evidence",

    # Structured financial graph backbone
    "Metric",
    "FinancialFact",

    # Semantic business graph
    "VehicleModel",
    "Technology",
    "BusinessSegment",
    "Geography",
    "RiskFactor",
    "Event",
    "Trend",
    "Strategy",
    "Organization",
    "BusinessConcept",

    # Optional document context
    "Filing",
    "Section",
    "Chunk",
]


# =============================================================================
# RELATIONSHIP TYPES
# =============================================================================

RELATION_TYPES = [
    # Structured financial relationships
    "REPORTED",
    "MEASURES",
    "FOR_YEAR",
    "SUPPORTED_BY",
    "FROM_SOURCE",

    # Company/business relationships
    "MANUFACTURES",
    "USES_TECHNOLOGY",
    "OPERATES_IN",
    "HAS_SEGMENT",
    "FACES_RISK",
    "EXPERIENCED_EVENT",
    "HAS_STRATEGY",
    "COMPETES_WITH",
    "PARTNERS_WITH",

    # Trend/reasoning relationships
    "SHOWED_TREND",
    "AFFECTS",
    "CAUSES",
    "IMPACTS",
    "INCREASES",
    "DECREASES",
    "ASSOCIATED_WITH",

    # Optional document relationships
    "FILED",
    "HAS_SECTION",
    "HAS_CHUNK",
    "NEXT",
    "MENTIONS",
]


# =============================================================================
# STRUCTURED GRAPH SCHEMA
# Built from SQLite canonical_financials and financial_evidence
# =============================================================================

STRUCTURED_GRAPH_SCHEMA = {
    "nodes": {
        "Company": {
            "required": ["name"],
            "optional": ["ticker", "cik"],
        },
        "Metric": {
            "required": ["name"],
            "optional": ["unit", "description"],
        },
        "FinancialFact": {
            "required": [
                "canonical_id",
                "value",
                "unit",
                "filing_year",
                "confidence_score",
                "conflict_status",
            ],
            "optional": [
                "source_count",
                "max_percent_difference",
                "selected_source_type",
                "selected_evidence_id",
            ],
        },
        "Year": {
            "required": ["year"],
            "optional": [],
        },
        "Evidence": {
            "required": ["evidence_id"],
            "optional": [
                "source_type",
                "source_name",
                "publication_date",
                "confidence_score",
            ],
        },
        "Source": {
            "required": ["name"],
            "optional": ["source_type", "source_url"],
        },
    },
    "relationships": [
        ("Company", "REPORTED", "FinancialFact"),
        ("FinancialFact", "MEASURES", "Metric"),
        ("FinancialFact", "FOR_YEAR", "Year"),
        ("FinancialFact", "SUPPORTED_BY", "Evidence"),
        ("Evidence", "FROM_SOURCE", "Source"),
    ],
}


# =============================================================================
# LLM SEMANTIC EXTRACTION SCHEMA
# Used only for semantic relationships, not exact financial values
# =============================================================================

LLM_ENTITY_LABELS = [
    "Company",
    "VehicleModel",
    "Technology",
    "BusinessSegment",
    "Geography",
    "RiskFactor",
    "Event",
    "Trend",
    "Strategy",
    "Organization",
    "BusinessConcept",
]

LLM_RELATION_TYPES = [
    "MANUFACTURES",
    "USES_TECHNOLOGY",
    "OPERATES_IN",
    "HAS_SEGMENT",
    "FACES_RISK",
    "EXPERIENCED_EVENT",
    "HAS_STRATEGY",
    "COMPETES_WITH",
    "PARTNERS_WITH",
    "SHOWED_TREND",
    "AFFECTS",
    "CAUSES",
    "IMPACTS",
    "INCREASES",
    "DECREASES",
    "ASSOCIATED_WITH",
]

LLM_EXTRACTION_SCHEMA = {
    "allowed_entity_labels": LLM_ENTITY_LABELS,
    "allowed_relationship_types": LLM_RELATION_TYPES,
    "rules": [
        "Do not extract exact financial metric values.",
        "Do not create relationships from SEC boilerplate.",
        "Only extract relationships clearly supported by the text.",
        "Every extracted relationship must include supporting text.",
        "Prefer business-relevant relationships over generic mentions.",
    ],
}


# =============================================================================
# CHUNK FILTERING KEYWORDS
# Used to select candidate chunks for semantic extraction
# =============================================================================

RELEVANT_KEYWORDS = [
    "revenue",
    "automotive",
    "energy generation",
    "energy storage",
    "gross margin",
    "profitability",
    "demand",
    "supply chain",
    "manufacturing",
    "production",
    "deliveries",
    "operations",
    "liquidity",
    "cash flow",
    "competition",
    "risk",
    "inflation",
    "interest rates",
    "cost of revenues",
    "battery",
    "electric vehicle",
    "charging",
    "autonomous",
    "software",
    "regulatory",
    "pricing",
    "margin",
]


# =============================================================================
# BACKWARD-COMPATIBILITY ALIASES
# Keep these so older scripts do not immediately break.
# =============================================================================

EXTRACTION_SCHEMA = LLM_EXTRACTION_SCHEMA