from enum import Enum
import uuid
from datetime import date, datetime, timezone

import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Text
from sqlmodel import Column, Field, Relationship, SQLModel


def utcnow():
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    super_admin = "super_admin"
    records_admin = "records_admin"
    clinician = "clinician"
    auditor = "auditor"

class Invitable(str, Enum):
    clinician = "clinician"
    auditor = "auditor"


class AuditAction(str, Enum):
    read = "read"
    create = "create"
    update = "update"
    extract = "extract"


class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str = Field(nullable=False, max_length=200, unique=True)
    email: str = Field(nullable=False, max_length=200, unique=True)
    address: str = Field(nullable=False, max_length=600, unique=True)
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, index=True),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False),
    )


class User(SQLModel, table=True):
    __tablename__ = "users"

    uid: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    email: str = Field(nullable=False, unique=True, index=True)
    password_hash: str = Field(exclude=True)
    role: UserRole = Field(
        sa_column=Column(
            pg.ENUM(UserRole, name="user_role_enum"),
            nullable=False,
            index=True,
        )
    )
    is_active: bool = Field(default=True)
    tenant_id: uuid.UUID | None = Field(default=None, foreign_key="tenants.id", nullable=True, index=True)
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, index=True),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False),
    )


class Patient(SQLModel, table=True):
    __tablename__ = "patients"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    tenant_id: uuid.UUID = Field(default=None, foreign_key="tenants.id", index=True)
    external_ref: str | None = Field(default=None, max_length=100)
    full_name: str = Field(max_length=200)
    birth_date: date | None = None
    sex: str | None = Field(default=None, max_length=20)
    encounters: list["Encounter"] = Relationship(back_populates="patient")


class Encounter(SQLModel, table=True):
    __tablename__ = "encounters"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    tenant_id: uuid.UUID = Field(default=None, foreign_key="tenants.id", index=True)
    patient_id: uuid.UUID = Field(default=None, foreign_key="patients.id", index=True)
    clinician_id: uuid.UUID = Field(default=None, foreign_key="users.uid")
    external_ref: str | None = Field(default=None, max_length=100)
    occurred_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, index=True),
    )
    patient: Patient = Relationship(back_populates="encounters")
    notes: list["ClinicalNote"] = Relationship(back_populates="encounter")


class ClinicalNote(SQLModel, table=True):
    __tablename__ = "clinical_notes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    tenant_id: uuid.UUID = Field(default=None, foreign_key="tenants.id", index=True)
    encounter_id: uuid.UUID = Field(default=None, foreign_key="encounters.id", index=True)
    raw_text: str = Field(sa_column=Column(Text))
    extracted: dict | None = Field(default=None, sa_column=Column(pg.JSONB))
    encounter: Encounter = Relationship(back_populates="notes")
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, index=True),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False),
    )


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    tenant_id: uuid.UUID | None = Field(default=None, foreign_key="tenants.id", index=True)
    user_id: uuid.UUID = Field(default=None, foreign_key="users.uid")
    action: AuditAction = Field(
        sa_column=Column(
            pg.ENUM(AuditAction, name="audit_action_enum"),
            nullable=False,
            index=True,
        )
    )
    resource_type: str = Field(max_length=50)
    resource_id: str = Field(max_length=64)
    at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, index=True),
    )
