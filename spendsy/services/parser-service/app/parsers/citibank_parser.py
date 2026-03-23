from __future__ import annotations
import re
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, List

from app.core.base_parser import BaseParser
from app.core.schemas import ParserResponse, ParsedTransaction

logger = logging.getLogger(__name__)

class CitibankParser(BaseParser):
    """
    Dedicated parser for Citibank India savings account statements.
    Handles messy text extraction, multi-line descriptions, and 
    amount-index orientation.
    """

    @property
    def name(self) -> str:
        return "citibank_india"

    @property
    def version(self) -> str:
        return "1.1.0"

    @property
    def priority(self) -> int:
        return 80  # Higher priority than generic tabular

    def can_handle(self, content: bytes, text: str, **kwargs: Any) -> float:
        """
        Check if this is a Citibank statement.
        """
        if not text:
            return 0.0
        
        text_upper = text.upper()
        # Strong indicators for Citibank India
        if "CITIBANK" in text_upper and "SAVINGS ACCOUNT NUMBER" in text_upper:
            return 1.0
        if "CITI" in text_upper and "OPENING BALANCE" in text_upper and "CLOSING BALANCE" in text_upper:
            return 0.8
            
        return 0.0

    def parse(self, content: bytes, text: str, **kwargs: Any) -> ParserResponse:
        logger.info("citibank_parse_start")
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        # 1. Identify balances
        opening_balance = Decimal("0.0")
        closing_balance = Decimal("0.0")
        
        for i, line in enumerate(lines):
            if "Opening Balance" in line:
                match = re.search(r"Opening Balance\s+([\d,]+\.\d{2})", line)
                if match:
                    opening_balance = Decimal(match.group(1).replace(",", ""))
            if "Closing Balance :" in line:
                match = re.search(r"Closing Balance\s*:\s*\w+\s+([\d,]+\.\d{2})", line)
                if match:
                    closing_balance = Decimal(match.group(1).replace(",", ""))

        # 2. Transaction Extraction
        transactions: List[ParsedTransaction] = []
        current_tx: ParsedTransaction | None = None
        
        # Regex patterns
        date_pattern = re.compile(r"^(\d{2}/\d{2}/\d{4})")
        # Matches amounts like 1,234.56, --, or ----
        val_pattern = re.compile(r"([\d,]+\.\d{2}|--|----)")
        
        body_started = False
        for line in lines:
            if "Date Description" in line:
                body_started = True
                continue
            
            if not body_started:
                continue
                
            if "Total" in line:
                continue
                
            date_match = date_pattern.match(line)
            if date_match:
                date_str = date_match.group(1)
                try:
                    tx_date = datetime.strptime(date_str, "%d/%m/%Y").date()
                except ValueError:
                    continue
                
                rem_text = line[len(date_str):].strip()
                vals = val_pattern.findall(rem_text)
                
                # Cleanup description
                desc = rem_text
                for val in vals:
                    desc = desc.replace(val, "").strip()
                
                # Extract amounts
                deposit = Decimal("0.0")
                withdrawal = Decimal("0.0")
                balance = Decimal("0.0")
                
                if len(vals) >= 2:
                    v_dep = vals[0].replace(",", "")
                    v_with = vals[1].replace(",", "")
                    
                    deposit = Decimal(v_dep) if v_dep not in ("--", "----") else Decimal("0.0")
                    withdrawal = Decimal(v_with) if v_with not in ("--", "----") else Decimal("0.0")
                    
                    if len(vals) >= 3:
                        v_bal = vals[2].replace(",", "")
                        balance = Decimal(v_bal) if v_bal not in ("--", "----") else Decimal("0.0")
                
                current_tx = ParsedTransaction(
                    date=tx_date,
                    description=desc,
                    amount=float(deposit if deposit > 0 else withdrawal),
                    type="income" if deposit > 0 else "expense",
                    debit=float(withdrawal) if withdrawal > 0 else None,
                    credit=float(deposit) if deposit > 0 else None,
                    balance=float(balance),
                    confidence=1.0,
                    source="statement"
                )
                transactions.append(current_tx)
            elif current_tx:
                # Append to previous description (multi-line)
                current_tx.description += " " + line

        # 3. Final Reconciliation Score
        total_deps = sum(Decimal(str(t.credit or 0)) for t in transactions)
        total_withs = sum(Decimal(str(t.debit or 0)) for t in transactions)
        
        if not transactions:
             is_recon_ok = False
             score = 0.0
        else:
             calculated_closing = opening_balance + total_deps - total_withs
             is_recon_ok = abs(calculated_closing - closing_balance) < Decimal("0.01")
             # If balances were never found (stayed 0.0), we can't be 100% sure
             if opening_balance == 0 and closing_balance == 0:
                 score = 0.7 if transactions else 0.0
             else:
                 score = 1.0 if is_recon_ok else 0.5

        
        return ParserResponse(
            status="success" if transactions else "no_transactions",
            reconciliation_score=score,
            transactions=transactions,
            meta={
                "bank": "Citibank",
                "method": "citibank_custom",
                "reconciliation_ok": is_recon_ok,
                "opening_balance": float(opening_balance),
                "closing_balance": float(closing_balance),
                "total_deposits": float(total_deps),
                "total_withdrawals": float(total_withs),
            }
        )
