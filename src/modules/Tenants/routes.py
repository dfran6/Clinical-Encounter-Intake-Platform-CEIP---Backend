from src.core.dependencies import RoleChecker, get_current_user
from src.db.mains import get_session
from src.models.main_model import User, UserRole
from src.modules.Tenants.schemas import TenantCreate, TenantOut
from src.modules.Tenants.services import TenantService

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Query, status
from sqlalchemy.ext.asyncio import AsyncSession


tenant_service = TenantService()
role_checker = RoleChecker(["super_admin"])

tenant_router = APIRouter()




@tenant_router.post(
    "/", 
    response_model=TenantOut, 
    status_code=201,
    dependencies=[Depends(role_checker)]
    )
async def create_tenant(
    body: TenantCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    tenant = await tenant_service.create_tenant(body,user,session)
    
    return tenant


@tenant_router.get("/", response_model=list[TenantOut], dependencies=[Depends(role_checker)])
async def get_tenants(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(20, le=100), offset: int = 0
):
    if user.role != UserRole.super_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "user not permitted to perform this action")
            
    tenant = await tenant_service.get_all_tenants(limit, offset,session)
    return tenant


@tenant_router.get(
    "/{tenant_id}",
    # response_model=TenantOut, 
    dependencies=[Depends(role_checker)])
async def get_tenant(
    tenant_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    tenant = await tenant_service.get_tenant(tenant_id,user, session)
    
    if not tenant:
        return {}
    
    return tenant
