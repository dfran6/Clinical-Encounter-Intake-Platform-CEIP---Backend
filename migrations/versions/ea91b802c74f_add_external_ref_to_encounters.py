"""Add Synthea source reference to encounters.

Revision ID: ea91b802c74f
Revises: c20d0999ac94
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ea91b802c74f"
down_revision: Union[str, Sequence[str], None] = "c20d0999ac94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_patients_tenant_external_ref",
        "patients",
        ["tenant_id", "external_ref"],
        unique=True,
    )
    op.add_column(
        "encounters",
        sa.Column("external_ref", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "uq_encounters_tenant_external_ref",
        "encounters",
        ["tenant_id", "external_ref"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_encounters_tenant_external_ref", table_name="encounters")
    op.drop_column("encounters", "external_ref")
    op.drop_index("uq_patients_tenant_external_ref", table_name="patients")
