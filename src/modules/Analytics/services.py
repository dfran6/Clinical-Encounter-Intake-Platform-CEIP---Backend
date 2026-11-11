from datetime import date, datetime, timedelta, timezone
import uuid

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.main_model import AuditAction, User
from src.modules.Audit.services import AuditService


class AnalyticsService:
    def __init__(self):
        self.audit_service = AuditService()

    @staticmethod
    def _tenant_id(user: User):
        # A Super Admin has no clinic context. Analytics never accept a tenant
        # identifier from the request, so cross-tenant aggregate access is denied.
        if user.tenant_id is None:
            raise HTTPException(status_code=403, detail="Analytics require a clinic user")
        return user.tenant_id

    @staticmethod
    def _date_range(start_date: date | None, end_date: date | None):
        end = end_date or datetime.now(timezone.utc).date()
        start = start_date or end - timedelta(days=29)
        if start > end:
            raise HTTPException(status_code=422, detail="start_date must be on or before end_date")
        if (end - start).days > 364:
            raise HTTPException(status_code=422, detail="Date range cannot exceed 365 days")
        return start, end

    async def diagnosis_frequency(
        self, user: User, session: AsyncSession, start_date: date | None, end_date: date | None
    ):
        tenant_id = self._tenant_id(user)
        start, end = self._date_range(start_date, end_date)
        statement = text("""
            SELECT diagnosis.value ->> 'code' AS diagnosis_code, COUNT(*)::int AS count
            FROM clinical_notes AS note
            JOIN encounters AS encounter
              ON encounter.id = note.encounter_id
             AND encounter.tenant_id = :tenant_id
            CROSS JOIN LATERAL jsonb_array_elements(
                CASE
                    WHEN jsonb_typeof(note.extracted -> 'diagnoses') = 'array'
                    THEN note.extracted -> 'diagnoses'
                    ELSE '[]'::jsonb
                END
            ) AS diagnosis(value)
            WHERE note.tenant_id = :tenant_id
              AND encounter.occurred_at >= (CAST(:start_date AS date)::timestamp AT TIME ZONE 'UTC')
              AND encounter.occurred_at < ((CAST(:end_date AS date) + 1)::timestamp AT TIME ZONE 'UTC')
            GROUP BY diagnosis.value ->> 'code'
            ORDER BY count DESC, diagnosis_code
        """)
        result = await session.execute(statement, {
            "tenant_id": tenant_id, "start_date": start, "end_date": end,
        })
        rows = [dict(row._mapping) for row in result]
        audit_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{tenant_id}:diagnosis_frequency:{start}:{end}")
        await self.audit_service.log_access(session, user, AuditAction.read, "analytics_diagnosis_frequency", audit_id)
        await session.commit()
        return rows

    async def encounter_volume(
        self, user: User, session: AsyncSession, start_date: date | None, end_date: date | None
    ):
        tenant_id = self._tenant_id(user)
        start, end = self._date_range(start_date, end_date)
        statement = text("""
            SELECT (occurred_at AT TIME ZONE 'UTC')::date AS date, COUNT(*)::int AS count
            FROM encounters
            WHERE tenant_id = :tenant_id
              AND occurred_at >= (CAST(:start_date AS date)::timestamp AT TIME ZONE 'UTC')
              AND occurred_at < ((CAST(:end_date AS date) + 1)::timestamp AT TIME ZONE 'UTC')
            GROUP BY (occurred_at AT TIME ZONE 'UTC')::date
            ORDER BY date
        """)
        result = await session.execute(statement, {
            "tenant_id": tenant_id, "start_date": start, "end_date": end,
        })
        rows = [dict(row._mapping) for row in result]
        audit_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{tenant_id}:encounter_volume:{start}:{end}")
        await self.audit_service.log_access(session, user, AuditAction.read, "analytics_encounter_volume", audit_id)
        await session.commit()
        return rows
