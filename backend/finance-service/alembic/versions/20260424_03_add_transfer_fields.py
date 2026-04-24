"""add transfer_group_id + is_transfer to finance_transaction

Revision ID: 20260424_03
Revises: 20260424_02
Create Date: 2026-04-24 13:00:00.000000

Adds fields used to mark inter-account transfers (e.g. credit card bill
payment from debit account) so dashboards can exclude them from spend/income
aggregations without losing them from the ledger.

- transfer_group_id: shared UUID across the two sides of a transfer pair;
  NULL for non-transfers.
- is_transfer: convenience flag for aggregation filters. Indexed.

Existing rows are not reclassified; both columns default to non-transfer.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260424_03"
down_revision = "20260424_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("finance_transaction")}

    if "transfer_group_id" not in cols:
        op.add_column(
            "finance_transaction",
            sa.Column("transfer_group_id", sa.String(length=36), nullable=True),
        )
        op.create_index(
            "idx_finance_txn_transfer_group",
            "finance_transaction",
            ["transfer_group_id"],
        )

    if "is_transfer" not in cols:
        op.add_column(
            "finance_transaction",
            sa.Column(
                "is_transfer",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
        op.create_index(
            "idx_finance_txn_is_transfer",
            "finance_transaction",
            ["user_id", "is_transfer"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {i["name"] for i in inspector.get_indexes("finance_transaction")}
    cols = {c["name"] for c in inspector.get_columns("finance_transaction")}

    if "idx_finance_txn_is_transfer" in indexes:
        op.drop_index("idx_finance_txn_is_transfer", table_name="finance_transaction")
    if "is_transfer" in cols:
        op.drop_column("finance_transaction", "is_transfer")

    if "idx_finance_txn_transfer_group" in indexes:
        op.drop_index("idx_finance_txn_transfer_group", table_name="finance_transaction")
    if "transfer_group_id" in cols:
        op.drop_column("finance_transaction", "transfer_group_id")
