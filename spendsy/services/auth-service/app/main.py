from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes_auth import router as auth_router
from app.api.routes_health import router as health_router

logger = logging.getLogger("auth.main")

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(title="Spendsy Auth Service", lifespan=lifespan)

# Register CORS before routers so preflight OPTIONS requests are handled
# for cookie-based auth flows from the Vite frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    logger.exception("Database error occurred: %s", str(exc))
    return JSONResponse(
        status_code=503,
        content={
            "error": "database_error",
            "message": "Authentication database unavailable",
        },
    )


app.include_router(health_router)
app.include_router(auth_router, prefix="/auth")
