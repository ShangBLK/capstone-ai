import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "storage" / "sqlite" / "financials.db"


def connect_db() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"SQLite database not found: {DB_PATH}")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def print_table_schema(connection: sqlite3.Connection, table_name: str) -> None:
    print(f"\nSchema for table: {table_name}")
    print("-" * 80)

    rows = connection.execute(f"PRAGMA table_info({table_name});").fetchall()

    for row in rows:
        print(
            f"{row['cid']:02d} | "
            f"{row['name']} | "
            f"{row['type']} | "
            f"not_null={row['notnull']} | "
            f"default={row['dflt_value']} | "
            f"pk={row['pk']}"
        )


def print_row_count(connection: sqlite3.Connection, table_name: str) -> None:
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name};").fetchone()
    print(f"\nTotal rows in {table_name}: {row['count']}")


def print_distinct_values(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
) -> None:
    print(f"\nDistinct {column_name} in {table_name}:")
    print("-" * 80)

    query = f"""
        SELECT {column_name}, COUNT(*) AS count
        FROM {table_name}
        GROUP BY {column_name}
        ORDER BY {column_name};
    """

    rows = connection.execute(query).fetchall()

    for row in rows:
        print(f"{row[column_name]}: {row['count']}")


def print_recent_evidence_records(
    connection: sqlite3.Connection,
    limit: int = 10,
) -> None:
    print(f"\nMost recent financial evidence records by filed date, limit {limit}:")
    print("-" * 80)

    query = """
        SELECT
            evidence_id,
            company_name,
            filing_year,
            metric,
            value,
            unit,
            source_type,
            filed
        FROM financial_evidence
        ORDER BY filed DESC, company_name, metric
        LIMIT ?;
    """

    rows = connection.execute(query, (limit,)).fetchall()

    for row in rows:
        print(dict(row))


def print_canonical_preview(
    connection: sqlite3.Connection,
    limit: int = 20,
) -> None:
    print(f"\nCanonical financials preview, limit {limit}:")
    print("-" * 80)

    query = """
        SELECT
            canonical_id,
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
        LIMIT ?;
    """

    rows = connection.execute(query, (limit,)).fetchall()

    for row in rows:
        print(dict(row))


def print_conflicts(
    connection: sqlite3.Connection,
) -> None:
    print("\nCanonical records with differences/conflicts:")
    print("-" * 80)

    query = """
        SELECT
            canonical_id,
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
        WHERE conflict_status IN ('minor_difference', 'conflict')
        ORDER BY conflict_status, company_name, filing_year, metric;
    """

    rows = connection.execute(query).fetchall()

    if not rows:
        print("No conflicts or minor differences found.")
        return

    for row in rows:
        print(dict(row))


def main() -> None:
    with connect_db() as connection:
        print(f"Inspecting SQLite database: {DB_PATH}")

        print_table_schema(connection, "financial_evidence")
        print_table_schema(connection, "canonical_financials")

        print_row_count(connection, "financial_evidence")
        print_row_count(connection, "canonical_financials")

        print_distinct_values(connection, "financial_evidence", "company_name")
        print_distinct_values(connection, "financial_evidence", "metric")
        print_distinct_values(connection, "financial_evidence", "source_type")

        print_distinct_values(connection, "canonical_financials", "company_name")
        print_distinct_values(connection, "canonical_financials", "metric")
        print_distinct_values(connection, "canonical_financials", "selected_source_type")
        print_distinct_values(connection, "canonical_financials", "conflict_status")

        print_recent_evidence_records(connection)
        print_canonical_preview(connection)
        print_conflicts(connection)


if __name__ == "__main__":
    main()