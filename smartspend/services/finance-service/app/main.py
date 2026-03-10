from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes_finance import router as finance_router
from .api.routes_internal import router as internal_router
from .core.database import Base, engine
from .core.middleware import RequestLoggingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
]

app = FastAPI(title="SmartSpend Finance Service")

# Observability: request ID generation and structured access logging
app.add_middleware(RequestLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
