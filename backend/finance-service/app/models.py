from __future__ import annotations

import uuid

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "finance_userprofile"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)

    monthly_income = Column("monthlyIncome", Numeric(15, 2), default=0)
    monthly_budget = Column("monthlyBudget", Numeric(15, 2), default=0)
    daily_budget = Column("dailyBudget", Numeric(15, 2), default=0)
    is_business = Column(Boolean, default=False)
    tier = Column(String(20), default="free")  # 'free', 'pro', 'enterprise'

    # Personalization fields — drive life-stage- and risk-aware advice.
    # Populated by onboarding questionnaire or user-facing profile editor.
    risk_tolerance = Column(String(20), nullable=True)  # 'conservative' | 'balanced' | 'aggressive'
    dependents = Column(Integer, default=0, nullable=False)
    life_stage = Column(String(20), nullable=True)  # 'student' | 'early_career' | 'married' | 'parent' | 'pre_retirement' | 'retired'
    preferences = Column(JSONB, default=dict)

    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "finance_transaction"
    __table_args__ = (
        UniqueConstraint("user_id", "statement_hash", "statement_row_hash", name="uq_finance_statement_row"),
        Index("idx_finance_txn_semantic_dedupe", "user_id", "date", "amount", "type", "title"),
        Index("idx_finance_txn_fingerprint", "user_id", "fingerprint"),
    )

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    uid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    raw_description = Column(String(255), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    type = Column(String(10), nullable=False)
    category = Column(String(100), default="other")
    date = Column(Date, default=date.today)
    # True when the parser couldn't read an exact day off the statement and
    # inherited month/year from the previous dated row. Date stored with day=01.
    date_inferred = Column(Boolean, default=False, nullable=False)
    balance = Column(Numeric(14, 2), nullable=True)
    source = Column(String(32), default="manual", nullable=False, index=True)
    statement_hash = Column(String(64), nullable=True, index=True)
    statement_row_hash = Column(String(64), nullable=True, index=True)
    fingerprint = Column(String(64), nullable=True)
    is_recurring = Column(Boolean, default=False)
    account_type = Column(String(20), nullable=True)  # 'debit', 'credit'
    confidence = Column(Integer, default=100, nullable=False)
    status = Column(String(20), default="active", nullable=False)  # 'active', 'flagged'
    reconciliation_flags = Column(JSONB, default=list, nullable=False)

    # Inter-account transfer linkage — used to mark e.g. a credit-card bill
    # payment made from a debit account, so the same rupees aren't counted
    # once as a debit expense and again as a credit-card refund/income.
    # Both sides of a pair share the same transfer_group_id. is_transfer is
    # the aggregation filter — all spend/income queries exclude these.
    transfer_group_id = Column(String(36), nullable=True)
    is_transfer = Column(Boolean, default=False, nullable=False)
    embedding = Column(Vector(768), nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class WealthItem(Base):
    __tablename__ = "finance_wealthitem"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    uid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    title = Column(String(100), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    type = Column(String(10), nullable=False)
    category = Column(String(50), default="General")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class TaxProfile(Base):
    __tablename__ = "finance_taxprofile"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)

    is_business = Column(Boolean, default=False)
    annual_rent = Column(Numeric(12, 2), default=0)
    annual_epf = Column(Numeric(12, 2), default=0)
    nps_contribution = Column(Numeric(12, 2), default=0)
    health_insurance_self = Column(Numeric(12, 2), default=0)
    health_insurance_parents = Column(Numeric(12, 2), default=0)
    home_loan_interest = Column(Numeric(12, 2), default=0)
    education_loan_interest = Column(Numeric(12, 2), default=0)

    # Extended profile fields (TORA tax integration)
    parents_are_senior = Column(Boolean, default=False)
    age = Column(Integer, default=30)
    is_metro = Column(Boolean, default=False)
    is_presumptive = Column(Boolean, default=False)
    is_nri = Column(Boolean, default=False)
    foreign_assets = Column(Boolean, default=False)

    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ITRData(Base):
    __tablename__ = "finance_itrdata"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)

    income_data = Column(JSONB, default=dict)
    deductions_data = Column(JSONB, default=dict)
    filing_details = Column(JSONB, default=dict)
    tax_regime = Column(String(10), default="new")
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)



