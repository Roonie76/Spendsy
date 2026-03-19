from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException, Response
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "spendsy")
os.environ.setdefault("DB_USER", "smartuser")
os.environ.setdefault("DB_PASSWORD", "smartpass")
os.environ.setdefault("JWT_SECRET", "test-secret")

from app.api import routes_auth
from app.core import security
from app.core.database import Base
from app.models import User
from app.schemas import UserCreate, UserLogin


@pytest.fixture(autouse=True)
def stub_auth_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(routes_auth, "is_rate_limited", lambda *args, **kwargs: False)
    monkeypatch.setattr(routes_auth, "record_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes_auth, "get_identity_from_request", lambda request: "127.0.0.1")


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def make_request() -> Request:
    return Request(
        {
            "type": "http",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }
    )


def create_user(
    db_session,
    *,
    username: str = "alice",
    email: str = "alice@example.com",
    password: str = "Password1",
) -> User:
    user = User(
        username=username,
        email=email,
        password=security.hash_password(password),
        first_name="",
        last_name="",
        is_staff=False,
        is_superuser=False,
        is_active=True,
        date_joined=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_register_rejects_username_duplicates_after_trimming(db_session) -> None:
    create_user(db_session, username="alice", email="alice@example.com")

    with pytest.raises(HTTPException) as exc_info:
        routes_auth.register(
            UserCreate(username=" Alice ", email="new@example.com", password="Password1"),
            make_request(),
            Response(),
            db_session,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Username already exists"


def test_register_rejects_duplicate_email_case_insensitively(db_session) -> None:
    create_user(db_session, username="alice", email="alice@example.com")

    with pytest.raises(HTTPException) as exc_info:
        routes_auth.register(
            UserCreate(username="bob", email="ALICE@EXAMPLE.COM", password="Password1"),
            make_request(),
            Response(),
            db_session,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Email already exists"


def test_register_returns_specific_conflict_after_integrity_error(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conflict_details = iter([None, "Email already exists"])

    monkeypatch.setattr(
        routes_auth,
        "_get_registration_conflict_detail",
        lambda *args, **kwargs: next(conflict_details),
    )
    monkeypatch.setattr(
        db_session,
        "commit",
        lambda: (_ for _ in ()).throw(IntegrityError("INSERT", {}, Exception("duplicate key"))),
    )

    with pytest.raises(HTTPException) as exc_info:
        routes_auth.register(
            UserCreate(username="bob", email="bob@example.com", password="Password1"),
            make_request(),
            Response(),
            db_session,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Email already exists"


def test_login_accepts_trimmed_username_lookup(db_session) -> None:
    existing_user = create_user(db_session, username="alice", email="alice@example.com")

    result = routes_auth.login(
        UserLogin(username=" Alice ", password="Password1"),
        make_request(),
        Response(),
        db_session,
    )

    assert result.user.id == existing_user.id
    assert result.user.username == "alice"


def test_login_returns_human_readable_error_message(db_session) -> None:
    result = routes_auth.login(
        UserLogin(username="unknown", password="Password1"),
        make_request(),
        Response(),
        db_session,
    )

    assert result.status_code == 401
    assert result.body == (
        b'{"error":"authentication_failed","detail":"Invalid username/email or password",'
        b'"message":"Invalid username/email or password"}'
    )
