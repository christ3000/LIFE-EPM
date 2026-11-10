"""Mise à jour des noms et initiales historiques de l'église.

Revision ID: 3de9ab70a2f1
Revises: bfbf3ce09019
Create Date: 2026-11-03 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3de9ab70a2f1"
down_revision: Union[str, None] = "bfbf3ce09019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEGACY_NAME = "Église Pentecôtiste Unie de Côte d'Ivoire"
CHURCH_NAME = "Église Pentecôte Missionnaire"


def upgrade() -> None:
    churches = sa.table(
        "churches",
        sa.column("name", sa.String()),
        sa.column("denomination", sa.String()),
        sa.column("initials", sa.String()),
    )
    op.execute(
        churches.update()
        .where(churches.c.name == LEGACY_NAME)
        .values(name=CHURCH_NAME)
    )
    op.execute(
        churches.update()
        .where(churches.c.denomination == LEGACY_NAME)
        .values(denomination=CHURCH_NAME)
    )
    op.execute(
        churches.update()
        .where(churches.c.initials == "EPUCI")
        .values(initials="EPM")
    )


def downgrade() -> None:
    """Keep the migrated identity so a downgrade cannot overwrite later edits."""
