from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes_ai import router as ai_router
from .api.routes_chat import router as chat_router

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
]

app = FastAPI(title="SmartSpend AI Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)
app.include_router(chat_router)
