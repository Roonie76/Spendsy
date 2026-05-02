"""
Compliance & Safety Filter — Production hardened.

Two-tier architecture:
  TIER 1 — Hard blocks: response replaced with safe refusal
  TIER 2 — Soft disclaimers: regulatory text appended to response

Hard block triggers:
  1. Emergency fund depletion for equity investment
  2. New loan when EMI-to-income > 40%
  3. Specific stock/crypto/options pick
  4. Financial distress signal
  5. Minor age + investment product

Soft disclaimer triggers:
  loan, investment, tax, debt consolidation
"""
from __future__ import annotations
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Patterns ──────────────────────────────────────────────────────────────────

_EMERGENCY_LIQUIDATE_RE = re.compile(
    r"(use|withdraw|redeem|liquidat|break|dip.into)\s+.{0,40}?"
    r"(emergency.fund|contingency.fund|rainy.day.fund)"
    r".{0,40}?(invest|equity|sip|stock|mutual.fund|crypto)",
    re.IGNORECASE | re.DOTALL,
)
_EQUITY_FROM_EMERGENCY_RE = re.compile(
    r"(invest|put|move)\s+.{0,30}?(emergency.fund|contingency)"
    r"\s+.{0,30}?(equity|sip|stock|market)",
    re.IGNORECASE | re.DOTALL,
)
# Tickers (2-6 uppercase letters) often used for stocks.
# We remove re.IGNORECASE from the ticker part to avoid matching "gold", "car", etc.
_TICKER_RE = re.compile(r"\b(buy|invest\s+in|pick|recommend)\s+(?:shares?\s+of\s+)?([A-Z]{2,6}(?:\.NS|\.BSE)?)\b")

# Assets that are always blocked regardless of case
_CRYPTO_DERIV_RE = re.compile(
    r"\b(bitcoin|btc|ethereum|eth|dogecoin|crypto|options?\s+contract|nifty.call|put.option|futures.contract)\b",
    re.IGNORECASE
)

_SPECIFIC_STOCK_RE = re.compile(
    r"\b(reliance|tcs|infosys|hdfc\s+bank|icici\s+bank|wipro|hcl|bajaj|adani|tata\s+motors)\b"
    r"\s+(?:shares?|stock|equity|call|put)",
    re.IGNORECASE,
)

# List of common purchase goals that should NEVER trigger a compliance block
_SAFE_GOALS_RE = re.compile(r"\b(gold|silver|macbook|iphone|laptop|car|house|home|education|marriage|wedding|travel|vacation|holiday)\b", re.I)
_DISTRESS_RE = re.compile(
    r"\b(can.t\s+pay|cannot\s+pay|missed\s+emi|defaulted|bankruptcy|insolvent|"
    r"debt.trap|drowning.in.debt|no\s+money\s+left|can.t\s+afford|unable\s+to\s+pay|"
    r"repo\s+notice|eviction|foreclosure.notice)\b",
    re.IGNORECASE,
)
_MINOR_RE = re.compile(
    r"\b(?:i\s+am\s+|i.m\s+|age\s+is\s+|aged?\s+)(\d{1,2})\s*(?:years?\s*old|yr)?\b",
    re.IGNORECASE,
)
_NEW_LOAN_RE = re.compile(
    r"\b(take|get|apply.for|avail)\s+(a\s+)?(new\s+)?(personal\s+|car\s+|home\s+)?loan\b",
    re.IGNORECASE,
)
_LOAN_RE       = re.compile(r"\b(loan|emi|borrow|credit)\b", re.I)
_INVEST_RE     = re.compile(r"\b(invest|sip|mutual.fund|mf|equity|elss|ppf|nps|stock)\b", re.I)
_TAX_RE        = re.compile(r"\b(tax|itr|deduction|80c|80d|hra|surcharge|regime)\b", re.I)
_DEBT_CONSOL_RE = re.compile(r"\b(consolidate|pay.off|clear.*debt|balance.transfer)\b", re.I)

# ── Safe refusal builder ──────────────────────────────────────────────────────

