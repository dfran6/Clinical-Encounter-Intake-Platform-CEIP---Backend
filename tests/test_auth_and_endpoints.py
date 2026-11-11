from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.dependencies import get_current_user
from src.db.mains import get_session
from src.models.main_model import Patient, UserRole
from src.modules.Auth.routes import auth_router
from src.modules.Patients.routes import patient_router
from src.modules.Patients import routes as patient_routes


def _app_with_session(router, session, user=None, prefix="/api/v1"):
    app = FastAPI()
    app.include_router(router, prefix=prefix)

    async def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return app


def test_login_returns_tokens_for_valid_credentials(monkeypatch):
    user = SimpleNamespace(
        email="clinician@example.com",
        uid="user-123",
        role=UserRole.clinician,
        is_active=True,
        password_hash="fake-hash",
    )
    session = AsyncMock()
    query_result = Mock()
    query_result.scalar_one_or_none.return_value = user
    session.execute.return_value = query_result
    monkeypatch.setattr("src.modules.Auth.services.verify_password", lambda password, _hash: password == "secret")
    monkeypatch.setattr(
        "src.modules.Auth.services.create_access_token",
        lambda user_data, refresh=False, expiry=None: "refresh-token" if refresh else "access-token",
    )

    with TestClient(_app_with_session(auth_router, session, prefix="/api/v1/auth")) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "clinician@example.com", "password": "secret"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "access-token"
    assert body["refresh_token"] == "refresh-token"
    assert body["user"]["role"] == "clinician"


def test_login_rejects_invalid_password(monkeypatch):
    user = SimpleNamespace(
        email="clinician@example.com",
        uid="user-123",
        role=UserRole.clinician,
        is_active=True,
        password_hash="fake-hash",
    )
    session = AsyncMock()
    query_result = Mock()
    query_result.scalar_one_or_none.return_value = user
    session.execute.return_value = query_result
    monkeypatch.setattr("src.modules.Auth.services.verify_password", lambda _password, _hash: False)

    with TestClient(_app_with_session(auth_router, session, prefix="/api/v1/auth")) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "clinician@example.com", "password": "wrong"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid email or password"


def test_auditor_cannot_create_patient():
    auditor = SimpleNamespace(role=UserRole.auditor, is_active=True, tenant_id="tenant-1")
    with TestClient(_app_with_session(patient_router, AsyncMock(), auditor)) as client:
        response = client.post("/api/v1/", json={"full_name": "Demo Patient"})

    assert response.status_code == 403


def test_clinician_can_create_patient_endpoint(monkeypatch):
    import uuid

    tenant_id = uuid.uuid4()
    clinician = SimpleNamespace(role=UserRole.clinician, is_active=True, tenant_id=tenant_id)
    patient = Patient(tenant_id=tenant_id, full_name="Demo Patient")
    monkeypatch.setattr(patient_routes.patient_service, "create_patient", AsyncMock(return_value=patient))

    with TestClient(_app_with_session(patient_router, AsyncMock(), clinician)) as client:
        response = client.post("/api/v1/", json={"full_name": "Demo Patient"})

    assert response.status_code == 201
    assert response.json()["full_name"] == "Demo Patient"