class ParsedDocument(Base):
    """
    Stores a user-uploaded tax document (Form 16, 26AS, CG statement, etc.)
    and its machine-parsed structured output.

    doc_type values:
        form16          Form 16 Part A + B from employer
        form26as        Form 26AS / AIS / TIS from income-tax portal
        cg_statement    Broker capital gains P&L (Zerodha, Groww, Upstox, etc.)
        nps_statement   NPS CRA annual statement
        ppf_passbook    PPF passbook / statement
        elss_statement  ELSS / mutual fund investment statement
        rent_receipt    Rent receipts for HRA / 80GG
        hl_certificate  Home loan interest certificate
        health_ins      Health insurance premium receipt
        other           Any other supporting document
    """
    __tablename__ = "finance_parsed_document"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    ay = Column(String(7), nullable=False, default="2025-26")
    # Document identity
    doc_type = Column(String(30), nullable=False)                   # see docstring above
    filename = Column(String(255), nullable=True)
    file_hash = Column(String(64), nullable=True, index=True)       # SHA-256 — dedup guard

    # Parse output
    parsed_data = Column(JSONB, default=dict)                       # structured fields from parser
    parse_status = Column(String(20), nullable=False, default="pending")  # pending/done/failed
    parse_error = Column(String(500), nullable=True)
    confidence_score = Column(Numeric(5, 2), nullable=True)         # 0–100 overall confidence
    field_confidence = Column(JSONB, default=dict)                  # {field: confidence_pct}

    # Parser metadata
    parser_version = Column(String(20), nullable=True)
    page_count = Column(Integer, nullable=True)
    ocr_used = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ApiAuditLog(Base):
    __tablename__ = "finance_apiauditlog"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, nullable=True)
    request_id = Column(String(64), index=True)
    action = Column(String(64))
    resource_type = Column(String(64))
    resource_id = Column(String(64), default="")
    method = Column(String(10))
    path = Column(String(255))
    status_code = Column(Integer)
    error_code = Column(String(64), default="")
    ip_address = Column(String(64), nullable=True)
    details = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class DebitCard(Base):
    __tablename__ = "finance_debitcard"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    uid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    bank_name = Column(String(100), nullable=False)
    last_four_digits = Column(String(4), nullable=False)
    card_holder_name = Column(String(100), nullable=False)
    expiry_date = Column(String(7), nullable=False)  # MM/YYYY
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class CreditCard(Base):
    __tablename__ = "finance_creditcard"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    uid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    bank_name = Column(String(100), nullable=False)
    card_holder_name = Column(String(100), nullable=False)
    last_four_digits = Column(String(4), nullable=False)
    credit_limit = Column(Numeric(15, 2), default=0)
    billing_cycle = Column(Integer, default=1)
    due_day = Column(Integer, default=20)

    # Balance tracking — updated by statement ingest or manual reconciliation.
    # `outstanding_balance` is the running total; `last_statement_balance`
    # freezes at the last cycle close; `payment_due_date` is the next
    # due date derived from billing cycle (denormalized for quick UI access).
    outstanding_balance = Column(Numeric(15, 2), default=0, nullable=False)
    last_statement_balance = Column(Numeric(15, 2), default=0, nullable=False)
    payment_due_date = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Loan(Base):
    __tablename__ = "finance_loan"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    uid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    loan_type = Column(String(20), nullable=False)  # home, car, student, personal
    bank_name = Column(String(100), nullable=True)
    principal_amount = Column(Numeric(15, 2), nullable=False)

    interest_rate = Column(Numeric(5, 2), nullable=False)
    tenure_months = Column(Integer, nullable=False)
    start_date = Column(Date, default=date.today)
    emi_amount = Column(Numeric(15, 2), nullable=False)
    remaining_balance = Column(Numeric(15, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class StatementRecord(Base):
    __tablename__ = "finance_statementrecord"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    uid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=True)
    file_hash = Column(String(64), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="pending")  # 'pending', 'success', 'failed'
    account_type = Column(String(20), nullable=True)  # e.g., 'credit_card', 'savings'
    tx_count = Column(Integer, default=0)
    reconciliation_score = Column(Numeric(5, 4), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class NetWorthSnapshot(Base):
    __tablename__ = "finance_networthsnapshot"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    uid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    date = Column(Date, default=date.today, nullable=False)
    total_assets = Column(Numeric(15, 2), nullable=False, default=0)
    total_liabilities = Column(Numeric(15, 2), nullable=False, default=0)
    net_worth = Column(Numeric(15, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class FinanceGoal(Base):
    """Saving goals — e.g. 'Emergency Fund', 'New Car', 'Down Payment'."""

    __tablename__ = "finance_goal"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    uid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    target_amount = Column(Numeric(15, 2), nullable=False)
    current_amount = Column(Numeric(15, 2), nullable=False, default=0)
    target_date = Column(Date, nullable=True)
    category = Column(String(50), default="savings")  # e.g. emergency, travel, asset, education
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ToraConversation(Base):
    """Stores TORA chat history per user for persistent conversational memory."""

    __tablename__ = "tora_conversation"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(String(2000), nullable=False)
    # Structured AI response components (only set for role='assistant')
    financial_overview = Column(String(2000), nullable=True)
    current_position = Column(String(2000), nullable=True)
    recommended_strategy = Column(String(4000), nullable=True)
    expected_outcome = Column(String(2000), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)


class ToraFeedback(Base):
    """User reactions (thumbs up/down) on individual TORA responses.

    One row per user feedback event. A user may change their rating by
    POSTing a new row — we read the most recent per (user_id, message_id)
    in aggregation queries.
    """

    __tablename__ = "tora_feedback"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    # Links to the ToraConversation row this feedback is about. Nullable
    # for client-generated message ids that don't correspond to a stored row.
    message_id = Column(BigInteger, nullable=True, index=True)
    # Client-side id for the chat bubble (e.g. "msg-abc123"). Stored so we
    # can dedupe and update even when message_id isn't available.
    client_message_id = Column(String(64), nullable=True, index=True)
    rating = Column(String(8), nullable=False)  # 'up' or 'down'
    reason = Column(String(64), nullable=True)  # optional tag: 'wrong', 'slow', 'unhelpful', 'great'
    comment = Column(String(500), nullable=True)  # optional free text
    # Snapshot of what the user was reacting to, for offline analysis.
    prompt = Column(String(500), nullable=True)
    response_preview = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)


class SecurityAlert(Base):
    __tablename__ = "finance_securityalert"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    type = Column(String(32))  # 'mass_data_access', 'unusual_resource_access', 'parser_attacks'
    severity = Column(String(16))  # 'low', 'medium', 'high', 'critical'
    description = Column(String(255))
    actor_identity = Column(String(64), nullable=True, index=True)  # IP or UserID/UID
    details = Column(JSONB, default=dict)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Document(Base):
    """Generic document storage tracking (Phase 5 requirement)."""
    __tablename__ = "finance_document"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    uid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=True)  # 'statement', 'receipt', 'identity', etc.
    file_size = Column(BigInteger, nullable=True)
    file_hash = Column(String(64), nullable=True, index=True)
    storage_path = Column(String(512), nullable=True)  # Relative to storage root
    metadata_json = Column(JSONB, default=dict)
    embedding = Column(Vector(768), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class FinancialHealth(Base):
    """Stores computed financial health scores and high-level metrics."""
    __tablename__ = "finance_health"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    score = Column(Integer, default=0)  # 0-100
    savings_rate = Column(Numeric(5, 4), default=0.0)
    stability_index = Column(Numeric(5, 4), default=0.0)
    debt_to_income = Column(Numeric(5, 4), default=0.0)
    explanation = Column(String(1000), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class FinancialInsight(Base):
    """Stores monthly aggregated financial snapshots for the dashboard."""
    __tablename__ = "finance_insight"
    __table_args__ = (
        UniqueConstraint("user_id", "period", name="uq_user_period_insight"),
    )

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    period = Column(String(7), nullable=False)  # YYYY-MM
    total_income = Column(Numeric(15, 2), default=0.0)
    total_expense = Column(Numeric(15, 2), default=0.0)
    category_json = Column(JSONB, default=dict)  # {"Shopping": 1200, "Food": 800}
    merchant_json = Column(JSONB, default=dict)  # {"Amazon": 500, "Uber": 200}
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class SmartRecommendation(Base):
    """Stores Tora Engine generated financial tips and recommendations."""
    __tablename__ = "finance_recommendation"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    uid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    type = Column(String(32))  # 'overspending', 'debt', 'savings', 'income'
    priority = Column(String(16))  # 'low', 'medium', 'high', 'critical'
    message = Column(String(512), nullable=False)
    action_url = Column(String(255), nullable=True)
    is_dismissed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)



class UserAlert(Base):
    """Stores proactive financial alerts for the user."""
    __tablename__ = "finance_useralert"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    alert_type = Column(String(32))  # 'spike', 'duplicate', 'low_balance', 'late_payment'
    severity = Column(String(16))  # 'info', 'warning', 'danger'
    title = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    data_json = Column(JSONB, default=dict)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class FinancePlan(Base):
    """Detailed financial plans — e.g. 'Retirement', 'House Purchase', 'Debt Payoff'."""
    __tablename__ = "finance_plan"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    uid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    loan_id = Column(BigInteger, nullable=True)  # Link to finance_loan
    title = Column(String(100), nullable=False)

    source = Column(String(20), default="manual")  # 'manual' or 'ai'

    target_amount = Column(Numeric(15, 2), nullable=False)
    current_saved = Column(Numeric(15, 2), nullable=False, default=0)
    deadline = Column(Date, nullable=False)

    monthly_saving = Column(Numeric(15, 2), nullable=False)
    daily_saving = Column(Numeric(15, 2), nullable=False)

    confidence_score = Column(Numeric(5, 2), default=1.0)  # 0.0 to 1.0 (AI confidence)
    reasoning = Column(String(1000), nullable=True)

    status = Column(String(20), default="on_track")  # 'on_track', 'risk', 'delayed', 'completed'
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
