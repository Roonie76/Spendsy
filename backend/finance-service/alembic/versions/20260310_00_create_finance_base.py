"""create finance base schema

Revision ID: 20260310_00
Revises:
Create Date: 2026-03-10 22:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260310_00"
down_revision = None
branch_labels = None
depends_on = None


def _json_type() -> sa.types.TypeEngine:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "finance_userprofile" not in tables:
        op.create_table(
            "finance_userprofile",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("monthlyIncome", sa.Numeric(15, 2), nullable=True, server_default="0"),
            sa.Column("monthlyBudget", sa.Numeric(15, 2), nullable=True, server_default="0"),
            sa.Column("dailyBudget", sa.Numeric(15, 2), nullable=True, server_default="0"),
            sa.Column("is_business", sa.Boolean(), nullable=True, server_default=sa.false()),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.UniqueConstraint("user_id"),
        )
        op.create_index("ix_finance_userprofile_user_id", "finance_userprofile", ["user_id"], unique=True)

    if "finance_transaction" not in tables:
        op.create_table(
            "finance_transaction",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("type", sa.String(length=10), nullable=False),
            sa.Column("category", sa.String(length=100), nullable=True, server_default="other"),
            sa.Column("date", sa.Date(), nullable=True),
            sa.Column("is_recurring", sa.Boolean(), nullable=True, server_default=sa.false()),
        )
        op.create_index("ix_finance_transaction_user_id", "finance_transaction", ["user_id"], unique=False)

    if "finance_wealthitem" not in tables:
        op.create_table(
            "finance_wealthitem",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("title", sa.String(length=100), nullable=False),
            sa.Column("amount", sa.Numeric(15, 2), nullable=False),
            sa.Column("type", sa.String(length=10), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=True, server_default="General"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
        op.create_index("ix_finance_wealthitem_user_id", "finance_wealthitem", ["user_id"], unique=False)

    if "finance_taxprofile" not in tables:
        op.create_table(
            "finance_taxprofile",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("is_business", sa.Boolean(), nullable=True, server_default=sa.false()),
            sa.Column("annual_rent", sa.Numeric(12, 2), nullable=True, server_default="0"),
            sa.Column("annual_epf", sa.Numeric(12, 2), nullable=True, server_default="0"),
            sa.Column("nps_contribution", sa.Numeric(12, 2), nullable=True, server_default="0"),
            sa.Column("health_insurance_self", sa.Numeric(12, 2), nullable=True, server_default="0"),
            sa.Column("health_insurance_parents", sa.Numeric(12, 2), nullable=True, server_default="0"),
            sa.Column("home_loan_interest", sa.Numeric(12, 2), nullable=True, server_default="0"),
            sa.Column("education_loan_interest", sa.Numeric(12, 2), nullable=True, server_default="0"),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.UniqueConstraint("user_id"),
        )
        op.create_index("ix_finance_taxprofile_user_id", "finance_taxprofile", ["user_id"], unique=True)

    if "finance_itrdata" not in tables:
        op.create_table(
            "finance_itrdata",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("income_data", _json_type(), nullable=True, server_default=sa.text("'{}'")),
            sa.Column("deductions_data", _json_type(), nullable=True, server_default=sa.text("'{}'")),
            sa.Column("filing_details", _json_type(), nullable=True, server_default=sa.text("'{}'")),
            sa.Column("tax_regime", sa.String(length=10), nullable=True, server_default="new"),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.UniqueConstraint("user_id"),
        )
        op.create_index("ix_finance_itrdata_user_id", "finance_itrdata", ["user_id"], unique=True)

    if "finance_apiauditlog" not in tables:
        op.create_table(
            "finance_apiauditlog",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=True),
            sa.Column("request_id", sa.String(length=64), nullable=True),
            sa.Column("action", sa.String(length=64), nullable=True),
            sa.Column("resource_type", sa.String(length=64), nullable=True),
            sa.Column("resource_id", sa.String(length=64), nullable=True, server_default=""),
            sa.Column("method", sa.String(length=10), nullable=True),
            sa.Column("path", sa.String(length=255), nullable=True),
            sa.Column("status_code", sa.Integer(), nullable=True),
            sa.Column("error_code", sa.String(length=64), nullable=True, server_default=""),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.Column("details", _json_type(), nullable=True, server_default=sa.text("'{}'")),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
        op.create_index("ix_finance_apiauditlog_request_id", "finance_apiauditlog", ["request_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "finance_apiauditlog" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("finance_apiauditlog")}
        if "ix_finance_apiauditlog_request_id" in indexes:
            op.drop_index("ix_finance_apiauditlog_request_id", table_name="finance_apiauditlog")
        op.drop_table("finance_apiauditlog")

    if "finance_itrdata" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("finance_itrdata")}
        if "ix_finance_itrdata_user_id" in indexes:
            op.drop_index("ix_finance_itrdata_user_id", table_name="finance_itrdata")
        op.drop_table("finance_itrdata")

    if "finance_taxprofile" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("finance_taxprofile")}
        if "ix_finance_taxprofile_user_id" in indexes:
            op.drop_index("ix_finance_taxprofile_user_id", table_name="finance_taxprofile")
        op.drop_table("finance_taxprofile")

    if "finance_wealthitem" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("finance_wealthitem")}
        if "ix_finance_wealthitem_user_id" in indexes:
            op.drop_index("ix_finance_wealthitem_user_id", table_name="finance_wealthitem")
        op.drop_table("finance_wealthitem")

    if "finance_transaction" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("finance_transaction")}
        if "ix_finance_transaction_user_id" in indexes:
            op.drop_index("ix_finance_transaction_user_id", table_name="finance_transaction")
        op.drop_table("finance_transaction")

    if "finance_userprofile" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("finance_userprofile")}
        if "ix_finance_userprofile_user_id" in indexes:
            op.drop_index("ix_finance_userprofile_user_id", table_name="finance_userprofile")
        op.drop_table("finance_userprofile")
