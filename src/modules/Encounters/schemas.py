import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CreateEncounterModel(BaseModel):
    occurred_at: datetime | None = None


class EncounterModelResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    patient_id: uuid.UUID
    clinician_id: uuid.UUID
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)
