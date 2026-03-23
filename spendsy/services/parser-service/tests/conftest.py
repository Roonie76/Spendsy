"""
Shared test fixtures for the bank statement parser test suite.

Provides:
    - Sample TYPE_A text (HDFC-style structured table)
    - Sample TYPE_B text (SBI-style DR/CR format)
    - Minimal PDF-like bytes (text-based, not truly a PDF but accepted by text extractors)
    - Helper to build ParsedTransaction objects quickly
"""

from __future__ import annotations

import pytest
from datetime import date


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

TYPE_A_TEXT = """\
Account Statement - HDFC Bank Ltd
Account Number: 1234567890  |  Period: 01/11/2025 to 30/11/2025

Date          Narration                      Withdrawal(Dr)  Deposit(Cr)  Balance
01/11/2025    Opening Balance                                              50000.00
03/11/2025    UPI-SWIGGY FOOD ORDER          270.00                        49730.00
05/11/2025    SALARY CREDIT NOVEMBER                         30000.00      79730.00
10/11/2025    UPI-AMAZON PAY                 1500.00                       78230.00
15/11/2025    EMI PAYMENT HOUSING LOAN       12000.00                      66230.00
20/11/2025    NEFT-REFUND FROM INSURANCE                     2000.00       68230.00
25/11/2025    POS-GROCERY STORE              850.00                        67380.00
30/11/2025    UPI-NETFLIX SUBSCRIPTION       199.00                        67181.00
"""


TYPE_B_TEXT = """\
State Bank of India - Account Statement
Account No: 9876543210    |    From: 01-11-2025  To: 30-11-2025

Date         Amount      DR/CR   Balance      Particulars
01/11/2025   270.00      DR      49730.00     UPI TRANSFER AMAZON
05/11/2025   30000.00    CR      79730.00     SALARY CREDIT NOV 2025
10/11/2025   1500.00     DR      78230.00     NEFT PAYMENT INSURANCE
15/11/2025   12000.00    DR      66230.00     EMI DEDUCTION
20/11/2025   2000.00     CR      68230.00     REFUND FROM MERCHANT
25/11/2025   850.00      DR      67380.00     POS PURCHASE SUPERMARKET
"""


TYPE_C_LOW_TEXT = """
s+Mte Bank
OCR d4ta 0f poor quality
Amnt: 1.0o0.oo
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def type_a_text() -> str:
    return TYPE_A_TEXT


@pytest.fixture
def type_b_text() -> str:
    return TYPE_B_TEXT


@pytest.fixture
def empty_text() -> str:
    return ""


@pytest.fixture
def low_quality_text() -> str:
    return TYPE_C_LOW_TEXT


@pytest.fixture
def sample_transactions():
    """Build a list of minimal ParsedTransaction-like dicts for tests."""
    from app.parser import ParsedTransaction
    return [
        ParsedTransaction(
            date=date(2025, 11, 3),
            description="UPI SWIGGY ORDER",
            amount=270.0,
            type="expense",
            debit=270.0,
            credit=None,
            balance=49730.0,
            confidence=0.95,
        ),
        ParsedTransaction(
            date=date(2025, 11, 5),
            description="SALARY CREDIT NOVEMBER",
            amount=30000.0,
            type="income",
            debit=None,
            credit=30000.0,
            balance=79730.0,
            confidence=0.95,
        ),
        ParsedTransaction(
            date=date(2025, 11, 10),
            description="UPI AMAZON PAY",
            amount=1500.0,
            type="expense",
            debit=1500.0,
            credit=None,
            balance=78230.0,
            confidence=0.95,
        ),
    ]
