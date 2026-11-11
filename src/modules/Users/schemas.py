from datetime import datetime
import uuid
from src.models.main_model import Invitable, UserRole
from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    uid: uuid.UUID
    email: EmailStr
    role: UserRole
    tenant_id: uuid.UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class CreateUser(BaseModel):
    email: EmailStr
    password: str
    role: Invitable
    
class CreateAdminUser(BaseModel):
    email: EmailStr
    password: str