from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import RoleChecker, get_current_user
from src.db.mains import get_session
from src.models.main_model import User
from src.modules.Analytics.schemas import DiagnosisFrequencyItem, EncounterVolumeItem
from src.modules.Analytics.services import AnalyticsService


analytics_router = APIRouter()
analytics_service = AnalyticsService()
analytics_reader = RoleChecker(["records_admin", "clinician", "auditor"])


@analytics_router.get("/diagnosis-frequency", response_model=list[DiagnosisFrequencyItem], dependencies=[Depends(analytics_reader)])
async def diagnosis_frequency(
    start_date: date | None = Query(None, description="Inclusive UTC date; defaults to 29 days before end_date"),
    end_date: date | None = Query(None, description="Inclusive UTC date; defaults to today"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return diagnosis-code counts in a maximum 365-day inclusive UTC range; response rows are diagnosis_code/count."""
    return await analytics_service.diagnosis_frequency(user, session, start_date, end_date)


@analytics_router.get("/encounter-volume", response_model=list[EncounterVolumeItem], dependencies=[Depends(analytics_reader)])
async def encounter_volume(
    start_date: date | None = Query(None, description="Inclusive UTC date; defaults to 29 days before end_date"),
    end_date: date | None = Query(None, description="Inclusive UTC date; defaults to today"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return daily UTC encounter counts in a maximum 365-day inclusive range; dates with no encounters are omitted."""
    return await analytics_service.encounter_volume(user, session, start_date, end_date)
