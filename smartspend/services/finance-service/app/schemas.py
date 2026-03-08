from __future__ import annotations

from datetime import date as dt_date
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    status: str
    service: str


class ErrorResponse(BaseModel):
    ok: bool = False
    code: str
    message: str
    meta: dict
    details: dict | None = None


class UserProfilePayload(BaseModel):
    monthly_income: float | None = Field(default=None, alias="monthlyIncome")
    monthly_budget: float | None = Field(default=None, alias="monthlyBudget")
    daily_budget: float | None = Field(default=None, alias="dailyBudget")
    is_business: bool | None = Field(default=None, alias="is_business")
    email: str | None = None

    class Config:
        populate_by_name = True


class TransactionPayload(BaseModel):
    title: str | None = None
    description: str | None = None
    amount: float | None = None
    type: str | None = None
    category: str | None = None
    date: dt_date | None = None
    is_recurring: bool | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in {"income", "expense"}:
            raise ValueError("Transaction type must be 'income' or 'expense'")
        return normalized

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip().lower() or "other"


class TransactionOut(BaseModel):
    id: int
    title: str
    amount: float
    type: str
    category: str
    date: dt_date
    is_recurring: bool


class WealthPayload(BaseModel):
    title: str | None = None
    name: str | None = None
    amount: float | None = None
    type: str | None = None
    category: str | None = None

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
    amount: float
    type: str
    category: str


class TaxProfilePayload(BaseModel):
    isBusiness: Optional[bool] = None
    annualRent: Optional[float] = None
    annualEPF: Optional[float] = None
    npsContribution: Optional[float] = None
    healthInsuranceSelf: Optional[float] = None
    healthInsuranceParents: Optional[float] = None
    homeLoanInterest: Optional[float] = None
    educationLoanInterest: Optional[float] = None


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
    amount: float
    type: str
    category: str
    confidence: int
    bank: str
    balance: float | None
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
    reconciliation_score: float
    transactions: list[ParsedTransaction]
    meta: ParserMeta
    saved_count: int
    financial_summary: dict
