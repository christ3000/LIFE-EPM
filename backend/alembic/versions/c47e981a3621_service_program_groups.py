"""Séparation des cultes et des programmes dans les événements.

Revision ID: c47e981a3621
Revises: da68c048b4a1
Create Date: 2026-11-02 20:56:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c47e981a3621"
down_revision: Union[str, None] = "da68c048b4a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "services",
        sa.Column("service_group", sa.String(length=16), server_default="culte", nullable=False),
    )
    op.create_index("ix_services_service_group", "services", ["service_group"])


def downgrade() -> None:
    op.drop_index("ix_services_service_group", table_name="services")
    op.drop_column("services", "service_group")
