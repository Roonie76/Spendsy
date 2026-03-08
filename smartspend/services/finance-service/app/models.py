from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB

from .core.database import Base


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

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    type = Column(String(10), nullable=False)
    category = Column(String(100), default="other")
    date = Column(Date, default=date.today)
    is_recurring = Column(Boolean, default=False)


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
