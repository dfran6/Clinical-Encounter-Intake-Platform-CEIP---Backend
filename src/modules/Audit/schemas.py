import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    tenant_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str
    at: datetime

    model_config = {"from_attributes": True}

