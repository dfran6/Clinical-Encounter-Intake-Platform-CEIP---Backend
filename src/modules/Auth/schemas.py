import uuid
from src.models.main_model import UserRole
from pydantic import BaseModel, EmailStr


class LoginModel(BaseModel):
    email: EmailStr
    password:str


class LogoutModel(BaseModel):
    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str
