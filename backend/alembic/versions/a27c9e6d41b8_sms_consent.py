"""Ajout du consentement explicite aux SMS.

Revision ID: a27c9e6d41b8
Revises: 91d6f01a4c32
Create Date: 2026-11-03 23:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a27c9e6d41b8"
down_revision: Union[str, None] = "91d6f01a4c32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "members",
        sa.Column("sms_opt_in", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("members", "sms_opt_in")
