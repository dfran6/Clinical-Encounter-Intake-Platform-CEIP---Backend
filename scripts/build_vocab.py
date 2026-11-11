"""Build a review-only vocabulary draft from Synthea condition/medication CSVs.

This script does not change the active extractor vocabulary or load data into the DB.
"""

import csv
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_PATH = DATA_DIR / "vocabulary_candidates.json"
TOP_DIAGNOSES = 100
TOP_MEDICATIONS = 100

DOSE_SUFFIX = re.compile(
    r"\s+\d+(?:\.\d+)?\s*(?:mcg|mg|g|ml|units?)\b.*$",
    re.IGNORECASE,
)
DISORDER_SUFFIX = re.compile(r"\s*\(disorder\)\s*$", re.IGNORECASE)


def read_csv(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = set(reader.fieldnames or [])
        missing = required_columns - columns
        if missing:
            raise ValueError(f"{path.name} is missing required columns: {', '.join(sorted(missing))}")
        return list(reader)


def build_diagnoses() -> list[dict[str, object]]:
    counts: Counter[tuple[str, str, str]] = Counter()
    rows = read_csv(DATA_DIR / "conditions.csv", {"DESCRIPTION", "CODE", "SYSTEM"})

    for row in rows:
        description = row["DESCRIPTION"].strip()
        # Keep disorder concepts only; findings and situations need a separate review.
        if not DISORDER_SUFFIX.search(description):
            continue
        term = DISORDER_SUFFIX.sub("", description).strip().casefold()
        code = row["CODE"].strip()
        system = row["SYSTEM"].strip()
        if term and code and system:
            counts[(term, code, system)] += 1

    candidates = [
        {"term": term, "code": code, "code_system": system, "count": count}
        for (term, code, system), count in counts.items()
    ]
    return sorted(candidates, key=lambda item: (-int(item["count"]), str(item["term"]), str(item["code"])))[:TOP_DIAGNOSES]


def build_medications() -> list[dict[str, object]]:
    counts: Counter[tuple[str, str, str]] = Counter()
    rows = read_csv(DATA_DIR / "medications.csv", {"DESCRIPTION", "CODE"})

    for row in rows:
        description = row["DESCRIPTION"].strip()
        code = row["CODE"].strip()
        # Remove a trailing dosage/formulation while preserving names such as Vitamin B12.
        name = DOSE_SUFFIX.sub("", description).strip().casefold()
        if name and code:
            counts[(name, code, description)] += 1

    candidates = [
        {
            "name": name,
            "code": code,
            "code_system": "RxNorm",
            "source_description": source_description,
            "count": count,
        }
        for (name, code, source_description), count in counts.items()
    ]
    return sorted(candidates, key=lambda item: (-int(item["count"]), str(item["name"]), str(item["code"])))[:TOP_MEDICATIONS]


def main() -> None:
    output = {
        "source_files": ["data/conditions.csv", "data/medications.csv"],
        "notes": [
            "Review candidates before adding them to src/extraction/vocab.py.",
            "Diagnosis candidates include only Synthea condition descriptions ending in (disorder).",
            "Diagnosis candidates retain Synthea's source SYSTEM; review it before adding candidates to the active SNOMED CT vocabulary.",
            "Medication candidates retain their source code and description; verify code system and normalized name.",
            "Counts are row frequencies in the synthetic CSVs, not clinical prevalence.",
        ],
        "diagnoses": build_diagnoses(),
        "medications": build_medications(),
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"Wrote {OUTPUT_PATH.relative_to(ROOT)} with "
        f"{len(output['diagnoses'])} diagnosis candidates and "
        f"{len(output['medications'])} medication candidates."
    )


if __name__ == "__main__":
    main()
