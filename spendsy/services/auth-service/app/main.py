from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes_auth import router as auth_router
from .api.routes_health import router as health_router

import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("auth.main")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


origins = [
    "http://localhost:5173",
    "http://localhost:5174",
]

app = FastAPI(title="Spendsy Auth Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Catch all unhandled database exceptions and return a standardized 500 response."""
    logger.exception("Database error occurred: %s", str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": "database_error",
            "message": "A database operation failed",
            "meta": {}
        },
    )


app.include_router(health_router)
app.include_router(auth_router)
