import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import RoleChecker, get_current_user
from src.db.mains import get_session
from src.models.main_model import User
from src.modules.ClinicalNotes.schemas import ClinicalNoteCreate, ClinicalNoteResponse, StructuredEncounterData
from src.modules.ClinicalNotes.services import ClinicalNoteService


encounter_note_router = APIRouter()
encounter_note_service = ClinicalNoteService()
clinical_role_checker = RoleChecker(["records_admin", "clinician"])
read_role_checker = RoleChecker(["records_admin", "clinician", "auditor"])


@encounter_note_router.post(
    "/encounters/{encounter_id}/notes", response_model=ClinicalNoteResponse,
    status_code=201, dependencies=[Depends(clinical_role_checker)])
async def create_patient_encounter_notes(
    encounter_id: uuid.UUID, body: ClinicalNoteCreate,
    user: User = Depends(get_current_user), 
    session: AsyncSession = Depends(get_session)):
    return await encounter_note_service.create_note(encounter_id, body, user, session)


@encounter_note_router.post(
    "/encounters/{encounter_id}/notes/{note_id}/extract", response_model=ClinicalNoteResponse,
    dependencies=[Depends(clinical_role_checker)])
async def extract_encounter_notes(
    encounter_id: uuid.UUID, note_id: uuid.UUID,
    user: User = Depends(get_current_user), 
    session: AsyncSession = Depends(get_session)):
    return await encounter_note_service.extract_note(encounter_id, note_id, user, session)


@encounter_note_router.get(
    "/encounters/{encounter_id}/structured-data", response_model=StructuredEncounterData,
    dependencies=[Depends(read_role_checker)])
async def get_patient_encounter_data(
    encounter_id: uuid.UUID, user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)):
    return await encounter_note_service.get_structured_data(encounter_id, user, session)
