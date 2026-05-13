import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "storage" / "sqlite" / "financials.db"


def connect_db() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"SQLite database not found: {DB_PATH}")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def row_to_dict(row: sqlite3.Row | None) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return dict(row)


def rows_to_dicts(rows: list[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(row) for row in rows]


def get_financial_metric(
    company_name: str,
    metric: str,
    filing_year: int,
) -> Optional[Dict[str, Any]]:
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
        WHERE LOWER(company_name) = LOWER(?)
          AND LOWER(metric) = LOWER(?)
          AND filing_year = ?
        LIMIT 1;
    """

    with connect_db() as conn:
        row = conn.execute(query, (company_name, metric, filing_year)).fetchone()

    return row_to_dict(row)


def get_company_financials(
    company_name: str,
    filing_year: int,
) -> List[Dict[str, Any]]:
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
        WHERE LOWER(company_name) = LOWER(?)
          AND filing_year = ?
        ORDER BY metric;
    """

    with connect_db() as conn:
        rows = conn.execute(query, (company_name, filing_year)).fetchall()

    return rows_to_dicts(rows)


def get_metric_trend(
    company_name: str,
    metric: str,
) -> List[Dict[str, Any]]:
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
        WHERE LOWER(company_name) = LOWER(?)
          AND LOWER(metric) = LOWER(?)
        ORDER BY filing_year;
    """

    with connect_db() as conn:
        rows = conn.execute(query, (company_name, metric)).fetchall()

    return rows_to_dicts(rows)


def compare_metric_between_companies(
    metric: str,
    filing_year: int,
    company_names: list[str] | None = None,
) -> List[Dict[str, Any]]:
    params: list[Any] = [metric, filing_year]
    company_filter = ""

    if company_names:
        placeholders = ",".join(["?"] * len(company_names))
        company_filter = f"AND LOWER(company_name) IN ({placeholders})"
        params.extend([name.lower() for name in company_names])

    query = f"""
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
        WHERE LOWER(metric) = LOWER(?)
          AND filing_year = ?
          {company_filter}
        ORDER BY value DESC;
    """

    with connect_db() as conn:
        rows = conn.execute(query, params).fetchall()

    return rows_to_dicts(rows)


def get_underlying_evidence(selected_evidence_id: str) -> Optional[Dict[str, Any]]:
    query = """
        SELECT
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
        FROM financial_evidence
        WHERE evidence_id = ?
        LIMIT 1;
    """

    with connect_db() as conn:
        row = conn.execute(query, (selected_evidence_id,)).fetchone()

    return row_to_dict(row)


def get_conflicted_facts() -> List[Dict[str, Any]]:
    query = """
        SELECT
            canonical_id,
            company_name,
            ticker,
            filing_year,
            metric,
            value,
            unit,
            selected_evidence_id,
            selected_source_type,
            source_count,
            conflict_status,
            max_percent_difference,
            confidence_score
        FROM canonical_financials
        WHERE conflict_status IN ('conflict', 'minor_difference')
        ORDER BY company_name, filing_year, metric;
    """

    with connect_db() as conn:
        rows = conn.execute(query).fetchall()

    return rows_to_dicts(rows)


def get_available_metrics() -> List[str]:
    query = """
        SELECT DISTINCT metric
        FROM canonical_financials
        ORDER BY metric;
    """

    with connect_db() as conn:
        rows = conn.execute(query).fetchall()

    return [row["metric"] for row in rows]


def get_available_companies() -> List[str]:
    query = """
        SELECT DISTINCT company_name
        FROM canonical_financials
        ORDER BY company_name;
    """

    with connect_db() as conn:
        rows = conn.execute(query).fetchall()

    return [row["company_name"] for row in rows]


def format_value(value, unit):
    if value is None:
        return "None"

    if unit == "USD":
        return f"${value:,.0f}"
    if unit == "USD/share":
        return f"${value:,.2f} per share"

    return f"{value:,.2f} {unit or ''}".strip()


def print_record(record: Optional[Dict[str, Any]]) -> None:
    if record is None:
        print("No matching SQL record found.")
        return

    print("-" * 80)
    print(f"Canonical ID: {record.get('canonical_id')}")
    print(f"Company: {record.get('company_name')}")
    print(f"Ticker: {record.get('ticker')}")
    print(f"Year: {record.get('filing_year')}")
    print(f"Metric: {record.get('metric')}")
    print(f"Value: {format_value(record.get('value'), record.get('unit'))}")
    print(f"Selected Evidence ID: {record.get('selected_evidence_id')}")
    print(f"Selected Source Type: {record.get('selected_source_type')}")
    print(f"Source Count: {record.get('source_count')}")
    print(f"Conflict Status: {record.get('conflict_status')}")
    print(f"Max Percent Difference: {record.get('max_percent_difference')}")
    print(f"Confidence: {record.get('confidence_score')}")


def print_records(records: List[Dict[str, Any]]) -> None:
    if not records:
        print("No matching SQL records found.")
        return

    for record in records:
        print_record(record)


if __name__ == "__main__":
    print("\nAVAILABLE COMPANIES")
    print(get_available_companies())

    print("\nAVAILABLE METRICS")
    print(get_available_metrics())

    print("\nTEST 1: Tesla revenue in 2022")
    result = get_financial_metric("tesla", "revenue", 2022)
    print_record(result)

    print("\nTEST 2: Tesla net income in 2022")
    result = get_financial_metric("tesla", "net_income", 2022)
    print_record(result)

    print("\nTEST 3: Tesla financials in 2022")
    results = get_company_financials("tesla", 2022)
    print_records(results)

    print("\nTEST 4: Tesla revenue trend")
    results = get_metric_trend("tesla", "revenue")
    print_records(results)

    print("\nTEST 5: Revenue comparison in 2024")
    results = compare_metric_between_companies(
        metric="revenue",
        filing_year=2024,
        company_names=["tesla", "ford"],
    )
    print_records(results)

    print("\nTEST 6: Conflicted facts")
    results = get_conflicted_facts()
    print_records(results)