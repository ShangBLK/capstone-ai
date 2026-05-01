"""
Graph Schema for Financial GraphRAG

Purpose:
Defines node labels and relationship types used for LLM-based
entity and relationship extraction.

Design principles:
- SQL handles exact numerical facts
- Graph handles semantic relationships and reasoning
- LLM extracts entities and relationships from chunks

This schema will guide:
- LLM extraction prompts
- Neo4j node/relationship creation
- GraphRAG retrieval patterns
"""
# GraphRAG Node Labels for Financial Domain

NODE_LABELS = [

    # Core structure
    "Company",
    "Filing",
    "Section",
    "Chunk",

    # Financial + business entities
    "FinancialMetric",
    "BusinessSegment",
    "ProductOrService",
    "Geography",
    "Strategy",
    "RiskFactor",
    "Event",
    "TimePeriod",

    # Abstract concepts
    "BusinessConcept"
    "Organization",
]

# GraphRAG Relationship Types

RELATION_TYPES = [

    # Structural (still useful)
    "FILED",
    "HAS_SECTION",
    "HAS_CHUNK",
    "NEXT",

    # Semantic extraction (core GraphRAG)
    "MENTIONS",
    "AFFECTS",
    "CAUSES",
    "ASSOCIATED_WITH",
    "PART_OF",
    "OPERATES_IN",
    "GENERATES_REVENUE_FROM",
    "FACES_RISK",
    "IMPACTS",
    "INCREASES",
    "DECREASES",
    "COMPARED_TO",
    "OCCURRED_IN",

    # Evidence linkage
    "SUPPORTED_BY_CHUNK"
]

# Schema guidance for LLM extraction

EXTRACTION_SCHEMA = {
    "entities": [
        "FinancialMetric",
        "BusinessSegment",
        "ProductOrService",
        "Geography",
        "Strategy",
        "RiskFactor",
        "Event",
        "TimePeriod",
        "Organization",
        "BusinessConcept"
    ],
    "relationships": [
        "AFFECTS",
        "CAUSES",
        "ASSOCIATED_WITH",
        "OPERATES_IN",
        "GENERATES_REVENUE_FROM",
        "FACES_RISK",
        "IMPACTS",
        "INCREASES",
        "DECREASES",
    ]
}
# Keywords used to select business-relevant chunks for test extraction.
# These help avoid SEC cover pages, filing checkboxes, and legal boilerplate.
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
    "cost of revenues"
]