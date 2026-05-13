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


ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"

ALPHA_VANTAGE_METRIC_MAP = {
    "revenue": "totalRevenue",
    "gross_profit": "grossProfit",
    "operating_income": "operatingIncome",
    "net_income": "netIncome",
    "ebit": "ebit",
    "ebitda": "ebitda",
}


def fetch_income_statement(symbol: str, api_key: str) -> Dict[str, Any]:
    response = requests.get(
        ALPHA_VANTAGE_BASE_URL,
        params={
            "function": "INCOME_STATEMENT",
            "symbol": symbol,
            "apikey": api_key,
        },
        timeout=30,
    )

    response.raise_for_status()
    data = response.json()

    if "Note" in data:
        raise ValueError(f"Alpha Vantage rate limit message: {data['Note']}")

    if "Information" in data:
        raise ValueError(f"Alpha Vantage information message: {data['Information']}")

    if "Error Message" in data:
        raise ValueError(f"Alpha Vantage error message: {data['Error Message']}")

    if "annualReports" not in data:
        raise ValueError(f"Unexpected Alpha Vantage response for {symbol}: {data}")

    return data


def create_alpha_vantage_evidence_for_company(
    company: Dict[str, Any],
    annual_reports: List[Dict[str, Any]],
    target_years: set[int],
) -> List[EvidenceObject]:
    evidence_objects = []

    symbol = company["ticker"]
    company_name = company["company_name"]

    for report in annual_reports:
        fiscal_date = report.get("fiscalDateEnding")

        if not fiscal_date:
            continue

        try:
            year = int(fiscal_date[:4])
        except ValueError:
            continue

        if year not in target_years:
            continue

        reported_currency = report.get("reportedCurrency", "USD")

        for metric_name, alpha_field in ALPHA_VANTAGE_METRIC_MAP.items():
            metric_value = normalize_number(report.get(alpha_field))

            if metric_value is None:
                continue

            evidence = EvidenceObject(
                evidence_id=f"alpha_vantage_{company_name}_{metric_name}_{year}",
                source_type="alpha_vantage",
                source_name="Alpha Vantage Income Statement API",
                source_url=(
                    f"{ALPHA_VANTAGE_BASE_URL}"
                    f"?function=INCOME_STATEMENT&symbol={symbol}"
                ),
                publication_date=fiscal_date,
                company=company_name,
                year=year,
                metric_name=metric_name,
                metric_value=metric_value,
                metric_unit=reported_currency,
                confidence_score=0.9,
                target_layers=["sql"],
                metadata={
                    "ticker": symbol,
                    "reported_currency": reported_currency,
                    "alpha_vantage_field": alpha_field,
                    "fiscal_date_ending": fiscal_date,
                    "source_function": "INCOME_STATEMENT",
                },
            )

            evidence.validate()
            evidence_objects.append(evidence)

    return evidence_objects


def create_alpha_vantage_evidence_objects() -> List[EvidenceObject]:
    load_env()
    config = load_source_config()

    if not get_enabled_source(config, "alpha_vantage"):
        print("Alpha Vantage source is disabled in source_config.json.")
        return []

    api_key = get_env_value("ALPHA_VANTAGE_API_KEY", required=True)

    companies = config.get("companies", [])
    target_years = set(config.get("target_years", []))

    all_evidence = []

    for company in companies:
        symbol = company["ticker"]
        print(f"Fetching Alpha Vantage income statement for {symbol}...")

        try:
            data = fetch_income_statement(symbol=symbol, api_key=api_key)
            reports = data.get("annualReports", [])

            evidence = create_alpha_vantage_evidence_for_company(
                company=company,
                annual_reports=reports,
                target_years=target_years,
            )

            print(
                f"Extracted {len(evidence)} Alpha Vantage record(s) "
                f"for {company['company_name']}"
            )

            all_evidence.extend(evidence)

        except Exception as error:
            print(
                f"Failed to process Alpha Vantage data for "
                f"{company['company_name']}: {error}"
            )

    return all_evidence


def main() -> None:
    evidence_objects = create_alpha_vantage_evidence_objects()

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
        output_file_name="alpha_vantage_sql_metric_evidence.json",
    )


if __name__ == "__main__":
    main()