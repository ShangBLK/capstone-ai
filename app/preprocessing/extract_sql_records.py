from pathlib import Path
import json
import requests


SEC_USER_AGENT = "Shang Andrews capstone-ai shanglandrews@gmail.com"

COMPANIES = [
    {
        "company_name": "tesla",
        "ticker": "TSLA",
        "cik": "0001318605"
    },
    {
        "company_name": "ford",
        "ticker": "F",
        "cik": "0000037996"
    }
]

METRICS = {
    "revenue": "Revenues",
    "net_income": "NetIncomeLoss"
}

TARGET_YEARS = {2022, 2023}


def fetch_company_facts(cik: str) -> dict:
    """
    Fetch company facts from the SEC CompanyFacts API.
    """
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

    headers = {
        "User-Agent": SEC_USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov"
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    return response.json()


def extract_metric_records(company: dict, company_facts: dict, metric_name: str, xbrl_tag: str) -> list:
    """
    Extract one clean annual company-level record per company, year, and metric.
    """
    records = []

    us_gaap_facts = company_facts.get("facts", {}).get("us-gaap", {})

    if xbrl_tag not in us_gaap_facts:
        print(f"Missing XBRL tag for {company['company_name']}: {xbrl_tag}")
        return records

    metric_data = us_gaap_facts[xbrl_tag]
    usd_records = metric_data.get("units", {}).get("USD", [])

    for item in usd_records:
        filing_year = item.get("fy")
        form = item.get("form")
        fiscal_period = item.get("fp")
        value = item.get("val")
        frame = item.get("frame")

        if filing_year not in TARGET_YEARS:
            continue

        if form != "10-K":
            continue

        if fiscal_period != "FY":
            continue

        period_start = item.get("start")
        period_end = item.get("end")

        for target_year in TARGET_YEARS:
            expected_start = f"{target_year}-01-01"
            expected_end = f"{target_year}-12-31"

            if period_start == expected_start and period_end == expected_end:
                filing_year = target_year
                break
        else:
            continue    

        if item.get("start") != expected_start:
            continue

        if item.get("end") != expected_end:
            continue    

        record = {
            "company_name": company["company_name"],
            "ticker": company["ticker"],
            "cik": company["cik"],
            "filing_year": filing_year,
            "metric": metric_name,
            "xbrl_tag": f"us-gaap:{xbrl_tag}",
            "value": value,
            "unit": "USD",
            "form": form,
            "fiscal_period": fiscal_period,
            "frame": frame,
            "filed": item.get("filed"),
            "accession_number": item.get("accn"),
            "source": "SEC CompanyFacts API"
        }

        records.append(record)

    return records


def deduplicate_records(records: list) -> list:
    """
    Keep only one record per company, year, and metric.
    If duplicates exist, keep the most recently filed record.
    """
    selected = {}

    for record in records:
        key = (
            record["company_name"],
            record["filing_year"],
            record["metric"]
        )

        existing = selected.get(key)

        if existing is None:
            selected[key] = record
            continue

        if record.get("filed", "") > existing.get("filed", ""):
            selected[key] = record

    return list(selected.values())


def save_records(records: list, output_path: Path) -> None:
    """
    Save extracted SQL-ready records to JSON.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=4)


def main() -> None:
    all_records = []

    for company in COMPANIES:
        print(f"Fetching SEC data for {company['company_name']}...")

        try:
            company_facts = fetch_company_facts(company["cik"])

            for metric_name, xbrl_tag in METRICS.items():
                metric_records = extract_metric_records(
                    company=company,
                    company_facts=company_facts,
                    metric_name=metric_name,
                    xbrl_tag=xbrl_tag
                )

                print(
                    f"Extracted {len(metric_records)} clean record(s) for "
                    f"{company['company_name']} - {metric_name}"
                )

                all_records.extend(metric_records)

        except Exception as error:
            print(f"Failed to process {company['company_name']}: {error}")

    final_records = deduplicate_records(all_records)

    final_records = sorted(
        final_records,
        key=lambda record: (
            record["company_name"],
            record["filing_year"],
            record["metric"]
        )
    )

    output_path = Path("data/processed/sql_records/financials_records.json")
    save_records(final_records, output_path)

    print(f"Saved {len(final_records)} total SQL record(s) to: {output_path}")


if __name__ == "__main__":
    main()