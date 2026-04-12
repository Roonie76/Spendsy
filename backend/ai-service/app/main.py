from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
import logging
from .api.routes_ai import router as ai_router
from .api.routes_chat import router as chat_router

logger = logging.getLogger(__name__)

from app.core.config import settings

app = FastAPI(title="Spendsy AI Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)
app.include_router(chat_router)

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.exception("Database error occurred: %s", str(exc))
    return JSONResponse(
        status_code=500,
        content={"ok": False, "message": "A database error occurred", "error": "Internal Server Error"},
    )
