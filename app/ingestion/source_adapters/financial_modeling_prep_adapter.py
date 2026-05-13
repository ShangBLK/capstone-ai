from typing import Any, Dict, List

import requests

from app.ingestion.evidence_schema import EvidenceObject
from app.ingestion.source_adapters.api_adapter_utils import (
    get_enabled_source,
    get_env_value,
    load_env,
    load_source_config,
    normalize_number,
    save_adapter_evidence,
)


FMP_BASE_URL = "https://financialmodelingprep.com/stable/income-statement"

FMP_METRIC_MAP = {
    "revenue": "revenue",
    "gross_profit": "grossProfit",
    "operating_income": "operatingIncome",
    "net_income": "netIncome",
    "eps": "eps",
    "eps_diluted": "epsDiluted",
}


def fetch_income_statement(symbol: str, api_key: str) -> List[Dict[str, Any]]:
    response = requests.get(
        FMP_BASE_URL,
        params={
            "symbol": symbol,
            "period": "annual",
            "apikey": api_key,
        },
        timeout=30,
    )

    response.raise_for_status()
    data = response.json()

    if not isinstance(data, list):
        raise ValueError(f"Unexpected FMP response for {symbol}: {data}")

    return data


def create_fmp_evidence_for_company(
    company: Dict[str, Any],
    income_statement_rows: List[Dict[str, Any]],
    target_years: set[int],
) -> List[EvidenceObject]:
    evidence_objects = []

    symbol = company["ticker"]
    company_name = company["company_name"]

    for row in income_statement_rows:
        fiscal_year = row.get("fiscalYear") or row.get("calendarYear")
        date = row.get("date")

        if fiscal_year is None and date:
            fiscal_year = str(date)[:4]

        if fiscal_year is None:
            continue

        try:
            year = int(fiscal_year)
        except ValueError:
            continue

        if year not in target_years:
            continue

        for metric_name, fmp_field in FMP_METRIC_MAP.items():
            metric_value = normalize_number(row.get(fmp_field))

            if metric_value is None:
                continue

            evidence = EvidenceObject(
                evidence_id=f"fmp_{company_name}_{metric_name}_{year}",
                source_type="financial_modeling_prep",
                source_name="Financial Modeling Prep Income Statement API",
                source_url=f"{FMP_BASE_URL}?symbol={symbol}",
                publication_date=row.get("date"),
                company=company_name,
                year=year,
                metric_name=metric_name,
                metric_value=metric_value,
                metric_unit="USD" if not metric_name.startswith("eps") else "USD/share",
                confidence_score=0.95,
                target_layers=["sql"],
                metadata={
                    "ticker": symbol,
                    "reported_currency": row.get("reportedCurrency"),
                    "fmp_field": fmp_field,
                    "period": row.get("period"),
                    "fiscal_year": fiscal_year,
                    "date": row.get("date"),
                    "accepted_date": row.get("acceptedDate"),
                    "filing_date": row.get("filingDate"),
                },
            )

            evidence.validate()
            evidence_objects.append(evidence)

    return evidence_objects


def create_fmp_evidence_objects() -> List[EvidenceObject]:
    load_env()
    config = load_source_config()

    if not get_enabled_source(config, "financial_modeling_prep"):
        print("Financial Modeling Prep source is disabled in source_config.json.")
        return []

    api_key = get_env_value("FMP_API_KEY", required=True)

    companies = config.get("companies", [])
    target_years = set(config.get("target_years", []))

    all_evidence = []

    for company in companies:
        symbol = company["ticker"]
        print(f"Fetching FMP income statement for {symbol}...")

        try:
            rows = fetch_income_statement(symbol=symbol, api_key=api_key)
            evidence = create_fmp_evidence_for_company(
                company=company,
                income_statement_rows=rows,
                target_years=target_years,
            )

            print(f"Extracted {len(evidence)} FMP record(s) for {company['company_name']}")
            all_evidence.extend(evidence)

        except Exception as error:
            print(f"Failed to process FMP data for {company['company_name']}: {error}")

    return all_evidence


def main() -> None:
    evidence_objects = create_fmp_evidence_objects()

    evidence_objects = sorted(
        evidence_objects,
        key=lambda obj: (
            obj.company or "",
            obj.year or 0,
            obj.metric_name or "",
        ),
    )

    save_adapter_evidence(
        evidence_objects=evidence_objects,
        output_file_name="fmp_sql_metric_evidence.json",
    )


if __name__ == "__main__":
    main()