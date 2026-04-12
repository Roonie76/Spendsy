"""add transaction ingestion fields

Revision ID: 20260310_01
Revises: 20260310_00
Create Date: 2026-03-10 17:25:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260310_01"
down_revision = "20260310_00"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "finance_transaction" not in set(inspector.get_table_names()):
        return

    columns = {column["name"] for column in inspector.get_columns("finance_transaction")}
    indexes = {index["name"] for index in inspector.get_indexes("finance_transaction")}
    uniques = {constraint["name"] for constraint in inspector.get_unique_constraints("finance_transaction")}

    if "balance" not in columns:
        op.add_column("finance_transaction", sa.Column("balance", sa.Numeric(14, 2), nullable=True))
    if "source" not in columns:
        op.add_column(
            "finance_transaction",
            sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
        )
    if "statement_hash" not in columns:
        op.add_column(
            "finance_transaction",
            sa.Column("statement_hash", sa.String(length=64), nullable=True),
        )
    if "statement_row_hash" not in columns:
        op.add_column(
            "finance_transaction",
            sa.Column("statement_row_hash", sa.String(length=64), nullable=True),
        )
    if "created_at" not in columns:
        op.add_column(
            "finance_transaction",
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("finance_transaction")}
    uniques = {constraint["name"] for constraint in inspector.get_unique_constraints("finance_transaction")}

    if "ix_finance_transaction_source" not in indexes:
        op.create_index("ix_finance_transaction_source", "finance_transaction", ["source"], unique=False)
    if "ix_finance_transaction_statement_hash" not in indexes:
        op.create_index("ix_finance_transaction_statement_hash", "finance_transaction", ["statement_hash"], unique=False)
    if "ix_finance_transaction_statement_row_hash" not in indexes:
        op.create_index(
            "ix_finance_transaction_statement_row_hash",
            "finance_transaction",
            ["statement_row_hash"],
            unique=False,
        )
    if "uq_finance_statement_row" not in uniques:
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("finance_transaction") as batch_op:
                batch_op.create_unique_constraint(
                    "uq_finance_statement_row",
                    ["user_id", "statement_hash", "statement_row_hash"],
                )
        else:
            op.create_unique_constraint(
                "uq_finance_statement_row",
                "finance_transaction",
                ["user_id", "statement_hash", "statement_row_hash"],
            )

    if bind.dialect.name != "sqlite":
        op.alter_column("finance_transaction", "source", server_default=None)
        op.alter_column("finance_transaction", "created_at", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "finance_transaction" not in set(inspector.get_table_names()):
        return

    indexes = {index["name"] for index in inspector.get_indexes("finance_transaction")}
    uniques = {constraint["name"] for constraint in inspector.get_unique_constraints("finance_transaction")}
    columns = {column["name"] for column in inspector.get_columns("finance_transaction")}

    if "uq_finance_statement_row" in uniques:
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("finance_transaction") as batch_op:
                batch_op.drop_constraint("uq_finance_statement_row", type_="unique")
        else:
            op.drop_constraint("uq_finance_statement_row", "finance_transaction", type_="unique")
    if "ix_finance_transaction_statement_row_hash" in indexes:
        op.drop_index("ix_finance_transaction_statement_row_hash", table_name="finance_transaction")
    if "ix_finance_transaction_statement_hash" in indexes:
        op.drop_index("ix_finance_transaction_statement_hash", table_name="finance_transaction")
    if "ix_finance_transaction_source" in indexes:
        op.drop_index("ix_finance_transaction_source", table_name="finance_transaction")

    if "created_at" in columns:
        op.drop_column("finance_transaction", "created_at")
    if "statement_row_hash" in columns:
        op.drop_column("finance_transaction", "statement_row_hash")
    if "statement_hash" in columns:
        op.drop_column("finance_transaction", "statement_hash")
    if "source" in columns:
        op.drop_column("finance_transaction", "source")
    if "balance" in columns:
        op.drop_column("finance_transaction", "balance")
