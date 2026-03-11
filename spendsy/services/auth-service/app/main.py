from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes_auth import router as auth_router
from .api.routes_health import router as health_router

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

app.include_router(health_router)
app.include_router(auth_router)
