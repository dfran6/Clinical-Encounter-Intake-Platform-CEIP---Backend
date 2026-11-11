import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.main_model import AuditAction, ClinicalNote, Encounter, User
from src.modules.Audit.services import AuditService
from src.modules.ClinicalNotes.schemas import ClinicalNoteCreate
from src.extraction.extractor import extract


class ClinicalNoteService:
    def __init__(self):
        self.audit_service = AuditService()

    async def _get_encounter(self, encounter_id: uuid.UUID, user: User, session: AsyncSession):
        if user.tenant_id is None:
            raise HTTPException(status_code=403, detail="Clinical-note access requires a clinic user")
        encounter = (await session.execute(select(Encounter).where(
            Encounter.id == encounter_id, Encounter.tenant_id == user.tenant_id
        ))).scalar_one_or_none()
        if encounter is None:
            raise HTTPException(status_code=404, detail="Encounter not found")
        return encounter

    async def create_note(self, encounter_id: uuid.UUID, body: ClinicalNoteCreate, user: User, session: AsyncSession):
        encounter = await self._get_encounter(encounter_id, user, session)
        note = ClinicalNote(tenant_id=user.tenant_id, encounter_id=encounter.id, raw_text=body.raw_text)
        session.add(note)
        await session.flush()
        await self.audit_service.log_access(session, user, AuditAction.create, "clinical_note", note.id)
        await session.commit()
        return note

    async def extract_note(self, encounter_id: uuid.UUID, note_id: uuid.UUID, user: User, session: AsyncSession):
        await self._get_encounter(encounter_id, user, session)
        note = (await session.execute(select(ClinicalNote).where(
            ClinicalNote.id == note_id,
            ClinicalNote.encounter_id == encounter_id,
            ClinicalNote.tenant_id == user.tenant_id,
        ))).scalar_one_or_none()
        if note is None:
            raise HTTPException(status_code=404, detail="Clinical note not found")

        note.extracted = extract(note.raw_text)
        note.updated_at = datetime.now(timezone.utc)
        await session.flush()
        await self.audit_service.log_access(session, user, AuditAction.extract, "clinical_note", note.id)
        await session.commit()
        return note

    async def get_structured_data(self, encounter_id: uuid.UUID, user: User, session: AsyncSession):
        encounter = await self._get_encounter(encounter_id, user, session)
        notes = (await session.execute(select(ClinicalNote).where(
            ClinicalNote.encounter_id == encounter_id,
            ClinicalNote.tenant_id == user.tenant_id,
        ).order_by(ClinicalNote.created_at))).scalars().all()
        for note in notes:
            await self.audit_service.log_access(session, user, AuditAction.read, "clinical_note", note.id)
        await self.audit_service.log_access(session, user, AuditAction.read, "encounter_structured_data", encounter.id)
        await session.commit()
        return {"encounter_id": encounter_id, "notes": notes}
