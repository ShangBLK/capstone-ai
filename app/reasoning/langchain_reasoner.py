"""
LangChain-style Reasoner for Explainable Hybrid RAG

Purpose:
Takes a user question, retrieves evidence from SQL/Neo4j/FAISS,
and generates a cited analytical answer.

This is intentionally controlled rather than fully autonomous.
"""

import json
import os
from dotenv import load_dotenv
from openai import OpenAI

from app.retrieval.hybrid_retriever import retrieve_evidence


MODEL = "gpt-4o-mini"


SYSTEM_PROMPT = """
You are an explainable financial analysis assistant for a capstone AI prototype.

You must answer only using the provided retrieved evidence.
Do not invent facts.
If evidence is missing, say so clearly.

The system is scoped to Tesla/Ford financial and EV-related analysis using:
1. SQL canonical financial evidence
2. Neo4j semantic graph evidence
3. FAISS vector text evidence

Always include:
- Answer
- Evidence Used
- Limitations

Be concise, specific, and transparent.
"""


def build_prompt(question, evidence):
    return f"""
User question:
{question}

Retrieved evidence JSON:
{json.dumps(evidence, indent=2)}

Instructions:
1. Answer the question using only the retrieved evidence.
2. Cite specific SQL evidence IDs when using numerical facts.
3. Cite graph relationships when using semantic reasoning.
4. Cite vector chunk IDs when using text excerpts.
5. If vector evidence is empty or weak, say so.
6. Include a short scope note.
7. Do not overclaim causality. Use cautious language like "may", "suggests", or "is linked to" unless the evidence directly proves causation.

Return the answer in this format:

Question:
...

Answer:
...

Evidence Used:
SQL:
- ...

Graph:
- ...

Vector:
- ...

Limitations:
...
"""


def answer_question(question):
    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is missing from .env")

    evidence = retrieve_evidence(question)

    client = OpenAI()

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(question, evidence)},
        ],
    )

    return {
        "question": question,
        "route": evidence["route"],
        "route_reason": evidence["route_reason"],
        "answer": response.choices[0].message.content,
        "raw_evidence": evidence,
    }


def main():
    print("=" * 80)
    print("Explainable Financial RAG Prototype")
    print("=" * 80)
    print(
        "Scope note: Ask narrow questions about Tesla/Ford revenue, profit, "
        "risks, vehicle models, technologies, events, or business drivers."
    )
    print("Example: Why did Tesla revenue increase from 2022 to 2023?")
    print("Type 'exit' to quit.")
    print("=" * 80)

    while True:
        question = input("\nAsk a question: ").strip()

        if question.lower() in ["exit", "quit"]:
            break

        if not question:
            continue

        result = answer_question(question)

        print("\n" + "=" * 80)
        print(f"ROUTE: {result['route']}")
        print(f"REASON: {result['route_reason']}")
        print("=" * 80)
        print(result["answer"])


if __name__ == "__main__":
    main()