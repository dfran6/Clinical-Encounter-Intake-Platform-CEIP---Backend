import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.dependencies import RoleChecker, get_current_user
from src.db.mains import get_session
from src.models.main_model import User, UserRole
from src.modules.Users.schemas import CreateAdminUser, CreateUser, UserResponse
from src.modules.Users.services import UserService

user_router = APIRouter()
user_service = UserService()


role_checker = RoleChecker(
    ["super_admin",
    "records_admin",
    "clinician",
    "auditor"])

admin_role_checker = RoleChecker(
    ["super_admin",
    "records_admin",])
records_admin_checker = RoleChecker(["records_admin"])
super_admin_checker = RoleChecker(["super_admin"])





@user_router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user


@user_router.post(
    "/", 
    response_model=UserResponse, 
    status_code=201,
    dependencies=[Depends(records_admin_checker)]
    )
async def invite_user(
    body: CreateUser,
    admin: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    user = await user_service.invite_user(body, admin, session)
    return user

@user_router.post(
    "/create_record_admin", 
    response_model=UserResponse, 
    dependencies=[Depends(super_admin_checker)],
    status_code=201,
    )
async def create_records_admin_user(
    body: CreateAdminUser,
    tenant_id: uuid.UUID = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)):
    
    return await user_service.create_record_admin_user(body, tenant_id, current_user, session)


@user_router.get(
    "/",
    dependencies=[Depends(admin_role_checker)],
    # response_model=list[UserResponse],
    )
async def get_users(
    limit:int = Query(20, ge=1, le=100),
    offset:int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
    ):
    
    users = await user_service.get_users(limit,offset,current_user,session)
    
    return users


# @user_router.patch("/{user_id}/role")
# async def update_users(user_id:str):
#     return user_id
