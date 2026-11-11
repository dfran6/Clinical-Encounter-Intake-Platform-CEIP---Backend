import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from src.core.config import Config
from src.core.utils import generate_password_hash
from src.db.mains import AsyncSessionLocal
from src.models.main_model import User, UserRole


logger = logging.getLogger(__name__)


async def ensure_superadmin() -> bool:
    """Create the configured tenantless Super Admin once; return whether it was created."""
    email = Config.SUPERADMIN_EMAIL.strip().casefold()
    password = Config.SUPERADMIN_PASSWORD
    if not email or not password.strip():
        raise RuntimeError("SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD must not be blank")

    async with AsyncSessionLocal() as session:
        existing = (await session.execute(
            select(User).where(func.lower(User.email) == email)
        )).scalar_one_or_none()

        if existing is not None:
            if existing.role != UserRole.super_admin:
                raise RuntimeError(
                    "The configured Super Admin email is already used by a non-Super-Admin account"
                )
            logger.info("Configured Super Admin already exists; leaving its account unchanged")
            return False

        superadmin = User(
            email=email,
            password_hash=generate_password_hash(password),
            role=UserRole.super_admin,
            is_active=True,
            tenant_id=None,
        )
        session.add(superadmin)
        try:
            await session.commit()
        except IntegrityError:
            # Multiple application workers can start together. The unique email
            # constraint elects one insert; confirm the winning row is valid.
            await session.rollback()
            existing = (await session.execute(
                select(User).where(func.lower(User.email) == email)
            )).scalar_one_or_none()
            if existing is None or existing.role != UserRole.super_admin:
                raise
            logger.info("Another application worker created the configured Super Admin")
            return False

    logger.info("Created configured tenantless Super Admin account")
    return True
