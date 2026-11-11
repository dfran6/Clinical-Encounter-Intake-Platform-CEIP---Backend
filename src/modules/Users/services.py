
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.core.utils import generate_password_hash
from src.models.main_model import Tenant, User, UserRole
from src.modules.Audit.services import AuditService
from src.modules.Users.schemas import CreateUser


audit_service= AuditService()

class UserService():
    
    
    
    async def get_users(self, limit:int, offset:int, current_user:User, session:AsyncSession):
        if current_user.role ==  UserRole.super_admin:
            statement = select(User).limit(limit).offset(offset)
            result = await session.execute(statement)
            
            users = result.scalars().all()
            return users
        
        statement = select(User).where(User.tenant_id == current_user.tenant_id).limit(limit).offset(offset)
        result = await session.execute(statement)
        
        users = result.scalars().all()
        return users
            
        
        
    async def get_user_by_email(self, email:str, session:AsyncSession):
        statement = select(User).where(User.email == email)
        result = await session.execute(statement)
        user = result.scalar_one_or_none()
       
        return user
    
    async def invite_user(self, body:CreateUser, admin:User, session: AsyncSession):
        if admin.role != UserRole.records_admin or admin.tenant_id is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a clinic records admin can invite clinic staff")
        if body.role in (UserRole.super_admin, UserRole.records_admin):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot grant that role")
        
        user_exist = await self.get_user_by_email(body.email, session)
        
        if user_exist:
            raise HTTPException(status.HTTP_409_CONFLICT, "user exists")
            
        password= generate_password_hash(body.password)
        
        user = User(
            email=body.email,
            password_hash=password,
            role=body.role,
            is_active=True,
            tenant_id=admin.tenant_id,
            )
        
        session.add(user)
        await session.flush()
                            
        await audit_service.log_access(session, admin, "create", f"{str(user.role)}", user.uid)
                    
        await session.commit()
        
        return user
    
    async def create_record_admin_user(self, body:CreateUser, tenant_id:uuid.UUID, user:User, session: AsyncSession):
            if user.role != UserRole.super_admin:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a Super Admin can create records admins")
            if tenant_id is None or await session.get(Tenant, tenant_id) is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found, add one or create a new one")
            user_exist = await self.get_user_by_email(body.email, session)
            
            if user_exist:
                raise HTTPException(status.HTTP_409_CONFLICT, "user exists")
                            
                
            password= generate_password_hash(body.password)
            
            new_user = User(
                email=body.email,
                password_hash=password,
                role= UserRole.records_admin,
                is_active=True,
                tenant_id=tenant_id,
                )
            
            session.add(new_user)
            await session.flush()
                    
            await audit_service.log_access(session, user, "create", "record_admin", new_user.uid, tenant_id=tenant_id)
            
            await session.commit()
            
            return new_user
