from pathlib import Path
import json
import sqlite3
from typing import Any, Dict, List, Tuple


EVIDENCE_DIR = Path("data/normalized/evidence_objects")
DATABASE_PATH = Path("storage/sqlite/financials.db")

SOURCE_PRIORITY = {
    "sec_api": 1,
    "financial_modeling_prep": 2,
    "alpha_vantage": 3,
}


def load_sql_evidence_files() -> List[Dict[str, Any]]:
    records = []

    for path in EVIDENCE_DIR.glob("*.json"):
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        for item in data:
            if "sql" in item.get("target_layers", []):
                records.append(item)

    return records


def create_tables(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS financial_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evidence_id TEXT NOT NULL UNIQUE,
            source_type TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT,
            publication_date TEXT,
            company_name TEXT NOT NULL,
            ticker TEXT,
            cik TEXT,
            filing_year INTEGER NOT NULL,
            metric TEXT NOT NULL,
            xbrl_tag TEXT,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            form TEXT,
            fiscal_period TEXT,
            period_start TEXT,
            period_end TEXT,
            frame TEXT,
            filed TEXT,
            accession_number TEXT,
            confidence_score REAL NOT NULL,
            metadata_json TEXT
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS canonical_financials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_id TEXT NOT NULL UNIQUE,
            company_name TEXT NOT NULL,
            ticker TEXT,
            cik TEXT,
            filing_year INTEGER NOT NULL,
            metric TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            selected_evidence_id TEXT NOT NULL,
            selected_source_type TEXT NOT NULL,
            source_count INTEGER NOT NULL,
            conflict_status TEXT NOT NULL,
            max_percent_difference REAL,
            confidence_score REAL NOT NULL,
            metadata_json TEXT,
            UNIQUE(company_name, filing_year, metric, unit)
        );
        """
    )

    connection.commit()


def evidence_to_row(evidence: Dict[str, Any]) -> Dict[str, Any]:
    metadata = evidence.get("metadata") or {}

    if evidence.get("metric_name") is None:
        raise ValueError(f"Missing metric_name: {evidence.get('evidence_id')}")

    if evidence.get("metric_value") is None:
        raise ValueError(f"Missing metric_value: {evidence.get('evidence_id')}")

    return {
        "evidence_id": evidence["evidence_id"],
        "source_type": evidence["source_type"],
        "source_name": evidence["source_name"],
        "source_url": evidence.get("source_url"),
        "publication_date": evidence.get("publication_date"),
        "company_name": evidence["company"],
        "ticker": metadata.get("ticker"),
        "cik": metadata.get("cik"),
        "filing_year": evidence["year"],
        "metric": evidence["metric_name"],
        "xbrl_tag": metadata.get("xbrl_tag"),
        "value": evidence["metric_value"],
        "unit": evidence["metric_unit"],
        "form": metadata.get("form"),
        "fiscal_period": metadata.get("fiscal_period"),
        "period_start": metadata.get("period_start"),
        "period_end": metadata.get("period_end"),
        "frame": metadata.get("frame"),
        "filed": metadata.get("filed"),
        "accession_number": metadata.get("accession_number"),
        "confidence_score": evidence.get("confidence_score", 1.0),
        "metadata_json": json.dumps(metadata, ensure_ascii=False),
    }


def insert_financial_evidence(
    connection: sqlite3.Connection,
    evidence_records: List[Dict[str, Any]],
) -> None:
    cursor = connection.cursor()

    inserted = 0
    skipped = 0

    for evidence in evidence_records:
        if "sql" not in evidence.get("target_layers", []):
            skipped += 1
            continue

        record = evidence_to_row(evidence)

        cursor.execute(
            """
            INSERT OR REPLACE INTO financial_evidence (
                evidence_id,
                source_type,
                source_name,
                source_url,
                publication_date,
                company_name,
                ticker,
                cik,
                filing_year,
                metric,
                xbrl_tag,
                value,
                unit,
                form,
                fiscal_period,
                period_start,
                period_end,
                frame,
                filed,
                accession_number,
                confidence_score,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                record["evidence_id"],
                record["source_type"],
                record["source_name"],
                record["source_url"],
                record["publication_date"],
                record["company_name"],
                record["ticker"],
                record["cik"],
                record["filing_year"],
                record["metric"],
                record["xbrl_tag"],
                record["value"],
                record["unit"],
                record["form"],
                record["fiscal_period"],
                record["period_start"],
                record["period_end"],
                record["frame"],
                record["filed"],
                record["accession_number"],
                record["confidence_score"],
                record["metadata_json"],
            ),
        )

        inserted += 1

    connection.commit()

    print(f"Inserted/replaced {inserted} financial evidence record(s).")
    print(f"Skipped {skipped} non-SQL record(s).")


