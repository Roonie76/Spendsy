from __future__ import annotations

from datetime import date
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

class ParsedTransaction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    description: str
    amount: float
    type: Literal["income", "expense"]
    debit: float | None = None
    credit: float | None = None
    balance: float | None = None
    confidence: float | None = None
    source: Literal["statement"] = "statement"
    is_valid: bool = True
    # Validation flags attached by the validator (e.g. ["DUPLICATE", "LOW_CONFIDENCE"])
    validation_flags: list[str] = Field(default_factory=list)
    # Spending category assigned by the categorizer (e.g. "Food & Dining")
    category: str | None = None

class ParserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    reconciliation_score: float
    transactions: list[ParsedTransaction]
    error: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class TransactionFeedback(BaseModel):
    transaction_id: str
    user_id: str
    correction_data: dict[str, Any]
    reason: str | None = None
