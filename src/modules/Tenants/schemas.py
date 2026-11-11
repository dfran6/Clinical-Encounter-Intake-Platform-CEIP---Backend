
import uuid

from pydantic import BaseModel, EmailStr




class TenantCreate(BaseModel):
    name: str
    email: EmailStr
    address:str


class TenantOut(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    address:str
    
    model_config = {"from_attributes": True}

