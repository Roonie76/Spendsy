from __future__ import annotations

from datetime import date as dt_date, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionCategory(str, Enum):
    salary = "salary"
    investment = "investment"
    housing = "housing"
    utilities = "utilities"
    food = "food"
    shopping = "shopping"
    transport = "transport"
    entertainment = "entertainment"
    rent = "rent"
    travel = "travel"
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
    model_config = ConfigDict(populate_by_name=True)

    monthly_income: Decimal | None = Field(default=None, alias="monthlyIncome", ge=0)
    monthly_budget: Decimal | None = Field(default=None, alias="monthlyBudget", ge=0)
    daily_budget: Decimal | None = Field(default=None, alias="dailyBudget", ge=0)
    is_business: bool | None = Field(default=None, alias="is_business")
    email: str | None = None


class TransactionPayload(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    amount: Decimal | None = None
    type: str | None = None
    category: TransactionCategory | None = None
    date: dt_date | None = None
    balance: Decimal | None = None
    source: str | None = None
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

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in {"manual", "statement"}:
            raise ValueError("Transaction source must be 'manual' or 'statement'")
        return normalized


class TransactionOut(BaseModel):
    id: int
    uid: str
    title: str
    description: str
    raw_description: str | None = None
    amount: Decimal
    type: str
    category: str
    date: dt_date
    balance: Decimal | None = None
    source: str
    is_recurring: bool
    created_at: datetime


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
    uid: str
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
    source: str
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


class DebitCardPayload(BaseModel):
    bank_name: str = Field(..., max_length=100, alias="bankName")
    last_four_digits: str = Field(..., min_length=4, max_length=4, alias="lastFour")
    card_holder_name: str = Field(..., max_length=100, alias="cardHolder")
    expiry_date: str = Field(..., max_length=7, alias="expiry")

    model_config = ConfigDict(populate_by_name=True)


class DebitCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    uid: str
    bank_name: str = Field(alias="bankName")
    last_four_digits: str = Field(alias="lastFour")
    card_holder_name: str = Field(alias="cardHolder")
    expiry_date: str = Field(alias="expiry")
    created_at: datetime


class CreditCardPayload(BaseModel):
    bank_name: str = Field(..., max_length=100, alias="bankName")
    card_holder_name: str = Field(..., max_length=100, alias="cardHolder")
    last_four_digits: str = Field(..., min_length=4, max_length=4, alias="lastFour")
    credit_limit: Decimal = Field(default=0, ge=0, alias="creditLimit")
    billing_cycle: int = Field(default=1, ge=1, le=31, alias="billingCycle")
    due_day: int = Field(default=20, ge=1, le=31, alias="dueDay")

    model_config = ConfigDict(populate_by_name=True)


class CreditCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    uid: str
    bank_name: str = Field(alias="bankName")
    card_holder_name: str = Field(alias="cardHolder")
    last_four_digits: str = Field(alias="lastFour")
    credit_limit: Decimal = Field(alias="creditLimit")
    billing_cycle: int = Field(alias="billingCycle")
    due_day: int = Field(alias="dueDay")
    created_at: datetime
    updated_at: datetime


class LoanPayload(BaseModel):
    loan_type: str | None = Field(default=None, max_length=20)
    principal_amount: Decimal | None = Field(default=None, ge=0)
    interest_rate: Decimal | None = Field(default=None, ge=0)
    tenure_months: int | None = Field(default=None, ge=1)
    start_date: date | None = None
    emi_amount: Decimal | None = Field(default=None, ge=0)
    remaining_balance: Decimal | None = Field(default=None, ge=0)


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    uid: str
    loan_type: str
    principal_amount: Decimal
    interest_rate: Decimal
    tenure_months: int
    start_date: date
    emi_amount: Decimal
    remaining_balance: Decimal
    created_at: datetime


class StatementRecordPayload(BaseModel):
    filename: str
    status: str = "pending"
    account_type: str | None = None
    tx_count: int = 0
    reconciliation_score: Decimal | None = None
    file_size: int | None = Field(default=None, alias="fileSize")
    file_hash: str | None = Field(default=None, alias="fileHash")


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    uid: str
    user_id: int
    filename: str
    file_type: str | None = Field(alias="fileType")
    file_size: int | None = Field(alias="fileSize")
    file_hash: str | None = Field(alias="fileHash")
    storage_path: str | None = Field(alias="storagePath")
    metadata_json: dict = Field(alias="metadata")
    created_at: datetime


class StatementRecordOut(StatementRecordPayload):
    model_config = ConfigDict(from_attributes=True)
    id: int
    uid: str
    user_id: int
    created_at: datetime


class NetWorthSnapshotPayload(BaseModel):
    date: date
    total_assets: Decimal = Field(default=0)
    total_liabilities: Decimal = Field(default=0)
    net_worth: Decimal = Field(default=0)


class NetWorthSnapshotOut(NetWorthSnapshotPayload):
    model_config = ConfigDict(from_attributes=True)
    id: int
    uid: str
    user_id: int
    created_at: datetime


# ─── Goals ────────────────────────────────────────────────────────────────────

class GoalCategory(str, Enum):
    savings = "savings"
    emergency = "emergency"
    travel = "travel"
    education = "education"
    asset = "asset"
    retirement = "retirement"
    other = "other"


class GoalPayload(BaseModel):
    title: str = Field(..., max_length=100)
    description: str | None = Field(default=None, max_length=255)
    target_amount: Decimal = Field(..., gt=0)
    current_amount: Decimal = Field(default=0, ge=0)
    target_date: dt_date | None = None
    category: GoalCategory = GoalCategory.savings


class GoalUpdatePayload(BaseModel):
    title: str | None = Field(default=None, max_length=100)
    description: str | None = None
    target_amount: Decimal | None = Field(default=None, gt=0)
    current_amount: Decimal | None = Field(default=None, ge=0)
    target_date: dt_date | None = None
    category: GoalCategory | None = None
    is_completed: bool | None = None


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    uid: str
    user_id: int
    title: str
    description: str | None
    target_amount: Decimal
    current_amount: Decimal
    target_date: dt_date | None
    category: str
    is_completed: bool
    created_at: datetime
    updated_at: datetime


# ─── Product Layer ────────────────────────────────────────────────────────────

class FinancialHealthOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    score: int
    savings_rate: Decimal
    stability_index: Decimal
    debt_to_income: Decimal
    explanation: str | None
    updated_at: datetime


class FinancialInsightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    user_id: int
    period: str
    total_income: Decimal = Field(alias="totalIncome")
    total_expense: Decimal = Field(alias="totalExpense")
    category_summary: dict[str, float] = Field(alias="category_json")
    merchant_summary: dict[str, float] = Field(alias="merchant_json")
    updated_at: datetime


class SmartRecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    uid: str
    type: str # 'overspending', 'debt', 'savings'
    priority: str # 'low', 'medium', 'high', 'critical'
    message: str
    action_url: str | None = None
    created_at: datetime


class UserAlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    alert_type: str = Field(alias="type")
    severity: str
    title: str
    description: str | None
    is_read: bool
    created_at: datetime


class DashboardOverview(BaseModel):
    health_score: int
    monthly_income: Decimal
    monthly_expense: Decimal
    savings_rate: float
    top_categories: list[dict[str, Any]]
    recommendation_count: int
    unread_alerts: int
