"""add uid column to networthsnapshot

Revision ID: 20260503_02
Revises: 20260503_01
Create Date: 2026-05-03

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
import uuid


revision = '20260503_02'
down_revision = '20260503_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    
    if "finance_networthsnapshot" in tables:
        columns = {column["name"] for column in inspector.get_columns("finance_networthsnapshot")}
        if "uid" not in columns:
            op.add_column(
                "finance_networthsnapshot",
                sa.Column("uid", sa.String(length=36), nullable=True),
            )
            # Generate UUIDs for existing rows
            op.execute("UPDATE finance_networthsnapshot SET uid = md5(random()::text || clock_timestamp()::text)::uuid::text WHERE uid IS NULL")
            # Make it non-nullable and add index
            op.alter_column("finance_networthsnapshot", "uid", nullable=False)
            op.create_index("idx_finance_networthsnapshot_uid", "finance_networthsnapshot", ["uid"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    
    if "finance_networthsnapshot" in tables:
        columns = {column["name"] for column in inspector.get_columns("finance_networthsnapshot")}
        if "uid" in columns:
            op.drop_index("idx_finance_networthsnapshot_uid", table_name="finance_networthsnapshot")
            op.drop_column("finance_networthsnapshot", "uid")
