"""add transaction fingerprint column and index

Revision ID: 20260310_04
Revises: 20260310_03
Create Date: 2026-03-10 23:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260310_04"
down_revision = "20260310_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "finance_transaction" not in set(inspector.get_table_names()):
        return

    columns = {column["name"] for column in inspector.get_columns("finance_transaction")}
    if "fingerprint" not in columns:
        op.add_column("finance_transaction", sa.Column("fingerprint", sa.String(length=64), nullable=True))

    index_names = {index["name"] for index in inspector.get_indexes("finance_transaction")}
    if "idx_finance_txn_fingerprint" in index_names:
        return

    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.create_index(
                "idx_finance_txn_fingerprint",
                "finance_transaction",
                ["user_id", "fingerprint"],
                unique=False,
                postgresql_concurrently=True,
            )
    else:
        op.create_index(
            "idx_finance_txn_fingerprint",
            "finance_transaction",
            ["user_id", "fingerprint"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "finance_transaction" not in set(inspector.get_table_names()):
        return

    index_names = {index["name"] for index in inspector.get_indexes("finance_transaction")}
    if "idx_finance_txn_fingerprint" in index_names:
        if bind.dialect.name == "postgresql":
            with op.get_context().autocommit_block():
                op.drop_index(
                    "idx_finance_txn_fingerprint",
                    table_name="finance_transaction",
                    postgresql_concurrently=True,
                )
        else:
            op.drop_index("idx_finance_txn_fingerprint", table_name="finance_transaction")

    columns = {column["name"] for column in inspector.get_columns("finance_transaction")}
    if "fingerprint" in columns:
        op.drop_column("finance_transaction", "fingerprint")
