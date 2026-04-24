"""add tora_feedback table for thumbs up/down on TORA responses

Revision ID: 20260424_01
Revises: 20260423_01
Create Date: 2026-04-24 12:00:00.000000

Creates `tora_feedback` — one row per rating event. Designed append-only:
the aggregation query reads the latest row per (user_id, message_id),
so users can change their vote by re-submitting.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260424_01"
down_revision = "20260423_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "tora_feedback" in tables:
        return

    op.create_table(
        "tora_feedback",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("message_id", sa.BigInteger(), nullable=True, index=True),
        sa.Column("client_message_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("rating", sa.String(length=8), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=True),
        sa.Column("comment", sa.String(length=500), nullable=True),
        sa.Column("prompt", sa.String(length=500), nullable=True),
        sa.Column("response_preview", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_tora_feedback_user_created",
        "tora_feedback",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "tora_feedback" not in tables:
        return
    op.drop_index("idx_tora_feedback_user_created", table_name="tora_feedback")
    op.drop_table("tora_feedback")
