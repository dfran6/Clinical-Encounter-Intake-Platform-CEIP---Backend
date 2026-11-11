import asyncio
import csv
import uuid
from pathlib import Path

from src.models.main_model import AuditLog, ClinicalNote, Encounter, Patient, Tenant, User, UserRole
from scripts import seed_synthea


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _SeedDatabase:
    def __init__(self, tenant, clinician):
        self.tenant = tenant
        self.clinician = clinician
        self.patients = {}
        self.encounters = {}
        self.notes = []
        self.audit_logs = []
        self.commit_count = 0

    def session(self):
        return _SeedSession(self)


class _SeedSession:
    def __init__(self, database):
        self.database = database

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, model, _identity):
        if model is Tenant:
            return self.database.tenant
        if model is User:
            return self.database.clinician
        return None

    async def exec(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        source_ref = next(
            criterion.right.value
            for criterion in statement._where_criteria
            if getattr(criterion.left, "name", None) == "external_ref"
        )
        records = self.database.patients if entity is Patient else self.database.encounters
        return _ScalarResult(records.get(source_ref))

    def add(self, item):
        if isinstance(item, Patient):
            self.database.patients[item.external_ref] = item
        elif isinstance(item, Encounter):
            self.database.encounters[item.external_ref] = item
        elif isinstance(item, ClinicalNote):
            self.database.notes.append(item)
        elif isinstance(item, AuditLog):
            self.database.audit_logs.append(item)

    async def flush(self):
        return None

    async def commit(self):
        self.database.commit_count += 1


def _write_csv(path: Path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_synthea_seed_creates_linked_records_and_is_safe_to_rerun(tmp_path, monkeypatch):
    data_dir = tmp_path / "synthea"
    data_dir.mkdir()
    _write_csv(
        data_dir / "patients.csv",
        ["Id", "BIRTHDATE", "FIRST", "LAST", "GENDER"],
        [{"Id": "patient-1", "BIRTHDATE": "1980-01-02", "FIRST": "Demo", "LAST": "Person", "GENDER": "F"}],
    )
    _write_csv(
        data_dir / "encounters.csv",
        ["Id", "PATIENT", "START", "ENCOUNTERCLASS"],
        [{"Id": "encounter-1", "PATIENT": "patient-1", "START": "2026-01-02T10:00:00Z", "ENCOUNTERCLASS": "ambulatory"}],
    )
    _write_csv(
        data_dir / "conditions.csv",
        ["ENCOUNTER", "DESCRIPTION"],
        [{"ENCOUNTER": "encounter-1", "DESCRIPTION": "Essential hypertension (disorder)"}],
    )
    _write_csv(
        data_dir / "medications.csv",
        ["ENCOUNTER", "DESCRIPTION"],
        [{"ENCOUNTER": "encounter-1", "DESCRIPTION": "Lisinopril 2.5 MG Oral Tablet"}],
    )
    _write_csv(
        data_dir / "observations.csv",
        ["ENCOUNTER", "DESCRIPTION", "VALUE", "UNITS"],
        [{"ENCOUNTER": "encounter-1", "DESCRIPTION": "Blood pressure", "VALUE": "120/80", "UNITS": "mmHg"}],
    )

    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Demo Clinic", email="clinic@example.test", address="1 Demo Street")
    clinician = User(
        email="clinician@example.test",
        password_hash="test-hash",
        role=UserRole.clinician,
        tenant_id=tenant_id,
    )
    database = _SeedDatabase(tenant, clinician)
    monkeypatch.setattr(seed_synthea, "AsyncSessionLocal", database.session)

    first = asyncio.run(seed_synthea.seed(data_dir, tenant_id, clinician.uid))
    second = asyncio.run(seed_synthea.seed(data_dir, tenant_id, clinician.uid))

    assert first == {
        "patients_created": 1,
        "encounters_created": 1,
        "notes_created": 1,
        "encounters_skipped": 0,
    }
    assert second == {
        "patients_created": 0,
        "encounters_created": 0,
        "notes_created": 0,
        "encounters_skipped": 1,
    }
    assert len(database.patients) == 1
    assert len(database.encounters) == 1
    assert len(database.notes) == 1
    assert database.commit_count == 2
    note = database.notes[0]
    assert "Synthetic Synthea encounter summary" in note.raw_text
    assert note.extracted["diagnoses"] == [{"term": "essential hypertension", "code": "59621000"}]
    assert note.extracted["medications"][0]["dose"] == "2.5mg"
    assert len(database.audit_logs) == 4
