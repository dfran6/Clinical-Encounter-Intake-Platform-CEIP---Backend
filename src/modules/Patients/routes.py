import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import RoleChecker, get_current_user
from src.db.mains import get_session
from src.models.main_model import User
from src.modules.Patients.schema import PatientCreate, PatientOut, PatientUpdate
from src.modules.Patients.service import PatientService


role_checker = RoleChecker(
    ["records_admin",
    "clinician"])
read_role_checker = RoleChecker(["records_admin", "clinician", "auditor"])


patient_service = PatientService()
patient_router = APIRouter()

@patient_router.post(
    "/", 
    response_model=PatientOut, 
    status_code=201,
    dependencies=[Depends(role_checker)])
async def create_patient(
    body: PatientCreate, 
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)):
    
    patient = await patient_service.create_patient(body, user, session)
    
    return patient
   


@patient_router.get("/", response_model=list[PatientOut], dependencies=[Depends(read_role_checker)])
async def list_patients(
    user: User = Depends(get_current_user), 
    session: AsyncSession = Depends(get_session),
    limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    
    patients = await patient_service.get_all_patients(user, limit,offset, session)
    
    return patients

@patient_router.get(
    "/{patient_id}",
    response_model=PatientOut,
    dependencies=[Depends(read_role_checker)]
    )
async def get_patient(
    patient_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)):
    
    patient = await patient_service.get_patient(patient_id, user, session)
    
    return patient

@patient_router.patch(
    "/{patient_id}", response_model=PatientOut,
    dependencies=[Depends(role_checker)])
async def update_patient(
    patient_id: uuid.UUID, body: PatientUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)):
    
    patient = await patient_service.update_patient(patient_id, body, user, session)
    
    return patient
