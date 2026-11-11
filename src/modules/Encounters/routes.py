import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import RoleChecker, get_current_user
from src.db.mains import get_session
from src.models.main_model import User
from src.modules.Encounters.schemas import CreateEncounterModel, EncounterModelResponse
from src.modules.Encounters.services import EncounterService


encounter_router = APIRouter()
encounter_service = EncounterService()
clinical_role_checker = RoleChecker(["records_admin", "clinician"])
read_role_checker = RoleChecker(["records_admin", "clinician", "auditor"])


@encounter_router.post(
    "/patients/{patient_id}/encounters", response_model=EncounterModelResponse,
    status_code=201, dependencies=[Depends(clinical_role_checker)])
async def create_encounter(
    patient_id: uuid.UUID, body: CreateEncounterModel,
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await encounter_service.create_encounter(patient_id, body, user, session)


@encounter_router.get(
    "/encounters/{encounter_id}", response_model=EncounterModelResponse,
    dependencies=[Depends(read_role_checker)])
async def get_encounter(
    encounter_id: uuid.UUID, user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)):
    return await encounter_service.get_encounter(encounter_id, user, session)


@encounter_router.get(
    "/patients/{patient_id}/encounters", response_model=list[EncounterModelResponse],
    dependencies=[Depends(read_role_checker)])
async def get_patient_encounters(
    patient_id: uuid.UUID, user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)):
    return await encounter_service.get_patient_encounters(patient_id, user, session)
