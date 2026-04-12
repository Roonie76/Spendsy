from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text

from app.core.database import Base


class User(Base):
    """
    Mirrors Django's auth_user table to preserve existing data.
    """
    __tablename__ = "auth_user"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    uid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    password = Column(String(128), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    is_superuser = Column(Boolean, nullable=False, default=False)
    username = Column(String(150), nullable=False, unique=True, index=True)
    first_name = Column(String(150), nullable=False, default="")
    last_name = Column(String(150), nullable=False, default="")
    email = Column(String(254), nullable=False, default="")
    is_staff = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    role = Column(String(20), nullable=False, default="user")  # 'admin', 'user', 'staff'
    date_joined = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("username", name="auth_user_username_key"),
        Index(
            "ix_auth_user_email_unique",
            "email",
            unique=True,
            postgresql_where=text("email != ''"),
            sqlite_where=text("email != ''"),
        ),
    )


class ApiAuditLog(Base):
    __tablename__ = "auth_apiauditlog"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, nullable=True)
    request_id = Column(String(64), index=True)
    action = Column(String(64))
    resource_type = Column(String(64))
    resource_id = Column(String(64), default="")
    method = Column(String(10))
    path = Column(String(255))
    status_code = Column(Integer)
    error_code = Column(String(64), default="")
    ip_address = Column(String(64), nullable=True)
    details = Column(Text, default="{}")  # SQLite/Generic fallback
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class SecurityAlert(Base):
    __tablename__ = "auth_securityalert"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    type = Column(String(32))  # 'brute_force', 'unusual_data_access', etc.
    severity = Column(String(16))  # 'low', 'medium', 'high', 'critical'
    description = Column(String(255))
    actor_identity = Column(String(64), nullable=True, index=True)  # IP or UserID
    details = Column(Text, default="{}")
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class RefreshToken(Base):
    __tablename__ = "auth_refreshtoken"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, ForeignKey("auth_user.id", ondelete="CASCADE"), nullable=False, index=True)
    jti = Column(String(64), unique=True, index=True, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
