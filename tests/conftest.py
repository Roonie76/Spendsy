import atexit
import os
import sys
import importlib
import importlib.util
import types
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICES_ROOT = REPO_ROOT / "smartspend" / "services"
TEST_DB_PATH = REPO_ROOT / "tests" / "test.db"

ENV_FILE_PATH = REPO_ROOT / ".env"
_ENV_FILE_BACKUP = None
if ENV_FILE_PATH.exists():
    _ENV_FILE_BACKUP = REPO_ROOT / ".env.test-backup"
    if _ENV_FILE_BACKUP.exists():
        _ENV_FILE_BACKUP.unlink()
    ENV_FILE_PATH.rename(_ENV_FILE_BACKUP)


def _restore_env_file() -> None:
    if _ENV_FILE_BACKUP and _ENV_FILE_BACKUP.exists():
        _ENV_FILE_BACKUP.rename(ENV_FILE_PATH)


atexit.register(_restore_env_file)


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **_kwargs) -> str:
    """Render JSONB as JSON when using SQLite for tests."""
    return "JSON"


class _DummyRedisClient:
    """Simple in-memory Redis replacement for tests."""

    def __init__(self) -> None:
        self._store: dict[str, list[str]] = defaultdict(list)

    @classmethod
    def from_url(cls, *args, **kwargs):
        return cls()

    def rpush(self, key: str, value: str) -> int:
        self._store[key].append(value)
        return len(self._store[key])

    def lrange(self, key: str, start: int, stop: int) -> list[str]:
        items = self._store.get(key, [])
        if not items:
            return []
        length = len(items)
        if start < 0:
            start = max(length + start, 0)
        if stop < 0:
            stop = length + stop
        stop = min(stop, length - 1)
        if stop < 0 or stop < start:
            return []
        return items[start : stop + 1]

    def ltrim(self, key: str, start: int, stop: int) -> None:
        self._store[key] = self.lrange(key, start, stop)

    def delete(self, key: str) -> int:
        return int(self._store.pop(key, None) is not None)

    def pipeline(self):
        return _DummyRedisPipeline(self)


class _DummyRedisPipeline:
    def __init__(self, client):
        self.client = client
        self.commands = []

    def incr(self, key: str, amount: int = 1):
        self.commands.append(("incr", key, amount))
        return self

    def ttl(self, key: str):
        self.commands.append(("ttl", key))
        return self

    def execute(self) -> list:
        results = []
        for cmd in self.commands:
            action, key, *args = cmd
            if action == "incr":
                amount = args[0]
                items = self.client._store.get(key, [])
                if not items:
                    self.client._store[key] = ["0"]
                current = int(self.client._store[key][-1])
                new_val = current + amount
                self.client._store[key][-1] = str(new_val)
                results.append(new_val)
            elif action == "ttl":
                results.append(-1)
        self.commands = []
        return results


redis_mod = types.ModuleType("redis")
redis_mod.Redis = _DummyRedisClient
sys.modules.setdefault("redis", redis_mod)

rq_mod = types.ModuleType("rq")

class _QueueStub:
    def __init__(self, *args, **kwargs):
        self.tasks: list[tuple] = []

    def enqueue(self, func_path: str, *args, **kwargs):
        self.tasks.append((func_path, args, kwargs))

rq_mod.Queue = _QueueStub
sys.modules.setdefault("rq", rq_mod)


def _set_env_case(key: str, value: str) -> None:
    os.environ.setdefault(key.upper(), value)
    os.environ.setdefault(key.lower(), value)

# --- Global test environment ---
# We set these before importing any service modules so pydantic Settings picks them up.
_set_env_case("database_url", f"sqlite+pysqlite:///{TEST_DB_PATH}?check_same_thread=false")
_set_env_case("db_host", "localhost")
_set_env_case("db_name", "test")
_set_env_case("db_user", "test")
_set_env_case("db_password", "test")
_set_env_case("jwt_secret", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key")
os.environ.setdefault("FINANCE_SERVICE_URL", "http://test-finance")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

_SERVICE_CACHE: dict[str, dict] = {}


def load_service(service_dir: str) -> dict:
    """
    Load a service's FastAPI app as an isolated Python package.
    This avoids name conflicts because each service folder uses 'app' as the package name.
    """
    if service_dir in _SERVICE_CACHE:
        return _SERVICE_CACHE[service_dir]

    app_dir = SERVICES_ROOT / service_dir / "app"
    package_name = f"{service_dir.replace('-', '_')}_app"

    if package_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            package_name,
            app_dir / "__init__.py",
            submodule_search_locations=[str(app_dir)],
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[package_name] = module
        spec.loader.exec_module(module)

    main = importlib.import_module(f"{package_name}.main")
    _SERVICE_CACHE[service_dir] = {"package": package_name, "app": main.app}
    return _SERVICE_CACHE[service_dir]


@pytest.fixture(scope="session")
def auth_service():
    return load_service("auth-service")


@pytest.fixture(scope="session")
def finance_service():
    return load_service("finance-service")


@pytest.fixture(scope="session")
def ai_service():
    return load_service("ai-service")


@pytest.fixture
def auth_client(auth_service):
    with TestClient(auth_service["app"]) as client:
        yield client


@pytest.fixture
def finance_client(finance_service):
    with TestClient(finance_service["app"]) as client:
        yield client


@pytest.fixture
def ai_client(ai_service):
    with TestClient(ai_service["app"]) as client:
        yield client


@pytest.fixture(autouse=True)
def reset_databases(auth_service, finance_service):
    """Make sure each test starts with a clean database."""
    auth_pkg = auth_service["package"]
    finance_pkg = finance_service["package"]

    auth_db = importlib.import_module(f"{auth_pkg}.core.database")
    finance_db = importlib.import_module(f"{finance_pkg}.core.database")

    auth_db.Base.metadata.drop_all(bind=auth_db.engine)
    finance_db.Base.metadata.drop_all(bind=finance_db.engine)
    auth_db.Base.metadata.create_all(bind=auth_db.engine)
    finance_db.Base.metadata.create_all(bind=finance_db.engine)

    yield


@pytest.fixture(autouse=True)
def mock_redis_dependencies(monkeypatch, auth_service, finance_service):
    """Disable Redis calls so tests can run without a real Redis server."""
    auth_pkg = auth_service["package"]
    finance_pkg = finance_service["package"]

    auth_redis = importlib.import_module(f"{auth_pkg}.core.redis")
    finance_redis = importlib.import_module(f"{finance_pkg}.core.redis")

    monkeypatch.setattr(auth_redis, "is_rate_limited", lambda *args, **kwargs: False)
    monkeypatch.setattr(auth_redis, "record_audit_event", lambda *args, **kwargs: None)

    monkeypatch.setattr(finance_redis, "is_rate_limited", lambda *args, **kwargs: False)
    monkeypatch.setattr(finance_redis, "record_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(finance_redis, "enqueue_task", lambda *args, **kwargs: None)


@pytest.fixture
def access_token():
    """Create a valid JWT access token for finance/AI endpoints."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "1",
        "username": "tester",
        "email": "tester@example.com",
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=30)).timestamp()),
    }
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=os.environ["JWT_ALGORITHM"])
