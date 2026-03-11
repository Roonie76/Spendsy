"""add semantic dedupe index on finance_transaction

Revision ID: 20260310_03
Revises: 20260310_02
Create Date: 2026-03-10 21:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260310_03"
down_revision = "20260310_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "finance_transaction" not in set(inspector.get_table_names()):
        return

    index_names = {index["name"] for index in inspector.get_indexes("finance_transaction")}
    if "idx_finance_txn_semantic_dedupe" in index_names:
        return

    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.create_index(
                "idx_finance_txn_semantic_dedupe",
                "finance_transaction",
                ["user_id", "date", "amount", "type", "title"],
                unique=False,
                postgresql_concurrently=True,
            )
    else:
        op.create_index(
            "idx_finance_txn_semantic_dedupe",
            "finance_transaction",
            ["user_id", "date", "amount", "type", "title"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "finance_transaction" not in set(inspector.get_table_names()):
        return

    index_names = {index["name"] for index in inspector.get_indexes("finance_transaction")}
    if "idx_finance_txn_semantic_dedupe" not in index_names:
        return

    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.drop_index(
                "idx_finance_txn_semantic_dedupe",
                table_name="finance_transaction",
                postgresql_concurrently=True,
            )
    else:
        op.drop_index("idx_finance_txn_semantic_dedupe", table_name="finance_transaction")
