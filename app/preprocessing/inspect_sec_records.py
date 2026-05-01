import requests


SEC_USER_AGENT = "Shang Andrews capstone-ai shanglandrews@gmail.com"

COMPANY = {
    "company_name": "ford",
    "ticker": "F",
    "cik": "0000037996"
}

XBRL_TAG = "NetIncomeLoss"


def fetch_company_facts(cik: str) -> dict:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

    headers = {
        "User-Agent": SEC_USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov"
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def main():
    data = fetch_company_facts(COMPANY["cik"])

    records = (
        data.get("facts", {})
        .get("us-gaap", {})
        .get(XBRL_TAG, {})
        .get("units", {})
        .get("USD", [])
    )

    print(f"Found {len(records)} USD records for {COMPANY['company_name']} - {XBRL_TAG}")
    print()

    for item in records:
        if item.get("fy") in {2022, 2023} and item.get("form") == "10-K":
            print({
                "fy": item.get("fy"),
                "fp": item.get("fp"),
                "form": item.get("form"),
                "val": item.get("val"),
                "filed": item.get("filed"),
                "accn": item.get("accn"),
                "frame": item.get("frame"),
                "start": item.get("start"),
                "end": item.get("end")
            })


if __name__ == "__main__":
    main()