from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field

class Transaction(BaseModel):
    date: date
    description: str
    deposits: Decimal = Field(default=Decimal("0.0"))
    withdrawals: Decimal = Field(default=Decimal("0.0"))
    balance: Decimal

class StatementResponse(BaseModel):
    account_holder: str
    account_number: str
    opening_balance: Decimal
    closing_balance: Decimal
    transactions: List[Transaction]
    reconciliation_ok: bool
    total_deposits: Decimal
    total_withdrawals: Decimal
    error_flags: List[str] = []
