import uuid

from sqlmodel import select

from sqlalchemy.ext.asyncio import AsyncSession
from src.models.main_model import AuditAction, AuditLog, User, UserRole


class AuditService():
    
    async def log_audit(self, user:User, limit:int, offset:int, session:AsyncSession):
        stmt = select(AuditLog)
        if user.role != UserRole.super_admin:
            if user.tenant_id is None:
                return []
            stmt = stmt.where(AuditLog.tenant_id == user.tenant_id)
        stmt = stmt.order_by(AuditLog.at.desc()).limit(limit).offset(offset)
        
        result = await session.execute(stmt)
        return (result).scalars().all()
    
    async def log_access(self, session: AsyncSession, user: User, action: AuditAction, resource_type: str, resource_id:uuid.UUID, tenant_id:uuid.UUID | None = None) -> None:
        new_log =  AuditLog(
                        tenant_id=tenant_id if tenant_id is not None else user.tenant_id, user_id=user.uid, action=action,
                        resource_type=resource_type, resource_id=str(resource_id),
                )
        session.add(new_log)
