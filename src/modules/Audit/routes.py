from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.dependencies import RoleChecker, get_current_user
from src.db.mains import get_session
from src.models.main_model import User
from src.modules.Audit.schemas import AuditOut
from src.modules.Audit.services import AuditService



role_checker = RoleChecker(
    ["super_admin",
    "records_admin",
    "clinician",
    "auditor"])

record_role_checker = RoleChecker(
    ["super_admin",
    "records_admin",
    "auditor"
    ])


audit_router = APIRouter()
audit_service = AuditService()

@audit_router.get(
    "/",
    response_model=list[AuditOut],
    dependencies=[Depends(record_role_checker)])
async def list_audit_logs(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    
    logs = await audit_service.log_audit(user,limit,offset, session)
    
    return logs
