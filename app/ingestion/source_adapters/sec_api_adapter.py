from typing import Any, Dict, List

import requests

from app.ingestion.evidence_schema import EvidenceObject
from app.ingestion.source_adapters.api_adapter_utils import (
    get_enabled_source,
    get_env_value,
    load_env,
    load_source_config,
    save_adapter_evidence,
)


def fetch_company_facts(cik: str, user_agent: str) -> Dict[str, Any]:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

    headers = {
        "User-Agent": user_agent,
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov",
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    return response.json()


def extract_sec_metric_evidence(
    company: Dict[str, Any],
    company_facts: Dict[str, Any],
    metric_config: Dict[str, Any],
    target_years: set[int],
) -> List[EvidenceObject]:
    evidence_objects = []

    metric_name = metric_config["metric_name"]
    xbrl_tag = metric_config["xbrl_tag"]
    unit = metric_config.get("unit", "USD")

    us_gaap_facts = company_facts.get("facts", {}).get("us-gaap", {})

    if xbrl_tag not in us_gaap_facts:
        print(f"Missing XBRL tag for {company['company_name']}: {xbrl_tag}")
        return evidence_objects

    metric_data = us_gaap_facts[xbrl_tag]
    unit_records = metric_data.get("units", {}).get(unit, [])

    for item in unit_records:
        filing_year = item.get("fy")
        form = item.get("form")
        fiscal_period = item.get("fp")
        value = item.get("val")
        period_start = item.get("start")
        period_end = item.get("end")

        if filing_year not in target_years:
            continue

        if form != "10-K":
            continue

        if fiscal_period != "FY":
            continue

        expected_start = f"{filing_year}-01-01"
        expected_end = f"{filing_year}-12-31"

        if period_start != expected_start or period_end != expected_end:
            continue

        evidence_id = (
            f"sec_api_{company['company_name']}_{metric_name}_{filing_year}"
        )

        evidence = EvidenceObject(
            evidence_id=evidence_id,
            source_type="sec_api",
            source_name="SEC CompanyFacts API",
            source_url=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{company['cik']}.json",
            publication_date=item.get("filed"),
            company=company["company_name"],
            year=int(filing_year),
            metric_name=metric_name,
            metric_value=float(value),
            metric_unit=unit,
            confidence_score=1.0,
            target_layers=["sql"],
            metadata={
                "ticker": company.get("ticker"),
                "cik": company.get("cik"),
                "xbrl_tag": f"us-gaap:{xbrl_tag}",
                "form": form,
                "fiscal_period": fiscal_period,
                "period_start": period_start,
                "period_end": period_end,
                "frame": item.get("frame"),
                "filed": item.get("filed"),
                "accession_number": item.get("accn"),
            },
        )

        evidence.validate()
        evidence_objects.append(evidence)

    return evidence_objects


def deduplicate_evidence(
    evidence_objects: List[EvidenceObject],
) -> List[EvidenceObject]:
    selected = {}

    for evidence in evidence_objects:
        key = (
            evidence.company,
            evidence.year,
            evidence.metric_name,
            evidence.metric_unit,
            evidence.source_type,
        )

        existing = selected.get(key)

        if existing is None:
            selected[key] = evidence
            continue

        existing_filed = existing.metadata.get("filed", "")
        current_filed = evidence.metadata.get("filed", "")

        if current_filed > existing_filed:
            selected[key] = evidence

    return list(selected.values())


def create_sec_api_evidence_objects() -> List[EvidenceObject]:
    load_env()
    config = load_source_config()

    if not get_enabled_source(config, "sec_companyfacts"):
        print("SEC CompanyFacts source is disabled in source_config.json.")
        return []

    user_agent = get_env_value("SEC_USER_AGENT", required=True)

    companies = config.get("companies", [])
    metrics = config.get("sec_companyfacts_metrics", [])
    target_years = set(config.get("target_years", []))

    all_evidence = []

    for company in companies:
        print(f"Fetching SEC CompanyFacts for {company['company_name']}...")

        try:
            company_facts = fetch_company_facts(
                cik=company["cik"],
                user_agent=user_agent,
            )

            for metric_config in metrics:
                metric_evidence = extract_sec_metric_evidence(
                    company=company,
                    company_facts=company_facts,
                    metric_config=metric_config,
                    target_years=target_years,
                )

                print(
                    f"Extracted {len(metric_evidence)} record(s) for "
                    f"{company['company_name']} - {metric_config['metric_name']}"
                )

                all_evidence.extend(metric_evidence)

        except Exception as error:
            print(f"Failed to process {company['company_name']}: {error}")

    return deduplicate_evidence(all_evidence)


def main() -> None:
    evidence_objects = create_sec_api_evidence_objects()

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
        output_file_name="sql_metric_evidence.json",
    )


if __name__ == "__main__":
    main()