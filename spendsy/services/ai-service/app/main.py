from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

from app.api.routes_ai import router as ai_router
from app.api.routes_chat import router as chat_router

app = FastAPI(title="Spendsy AI Service")

app.include_router(ai_router)
app.include_router(chat_router)

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.exception("Database error occurred: %s", str(exc))
    return JSONResponse(
        status_code=500,
        content={"ok": False, "message": "A database error occurred", "error": "Internal Server Error"},
    )
