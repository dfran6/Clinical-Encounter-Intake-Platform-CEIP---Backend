import uuid
from datetime import date

from pydantic import BaseModel



class PatientCreate(BaseModel):
    full_name: str
    birth_date: date | None = None
    sex: str | None = None
    external_ref: str | None = None


class PatientUpdate(BaseModel):
    full_name: str | None = None
    birth_date: date | None = None
    sex: str | None = None
    external_ref: str | None = None


class PatientOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    full_name: str
    birth_date: date | None
    sex: str | None
    external_ref: str | None

    model_config = {"from_attributes": True}


