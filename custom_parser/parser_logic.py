from __future__ import annotations
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from .schemas import Transaction, StatementResponse

def parse_statement_text(raw_text: str) -> StatementResponse:
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    
    # 1. IDENTIFY ACCOUNT HEADERS
    account_holder = "Unknown"
    account_number = "Unknown"
    opening_balance = Decimal("0.0")
    closing_balance = Decimal("0.0")
    
    # Simple header search
    for i, line in enumerate(lines):
        if "Savings Account Number :" in line:
            account_number = line.split(":")[-1].strip()
            # Name is usually on the next line or nearby
            if i + 1 < len(lines):
                account_holder = lines[i+1].strip()
        if "Opening Balance" in line:
            match = re.search(r"Opening Balance\s+([\d,]+\.\d{2})", line)
            if match:
                opening_balance = Decimal(match.group(1).replace(",", ""))
        if "Closing Balance :" in line:
            match = re.search(r"Closing Balance\s*:\s*\w+\s+([\d,]+\.\d{2})", line)
            if match:
                closing_balance = Decimal(match.group(1).replace(",", ""))

    # 2. ROW MATCHING AND MERGE LOGIC
    transactions = []
    current_tx = None
    
    # Regex for date: DD/MM/YYYY
    date_pattern = re.compile(r"^(\d{2}/\d{2}/\d{4})")
    
    body_started = False
    for line in lines:
        if "Date Description" in line:
            body_started = True
            continue
        if not body_started:
            continue
        if "Total" in line and "--" in line:
            break
            
        date_match = date_pattern.match(line)
        if date_match:
            # New Transaction Row
            date_str = date_match.group(1)
            tx_date = datetime.strptime(date_str, "%d/%m/%y" if len(date_str.split("/")[-1]) == 2 else "%d/%m/%Y").date()
            
            # Extract parts: Date Description [Deposits] [Withdrawals] [Balance]
            # Since the text is messy, we use regex to find amounts at the end
            rem_text = line[len(date_str):].strip()
            
            # Pattern for amounts: usually something like "-- 3,000.00 --" or "2,000.00 -- ----"
            # We look for decimals and "--"
            parts = re.split(r"\s+", rem_text)
            
            # This is tricky with raw text. Let's try a more robust approach.
            # We look for all numbers with .XX, --, or ----
            val_pattern = re.compile(r"([\d,]+\.\d{2}|--|----)")
            vals = val_pattern.findall(rem_text)
            
            desc = rem_text
            for val in vals:
                desc = desc.replace(val, "").strip()
            
            # Assign amounts based on position (Deposits, Withdrawals, Balance)
            deposit = Decimal("0.0")
            withdrawal = Decimal("0.0")
            balance = Decimal("0.0")
            
            if len(vals) >= 2:
                # We need at least Deposit and Withdrawal
                # If there are 3+, the last one is Balance
                
                # Help determine which belongs where:
                # Usually: [Deposits] [Withdrawals] [Balance]
                # If len == 3: deps=vals[0], withs=vals[1], bal=vals[2]
                # If len == 2: deps=vals[0], withs=vals[1]. Balance unknown or 0.
                
                v_dep = vals[0].replace(",", "")
                v_with = vals[1].replace(",", "")
                
                deposit = Decimal(v_dep) if v_dep not in ("--", "----") else Decimal("0.0")
                withdrawal = Decimal(v_with) if v_with not in ("--", "----") else Decimal("0.0")
                
                if len(vals) >= 3:
                    v_bal = vals[2].replace(",", "")
                    balance = Decimal(v_bal) if v_bal not in ("--", "----") else Decimal("0.0")
            
            current_tx = Transaction(
                date=tx_date,
                description=desc,
                deposits=deposit,
                withdrawals=withdrawal,
                balance=balance
            )
            transactions.append(current_tx)
        else:
            # MERGE LOGIC: Merge with previous description
            if current_tx:
                # Check if it's not a noise line
                if not line.startswith("--"):
                    current_tx.description += " " + line

    # 3. RECONCILIATION
    total_deposits = sum(t.deposits for t in transactions)
    total_withdrawals = sum(t.withdrawals for t in transactions)
    
    # Verification: Opening + Deposits - Withdrawals == Closing
    # If balances are present on rows, we can also check the last one.
    last_row_balance = transactions[-1].balance if transactions else opening_balance
    reconciliation_ok = (opening_balance + total_deposits - total_withdrawals) == closing_balance
    
    error_flags = []
    if not reconciliation_ok:
        error_flags.append(f"Math mismatch: Expected {closing_balance}, Calculated {opening_balance + total_deposits - total_withdrawals}")

    return StatementResponse(
        account_holder=account_holder,
        account_number=account_number,
        opening_balance=opening_balance,
        closing_balance=closing_balance,
        transactions=transactions,
        reconciliation_ok=reconciliation_ok,
        total_deposits=total_deposits,
        total_withdrawals=total_withdrawals,
        error_flags=error_flags
    )
