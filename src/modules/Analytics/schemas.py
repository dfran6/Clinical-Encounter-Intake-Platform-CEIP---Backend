from datetime import date

from pydantic import BaseModel


class DiagnosisFrequencyItem(BaseModel):
    diagnosis_code: str
    count: int


class EncounterVolumeItem(BaseModel):
    date: date
    count: int
