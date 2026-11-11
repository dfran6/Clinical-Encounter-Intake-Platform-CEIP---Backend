from fastapi import APIRouter, Body, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from src.core.dependencies import AccessTokenBearer, RoleChecker
from src.db.mains import get_session
from src.modules.Auth.schemas import LoginModel, LogoutModel, RefreshRequest
from src.modules.Auth.services import AuthService

auth_router = APIRouter()
auth_service = AuthService()

role_checker = RoleChecker(
    ["super_admin",
    "records_admin",
    "clinician",
    "auditor"])

admin_role_checker = RoleChecker(
    ["super_admin",
    "records_admin",])


@auth_router.post("/login")
async def login(form: LoginModel = Body(...), session: AsyncSession = Depends(get_session)):
    login_data = await auth_service.login(form, session)
    
    if not login_data:
        raise  HTTPException(
                status_code=403,
                detail="login Error")
        
    return login_data


@auth_router.post("/refresh")
async def refresh(body: RefreshRequest, session: AsyncSession = Depends(get_session)):
    return await auth_service.new_refresh_token(body.refresh_token, session)


@auth_router.post("/logout")
async def logout(
    body: LogoutModel,
    access_token_details: dict = Depends(AccessTokenBearer()),
):
    return await auth_service.logout(access_token_details, body.refresh_token)

