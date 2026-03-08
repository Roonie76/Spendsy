from __future__ import annotations

from datetime import date as dt_date, date
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class TransactionCategory(str, Enum):
    food = "food"
    rent = "rent"
    travel = "travel"
    shopping = "shopping"
    utilities = "utilities"
    investment = "investment"
    other = "other"


class HealthResponse(BaseModel):
    status: str
    service: str


class ErrorResponse(BaseModel):
    ok: bool = False
    error: str
    message: str
    meta: dict
    details: dict | None = None


class UserProfilePayload(BaseModel):
    monthly_income: Decimal | None = Field(default=None, alias="monthlyIncome", ge=0)
    monthly_budget: Decimal | None = Field(default=None, alias="monthlyBudget", ge=0)
    daily_budget: Decimal | None = Field(default=None, alias="dailyBudget", ge=0)
    is_business: bool | None = Field(default=None, alias="is_business")
    email: str | None = None

    class Config:
        populate_by_name = True


class TransactionPayload(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    amount: Decimal | None = None
    type: str | None = None
    category: TransactionCategory | None = None
    date: dt_date | None = None
    is_recurring: bool | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in {"income", "expense"}:
            raise ValueError("Transaction type must be 'income' or 'expense'")
        return normalized

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: dt_date | None) -> dt_date | None:
        if v is not None and v > date.today():
            raise ValueError("Transaction date cannot be in the future")
        return v


class TransactionOut(BaseModel):
    id: int
    title: str
    amount: Decimal
    type: str
    category: str
    date: dt_date
    is_recurring: bool


class PaginatedTransactions(BaseModel):
    data: list[TransactionOut]
    next_cursor: str | None


class WealthPayload(BaseModel):
    title: str | None = None
    name: str | None = None
    amount: Decimal | None = None
    type: str | None = None
    category: str | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in {"asset", "liability"}:
            raise ValueError("Wealth type must be 'asset' or 'liability'")
        return normalized


class WealthOut(BaseModel):
    id: int
    title: str
    amount: Decimal
    type: str
    category: str


class TaxProfilePayload(BaseModel):
    isBusiness: Optional[bool] = None
    annualRent: Optional[Decimal] = None
    annualEPF: Optional[Decimal] = None
    npsContribution: Optional[Decimal] = None
    healthInsuranceSelf: Optional[Decimal] = None
    healthInsuranceParents: Optional[Decimal] = None
    homeLoanInterest: Optional[Decimal] = None
    educationLoanInterest: Optional[Decimal] = None


class ITRPayload(BaseModel):
    income_data: dict[str, Any] | None = None
    deductions_data: dict[str, Any] | None = None
    filing_details: dict[str, Any] | None = None
    tax_regime: str | None = None

    @field_validator("tax_regime")
    @classmethod
    def validate_tax_regime(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in {"new", "old"}:
            raise ValueError("tax_regime must be 'new' or 'old'")
        return normalized


class ParsedTransaction(BaseModel):
    id: str
    date: str
    description: str
    amount: Decimal
    type: str
    category: str
    confidence: int
    bank: str
    balance: Decimal | None
    is_valid: bool


class ParserMeta(BaseModel):
    count: int
    method: str
    checksum_verified: bool
    warnings: list[str]
    errors: list[str]


class ParseStatementResponse(BaseModel):
    status: str
    request_id: str
    reconciliation_score: Decimal
    transactions: list[ParsedTransaction]
    meta: ParserMeta
    saved_count: int
    financial_summary: dict