def get_group_key(row: sqlite3.Row) -> Tuple[str, int, str, str]:
    return (
        row["company_name"],
        row["filing_year"],
        row["metric"],
        row["unit"],
    )


def calculate_conflict_status(values: List[float]) -> Tuple[str, float]:
    if len(values) <= 1:
        return "single_source", 0.0

    min_value = min(values)
    max_value = max(values)

    if max_value == 0:
        percent_difference = 0.0 if min_value == 0 else 100.0
    else:
        percent_difference = abs(max_value - min_value) / abs(max_value) * 100

    if percent_difference == 0:
        return "no_conflict", percent_difference

    if percent_difference <= 0.5:
        return "minor_difference", percent_difference

    return "conflict", percent_difference


def choose_canonical_record(rows: List[sqlite3.Row]) -> sqlite3.Row:
    return sorted(
        rows,
        key=lambda row: (
            SOURCE_PRIORITY.get(row["source_type"], 999),
            -float(row["confidence_score"]),
            row["filed"] or "",
        ),
    )[0]


def rebuild_canonical_financials(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()

    cursor.execute("DELETE FROM canonical_financials;")

    evidence_rows = cursor.execute(
        """
        SELECT *
        FROM financial_evidence
        ORDER BY company_name, filing_year, metric, source_type;
        """
    ).fetchall()

    grouped: Dict[Tuple[str, int, str, str], List[sqlite3.Row]] = {}

    for row in evidence_rows:
        key = get_group_key(row)
        grouped.setdefault(key, []).append(row)

    inserted = 0

    for key, rows in grouped.items():
        company_name, filing_year, metric, unit = key
        selected = choose_canonical_record(rows)

        values = [float(row["value"]) for row in rows]
        conflict_status, max_percent_difference = calculate_conflict_status(values)

        canonical_id = f"{company_name}_{metric}_{filing_year}_{unit}".lower()

        metadata = {
            "source_evidence_ids": [row["evidence_id"] for row in rows],
            "source_types": sorted(set(row["source_type"] for row in rows)),
            "source_values": [
                {
                    "source_type": row["source_type"],
                    "evidence_id": row["evidence_id"],
                    "value": row["value"],
                }
                for row in rows
            ],
        }

        cursor.execute(
            """
            INSERT OR REPLACE INTO canonical_financials (
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
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                canonical_id,
                company_name,
                selected["ticker"],
                selected["cik"],
                filing_year,
                metric,
                selected["value"],
                unit,
                selected["evidence_id"],
                selected["source_type"],
                len(rows),
                conflict_status,
                max_percent_difference,
                selected["confidence_score"],
                json.dumps(metadata, ensure_ascii=False),
            ),
        )

        inserted += 1

    connection.commit()
    print(f"Rebuilt {inserted} canonical financial record(s).")


def print_database_preview(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()

    print("\nFinancial evidence preview:")
    rows = cursor.execute(
        """
        SELECT company_name, filing_year, metric, value, unit, source_type
        FROM financial_evidence
        ORDER BY company_name, filing_year, metric, source_type
        LIMIT 20;
        """
    ).fetchall()

    for row in rows:
        print(tuple(row))

    print("\nCanonical financials preview:")
    rows = cursor.execute(
        """
        SELECT
            company_name,
            filing_year,
            metric,
            value,
            unit,
            selected_source_type,
            source_count,
            conflict_status,
            max_percent_difference
        FROM canonical_financials
        ORDER BY company_name, filing_year, metric
        LIMIT 20;
        """
    ).fetchall()

    for row in rows:
        print(tuple(row))


def main() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    evidence_records = load_sql_evidence_files()
    print(f"Loaded {len(evidence_records)} SQL-targeted EvidenceObject record(s).")

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        create_tables(connection)
        insert_financial_evidence(connection, evidence_records)
        rebuild_canonical_financials(connection)
        print(f"Saved records to SQLite database: {DATABASE_PATH}")
        print_database_preview(connection)

    finally:
        connection.close()


if __name__ == "__main__":
    main()