"""
Specialized prompts for different PDF types to optimize LLM extraction accuracy.
"""

SHARED_SCHEMA = """
Return ONLY a JSON object matching this schema:
{
  "document_type": string,
  "source_institution": string | null,
  "statement_period": { "from": "YYYY-MM-DD", "to": "YYYY-MM-DD" } | null,
  "account_id": string | null,
  "currency": string,
  "opening_balance": number | null,
  "closing_balance": number | null,
  "transactions": [
    {
      "date": "YYYY-MM-DD",
      "description": string,
      "type": "credit" | "debit" | "fee" | "interest" | "transfer" | "unknown",
      "amount": number,
      "running_balance": number | null,
      "reference": string | null
    }
  ],
  "extraction_confidence": "high" | "medium" | "low",
  "extraction_notes": string | null
}
"""

PROMPT_A = {
    "system": "You are a financial document OCR specialist. You receive raw OCR text extracted from a scanned document which may contain noise, misspellings, or formatting artifacts.",
    "user_template": f"""
Below is OCR-extracted text from a scanned financial document. Extract all transaction data despite any scanning noise. Apply these correction rules:
  - "O" and "0" are often confused — use context (dates vs numbers) to resolve
  - Decimals may appear as commas (European format) — normalize to periods
  - Dates may be fragmented (e.g. "Jan 15" "2024") — reconstruct to ISO 8601
  - If a field is unreadable, use null — never guess

{SHARED_SCHEMA}

OCR TEXT:
{{ocr_text}}
"""
}

PROMPT_B = {
    "system": "You are a financial data extraction engine specializing in structured ledgers, bank statements, and accounting exports with table-based layouts.",
    "user_template": f"""
Below is text extracted from a structured financial document (bank statement, ledger, or accounting export) with table formatting. The tables may use pipes, spaces, or aligned columns as delimiters.

Extract ALL transaction rows. Do not skip any rows.
Column headers may vary — map them to standard field names:
  - "Cr" / "Credit" / "Deposit" / "In" → type: "credit", positive amount
  - "Dr" / "Debit" / "Withdrawal" / "Out" → type: "debit", negative amount
  - "Ref" / "Reference No." / "Txn ID" → reference field
  - "Val Date" / "Value Date" / "Post Date" → use as date if transaction date absent

{SHARED_SCHEMA}

EXTRACTED TABLE TEXT:
{{table_text}}
"""
}

PROMPT_C = {
    "system": "You are a financial NLP specialist. You extract structured transaction data from prose-style financial documents — letters, summaries, investor reports, and narrative statements where transactions are described in flowing text.",
    "user_template": f"""
Below is text from a financial document without standard table formatting. 
Transactions may be described in sentences like:
  "On March 3rd, a payment of $1,200.00 was received from Acme Corp."
  "The account was debited USD 450 for service fees on 15-Feb-2024."

Extract every financial event mentioned. For ambiguous amounts, extract as-is and note uncertainty in extraction_notes.

{SHARED_SCHEMA}

DOCUMENT TEXT:
{{document_text}}
"""
}

def get_prompts_for_type(pdf_type: str) -> dict:
    if pdf_type == "ocr_scanned":
        return PROMPT_A
    elif pdf_type == "structured_ledger":
        return PROMPT_B
    else:
        return PROMPT_C