def _refusal(reason: str, suggestion: str) -> dict:
    return {
        "mode": "simple",
        "content": f"I'm not able to provide that specific advice. {reason}\n\n{suggestion}",
        "_compliance_blocked": True,
    }

SAFE_RESPONSES: dict[str, dict] = {
    "emergency_fund_equity": _refusal(
        "Using your emergency fund for investments puts your financial safety net at risk. "
        "An emergency fund must stay liquid and separate from investment accounts at all times.",
        "Keep 6 months of expenses in a liquid fund or sweep FD. "
        "Invest only from your monthly surplus beyond this buffer.",
    ),
    "stock_pick": _refusal(
        "I'm not able to recommend specific stocks, cryptocurrencies, or derivative contracts. "
        "TORA is a financial planning assistant, not a SEBI-registered Investment Advisor.",
        "For specific investment picks, consult a SEBI-registered Research Analyst (RA) or "
        "Investment Advisor (IA). I can help with asset allocation, SIP planning, and "
        "goal-based investment frameworks instead.",
    ),
    "financial_distress": _refusal(
        "It sounds like you're in a genuinely difficult financial situation that needs "
        "personalised, professional guidance.",
        "Please reach out to:\n"
        "* A SEBI-registered Credit Counsellor\n"
        "* RBI Banking Ombudsman: https://rbi.org.in/Scripts/Complaints.aspx\n"
        "* National Consumer Helpline: 1800-11-4000 (free, Mon-Sat)\n\n"
        "I'm here for general planning once your situation has stabilised.",
    ),
    "high_emi_loan": _refusal(
        "Adding a new loan when your existing EMIs already exceed 40% of your take-home income "
        "creates significant financial risk and may hurt your CIBIL score.",
        "Focus on reducing existing debt first using the debt avalanche strategy "
        "(pay highest-interest debt first). "
        "Consider balance transfer to a lower-rate product. "
        "Return when your EMI-to-income ratio is below 35%.",
    ),
    "minor_investment": _refusal(
        "Most investment products (mutual funds, stocks, FDs) require the account holder "
        "to be 18 or older.",
        "For minors, parents or guardians can:\n"
        "* Open a Sukanya Samriddhi Yojana account (for girls up to 10 yrs)\n"
        "* Open a PPF account in the parent's name\n"
        "* Open a custodial mutual fund account via a guardian\n\n"
        "Consult your bank for the correct procedure.",
    ),
}

# ── Soft disclaimers ──────────────────────────────────────────────────────────

REGULATORY_DISCLAIMERS: dict[str, str] = {
    "loan": (
        "\n\n*Note: Loan approval and interest rates are subject to bank policy "
        "and your credit profile. Compare offers across at least 3 lenders before signing.*"
    ),
    "investment": (
        "\n\n*Disclaimer: Mutual fund and equity investments are subject to market risks. "
        "Past performance is not indicative of future returns. "
        "Please read all offer documents carefully before investing.*"
    ),
    "tax": (
        "\n\n*Important: Tax calculations are based on current regime rules. "
        "Verify all deductions with a qualified CA before filing your ITR.*"
    ),
    "debt_consolidation": (
        "\n\n*Strategy Note: Debt consolidation can reduce interest burden, but avoid "
        "accumulating new debt while repaying the consolidated loan.*"
    ),
}


# ── Main filter ───────────────────────────────────────────────────────────────

