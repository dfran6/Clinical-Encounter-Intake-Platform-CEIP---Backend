import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.core import startup
from src.models.main_model import User, UserRole


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _StartupSession:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = []
        self.execute = AsyncMock(return_value=_ScalarResult(existing))
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def add(self, item):
        self.added.append(item)


def test_startup_creates_configured_tenantless_super_admin(monkeypatch):
    session = _StartupSession()
    monkeypatch.setattr(startup, "AsyncSessionLocal", lambda: session)
    monkeypatch.setattr(startup.Config, "SUPERADMIN_EMAIL", "  ADMIN@example.test  ")
    monkeypatch.setattr(startup.Config, "SUPERADMIN_PASSWORD", "secret")
    monkeypatch.setattr(startup, "generate_password_hash", lambda password: f"hashed:{password}")

    created = asyncio.run(startup.ensure_superadmin())

    assert created is True
    assert len(session.added) == 1
    user = session.added[0]
    assert isinstance(user, User)
    assert user.email == "admin@example.test"
    assert user.password_hash == "hashed:secret"
    assert user.role == UserRole.super_admin
    assert user.tenant_id is None
    session.commit.assert_awaited_once()


def test_startup_leaves_existing_super_admin_unchanged(monkeypatch):
    existing = User(
        email="admin@example.test",
        password_hash="existing-hash",
        role=UserRole.super_admin,
        tenant_id=None,
    )
    session = _StartupSession(existing)
    monkeypatch.setattr(startup, "AsyncSessionLocal", lambda: session)
    monkeypatch.setattr(startup.Config, "SUPERADMIN_EMAIL", "admin@example.test")
    monkeypatch.setattr(startup.Config, "SUPERADMIN_PASSWORD", "secret")

    created = asyncio.run(startup.ensure_superadmin())

    assert created is False
    assert session.added == []
    session.commit.assert_not_awaited()


def test_external_reference_migration_declares_tenant_scoped_unique_indexes(monkeypatch):
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "ea91b802c74f_add_external_ref_to_encounters.py"
    )
    spec = importlib.util.spec_from_file_location("external_ref_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    create_index = Mock()
    add_column = Mock()
    monkeypatch.setattr(migration.op, "create_index", create_index)
    monkeypatch.setattr(migration.op, "add_column", add_column)

    migration.upgrade()

    index_names = {call.args[0] for call in create_index.call_args_list}
    assert "uq_patients_tenant_external_ref" in index_names
    assert "uq_encounters_tenant_external_ref" in index_names
    assert all(call.kwargs["unique"] is True for call in create_index.call_args_list)
    assert add_column.call_args.args[0] == "encounters"
    assert add_column.call_args.args[1].name == "external_ref"
