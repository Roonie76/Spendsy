"""add extended fields to finance_taxprofile for TORA tax integration

Revision ID: 20260413_01
Revises: 3be1fbcda5c7
Create Date: 2026-04-13 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260413_01"
down_revision = "3be1fbcda5c7"
branch_labels = None
depends_on = None

NEW_COLUMNS = [
    ("parents_are_senior", sa.Boolean(), "false"),
    ("age", sa.Integer(), "30"),
    ("is_metro", sa.Boolean(), "false"),
    ("is_presumptive", sa.Boolean(), "false"),
    ("is_nri", sa.Boolean(), "false"),
    ("foreign_assets", sa.Boolean(), "false"),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "finance_taxprofile" not in tables:
        return

    existing = {col["name"] for col in inspector.get_columns("finance_taxprofile")}

    for name, col_type, default in NEW_COLUMNS:
        if name not in existing:
            op.add_column(
                "finance_taxprofile",
                sa.Column(name, col_type, nullable=False, server_default=default),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "finance_taxprofile" not in tables:
        return

    existing = {col["name"] for col in inspector.get_columns("finance_taxprofile")}

    for name, _, _ in NEW_COLUMNS:
        if name in existing:
            op.drop_column("finance_taxprofile", name)
