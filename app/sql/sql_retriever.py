import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "storage" / "sqlite" / "financials.db"


def connect_db():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"SQLite database not found: {DB_PATH}")

    return sqlite3.connect(DB_PATH)


def get_financial_metric(company_name, metric, filing_year):
    query = """
        SELECT company_name, ticker, filing_year, metric, value, unit, form, source
        FROM financials
        WHERE LOWER(company_name) = LOWER(?)
          AND LOWER(metric) = LOWER(?)
          AND filing_year = ?
    """

    with connect_db() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(query, (company_name, metric, filing_year)).fetchone()

    if row is None:
        return None

    return dict(row)


def get_company_financials(company_name, filing_year):
    query = """
        SELECT company_name, ticker, filing_year, metric, value, unit, form, source
        FROM financials
        WHERE LOWER(company_name) = LOWER(?)
          AND filing_year = ?
        ORDER BY metric
    """

    with connect_db() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, (company_name, filing_year)).fetchall()

    return [dict(row) for row in rows]


def get_metric_trend(company_name, metric):
    query = """
        SELECT company_name, ticker, filing_year, metric, value, unit, form, source
        FROM financials
        WHERE LOWER(company_name) = LOWER(?)
          AND LOWER(metric) = LOWER(?)
        ORDER BY filing_year
    """

    with connect_db() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, (company_name, metric)).fetchall()

    return [dict(row) for row in rows]


def print_record(record):
    if record is None:
        print("No matching SQL record found.")
        return

    print("-" * 80)
    print(f"Company: {record['company_name']}")
    print(f"Ticker: {record['ticker']}")
    print(f"Year: {record['filing_year']}")
    print(f"Metric: {record['metric']}")
    print(f"Value: {record['value']:,} {record['unit']}")
    print(f"Form: {record['form']}")
    print(f"Source: {record['source']}")


def print_records(records):
    if not records:
        print("No matching SQL records found.")
        return

    for record in records:
        print_record(record)


if __name__ == "__main__":
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