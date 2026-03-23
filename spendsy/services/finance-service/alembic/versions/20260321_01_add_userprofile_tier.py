"""add tier column to finance_userprofile

Revision ID: 20260321_01
Revises: 20260317_05
Create Date: 2026-03-21 16:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260321_01"
down_revision = "20260317_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "finance_userprofile" not in tables:
        return

    columns = {column["name"] for column in inspector.get_columns("finance_userprofile")}
    if "tier" in columns:
        return

    op.add_column(
        "finance_userprofile",
        sa.Column("tier", sa.String(length=20), nullable=False, server_default="free"),
    )
    op.execute("UPDATE finance_userprofile SET tier = 'free' WHERE tier IS NULL")
    op.alter_column("finance_userprofile", "tier", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "finance_userprofile" not in tables:
        return

    columns = {column["name"] for column in inspector.get_columns("finance_userprofile")}
    if "tier" in columns:
        op.drop_column("finance_userprofile", "tier")
