#!/usr/bin/env python3
import os
import sys
import json
import logging
from pathlib import Path

# Add parser-service to path
sys.path.insert(0, str(Path(__file__).parent / "spendsy" / "services" / "parser-service"))

from app.core.pipeline import DocumentParserPipeline

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def run(file_path: str):
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File {file_path} not found.")
        sys.exit(1)

    print(f"--- Processing {path.name} ---")
    
    with open(path, "rb") as f:
        content = f.read()

    # Simple content-type guessing
    ext = path.suffix.lower()
    content_type = "text/plain" # Default to text/plain
    if ext == ".pdf":
        content_type = "application/pdf"
    elif ext == ".csv":
        content_type = "text/csv"
    elif ext in (".xlsx", ".xls"):
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    pipeline = DocumentParserPipeline()
    try:
        result = pipeline.run(content, filename=path.name, content_type=content_type)
        
        print("\n--- Results ---")
        print(f"Status: {result.status}")
        print(f"Reconciliation Score: {result.reconciliation_score:.4f}")
        print(f"Model Used: {result.meta.get('model_used', 'regex/table')}")
        print(f"Strategy: {result.meta.get('pipeline_strategy')}")
        print(f"Transactions Extracted: {len(result.transactions)}")
        
        if result.transactions:
            print("\n--- Transactions (Sample) ---")
            for tx in result.transactions[:5]:
                print(f"{tx.date} | {tx.description[:40]:<40} | {tx.amount:>10.2f} | {tx.type}")
        
        if result.reconciliation_score < 0.95:
            print("\n[!] WARNING: Low reconciliation score. Review required.")
            
    except Exception as e:
        print(f"\n[!] Pipeline Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py <file_path>")
        sys.exit(1)
    
    # Set internal API key for cloud fallback to work if needed
    os.environ.setdefault("INTERNAL_API_KEY", "abcdef0123456789abcdef0123456789")
    
    run(sys.argv[1])
