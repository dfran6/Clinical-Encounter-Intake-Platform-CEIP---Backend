import asyncio
import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from src.models.main_model import AuditAction, AuditLog, Patient, User, UserRole
from src.modules.Analytics.services import AnalyticsService
from src.modules.Patients.schema import PatientCreate
from src.modules.Patients.service import PatientService


def _user(tenant_id=None):
    return User(
        email="clinician@example.test",
        password_hash="test-hash",
        role=UserRole.clinician,
        tenant_id=tenant_id or uuid.uuid4(),
    )


def test_patient_from_another_tenant_is_hidden_as_not_found():
    tenant_id = uuid.uuid4()
    user = _user(tenant_id)
    session = AsyncMock()
    result = Mock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    with pytest.raises(HTTPException) as error:
        asyncio.run(PatientService().get_patient(uuid.uuid4(), user, session))

    assert error.value.status_code == 404
    statement = session.execute.await_args.args[0]
    assert "patients.tenant_id" in str(statement)


def test_patient_and_audit_log_are_added_before_the_same_commit():
    class RecordingSession:
        def __init__(self):
            self.added = []
            self.committed_objects = []
            self.commit_count = 0

        def add(self, item):
            self.added.append(item)

        async def flush(self):
            return None

        async def commit(self):
            self.commit_count += 1
            self.committed_objects = list(self.added)

    tenant_id = uuid.uuid4()
    user = _user(tenant_id)
    session = RecordingSession()
    patient = asyncio.run(
        PatientService().create_patient(PatientCreate(full_name="Demo Patient"), user, session)
    )

    audit = next(item for item in session.committed_objects if isinstance(item, AuditLog))
    assert any(item is patient for item in session.committed_objects)
    assert session.commit_count == 1
    assert audit.tenant_id == tenant_id
    assert audit.user_id == user.uid
    assert audit.action == AuditAction.create
    assert audit.resource_type == "patient"
    assert audit.resource_id == str(patient.id)


def test_diagnosis_analytics_query_is_tenant_and_date_scoped():
    tenant_id = uuid.uuid4()
    user = _user(tenant_id)
    session = SimpleNamespace()
    session.execute = AsyncMock(return_value=[
        SimpleNamespace(_mapping={"diagnosis_code": "38341003", "count": 2})
    ])
    session.add = Mock()
    session.commit = AsyncMock()
    start = date(2026, 1, 1)
    end = date(2026, 1, 31)

    rows = asyncio.run(AnalyticsService().diagnosis_frequency(user, session, start, end))

    assert rows == [{"diagnosis_code": "38341003", "count": 2}]
    statement, params = session.execute.await_args.args
    sql = str(statement)
    assert "note.tenant_id = :tenant_id" in sql
    assert "encounter.tenant_id = :tenant_id" in sql
    assert params == {"tenant_id": tenant_id, "start_date": start, "end_date": end}
    audit = session.add.call_args.args[0]
    assert audit.action == AuditAction.read
    assert audit.tenant_id == tenant_id
    session.commit.assert_awaited_once()


def test_super_admin_without_tenant_cannot_query_analytics():
    user = _user()
    user.role = UserRole.super_admin
    user.tenant_id = None
    session = SimpleNamespace(execute=AsyncMock())

    with pytest.raises(HTTPException) as error:
        asyncio.run(AnalyticsService().encounter_volume(user, session, None, None))

    assert error.value.status_code == 403
    session.execute.assert_not_awaited()
