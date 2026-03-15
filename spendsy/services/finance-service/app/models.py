from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "finance_userprofile"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)

    monthly_income = Column("monthlyIncome", Numeric(15, 2), default=0)
    monthly_budget = Column("monthlyBudget", Numeric(15, 2), default=0)
    daily_budget = Column("dailyBudget", Numeric(15, 2), default=0)
    is_business = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "finance_transaction"
    __table_args__ = (
        UniqueConstraint("user_id", "statement_hash", "statement_row_hash", name="uq_finance_statement_row"),
        Index("idx_finance_txn_semantic_dedupe", "user_id", "date", "amount", "type", "title"),
        Index("idx_finance_txn_fingerprint", "user_id", "fingerprint"),
    )

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    raw_description = Column(String(255), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    type = Column(String(10), nullable=False)
    category = Column(String(100), default="other")
    date = Column(Date, default=date.today)
    balance = Column(Numeric(14, 2), nullable=True)
    source = Column(String(32), default="manual", nullable=False, index=True)
    statement_hash = Column(String(64), nullable=True, index=True)
    statement_row_hash = Column(String(64), nullable=True, index=True)
    fingerprint = Column(String(64), nullable=True)
    is_recurring = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class WealthItem(Base):
    __tablename__ = "finance_wealthitem"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
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


class CreditCard(Base):
    __tablename__ = "finance_creditcard"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    credit_limit = Column(Numeric(15, 2), default=0)
    billing_day = Column(Integer, default=1)
    due_day = Column(Integer, default=20)
    current_balance = Column(Numeric(15, 2), default=0)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Loan(Base):
    __tablename__ = "finance_loan"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    loan_type = Column(String(20), nullable=False)  # home, car, student, personal
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
    user_id = Column(BigInteger, index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # 'pending', 'success', 'failed'
    account_type = Column(String(20), nullable=True)  # e.g., 'credit_card', 'savings'
    tx_count = Column(Integer, default=0)
    reconciliation_score = Column(Numeric(5, 4), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class NetWorthSnapshot(Base):
    __tablename__ = "finance_networthsnapshot"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    date = Column(Date, default=date.today, nullable=False)
    total_assets = Column(Numeric(15, 2), nullable=False, default=0)
    total_liabilities = Column(Numeric(15, 2), nullable=False, default=0)
    net_worth = Column(Numeric(15, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
