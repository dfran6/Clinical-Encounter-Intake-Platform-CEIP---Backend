import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.main_model import AuditAction, Encounter, Patient, User
from src.modules.Audit.services import AuditService
from src.modules.Encounters.schemas import CreateEncounterModel


class EncounterService:
    def __init__(self):
        self.audit_service = AuditService()

    async def create_encounter(self, patient_id: uuid.UUID, body: CreateEncounterModel, user: User, session: AsyncSession):
        self._require_tenant(user)
        patient = (await session.execute(select(Patient).where(
            Patient.id == patient_id, Patient.tenant_id == user.tenant_id
        ))).scalar_one_or_none()
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")

        encounter = Encounter(
            tenant_id=user.tenant_id,
            patient_id=patient.id,
            clinician_id=user.uid,
            **body.model_dump(exclude_none=True),
        )
        session.add(encounter)
        await session.flush()
        await self.audit_service.log_access(session, user, AuditAction.create, "encounter", encounter.id)
        await session.commit()
        return encounter

    async def get_encounter(self, encounter_id: uuid.UUID, user: User, session: AsyncSession):
        self._require_tenant(user)
        encounter = (await session.execute(select(Encounter).where(
            Encounter.id == encounter_id, Encounter.tenant_id == user.tenant_id
        ))).scalar_one_or_none()
        if encounter is None:
            raise HTTPException(status_code=404, detail="Encounter not found")
        await self.audit_service.log_access(session, user, AuditAction.read, "encounter", encounter.id)
        await session.commit()
        return encounter

    async def get_patient_encounters(self, patient_id: uuid.UUID, user: User, session: AsyncSession):
        self._require_tenant(user)
        patient = (await session.execute(select(Patient).where(
            Patient.id == patient_id, Patient.tenant_id == user.tenant_id
        ))).scalar_one_or_none()
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        encounters = (await session.execute(select(Encounter).where(
            Encounter.patient_id == patient.id, Encounter.tenant_id == user.tenant_id
        ).order_by(Encounter.occurred_at.desc()))).scalars().all()
        await self.audit_service.log_access(session, user, AuditAction.read, "encounter_collection", patient.id)
        for encounter in encounters:
            await self.audit_service.log_access(session, user, AuditAction.read, "encounter", encounter.id)
        await session.commit()
        return encounters

    @staticmethod
    def _require_tenant(user: User) -> None:
        if user.tenant_id is None:
            raise HTTPException(status_code=403, detail="Encounter access requires a clinic user")
