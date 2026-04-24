"""add date_inferred to finance_transaction

Revision ID: 20260424_02
Revises: 20260424_01
Create Date: 2026-04-24 12:30:00.000000

When the PDF parser can't read a day off a statement row, it now inherits
month/year from the previous dated row (day=01) and marks the row as
date_inferred=True so the UI renders "Mon YYYY" instead of a fake full date.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260424_02"
down_revision = "20260424_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("finance_transaction")}
    if "date_inferred" in cols:
        return
    op.add_column(
        "finance_transaction",
        sa.Column(
            "date_inferred",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("finance_transaction")}
    if "date_inferred" not in cols:
        return
    op.drop_column("finance_transaction", "date_inferred")
