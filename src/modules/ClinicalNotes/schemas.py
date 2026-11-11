import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ClinicalNoteCreate(BaseModel):
    raw_text: str = Field(min_length=1)


class ClinicalNoteResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    encounter_id: uuid.UUID
    raw_text: str
    extracted: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StructuredEncounterData(BaseModel):
    encounter_id: uuid.UUID
    notes: list[ClinicalNoteResponse]
