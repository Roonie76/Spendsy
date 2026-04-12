from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    context: dict
    history: list[dict]


class HealthResponse(BaseModel):
    status: str
    service: str


class AIRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=15000)
    context: dict | list | str | None = None
    response_format: str = Field(default="text", pattern="^(text|json)$")
    image: str | None = None
    image_mime_type: str | None = None # e.g. "image/png", "application/pdf"



class AIResponse(BaseModel):
    status: str
    output: str | dict | list
    raw: str | None = None
