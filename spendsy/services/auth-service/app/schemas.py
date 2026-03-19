from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from pydantic import BaseModel, EmailStr, Field, field_validator

PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$"
)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    email: EmailStr | None = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not PASSWORD_PATTERN.match(v):
            raise ValueError(
                "Password must be at least 8 characters and contain "
                "at least one uppercase letter, one lowercase letter, and one digit."
            )
        return v


class UserLogin(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    password: str = Field(min_length=1, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    uid: str
    username: str
    email: EmailStr | None
    created_at: datetime

    @field_validator("email", mode="before")
    @classmethod
    def empty_to_none(cls, v: Any) -> Any:
        if v == "":
            return None
        return v


class AuthResponse(BaseModel):
    user: UserOut
    tokens: TokenPair


class RefreshRequest(BaseModel):
    refresh_token: str


class HealthResponse(BaseModel):
    status: str
    service: str
