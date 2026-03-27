import logging
import re
import tempfile
import time
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import pdfplumber

logger = logging.getLogger("finance.parser.deterministic")

# ───────────────────────── x-column boundaries ───────────────────────────────
DATE_COL_X_MIN  =  35    # transaction date tokens start here
DATE_COL_X_MAX  =  82    # transaction date tokens end before here
AMOUNT_X_MIN    = 410    # all amount-column tokens live above x=410 (some rows have amounts at 414)
BALANCE_X_MIN   = 510    # balance column starts here

# ───────────────────────── regex ─────────────────────────────────────────────
DATE_8     = re.compile(r'^\d{8,9}$')                        # DDMMYYYY (or 030072023 typo → drop leading 0)
DATE_SLASH = re.compile(r'^\d{2}[/\-]\d{2}[/\-]?\d{2,4}$')   # DD/MM/YYYY or 19/072023
# Amount token: optional bracket prefix/suffix, supports dot thousands  e.g. 4.000.00] or 3,000.00
AMOUNT_TOKEN = re.compile(r'[\[\]]*(\d[\d.,]+\d)[\[\]]*$')
AMOUNT_STRICT = re.compile(r'^\d[\d.,]+\d$')
# Integer amounts (no decimal): 4 or 5 digits e.g. 43000 → 430.00, 18000 → 180.00
INT_AMOUNT_RE = re.compile(r'^\d{3,6}$')

NOISE_RE = re.compile(r'^[\-–—|_~\[\]]+$')

# Summary/total rows that must NEVER merge with real transactions
TOTAL_ROW_RE = re.compile(r'\bTotal\b', re.IGNORECASE)

SKIP_RE = re.compile(
    r'\b(opening\s*balance|closing\s*balance|statement\s*of\s*account'
    r'|date\s*description|deposits|withdrawals|^\s*-\s*total\s*$|\btotal\b'
    r'|funds\s*in|money\s*multiplier|withdrawable'
    r'|line\s*amount|earmarking|multi\s*deposit'
    r'|summary\s*of\s*account|citibank|axis\s*bank'
    r'|savings\s*account|account\s*number|closing balance)\b',
    re.IGNORECASE,
)

CREDIT_KW = re.compile(r'\b(inward|credit|cr)\b', re.IGNORECASE)
DEBIT_KW  = re.compile(r'\b(outward|debit|dr|withdrawal|paid|ecs|payment)\b', re.IGNORECASE)

Y_TOL = 4.0


# ───────────────────────── amount parser ────────────────────────────────────
def _clean_amount_token(raw: str) -> str | None:
    """Strip brackets and normalise dot-thousands to comma-thousands."""
    # Strip surrounding [ ] characters
    text = raw.strip('[]')
    # Match digits/dots/commas
    m = AMOUNT_STRICT.match(text)
    if not m:
        # Try extracting from inside brackets e.g. '4.000.00]'
        m2 = AMOUNT_TOKEN.search(raw)
        if m2:
            text = m2.group(1)
        else:
            return None
    return text


def _parse_amount_str(text: str) -> Decimal | None:
    """
    Parse Indian-format amounts:
      3,000.00  → 3000.00
      4.000.00  → 4000.00  (dot as thousands sep)
      97.730.15 → 97730.15
      2365.00   → 2365.00
      92,00     → 92.00    (comma as decimal)
      43000     → 430.00   (integer with implicit decimal, div by 100)
    """
    clean = text.strip('[]').strip()
    if not clean:
        return None

    # Pure integer (no decimal separator): treat as paise → rupees
    if re.match(r'^\d+$', clean):
        try:
            val = Decimal(clean) / 100
            return val if val > 0 else None
        except Exception:
            return None

    # Comma as decimal (e.g. 92,00 — European style sometimes in scanned PDFs)
    comma_count = clean.count(',')
    dot_count   = clean.count('.')
    if comma_count == 1 and dot_count == 0:
        clean = clean.replace(',', '.')
    elif comma_count > 0 and dot_count <= 1:
        # Standard: 3,000.00
        clean = clean.replace(',', '')
    elif dot_count > 1:
        # Indian dot-thousands: 4.000.00 or 97.730.15
        parts = clean.split('.')
        paise  = parts[-1]
        rupees = ''.join(parts[:-1])
        clean  = rupees + '.' + paise
    # else: simple 2365.00 → leave as-is

    try:
        val = Decimal(clean)
        return val if val > 0 else None
    except Exception:
        return None


