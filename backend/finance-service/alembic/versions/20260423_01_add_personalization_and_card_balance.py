"""add personalization fields to userprofile and balance tracking to creditcard

Revision ID: 20260423_01
Revises: 20260413_01
Create Date: 2026-04-23 12:00:00.000000

Adds:
  finance_userprofile.risk_tolerance  (String(20), nullable)
  finance_userprofile.dependents      (Integer,    default 0, NOT NULL)
  finance_userprofile.life_stage      (String(20), nullable)

  finance_creditcard.outstanding_balance    (Numeric(15,2), default 0, NOT NULL)
  finance_creditcard.last_statement_balance (Numeric(15,2), default 0, NOT NULL)
  finance_creditcard.payment_due_date       (Date, nullable)

All column adds are idempotent — the migration inspects the current schema
and skips columns that already exist. Safe to replay.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260423_01"
down_revision = "20260413_01"
branch_labels = None
depends_on = None


USERPROFILE_COLUMNS = [
    ("risk_tolerance", sa.String(length=20), True, None),
    ("dependents", sa.Integer(), False, "0"),
    ("life_stage", sa.String(length=20), True, None),
]

CREDITCARD_COLUMNS = [
    ("outstanding_balance", sa.Numeric(15, 2), False, "0"),
    ("last_statement_balance", sa.Numeric(15, 2), False, "0"),
    ("payment_due_date", sa.Date(), True, None),
]


def _add_columns_if_missing(table: str, specs) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if table not in tables:
        return
    existing = {col["name"] for col in inspector.get_columns(table)}
    for name, col_type, nullable, server_default in specs:
        if name in existing:
            continue
        op.add_column(
            table,
            sa.Column(
                name,
                col_type,
                nullable=nullable,
                server_default=server_default,
            ),
        )


def _drop_columns_if_present(table: str, specs) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if table not in tables:
        return
    existing = {col["name"] for col in inspector.get_columns(table)}
    for name, _, _, _ in specs:
        if name in existing:
            op.drop_column(table, name)


def upgrade() -> None:
    _add_columns_if_missing("finance_userprofile", USERPROFILE_COLUMNS)
    _add_columns_if_missing("finance_creditcard", CREDITCARD_COLUMNS)


def downgrade() -> None:
    _drop_columns_if_present("finance_creditcard", CREDITCARD_COLUMNS)
    _drop_columns_if_present("finance_userprofile", USERPROFILE_COLUMNS)
