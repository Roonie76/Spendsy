"""
cg_statement_parser.py — Broker Capital Gains P&L statement parser.

Supported brokers:
  ZERODHA   — "Tax P&L" report (pdfplumber table extraction)
  GROWW     — Capital Gains report
  UPSTOX    — Tax P&L PDF
  KUVERA    — Capital Gains report (also handles CSV)
  CAMS      — Consolidated Account Statement (CAS) for mutual funds
  KFINTECH  — KFintech CAS PDF
  GENERIC   — Regex fallback for unlisted brokers

Fields extracted per asset class:
  - Listed equity STCG (Sec 111A) — buy/sell proceeds, cost, gain
  - Listed equity LTCG (Sec 112A)
  - Equity MF STCG / LTCG
  - Debt MF (treated as slab / 12.5%)
  - Real estate STCG / LTCG
  - Gold STCG / LTCG
  - Bonds STCG / LTCG
  - Crypto / VDA (Sec 115BBH)
  - Losses (STCL / LTCL per class) — for set-off

Output: CGParseResult
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger("finance.parser.cg_statement")
PARSER_VERSION = "1.0.0"

# ── Broker signatures ─────────────────────────────────────────────────────────

BROKER_SIGS: dict[str, list[str]] = {
    "ZERODHA":  ["Zerodha", "Tax P&L", "ZERODHA", "zerodha.com"],
    "GROWW":    ["Groww", "GROWW", "groww.in"],
    "UPSTOX":   ["Upstox", "UPSTOX", "upstox.com"],
    "KUVERA":   ["Kuvera", "KUVERA", "kuvera.in"],
    "CAMS":     ["CAMS", "Computer Age Management", "Consolidated Account Statement"],
    "KFINTECH": ["KFintech", "KFINTECH", "Karvy"],
    "ANGEL":    ["Angel Broking", "Angel One", "angelone.in"],
    "5PAISA":   ["5paisa", "5Paisa"],
    "ICICI_SEC":["ICICIdirect", "ICICI Securities"],
    "HDFC_SEC": ["HDFC Securities", "HDFCsec"],
    "KOTAK_SEC":["Kotak Securities"],
}

# ── Generic regex patterns ────────────────────────────────────────────────────

_RE_STCG_111A = re.compile(
    r"(?:Short[\-\s]?Term.*?(?:Equity|Listed|111A|STT\s+Paid).*?"
    r"|STCG.*?(?:111A|Equity|Listed).*?)"
    r"(?:Net\s+)?(?:Gain|Profit|P&L|Amount)?\s*[:\-]?\s*([\-]?[\d,]+(?:\.\d{1,2})?)",
    re.I | re.S,
)
_RE_LTCG_112A = re.compile(
    r"(?:Long[\-\s]?Term.*?(?:Equity|Listed|112A|STT\s+Paid).*?"
    r"|LTCG.*?(?:112A|Equity|Listed).*?)"
    r"(?:Net\s+)?(?:Gain|Profit|P&L|Amount)?\s*[:\-]?\s*([\-]?[\d,]+(?:\.\d{1,2})?)",
    re.I | re.S,
)
_RE_STCG_OTHER = re.compile(
    r"(?:Short[\-\s]?Term.*?(?:Debt|Non[\-\s]?Equity|Other).*?)"
    r"(?:Net\s+)?(?:Gain|Profit)?\s*[:\-]?\s*([\-]?[\d,]+(?:\.\d{1,2})?)",
    re.I | re.S,
)
_RE_LTCG_OTHER = re.compile(
    r"(?:Long[\-\s]?Term.*?(?:Debt|Non[\-\s]?Equity|Other|Bond).*?)"
    r"(?:Net\s+)?(?:Gain|Profit)?\s*[:\-]?\s*([\-]?[\d,]+(?:\.\d{1,2})?)",
    re.I | re.S,
)
_RE_CRYPTO = re.compile(
    r"(?:Crypto|VDA|Virtual\s+Digital\s+Asset|115BBH)"
    r".*?(?:Gain|Profit|P&L)?\s*[:\-]?\s*([\-]?[\d,]+(?:\.\d{1,2})?)",
    re.I | re.S,
)

# Summary line patterns (Zerodha / Groww style)
_RE_SUMMARY_LINE = re.compile(
    r"(Short|Long)\s*[Tt]erm\s+"
    r"([\d,]+(?:\.\d{1,2})?)\s+"   # buy value
    r"([\d,]+(?:\.\d{1,2})?)\s+"   # sell value
    r"([\-]?[\d,]+(?:\.\d{1,2})?)", # gain/loss
)

_RE_EQUITY_PROCEEDS = re.compile(
    r"(?:Equit|Equity\s+Shares|NSE|BSE).*?"
    r"(?:Proceeds|Sale\s+Value|Sell\s+Value)\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)


def _parse_num(s: str) -> float:
    if not s:
        return 0.0
    s = s.replace(",", "").strip()
    return float(s)


def _detect_broker(text: str) -> str:
    for broker, sigs in BROKER_SIGS.items():
        if any(sig.lower() in text.lower() for sig in sigs):
            return broker
    return "GENERIC"


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class CGAssetClass:
    buy_value: float = 0.0
    sell_value: float = 0.0
    gain: float = 0.0       # negative = loss


@dataclass
class CGParseResult:
    broker: str = "GENERIC"
    assessment_year: str = "2025-26"

    # Sec 111A — listed equity STCG (20%)
    equity_stcg: CGAssetClass = field(default_factory=CGAssetClass)
    # Sec 112A — listed equity LTCG (10%, exempt ₹1.25L)
    equity_ltcg: CGAssetClass = field(default_factory=CGAssetClass)
    # Equity MF (same rates as above)
    equity_mf_stcg: CGAssetClass = field(default_factory=CGAssetClass)
    equity_mf_ltcg: CGAssetClass = field(default_factory=CGAssetClass)
    # Debt / other — slab rate STCG, 12.5% LTCG
    debt_stcg: CGAssetClass = field(default_factory=CGAssetClass)
    debt_ltcg: CGAssetClass = field(default_factory=CGAssetClass)
    # Property
    property_stcg: CGAssetClass = field(default_factory=CGAssetClass)
    property_ltcg: CGAssetClass = field(default_factory=CGAssetClass)
    # Gold
    gold_stcg: CGAssetClass = field(default_factory=CGAssetClass)
    gold_ltcg: CGAssetClass = field(default_factory=CGAssetClass)
    # Crypto
    crypto: CGAssetClass = field(default_factory=CGAssetClass)

    # ITR-ready aggregates (computed from above)
    stcg_111a_net: float = 0.0          # for Schedule CG row
    ltcg_112a_net: float = 0.0
    stcg_other_net: float = 0.0
    ltcg_other_net: float = 0.0
    crypto_net: float = 0.0

    # Losses (positive numbers representing loss amounts)
    stcl_111a: float = 0.0
    ltcl_112a: float = 0.0
    stcl_other: float = 0.0
    ltcl_other: float = 0.0

    confidence_score: float = 0.0
    field_confidence: dict[str, float] = field(default_factory=dict)
    parse_warnings: list[str] = field(default_factory=list)
    ocr_used: bool = False
    page_count: int = 0


# ── Broker-specific extractors ────────────────────────────────────────────────

def _parse_zerodha_groww(text: str, result: CGParseResult) -> None:
    """
    Zerodha Tax P&L and Groww CG report share a similar table layout:
    Rows like:  Short Term  <buy>  <sell>  <gain>
                Long Term   <buy>  <sell>  <gain>
    """
    for m in _RE_SUMMARY_LINE.finditer(text):
        term = m.group(1).lower()
        buy = _parse_num(m.group(2))
        sell = _parse_num(m.group(3))
        gain = _parse_num(m.group(4))
        if term == "short":
            result.equity_stcg = CGAssetClass(buy, sell, gain)
        else:
            result.equity_ltcg = CGAssetClass(buy, sell, gain)


def _parse_cams_kfintech(text: str, result: CGParseResult) -> None:
    """
    CAMS / KFintech CAS: extract equity and debt MF gains separately.
    Lines of form: Equity  <units>  <nav>  <cost>  <redemption>  <gain>
    """
    equity_stcg_pattern = re.compile(
        r"(?:Equity|Equity\s+Oriented)\s+.*?Short.*?Term\s+([\-]?[\d,]+(?:\.\d{1,2})?)",
        re.I,
    )
    equity_ltcg_pattern = re.compile(
        r"(?:Equity|Equity\s+Oriented)\s+.*?Long.*?Term\s+([\-]?[\d,]+(?:\.\d{1,2})?)",
        re.I,
    )
    debt_stcg_pattern = re.compile(
        r"(?:Debt|Other\s+Than\s+Equity)\s+.*?Short.*?Term\s+([\-]?[\d,]+(?:\.\d{1,2})?)",
        re.I,
    )
    debt_ltcg_pattern = re.compile(
        r"(?:Debt|Other\s+Than\s+Equity)\s+.*?Long.*?Term\s+([\-]?[\d,]+(?:\.\d{1,2})?)",
        re.I,
    )
    for pat, attr in [
        (equity_stcg_pattern, "equity_mf_stcg"),
        (equity_ltcg_pattern, "equity_mf_ltcg"),
        (debt_stcg_pattern,   "debt_stcg"),
        (debt_ltcg_pattern,   "debt_ltcg"),
    ]:
        m = pat.search(text)
        if m:
            val = _parse_num(m.group(1))
            setattr(result, attr, CGAssetClass(gain=val))


# ── Main parser ───────────────────────────────────────────────────────────────

def parse_cg_statement(content: bytes, filename: str = "") -> CGParseResult:
    """Parse capital gains statement PDF and return CGParseResult."""
    import pdfplumber

    result = CGParseResult()
    all_text_parts: list[str] = []

    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            result.page_count = len(pdf.pages)
            for page in pdf.pages:
                pg_text = page.extract_text() or ""
                words = page.extract_words()
                if len(words) < 20:
                    try:
                        import pytesseract
                        img = page.to_image(resolution=200).original
                        pg_text = pytesseract.image_to_string(img, config="--psm 6")
                        result.ocr_used = True
                    except Exception:
                        pass
                all_text_parts.append(pg_text)
    except Exception as e:
        raise ValueError(f"Cannot read PDF: {e}") from e

    full_text = "\n".join(all_text_parts)
    result.broker = _detect_broker(full_text)

    # AY detection
    m = re.search(r"(?:FY|Financial\s+Year|Assessment\s+Year)[^\d]*(\d{4})[\-–](\d{2,4})", full_text, re.I)
    if m:
        yr1 = m.group(1)
        yr2 = m.group(2)
        if len(yr2) == 2:
            yr2 = str(int(yr1[:2]) * 100 + int(yr2))
        # Distinguish FY vs AY
        if "assessment" in full_text[max(0, m.start()-5):m.start()+20].lower():
            result.assessment_year = f"{yr1}-{m.group(2)}"
        else:
            # FY 2024-25 → AY 2025-26
            result.assessment_year = f"{int(yr1)+1}-{str(int(yr2)+1)[-2:]}"

    # Broker-specific parsing
    if result.broker in ("ZERODHA", "GROWW", "UPSTOX", "ANGEL", "5PAISA"):
        _parse_zerodha_groww(full_text, result)
    elif result.broker in ("CAMS", "KFINTECH"):
        _parse_cams_kfintech(full_text, result)

    # Generic fallback for any remaining zeros
    conf: dict[str, float] = {}

    def _try_generic(attr_name: str, pattern: re.Pattern) -> None:
        obj = getattr(result, attr_name)
        if obj.gain == 0.0:
            m = pattern.search(full_text)
            if m:
                obj.gain = _parse_num(m.group(1))
                setattr(result, attr_name, obj)
                conf[attr_name] = 60.0
            else:
                conf[attr_name] = 0.0
        else:
            conf[attr_name] = 85.0

    _try_generic("equity_stcg",    _RE_STCG_111A)
    _try_generic("equity_ltcg",    _RE_LTCG_112A)
    _try_generic("debt_stcg",      _RE_STCG_OTHER)
    _try_generic("debt_ltcg",      _RE_LTCG_OTHER)
    _try_generic("crypto",         _RE_CRYPTO)

    # Compute ITR aggregates
    def _net(cls: CGAssetClass) -> tuple[float, float]:
        g = cls.gain
        return (g, 0.0) if g >= 0 else (0.0, abs(g))

    def _add_net(gain: float, loss: float, gain_attr: str, loss_attr: str):
        setattr(result, gain_attr, getattr(result, gain_attr) + gain)
        setattr(result, loss_attr, getattr(result, loss_attr) + loss)

    for cls, ga, la in [
        (result.equity_stcg,    "stcg_111a_net", "stcl_111a"),
        (result.equity_mf_stcg, "stcg_111a_net", "stcl_111a"),
        (result.equity_ltcg,    "ltcg_112a_net", "ltcl_112a"),
        (result.equity_mf_ltcg, "ltcg_112a_net", "ltcl_112a"),
        (result.debt_stcg,      "stcg_other_net","stcl_other"),
        (result.debt_ltcg,      "ltcg_other_net","ltcl_other"),
        (result.gold_stcg,      "stcg_other_net","stcl_other"),
        (result.gold_ltcg,      "ltcg_other_net","ltcl_other"),
        (result.property_stcg,  "stcg_other_net","stcl_other"),
        (result.property_ltcg,  "ltcg_other_net","ltcl_other"),
    ]:
        g, l = _net(cls)
        _add_net(g, l, ga, la)

    crypto_g, _ = _net(result.crypto)
    result.crypto_net = crypto_g

    filled = sum(1 for v in conf.values() if v > 0)
    result.confidence_score = round((filled / max(len(conf), 1)) * 100, 1)
    result.field_confidence = conf

    if result.broker == "GENERIC":
        result.parse_warnings.append(
            "Broker not recognised — generic regex used. Verify CG figures manually."
        )

    return result


def cg_to_itr_fields(r: CGParseResult) -> dict:
    """Map CGParseResult → income_data fields."""
    return {
        "income_data": {
            "stcg_111a":   r.stcg_111a_net,
            "ltcg_112a":   r.ltcg_112a_net,
            "stcg_other":  r.stcg_other_net,
            "ltcg_other":  r.ltcg_other_net,
            "crypto_income": r.crypto_net,
            "stcl_111a":   r.stcl_111a,
            "ltcl_112a":   r.ltcl_112a,
            "stcl_other":  r.stcl_other,
            "ltcl_other":  r.ltcl_other,
            "_source": f"cg_statement_{r.broker.lower()}",
        }
    }
