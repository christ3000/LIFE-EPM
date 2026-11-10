"""Ajout du logo téléversé à l'identité de l'église.

Revision ID: f2a18c0d7b91
Revises: c47e981a3621
Create Date: 2026-11-03 17:55:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a18c0d7b91"
down_revision: Union[str, None] = "c47e981a3621"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("churches", sa.Column("logo_data", sa.LargeBinary(), nullable=True))
    op.add_column("churches", sa.Column("logo_content_type", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("churches", "logo_content_type")
    op.drop_column("churches", "logo_data")
