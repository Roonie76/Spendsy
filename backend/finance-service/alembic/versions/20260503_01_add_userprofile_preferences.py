"""add preferences column to userprofile

Revision ID: 20260503_01
Revises: 20260429_01
Create Date: 2026-05-03

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = '20260503_01'
down_revision = '20260429_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "finance_userprofile" not in tables:
        return

    columns = {column["name"] for column in inspector.get_columns("finance_userprofile")}
    if "preferences" in columns:
        return

    op.add_column(
        "finance_userprofile",
        sa.Column("preferences", JSONB, nullable=False, server_default='{}'),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "finance_userprofile" not in tables:
        return

    columns = {column["name"] for column in inspector.get_columns("finance_userprofile")}
    if "preferences" in columns:
        op.drop_column("finance_userprofile", "preferences")