def _parse_amount(raw: str) -> Decimal | None:
    cleaned = _clean_amount_token(raw)
    if cleaned is None:
        return None
    return _parse_amount_str(cleaned)


# ───────────────────────── date normaliser ───────────────────────────────────
def _normalize_date(token: str) -> str | None:
    # Handle 8/9-digit compact dates
    # Handle typos like '030072023' (extra 0) -> '03072023'
    if DATE_8.match(token):
        if len(token) == 9:
            # Assume extra 0 at index 2: 03[0]072023
            digits = token[:2] + token[3:]
        else:
            digits = token
        
        d, m, y = digits[:2], digits[2:4], digits[4:]
        try:
            return datetime(int(y), int(m), int(d)).strftime('%Y-%m-%d')
        except ValueError:
            return None

    if DATE_SLASH.match(token):
        # Handle malformed dates like '19/072023'
        digits = re.sub(r'[/\-]', '', token)
        if len(digits) == 8:
            d, m, y = digits[:2], digits[2:4], digits[4:]
            try:
                return datetime(int(y), int(m), int(d)).strftime('%Y-%m-%d')
            except ValueError:
                pass
        
        # Standard split
        parts = re.split(r'[/\-]', token)
        if len(parts) == 3:
            d, m, y = parts
            if len(y) == 2:
                y = '20' + y
            try:
                return datetime(int(y), int(m), int(d)).strftime('%Y-%m-%d')
            except ValueError:
                return None
    return None


# ───────────────────────── grouping helpers ──────────────────────────────────
def _group_by_row(words: list[dict]) -> list[list[dict]]:
    if not words:
        return []
    rows: list[list[dict]] = []
    cur_row  = [words[0]]
    cur_top  = words[0]['top']
    for w in words[1:]:
        if abs(w['top'] - cur_top) <= Y_TOL:
            cur_row.append(w)
        else:
            rows.append(cur_row)
            cur_row  = [w]
            cur_top  = w['top']
    rows.append(cur_row)
    return rows


def _has_tx_date(row_words: list[dict]) -> bool:
    return any(
        DATE_COL_X_MIN <= w['x0'] <= DATE_COL_X_MAX
        and _normalize_date(w['text']) is not None
        for w in row_words
    )


def _assemble_logical_rows(visual_rows: list[list[dict]]) -> list[list[dict]]:
    """
    Merge continuation lines (no date-column word) into the previous row.
    NEVER merge rows that look like a Total/Summary line.
    """
    logical: list[list[dict]] = []
    for vrow in visual_rows:
        row_text = ' '.join(w['text'] for w in vrow)
        is_total_row = bool(TOTAL_ROW_RE.search(row_text))
        
        if _has_tx_date(vrow) or not logical:
            if not is_total_row:
                logical.append(list(vrow))
        else:
            if is_total_row:
                # Do not merge total row into transaction
                continue
            logical[-1].extend(vrow)
    return logical


