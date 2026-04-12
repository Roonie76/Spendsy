"""add email unique index

Revision ID: 20260316_00
Revises: 20260310_00
Create Date: 2026-03-16 15:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260316_00"
down_revision = "20260310_00"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("auth_user")}
    if "ix_auth_user_email_unique" in indexes:
        return

    if bind.dialect.name == "sqlite":
        op.create_index(
            "ix_auth_user_email_unique",
            "auth_user",
            ["email"],
            unique=True,
            sqlite_where=sa.text("email != ''"),
        )
    else:
        op.create_index(
            "ix_auth_user_email_unique",
            "auth_user",
            ["email"],
            unique=True,
            postgresql_where=sa.text("email != ''"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("auth_user")}
    if "ix_auth_user_email_unique" in indexes:
        op.drop_index("ix_auth_user_email_unique", table_name="auth_user")
