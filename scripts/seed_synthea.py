"""Import Synthea CSV data as demo patients, encounters, and generated note summaries.

The generated notes are summaries made from structured Synthea CSV events. They are
not original clinician-authored notes. All imported records and audit logs commit in
one transaction, so a failed run can be safely retried.
"""

import argparse
import asyncio
import csv
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from src.db.mains import AsyncSessionLocal
from src.extraction.extractor import extract
from src.models.main_model import (
    AuditAction,
    ClinicalNote,
    Encounter,
    Patient,
    Tenant,
    User,
    UserRole,
)
from src.modules.Audit.services import AuditService


DEFAULT_DATA_DIR = ROOT / "data"
audit_service = AuditService()


def read_rows(path: Path, required: set[str], keep: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = set(reader.fieldnames or [])
        missing = required - columns
        if missing:
            raise ValueError(f"{path.name} is missing columns: {', '.join(sorted(missing))}")
        selected = columns & keep
        return [{key: row.get(key, "") or "" for key in selected} for row in reader]


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value[:10])


def parse_datetime(value: str | None) -> datetime:
    if not value:
        raise ValueError("Synthea encounter is missing START")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def patient_name(row: dict[str, str]) -> str:
    parts = [row.get("PREFIX", ""), row.get("FIRST", ""), row.get("MIDDLE", ""), row.get("LAST", ""), row.get("SUFFIX", "")]
    return " ".join(part.strip() for part in parts if part and part.strip()) or "Synthetic patient"


def event_summary(
    encounter_row: dict[str, str],
    conditions: list[dict[str, str]],
    medications: list[dict[str, str]],
    observations: list[dict[str, str]],
) -> str:
    """Format source events as explicit synthetic demo text for the existing extractor."""
    when = parse_datetime(encounter_row["START"]).date().isoformat()
    kind = encounter_row.get("ENCOUNTERCLASS", "").strip() or "clinical"
    lines = [f"Synthetic Synthea encounter summary ({kind}) on {when}."]

    condition_names = sorted({row.get("DESCRIPTION", "").strip() for row in conditions if row.get("DESCRIPTION", "").strip()})
    medication_names = sorted({row.get("DESCRIPTION", "").strip() for row in medications if row.get("DESCRIPTION", "").strip()})
    observed_values = sorted(
        {
            f"{row.get('DESCRIPTION', '').strip()}: {row.get('VALUE', '').strip()} {row.get('UNITS', '').strip()}".strip()
            for row in observations
            if row.get("DESCRIPTION", "").strip() and row.get("VALUE", "").strip()
        }
    )

    if condition_names:
        lines.append("Conditions recorded: " + "; ".join(condition_names) + ".")
    if medication_names:
        lines.append("Medications recorded: " + "; ".join(medication_names) + ".")
    if observed_values:
        lines.append("Observations recorded: " + "; ".join(observed_values) + ".")
    if len(lines) == 1:
        lines.append("No linked condition, medication, or observation rows were present in the supplied CSVs.")
    return " ".join(lines)


