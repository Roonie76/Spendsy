"""add raw_description to transaction

Revision ID: 20260310_02
Revises: 20260310_01
Create Date: 2026-03-10 19:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260310_02"
down_revision = "20260310_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "finance_transaction" not in set(inspector.get_table_names()):
        return

    columns = {column["name"] for column in inspector.get_columns("finance_transaction")}
    if "raw_description" not in columns:
        op.add_column("finance_transaction", sa.Column("raw_description", sa.String(length=255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "finance_transaction" not in set(inspector.get_table_names()):
        return

    columns = {column["name"] for column in inspector.get_columns("finance_transaction")}
    if "raw_description" in columns:
        op.drop_column("finance_transaction", "raw_description")
