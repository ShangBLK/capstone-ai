from pathlib import Path
import json
import sqlite3


INPUT_JSON_PATH = Path("data/processed/sql_records/financials_records.json")
DATABASE_PATH = Path("storage/sqlite/financials.db")


def load_json_records(input_path: Path) -> list:
    """
    Load financial records from a JSON file.

    Args:
        input_path (Path): Path to financial records JSON file.

    Returns:
        list: List of financial record dictionaries.
    """
    with open(input_path, "r", encoding="utf-8") as file:
        return json.load(file)


def create_financials_table(connection: sqlite3.Connection) -> None:
    """
    Create the financials table if it does not already exist.

    Args:
        connection (sqlite3.Connection): SQLite database connection.
    """
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS financials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            ticker TEXT NOT NULL,
            cik TEXT NOT NULL,
            filing_year INTEGER NOT NULL,
            metric TEXT NOT NULL,
            xbrl_tag TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            form TEXT NOT NULL,
            fiscal_period TEXT NOT NULL,
            frame TEXT,
            filed TEXT,
            accession_number TEXT,
            source TEXT NOT NULL,
            UNIQUE(company_name, filing_year, metric)
        );
        """
    )

    connection.commit()


def insert_financial_records(connection: sqlite3.Connection, records: list) -> None:
    """
    Insert financial records into the financials table.

    Args:
        connection (sqlite3.Connection): SQLite database connection.
        records (list): List of financial record dictionaries.
    """
    cursor = connection.cursor()

    for record in records:
        cursor.execute(
            """
            INSERT OR REPLACE INTO financials (
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
                frame,
                filed,
                accession_number,
                source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
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
                record.get("frame"),
                record.get("filed"),
                record.get("accession_number"),
                record["source"],
            ),
        )

    connection.commit()


def print_database_preview(connection: sqlite3.Connection) -> None:
    """
    Print a preview of all records currently stored in the financials table.

    Args:
        connection (sqlite3.Connection): SQLite database connection.
    """
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT company_name, filing_year, metric, value, unit
        FROM financials
        ORDER BY company_name, filing_year, metric;
        """
    )

    rows = cursor.fetchall()

    print("\nDatabase preview:")
    for row in rows:
        print(row)


def main() -> None:
    if not INPUT_JSON_PATH.exists():
        print(f"Input JSON file not found: {INPUT_JSON_PATH}")
        return

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    records = load_json_records(INPUT_JSON_PATH)

    print(f"Loaded {len(records)} record(s) from: {INPUT_JSON_PATH}")

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        create_financials_table(connection)
        insert_financial_records(connection, records)
        print(f"Saved records to SQLite database: {DATABASE_PATH}")
        print_database_preview(connection)

    finally:
        connection.close()


if __name__ == "__main__":
    main()