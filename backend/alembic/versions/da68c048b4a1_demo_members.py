"""Ajout de l'indicateur identifiant les fidèles de démonstration.

Revision ID: da68c048b4a1
Revises: 3de9ab70a2f1
Create Date: 2026-11-02 18:59:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "da68c048b4a1"
down_revision: Union[str, None] = "3de9ab70a2f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "members",
        sa.Column("is_demo", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("members", "is_demo")
