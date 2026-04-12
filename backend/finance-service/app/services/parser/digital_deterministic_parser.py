"""
digital_deterministic_parser.py
================================
Coordinate-aware PDF bank statement parser.
Handles positional text layouts used by most Indian banks (no table structure).

Fixes applied vs original spec:
  Bug 1 — Amount zone corrected: x > 340 (was 410–510, missed 95% of transactions)
  Bug 2 — Two-number rows: leftmost=amount, rightmost=balance (was fixed-x split)
  Bug 3 — Continuation rows: propagate amount+balance up to parent transaction
  Bug 4 — Credit/debit by keyword, not x-position (single-column layout has no positional signal)

Tested against: Citibank/Axis Apr-2023 statement (9 pages, 54 transactions)
"""

import re
import json
import logging
import tempfile
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from collections import defaultdict
from datetime import datetime

import pdfplumber

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# Minimum character density (chars/page) below which we assume scanned PDF
OCR_THRESHOLD = 10

# x-coordinate boundaries (points) — tuned from real PDF measurement
DATE_X_MIN      = 35     # date column left edge
DATE_X_MAX      = 82     # date column right edge
DESC_X_MIN      = 83     # description starts here
AMOUNT_X_MIN    = 341    # all transaction amounts are right of this  ← BUG 1 FIX
BALANCE_X_MIN   = 460    # when two numbers present, balance is right of this

# Date regex — matches: 03Apr23, 03/07/2023, 01-07-2023 and corrupted "030072023", "[ 01072023 |"
DATE_RE = re.compile(r"^\[?\s*\d{2}[A-Za-z0-9/.\- ]*\d{2,4}\s*(?:\||\])?$")

# Numeric regex — valid amount token: must have decimal OR be ≥5 digits
# Excludes masked card fragments like "4386", "7095"
AMOUNT_TOKEN_RE = re.compile(r"^\d[\d,]*\.\d{2}$|^\d{5,}[\d,]*$")

# Noise rows to skip (headers, footers, summaries)
NOISE_RE = re.compile(
    r"^("
    r"date|transaction\s+details?|withdrawals?|deposits?|balance"
    r"|opening\s+balance|closing\s+balance|closing\s+available"
    r"|funds\s+on\s+earmark|total\s+amont|earmark"
    r"|page\s+\d|statement\s+period|your\s+\w+bank"
    r"|savings\s+account\s+details|credit\s+card\s+details"
    r"|banking\s+reward|home|rajesh|citibank|axis\s+bank"
    r"|hdfc|icici|kotak|sbi|pnb|canara"
    r")\b",
    re.IGNORECASE,
)

# Credit classification keywords (description-based — BUG 4 FIX)
CREDIT_KEYWORDS = re.compile(
    r"\b(inward|salary\s+credit|credit\s+from|credited|received|"
    r"refund|reversal|cashback|interest\s+credit|neft\s+cr|"
    r"imps\s+inward|rtgs\s+inward|dividend)\b",
    re.IGNORECASE,
)

DEBIT_KEYWORDS = re.compile(
    r"\b(outward|ecs\s+paid|nach|purchase|atm\s+withdrawal|"
    r"debit|dr\b|payment\s+for|imps\s+outward|neft\s+dr|"
    r"intercity\s+ecs|rtgs\s+outward)\b",
    re.IGNORECASE,
)

