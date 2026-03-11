"""create auth base schema

Revision ID: 20260310_00
Revises:
Create Date: 2026-03-10 22:05:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260310_00"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "auth_user" not in tables:
        op.create_table(
            "auth_user",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("password", sa.String(length=128), nullable=False),
            sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("username", sa.String(length=150), nullable=False),
            sa.Column("first_name", sa.String(length=150), nullable=False, server_default=""),
            sa.Column("last_name", sa.String(length=150), nullable=False, server_default=""),
            sa.Column("email", sa.String(length=254), nullable=False, server_default=""),
            sa.Column("is_staff", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "date_joined",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.UniqueConstraint("username", name="auth_user_username_key"),
        )
        op.create_index("ix_auth_user_username", "auth_user", ["username"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "auth_user" in set(inspector.get_table_names()):
        indexes = {index["name"] for index in inspector.get_indexes("auth_user")}
        if "ix_auth_user_username" in indexes:
            op.drop_index("ix_auth_user_username", table_name="auth_user")
        op.drop_table("auth_user")
