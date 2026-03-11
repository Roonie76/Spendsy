from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

from .api.routes_health import router as health_router
from .api.routes_parser import router as parser_router

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
]

app = FastAPI(title="Spendsy Parser Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(parser_router)

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.exception("Database error occurred: %s", str(exc))
    return JSONResponse(
        status_code=500,
        content={"ok": False, "message": "A database error occurred", "error": "Internal Server Error"},
    )
