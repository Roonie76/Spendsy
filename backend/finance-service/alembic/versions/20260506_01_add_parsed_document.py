"""add ParsedDocument table

Revision ID: 20260506_01
Revises: 20260503_02
Create Date: 2026-05-06
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260506_01"
down_revision = "20260503_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "finance_parsed_document",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("ay", sa.String(7), nullable=False, server_default="2025-26"),

        sa.Column("doc_type", sa.String(30), nullable=False),
        sa.Column("filename", sa.String(255), nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True),

        sa.Column("parsed_data", JSONB, nullable=True, server_default="{}"),
        sa.Column("parse_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("parse_error", sa.String(500), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("field_confidence", JSONB, nullable=True, server_default="{}"),

        sa.Column("parser_version", sa.String(20), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("ocr_used", sa.Boolean(), nullable=False, server_default="false"),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),

        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_finance_parsed_document_id",            "finance_parsed_document", ["id"])
    op.create_index("ix_finance_parsed_document_user_id",       "finance_parsed_document", ["user_id"])
    op.create_index("ix_finance_parsed_document_file_hash",     "finance_parsed_document", ["file_hash"])


def downgrade() -> None:
    op.drop_table("finance_parsed_document")
