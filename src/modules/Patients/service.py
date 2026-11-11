import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.main_model import AuditAction, Patient, User
from src.modules.Patients.schema import PatientCreate, PatientUpdate
from src.modules.Audit.services import AuditService

audit_service = AuditService()

class PatientService():
    
    async def create_patient(self, body:PatientCreate, user:User, session: AsyncSession):
        self._require_tenant(user)
        patient = Patient(
            tenant_id=user.tenant_id,
            **body.model_dump()
            )
        session.add(patient)
        await session.flush()
        
        await audit_service.log_access(session, user, AuditAction.create, "patient", patient.id)
        await session.commit()
        return patient
    
    
    async def get_all_patients(self, user:User, limit:int, offset:int, session:AsyncSession):
        self._require_tenant(user)
        stmt = (select(Patient).where(Patient.tenant_id == user.tenant_id)
                .order_by(Patient.id).limit(limit).offset(offset))
        result = await session.execute(stmt)
        patients = result.scalars().all()
        await audit_service.log_access(session, user, AuditAction.read, "patient_collection", uuid.UUID(int=0))
        # Also retain resource-level history for the records returned.
        for patient in patients:
            await audit_service.log_access(session, user, AuditAction.read, "patient", patient.id)
        await session.commit()
        return patients
    
    async def get_patient(self,patient_id:uuid.UUID, user:User, session:AsyncSession):
        self._require_tenant(user)
        
        stmt = select(Patient).where(Patient.id == patient_id, Patient.tenant_id == user.tenant_id)
        patient = (await session.execute(stmt)).scalar_one_or_none()
        
        if not patient:
            raise HTTPException(404, "Patient not found")
        
        await audit_service.log_access(session, user, AuditAction.read, "patient", patient.id)
        await session.commit()
        
        return patient

    async def update_patient(self, patient_id: uuid.UUID, body: PatientUpdate, user: User, session: AsyncSession):
        self._require_tenant(user)
        stmt = select(Patient).where(Patient.id == patient_id, Patient.tenant_id == user.tenant_id)
        patient = (await session.execute(stmt)).scalar_one_or_none()
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")

        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(patient, field, value)
        await session.flush()
        await audit_service.log_access(session, user, AuditAction.update, "patient", patient.id)
        await session.commit()
        return patient

    @staticmethod
    def _require_tenant(user: User) -> None:
        if user.tenant_id is None:
            raise HTTPException(status_code=403, detail="Patient data access requires a clinic user")
        