async def seed(data_dir: Path, tenant_id: UUID, actor_user_id: UUID) -> dict[str, int]:
    patient_rows = read_rows(
        data_dir / "patients.csv",
        {"Id", "BIRTHDATE", "FIRST", "LAST", "GENDER"},
        {"Id", "BIRTHDATE", "FIRST", "MIDDLE", "LAST", "PREFIX", "SUFFIX", "GENDER"},
    )
    encounter_rows = read_rows(
        data_dir / "encounters.csv",
        {"Id", "PATIENT", "START", "ENCOUNTERCLASS"},
        {"Id", "PATIENT", "START", "ENCOUNTERCLASS"},
    )
    condition_rows = read_rows(data_dir / "conditions.csv", {"ENCOUNTER", "DESCRIPTION"}, {"ENCOUNTER", "DESCRIPTION"})
    medication_rows = read_rows(data_dir / "medications.csv", {"ENCOUNTER", "DESCRIPTION"}, {"ENCOUNTER", "DESCRIPTION"})
    observation_rows = read_rows(
        data_dir / "observations.csv",
        {"ENCOUNTER", "DESCRIPTION", "VALUE", "UNITS"},
        {"ENCOUNTER", "DESCRIPTION", "VALUE", "UNITS"},
    )

    conditions_by_encounter: dict[str, list[dict[str, str]]] = defaultdict(list)
    medications_by_encounter: dict[str, list[dict[str, str]]] = defaultdict(list)
    observations_by_encounter: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in condition_rows:
        conditions_by_encounter[row["ENCOUNTER"]].append(row)
    for row in medication_rows:
        medications_by_encounter[row["ENCOUNTER"]].append(row)
    for row in observation_rows:
        observations_by_encounter[row["ENCOUNTER"]].append(row)

    counts = {"patients_created": 0, "encounters_created": 0, "notes_created": 0, "encounters_skipped": 0}
    async with AsyncSessionLocal() as session:
        tenant = await session.get(Tenant, tenant_id)
        if tenant is None:
            raise ValueError(f"Tenant {tenant_id} does not exist")
        actor = await session.get(User, actor_user_id)
        if actor is None or actor.tenant_id != tenant_id or actor.role != UserRole.clinician:
            raise ValueError("Actor must be a clinician in the selected tenant")

        patients_by_source_id: dict[str, Patient] = {}
        for row in patient_rows:
            source_id = row["Id"].strip()
            if not source_id:
                continue
            patient = (await session.exec(select(Patient).where(
                Patient.tenant_id == tenant_id,
                Patient.external_ref == source_id,
            ))).scalar_one_or_none()
            if patient is None:
                patient = Patient(
                    tenant_id=tenant_id,
                    external_ref=source_id,
                    full_name=patient_name(row),
                    birth_date=parse_date(row.get("BIRTHDATE")),
                    sex=(row.get("GENDER") or None),
                )
                session.add(patient)
                await session.flush()
                await audit_service.log_access(session, actor, AuditAction.create, "patient", patient.id, tenant_id)
                counts["patients_created"] += 1
            patients_by_source_id[source_id] = patient

        for row in encounter_rows:
            source_encounter_id = row["Id"].strip()
            source_patient_id = row["PATIENT"].strip()
            patient = patients_by_source_id.get(source_patient_id)
            if not patient:
                raise ValueError(f"Encounter {source_encounter_id} references a patient absent from patients.csv")
            existing = (await session.exec(select(Encounter).where(
                Encounter.tenant_id == tenant_id,
                Encounter.external_ref == source_encounter_id,
            ))).scalar_one_or_none()
            if existing is not None:
                counts["encounters_skipped"] += 1
                continue

            encounter = Encounter(
                tenant_id=tenant_id,
                patient_id=patient.id,
                clinician_id=actor.uid,
                external_ref=source_encounter_id,
                occurred_at=parse_datetime(row["START"]),
            )
            session.add(encounter)
            await session.flush()
            await audit_service.log_access(session, actor, AuditAction.create, "encounter", encounter.id, tenant_id)
            counts["encounters_created"] += 1

            raw_text = event_summary(
                row,
                conditions_by_encounter[source_encounter_id],
                medications_by_encounter[source_encounter_id],
                observations_by_encounter[source_encounter_id],
            )
            note = ClinicalNote(
                tenant_id=tenant_id,
                encounter_id=encounter.id,
                raw_text=raw_text,
                extracted=extract(raw_text),
            )
            session.add(note)
            await session.flush()
            await audit_service.log_access(session, actor, AuditAction.create, "clinical_note", note.id, tenant_id)
            await audit_service.log_access(session, actor, AuditAction.extract, "clinical_note", note.id, tenant_id)
            counts["notes_created"] += 1

        await session.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Synthea CSVs into a selected clinic as demo data.")
    parser.add_argument("--tenant-id", required=True, type=UUID, help="Existing clinic UUID")
    parser.add_argument("--actor-user-id", required=True, type=UUID, help="Existing clinic clinician UUID for audit attribution")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Directory containing the five Synthea CSV files")
    args = parser.parse_args()
    counts = asyncio.run(seed(args.data_dir.resolve(), args.tenant_id, args.actor_user_id))
    print("Synthea import committed:")
    for name, count in counts.items():
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
