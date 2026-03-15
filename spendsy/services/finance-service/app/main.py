from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes_finance import router as finance_router
from app.api.routes_internal import router as internal_router
from app.api.routes_goals import router as goals_router
from app.core.middleware import RequestLoggingMiddleware
from sqlalchemy.exc import SQLAlchemyError


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("finance.main")

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(title="Spendsy Finance Service", lifespan=lifespan)

# Allow the Vite frontend to call finance-service directly during local dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Observability: request ID generation and structured access logging
app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return structured JSON for Pydantic validation failures."""
    errors = []
    for e in exc.errors():
        errors.append({"field": ".".join(str(x) for x in e["loc"]), "message": e["msg"]})
    return JSONResponse(
        status_code=422,
        content={
            "ok": False,
            "error": "VALIDATION_ERROR",
            "message": "Invalid request payload",
            "details": errors,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Catch unhandled SQLAlchemy failures so DB issues surface as structured JSON
    instead of opaque FastAPI 500 pages.
    """
    logger.exception("Database error occurred on %s: %s", request.url.path, str(exc))
    error_text = str(exc).lower()
    message = "A database operation failed"
    details = None

    if any(token in error_text for token in ("does not exist", "undefined table", "no such table", "undefined column")):
        message = "Finance database schema is missing or out of date"
        details = {
            "hint": "Run `alembic upgrade head` in spendsy/services/finance-service",
        }

    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": "database_error",
            "message": message,
            "meta": {
                "request_id": getattr(request.state, "request_id", None),
            },
            **({"details": details} if details else {}),
        },
    )

app.include_router(finance_router)
app.include_router(internal_router)
app.include_router(goals_router)
