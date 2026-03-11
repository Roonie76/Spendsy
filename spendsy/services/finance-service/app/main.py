from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes_finance import router as finance_router
from .api.routes_internal import router as internal_router
from .core.middleware import RequestLoggingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


origins = [
    "http://localhost:5173",
]

app = FastAPI(title="Spendsy Finance Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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


app.include_router(finance_router)
app.include_router(internal_router)
