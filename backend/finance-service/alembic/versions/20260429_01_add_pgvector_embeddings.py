"""Add pgvector embedding columns to transaction and document tables

Revision ID: 20260429_01
Revises: 20260424_03
Create Date: 2026-04-29

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260429_01'
down_revision = '20260424_03'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure the pgvector extension is available
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add embedding column to finance_transaction
    op.execute(
        "ALTER TABLE finance_transaction ADD COLUMN IF NOT EXISTS embedding vector(768)"
    )

    # Add embedding column to finance_document
    op.execute(
        "ALTER TABLE finance_document ADD COLUMN IF NOT EXISTS embedding vector(768)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE finance_document DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE finance_transaction DROP COLUMN IF EXISTS embedding")
