import json
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

from app.ingestion.evidence_schema import EvidenceObject
from app.ingestion.normalize_evidence import save_evidence_objects


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = PROJECT_ROOT / "data" / "curated" / "source_config.json"
EVIDENCE_OUTPUT_DIR = PROJECT_ROOT / "data" / "normalized" / "evidence_objects"


def load_env() -> None:
    load_dotenv(PROJECT_ROOT / ".env")


def get_env_value(name: str, required: bool = False) -> str | None:
    value = os.getenv(name)

    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")

    return value


def load_source_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing source config: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def get_enabled_source(config: Dict[str, Any], source_name: str) -> bool:
    return bool(config.get("enabled_sources", {}).get(source_name, False))


def save_adapter_evidence(
    evidence_objects: List[EvidenceObject],
    output_file_name: str,
) -> None:
    output_path = EVIDENCE_OUTPUT_DIR / output_file_name
    save_evidence_objects(evidence_objects, output_path)
    print(f"Saved {len(evidence_objects)} EvidenceObject(s) to: {output_path}")


def normalize_number(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()

        if cleaned in {"", "None", "null", "NaN"}:
            return None

        try:
            return float(cleaned)
        except ValueError:
            return None

    return None