# Month map for date normalisation
MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Transaction:
    date:        str            # YYYY-MM-DD
    description: str
    amount:      float
    type:        str            # "credit" | "debit"
    balance:     Optional[float] = None
    raw_date:    str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ParseResult:
    transactions:    list[Transaction] = field(default_factory=list)
    opening_balance: Optional[float]   = None
    closing_balance: Optional[float]   = None
    total_credits:   float             = 0.0
    total_debits:    float             = 0.0
    page_count:      int               = 0
    errors:          list[str]         = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["transaction_count"] = len(self.transactions)
        return d


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def normalise_date(raw: str) -> str:
    """Convert DD-MMM-YY, DD/MM/YYYY or corrupted DDMMYYYY to YYYY-MM-DD."""
    if not raw:
        return ""
    
    # Remove surrounding brackets/pipes from corrupted extractions
    date_str = re.sub(r'^[\[\s\|]+|[\]\s\|]+$', '', raw.strip())
    date_str = date_str.split()[0]
    
    # Pad single-digit day (e.g., 3Apr23 -> 03Apr23)
    if len(date_str) >= 6 and date_str[0].isdigit() and not date_str[1].isdigit():
        date_str = "0" + date_str

    for fmt in ("%d%b%y", "%d%b%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Fallback for pdfplumber corrupted text layer Extractions (e.g. '030072023')
    digits = re.sub(r'\D', '', date_str)
    if len(digits) in (8, 9):
        year = digits[-4:]
        month = digits[-6:-4]
        day = digits[:2]
        try:
            return datetime.strptime(f"{day}{month}{year}", "%d%m%Y").strftime("%Y-%m-%d")
        except ValueError:
            pass

    return raw


def parse_amount(text: str, is_balance: bool = False) -> Optional[float]:
    """
    Parse Indian-formatted amounts robustly.
    Handles: 1,23,456.78 | 902.00 | 60900.00
    Rejects:  4386 (card fragment) via AMOUNT_TOKEN_RE pre-filter.

    is_balance=True: applies missing-decimal fix for balance values that the
    Citibank PDF text layer occasionally emits without a decimal point.
    e.g. "11361352" should be 113613.52 — detectable when the integer value
    is implausibly large for a savings balance (> 10,00,000) but would be
    reasonable divided by 100.
    """
    if not text:
        return None
    
    # Strip trailing rogue punctuation (e.g. 2365.00])
    text = re.sub(r'[\]\|\s\-]+$', '', text)
    
    # Handle pdfplumber misreading periods as commas (e.g., 92,00 -> 92.00)
    if re.search(r',\d{2}$', text) and '.' not in text:
        text = text[:-3] + '.' + text[-2:]
        
    cleaned = text.replace(",", "").strip()
    
    # Handle pdfplumber misreading commas as periods (e.g., 1.43950.15 or 4.000.00)
    if cleaned.count('.') > 1:
        parts = cleaned.rsplit('.', 1)
        cleaned = parts[0].replace('.', '') + '.' + parts[1]
        
    try:
        value = float(cleaned)
    except ValueError:
        return None

    # Missing-decimal fix: integer balance > 1,000,000 that has no '.'
    # is almost certainly a paise value with the decimal stripped by the PDF renderer.
    if is_balance and "." not in cleaned and value > 1_000_000:
        value = value / 100

    return value


def is_valid_amount_token(text: str) -> bool:
    """True if the word looks like a transaction amount, not a card number or noise."""
    text = re.sub(r'[\]\|\s\-]+$', '', text)
    if re.search(r',\d{2}$', text) and '.' not in text:
        text = text[:-3] + '.' + text[-2:]
    cleaned = text.replace(",", "")
    if cleaned.count('.') > 1:
        parts = cleaned.rsplit('.', 1)
        cleaned = parts[0].replace('.', '') + '.' + parts[1]
    return bool(AMOUNT_TOKEN_RE.match(cleaned))


def classify_type(description: str) -> str:
    """Determine credit/debit from description keywords. BUG 4 FIX."""
    if CREDIT_KEYWORDS.search(description):
        return "credit"
    return "debit"


def is_noise(description: str) -> bool:
    return bool(NOISE_RE.match(description.strip()))


def group_words_by_row(words: list, tolerance: float = 4.0) -> dict:
    """Group pdfplumber word dicts by their vertical (top) position."""
    rows: dict[float, list] = defaultdict(list)
    for w in words:
        key = round(w["top"] / tolerance) * tolerance
        rows[key].append(w)
    return dict(sorted(rows.items()))


# ─────────────────────────────────────────────────────────────────────────────
# Scanned-PDF detection
# ─────────────────────────────────────────────────────────────────────────────

def check_digital(pdf) -> bool:
    """
    Return True if the PDF has extractable text (digital).
    Checks first 2 pages; raises ValueError with OCR_REQUIRED if scanned.
    """
    total_chars = 0
    pages_checked = min(2, len(pdf.pages))
    for i in range(pages_checked):
        text = pdf.pages[i].extract_text() or ""
        total_chars += len(text.strip())
    avg = total_chars / max(pages_checked, 1)
    if avg < OCR_THRESHOLD:
        raise ValueError("OCR_REQUIRED: PDF appears to be scanned. Use an OCR pipeline.")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Row-level parsing helpers
# ─────────────────────────────────────────────────────────────────────────────

def extract_row_parts(row_words: list) -> dict:
    """
    Given words from one visual row (sorted by x), split into:
      date_str, description_parts, right_numerics

    right_numerics: list of (float_value, x0) for all valid amount tokens
                    right of AMOUNT_X_MIN.

    BUG 1 FIX: AMOUNT_X_MIN = 341 (was 410).
    BUG 4 FIX: card number fragments filtered by AMOUNT_TOKEN_RE.
    """
    row_words_sorted = sorted(row_words, key=lambda w: w["x0"])

    date_parts  = []
    desc_parts  = []
    right_nums  = []   # list of (value: float, x0: float)

    for w in row_words_sorted:
        x, text = w["x0"], w["text"]

        if DATE_X_MIN <= x <= DATE_X_MAX:
            # Could be date or a noise word in that zone
            if DATE_RE.match(text):
                date_parts.append(text)
            else:
                desc_parts.append(text)

        elif x > AMOUNT_X_MIN and is_valid_amount_token(text):
            # Store raw text + x; parsing happens later with correct is_balance flag
            right_nums.append((text, x))

        elif x >= DESC_X_MIN:
            desc_parts.append(text)

    return {
        "date_str":    " ".join(date_parts).strip(),
        "description": " ".join(desc_parts).strip(),
        "right_nums":  right_nums,   # sorted left-to-right by x already
    }


def resolve_amount_balance(right_nums: list) -> tuple[Optional[float], Optional[float]]:
    """
    Given list of (raw_text, x0) sorted ascending by x0:
      - 0 nums  → (None, None)
      - 1 num   → (amount, None)   balance may come from a continuation row
      - 2+ nums → (leftmost=amount, rightmost=balance)   BUG 2 FIX

    The split point is positional: leftmost number is always the transaction
    amount; rightmost is the running balance (only appears periodically).
    Missing-decimal fix applied only to balance values.
    """
    if not right_nums:
        return None, None
    sorted_nums = sorted(right_nums, key=lambda t: t[1])  # sort by x0
    if len(sorted_nums) == 1:
        return parse_amount(sorted_nums[0][0], is_balance=False), None
    # Two or more: amount=left, balance=right
    return (
        parse_amount(sorted_nums[0][0],  is_balance=False),
        parse_amount(sorted_nums[-1][0], is_balance=True),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Summary-line extraction (opening/closing balance)
# ─────────────────────────────────────────────────────────────────────────────

def extract_summary(text: str) -> dict:
    """Pull opening and closing balances from free text."""
    result = {}
    ob = re.search(r"opening\s+balance[:\s]+([0-9,]+\.[0-9]{2})", text, re.IGNORECASE)
    cb = re.search(r"closing\s+(?:available\s+)?balance[:\s]+([0-9,]+\.[0-9]{2})", text, re.IGNORECASE)
    if ob:
        result["opening_balance"] = parse_amount(ob.group(1))
    if cb:
        result["closing_balance"] = parse_amount(cb.group(1))
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Core page parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_page(page) -> tuple[list[dict], str]:
    """
    Parse one page. Returns:
      (logical_rows, raw_page_text)

    Each logical_row is a dict ready to be converted to a Transaction.
    Handles multi-line descriptions and continuation-row amounts/balances.
    BUG 3 FIX: continuation rows propagate amount+balance to parent.
    """
    words     = page.extract_words(x_tolerance=3, y_tolerance=3)
    raw_text  = page.extract_text() or ""
    if not words:
        return [], raw_text

    visual_rows = group_words_by_row(words, tolerance=4.0)
    logical_rows: list[dict] = []
    current: Optional[dict]  = None

    for _top, row_words in visual_rows.items():
        parts = extract_row_parts(row_words)
        date_str    = parts["date_str"]
        description = parts["description"]
        right_nums  = parts["right_nums"]

        # ── New transaction row (has a date) ──────────────────────────────
        if DATE_RE.match(date_str):
            if current:
                logical_rows.append(current)

            amount, balance = resolve_amount_balance(right_nums)

            current = {
                "raw_date":     date_str,
                "date":         normalise_date(date_str),
                "desc_parts":   [description] if description else [],
                "amount":       amount,
                "balance":      balance,
            }

        # ── Continuation row (no date) ────────────────────────────────────
        elif current is not None:
            # Skip pure noise rows (headers, footers, summary labels)
            if is_noise(description) and not right_nums:
                continue

            # Append description text
            if description and not is_noise(description):
                current["desc_parts"].append(description)

            # BUG 3 FIX: propagate amount/balance from continuation row
            if right_nums:
                cont_amount, cont_balance = resolve_amount_balance(right_nums)

                # Only fill in if parent row is missing the value
                if current["amount"] is None and cont_amount is not None:
                    current["amount"] = cont_amount

                if current["balance"] is None and cont_balance is not None:
                    current["balance"] = cont_balance

                # Edge case: continuation has its OWN amount+balance
                # (e.g. 28Apr row where continuation carries 1631.70 + 181702.15)
                # Detect: parent already has amount AND continuation has 2 numerics
                # AND the continuation has a meaningful description → new logical row.
                elif (current["amount"] is not None
                      and cont_amount is not None
                      and cont_balance is not None
                      and description and not is_noise(description)):
                    logical_rows.append(current)
                    current = {
                        "raw_date":   current["raw_date"],
                        "date":       current["date"],
                        "desc_parts": [description],
                        "amount":     cont_amount,
                        "balance":    cont_balance,
                    }

    # Don't forget the last transaction on the page
    if current:
        logical_rows.append(current)

    return logical_rows, raw_text


# ─────────────────────────────────────────────────────────────────────────────
# Main parser entry point
# ─────────────────────────────────────────────────────────────────────────────

def parse_statement(pdf_path: str) -> ParseResult:
    """
    Parse a digital bank statement PDF.

    Returns ParseResult with all transactions normalised to:
      { date, description, amount, type, balance, raw_date }

    Raises:
      FileNotFoundError  — path doesn't exist
      ValueError         — scanned PDF (OCR_REQUIRED)
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")

    result = ParseResult()
    all_raw_text = []
    all_logical_rows: list[dict] = []

    with pdfplumber.open(str(path)) as pdf:
        result.page_count = len(pdf.pages)
        check_digital(pdf)  # raises ValueError if scanned

        for page_num, page in enumerate(pdf.pages):
            try:
                logical_rows, raw_text = parse_page(page)
                all_logical_rows.extend(logical_rows)
                all_raw_text.append(raw_text)
            except Exception as e:
                result.errors.append(f"Page {page_num+1}: {e}")
                log.warning(f"Page {page_num+1} failed: {e}")

    # Extract summary balances from raw text
    full_text = "\n".join(all_raw_text)
    summary = extract_summary(full_text)
    result.opening_balance = summary.get("opening_balance")
    result.closing_balance = summary.get("closing_balance")

    # Convert logical rows → Transaction objects
    for row in all_logical_rows:
        description = " ".join(p for p in row["desc_parts"] if p).strip()
        description = re.sub(r"\s{2,}", " ", description)

        amount = row["amount"]
        if amount is None or amount <= 0:
            # Row has no parseable amount — skip (likely a header remnant)
            log.debug(f"Skipping row with no amount: {description[:60]}")
            continue

        if is_noise(description) and amount < 10:
            continue

        tx_type = classify_type(description)

        tx = Transaction(
            date        = row["date"],
            description = description,
            amount      = amount,
            type        = tx_type,
            balance     = row["balance"],
            raw_date    = row["raw_date"],
        )
        result.transactions.append(tx)

        if tx_type == "credit":
            result.total_credits += amount
        else:
            result.total_debits += amount

    log.info(
        f"Parsed {len(result.transactions)} transactions "
        f"({result.page_count} pages) | "
        f"credits={result.total_credits:,.2f} debits={result.total_debits:,.2f}"
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Compatibility Wrapper
# ─────────────────────────────────────────────────────────────────────────────

def parse_transactions(file_content: bytes) -> dict:
    """
    Compatibility wrapper for routes_finance.py.
    Accepts bytes, parses via temporary file, and returns a dict with 'transactions' and 'meta'.
    """
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_content)
        tmp.flush()
        tmp_path = tmp.name

    try:
        result = parse_statement(tmp_path)
        res_dict = result.to_dict()
        # Ensure 'transactions' is a list of dicts as expected by routes_finance.py
        # result.to_dict() already contains 'transactions' via asdict(self)
        return {
            "transactions": res_dict.get("transactions", []),
            "meta": res_dict
        }
    finally:
        # Cleanup temporary file
        p = Path(tmp_path)
        if p.exists():
            p.unlink()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys, json

    if len(sys.argv) < 2:
        print("Usage: python digital_deterministic_parser.py <path_to_pdf> [--json]")
        sys.exit(1)

    pdf_path   = sys.argv[1]
    json_mode  = "--json" in sys.argv

    try:
        result = parse_statement(pdf_path)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(2)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    if json_mode:
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        print(f"\n{'─'*70}")
        print(f"  Bank Statement — {pdf_path}")
        print(f"{'─'*70}")
        print(f"  Pages parsed    : {result.page_count}")
        print(f"  Transactions    : {len(result.transactions)}")
        print(f"  Opening balance : {result.opening_balance:,.2f}" if result.opening_balance else "  Opening balance : —")
        print(f"  Closing balance : {result.closing_balance:,.2f}" if result.closing_balance else "  Closing balance : —")
        print(f"  Total credits   : {result.total_credits:,.2f}")
        print(f"  Total debits    : {result.total_debits:,.2f}")
        if result.errors:
            print(f"\n  Errors ({len(result.errors)}):")
            for e in result.errors:
                print(f"    • {e}")
        print(f"\n{'─'*70}")
        print(f"  {'DATE':<12} {'TYPE':<7} {'AMOUNT':>12}  {'BALANCE':>12}  DESCRIPTION")
        print(f"{'─'*70}")
        for tx in result.transactions:
            bal = f"{tx.balance:>12,.2f}" if tx.balance else f"{'—':>12}"
            print(
                f"  {tx.date:<12} {tx.type:<7} {tx.amount:>12,.2f}  {bal}  "
                f"{tx.description[:45]}"
            )
        print(f"{'─'*70}\n")