class ComplianceFilter:
    """
    Single entry point: ComplianceFilter.process_response(response, user_profile, query)
    Returns original response with disclaimers, or a safe refusal dict on hard block.
    Never raises.
    """

    @classmethod
    def process_response(
        cls,
        response: dict[str, Any],
        user_profile: dict[str, Any] | None = None,
        query: str = "",
    ) -> dict[str, Any]:
        try:
            content   = cls._extract_text(response)
            full_text = query + " " + content
            combined  = full_text.lower()

            # TIER 1: Hard blocks
            # 1. Emergency fund protection
            if (_EMERGENCY_LIQUIDATE_RE.search(full_text) or
                    _EQUITY_FROM_EMERGENCY_RE.search(full_text)):
                logger.warning("HARD BLOCK: emergency_fund_equity | q=%r", query[:80])
                return SAFE_RESPONSES["emergency_fund_equity"]

            # 2. Stock/Crypto blocking (with safe goal exception)
            if not _SAFE_GOALS_RE.search(full_text):
                if _TICKER_RE.search(full_text) or _CRYPTO_DERIV_RE.search(full_text) or _SPECIFIC_STOCK_RE.search(full_text):
                    logger.warning("HARD BLOCK: stock_pick | q=%r", query[:80])
                    return SAFE_RESPONSES["stock_pick"]

            # 3. Financial distress
            if _DISTRESS_RE.search(full_text):
                logger.warning("HARD BLOCK: financial_distress | q=%r", query[:80])
                return SAFE_RESPONSES["financial_distress"]

            if user_profile and _NEW_LOAN_RE.search(full_text):
                income       = float(user_profile.get("monthly_income") or
                                     user_profile.get("income") or 0)
                loans        = user_profile.get("loans") or []
                existing_emi = sum(
                    # finance-context returns emi_amount; MCP may return emi — check both
                    float(l.get("emi_amount") or l.get("emi") or 0)
                    for l in loans if isinstance(l, dict)
                )
                if income > 0 and existing_emi > 0 and (existing_emi / income) > 0.40:
                    logger.warning(
                        "HARD BLOCK: high_emi_loan | emi=%.0f income=%.0f ratio=%.2f",
                        existing_emi, income, existing_emi / income,
                    )
                    return SAFE_RESPONSES["high_emi_loan"]

            m_age = _MINOR_RE.search(full_text)
            if m_age:
                try:
                    age = int(m_age.group(1))
                    if age < 18 and _INVEST_RE.search(full_text):
                        logger.warning("HARD BLOCK: minor_investment | age=%d", age)
                        return SAFE_RESPONSES["minor_investment"]
                except (IndexError, ValueError):
                    pass

            # TIER 2: Soft disclaimers
            disclaimers: list[str] = []
            if _LOAN_RE.search(combined):
                disclaimers.append(REGULATORY_DISCLAIMERS["loan"])
            if _INVEST_RE.search(combined):
                disclaimers.append(REGULATORY_DISCLAIMERS["investment"])
            if _TAX_RE.search(combined):
                disclaimers.append(REGULATORY_DISCLAIMERS["tax"])
            if _DEBT_CONSOL_RE.search(combined):
                disclaimers.append(REGULATORY_DISCLAIMERS["debt_consolidation"])

            seen: set[str] = set()
            unique = [d for d in disclaimers if not (d in seen or seen.add(d))]
            if unique:
                response = cls._append_disclaimers(response, unique)
                logger.info("Soft compliance: %d disclaimer(s) appended", len(unique))

            return response

        except Exception as exc:
            logger.error("ComplianceFilter error (non-blocking): %s", exc)
            return response

    @staticmethod
    def _extract_text(response: dict[str, Any]) -> str:
        if not isinstance(response, dict):
            return str(response)
        parts: list[str] = []
        for key in ("content", "Financial Overview", "Current Position",
                    "Recommended Strategy", "Expected Outcome"):
            val = response.get(key)
            if isinstance(val, str):
                parts.append(val)
        return " ".join(parts)

    @staticmethod
    def _append_disclaimers(response: dict[str, Any], disclaimers: list[str]) -> dict[str, Any]:
        suffix = "".join(disclaimers)
        if response.get("mode") == "simple":
            response["content"] = str(response.get("content", "")) + suffix
        else:
            for key in reversed(("Expected Outcome", "Recommended Strategy",
                                  "Current Position", "Financial Overview")):
                val = response.get(key)
                if isinstance(val, str) and val.strip() and val != "N/A":
                    response[key] = val + suffix
                    return response
            response["content"] = str(response.get("content", "")) + suffix
        return response