# ───────────────────────── row processor ────────────────────────────────────
def _process_row(row_words: list[dict]) -> dict | None:
    sorted_w = sorted(row_words, key=lambda w: w['x0'])

    date_str:    str | None    = None
    desc_parts:  list[str]     = []
    tx_amounts:  list[tuple[float, Decimal]] = []
    bal_amounts: list[tuple[float, Decimal]] = []

    for w in sorted_w:
        raw  = w['text'].strip()
        text = raw.strip('[]')
        if not text or NOISE_RE.match(raw):
            continue

        x0 = w['x0']

        # ── date column ──
        if DATE_COL_X_MIN <= x0 <= DATE_COL_X_MAX:
            cand = _normalize_date(raw)
            if cand:
                date_str = cand
            continue  # don't add date text to description

        # ── amount/balance columns ──
        if x0 >= AMOUNT_X_MIN:
            # Try to parse as amount (may have trailing/leading brackets or Indian format)
            val = _parse_amount(raw)
            if val is None:
                # Try integer amounts (e.g. 43000, 17600, 18000)
                int_only = raw.strip('[]').strip()
                if INT_AMOUNT_RE.match(int_only):
                    val = _parse_amount_str(int_only)
            if val:
                if x0 >= BALANCE_X_MIN:
                    bal_amounts.append((x0, val))
                else:
                    tx_amounts.append((x0, val))
                continue
            # Noise/separator only – skip
            if NOISE_RE.match(raw.strip('[]')) or raw.strip('[]') in ('-', '–', '|', '~', '—', 'siIs', 's'):
                continue

        # ── description ──
        desc_parts.append(text)

    if not date_str:
        return None

    desc_text = ' '.join(desc_parts).strip()
    if SKIP_RE.search(desc_text):
        return None

    if not tx_amounts and not bal_amounts:
        return None

    # Prefer the first TX amount
    if not tx_amounts:
        return None

    amt_x0, amount = tx_amounts[0]
    balance = bal_amounts[0][1] if bal_amounts else None

    # Determine credit / debit
    # Primary signal: Column placement (x0)
    # Midpoint around 445 is a safe threshold for Citi/Axis format
    if amt_x0 < 445:
        tx_type = 'credit'
    else:
        tx_type = 'debit'

    # Secondary signal: Description keywords (override if very clear)
    if CREDIT_KW.search(desc_text) and not DEBIT_KW.search(desc_text):
        tx_type = 'credit'
    elif DEBIT_KW.search(desc_text) and not CREDIT_KW.search(desc_text):
        tx_type = 'debit'

    clean_desc = re.sub(r'\s+', ' ', desc_text).strip() or 'Parsed Transaction'

    return {
        'date':        date_str,
        'description': clean_desc,
        'amount':      float(amount.quantize(Decimal('0.01'))),
        'type':        tx_type,
        'balance':     float(balance.quantize(Decimal('0.01'))) if balance else None,
        'source':      'statement',
    }


# ───────────────────────── extraction ────────────────────────────────────────
def extract_lines(file_content: bytes) -> list[dict]:
    all_words: list[dict] = []
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(file_content)
        tmp.flush()
        try:
            with pdfplumber.open(tmp.name) as pdf:
                for page in pdf.pages:
                    words = page.extract_words(x_tolerance=3, y_tolerance=3)
                    all_words.extend(words)
        except Exception as e:
            logger.error(f'pdfplumber extraction failed: {e}')
            raise ValueError('Failed to extract text from PDF. It may be an OCR/image file.')
    return all_words


# ───────────────────────── public API ────────────────────────────────────────
def parse_transactions(file_content: bytes) -> dict:
    start = time.time()

    try:
        words = extract_lines(file_content)
    except Exception as e:
        raise ValueError(str(e))

    visual_rows  = _group_by_row(words)
    logical_rows = _assemble_logical_rows(visual_rows)

    transactions: list[dict] = []
    failed = 0

    for row in logical_rows:
        txn = _process_row(row)
        if txn and txn['amount'] > 0:
            transactions.append(txn)
        elif _has_tx_date(row):
            failed += 1

    elapsed = time.time() - start
    logger.info(
        'Column-aware parse done. found=%d failures=%d time=%.2fs',
        len(transactions), failed, elapsed,
    )

    return {
        'transactions': transactions,
        'meta': {
            'total_rows':           len(logical_rows),
            'parsed_rows':          len(transactions),
            'failed_rows':          failed,
            'parsing_time_seconds': elapsed,
        },
    }
