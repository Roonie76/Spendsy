#!/usr/bin/env python3
"""
run_pipeline.py — Dev CLI to run the full bank statement parser on a local file.

Usage:
    ./venv/bin/python run_pipeline.py Jan.pdf
    ./venv/bin/python run_pipeline.py statement.xlsx
"""
import os
import sys
import json
import time
from pathlib import Path

# Add parser-service to Python path
sys.path.insert(0, str(Path(__file__).parent / "spendsy" / "services" / "parser-service"))

from app.core.bank_orchestrator import BankStatementOrchestrator


def run(file_path: str) -> None:
    path = Path(file_path)
    if not path.exists():
        print(f"[Error] File not found: {file_path}")
        sys.exit(1)

    print(f"\n{'─'*60}")
    print(f"  Spendsy Bank Statement Parser")
    print(f"  File : {path.name}")
    print(f"{'─'*60}\n")

    with open(path, "rb") as f:
        content = f.read()

    orchestrator = BankStatementOrchestrator()
    result = orchestrator.parse(content, filename=path.name)

    # ── Summary ────────────────────────────────────────────────────────
    print(f"Bank identified  : {result.bank_id}")
    print(f"PDF type         : {result.pdf_type}")
    print(f"Transactions     : {result.transaction_count}")
    print(f"Parse time       : {result.parse_time_ms} ms")
    print(f"Balance clean    : {'✓' if result.reconciliation.is_clean else '✗ (' + str(len(result.reconciliation.drift_rows)) + ' drift rows)'}")

    # ── Account Info ───────────────────────────────────────────────────
    ai = result.account_info
    print(f"\nAccount holder   : {ai.account_holder or '—'}")
    print(f"Account number   : {ai.account_number or '—'}")
    print(f"IFSC code        : {ai.ifsc_code or '—'}")

    # ── Transactions sample ────────────────────────────────────────────
    if result.transactions:
        print(f"\n{'─'*60}")
        print(f"  Sample Transactions (up to 10)")
        print(f"{'─'*60}")
        print(f"{'Date':<12} {'Description':<35} {'Debit':>10} {'Credit':>10} {'Type':<8}")
        print(f"{'─'*12} {'─'*35} {'─'*10} {'─'*10} {'─'*8}")
        for tx in result.transactions[:10]:
            dr  = f"{tx.debit:.2f}"  if tx.debit  else "       —"
            cr  = f"{tx.credit:.2f}" if tx.credit else "       —"
            print(f"{str(tx.date):<12} {tx.description[:34]:<35} {dr:>10} {cr:>10} {tx.transaction_type:<8}")
    else:
        print("\n[!] No transactions extracted.")
        print("    This may mean:\n"
              "    • The PDF is scanned (install PaddleOCR for OCR support)\n"
              "    • The table format is not yet supported\n"
              "    • Column headers don't match known patterns")

    # ── Reconciliation errors ──────────────────────────────────────────
    if result.reconciliation.errors:
        print(f"\n[!] Balance drift detected in {len(result.reconciliation.drift_rows)} row(s):")
        for err in result.reconciliation.errors[:5]:
            print(f"    {err}")

    print(f"\n{'─'*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ./venv/bin/python run_pipeline.py <file_path>")
        sys.exit(1)
    os.environ.setdefault("INTERNAL_API_KEY", "dev-key")
    run(sys.argv[1])
