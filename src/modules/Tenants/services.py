

import uuid

from fastapi import HTTPException, status

from src.models.main_model import Tenant, User, UserRole
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from src.modules.Audit.services import AuditService
from src.modules.Tenants.schemas import TenantCreate


audit_service = AuditService()

class TenantService():
    
    async def get_tenant_by_name(self, tenant_name:str, session:AsyncSession):
        statement = select(Tenant).where(Tenant.name == tenant_name)
        result= await session.execute(statement)
        
        tenant = result.one_or_none()
        
        return tenant
    
    async def get_tenant_by_email(self, tenant_email:str, session:AsyncSession):
        statement = select(Tenant).where(Tenant.email == tenant_email)
        result= await session.execute(statement)
        
        tenant = result.one_or_none()
        
        return tenant
    
        
    async def create_tenant(self, body:TenantCreate,user:User, session: AsyncSession):
        tenant_exists = await self.get_tenant_by_name(body.name, session)
        email_exists = await self.get_tenant_by_email(body.email, session)
        
        if tenant_exists:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "name already in use")
        if email_exists:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "email already in use")
                    
        
        tenant = Tenant(name=body.name, email=body.email, address=body.address)
        session.add(tenant)
        await session.flush()
        
        await audit_service.log_access(session, user, "create", "tenant", tenant.id)
        await session.commit()
        
        return tenant
        
    async def get_tenant(self, tenant_id:uuid.UUID,user:User, session:AsyncSession):
        if user.role == UserRole.super_admin:
            tenant = await session.get(Tenant, tenant_id)
            if not tenant:
                print("here")
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
            return tenant
        
        statement = select(Tenant).where(Tenant.id == user.tenant_id)
        result = await session.execute(statement)
        
        tenant = result.one_or_none()
        
        return tenant
    
    async def get_all_tenants(self,limit:int, offset:int, session:AsyncSession):
        stmt = select(Tenant).limit(limit).offset(offset)
        result = await session.execute(stmt)
        
        return (result).scalars().all() or None