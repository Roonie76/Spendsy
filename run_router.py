#!/usr/bin/env python3
import os
import sys
import asyncio
from pathlib import Path

# Add parser-service to path
sys.path.insert(0, str(Path(__file__).parent / "spendsy" / "services" / "parser-service"))

from app.core.extractors import get_extractor
from app.core.quality import QualityDetector
from app.core.routers import ParsingRouter, ParsingStrategy
from app.core.registry import ParserRegistry, initialize_registry

# Initialize parsers
initialize_registry()

async def main(file_path):
    path = Path(file_path)
    if not path.exists():
        print(f"File not found: {file_path}")
        return

    with open(path, "rb") as f:
        content = f.read()

    filename = path.name
    ext = path.suffix.lower()
    content_type = "application/pdf" if ext == ".pdf" else "text/csv"

    # Step 1: Extract Text
    print(f"--- Extracting Text from {filename} ---")
    extractor = get_extractor(content_type, filename)
    text = extractor.extract(content)

    # Step 2: Quality Detection
    print("\n--- Running Quality Detector ---")
    detector = QualityDetector()
    quality = detector.detect(text)
    print(f"Detected Quality: {quality.name}")

    # Step 3: Strategy Routing
    print("\n--- Running Parsing Router Algorithm ---")
    router = ParsingRouter()
    strategy = router.route(quality, filename)
    print(f"Routed Strategy: {strategy.name}")

    print("\n--- Running Parsers matching Strategy ---")
    # Finding a parser in the registry that matches this strategy
    # Currently ParserRegistry groups by format_name (e.g. "tabular", "type_a", "citibank")
    # If strategy is TABULAR -> TabularParser
    # HYBRID / REGEX -> type_a / type_c
    
    target_parser_name = None
    if strategy == ParsingStrategy.TABULAR:
        target_parser_name = "tabular"
    elif strategy in (ParsingStrategy.REGEX, ParsingStrategy.HYBRID, ParsingStrategy.LLM):
        # TYPE_C inherently handles OCR, unstructured, and has disabled LLM fallbacks
        target_parser_name = "TYPE_C"
        
    if target_parser_name:
        parser = ParserRegistry.get_parser(target_parser_name)
        if parser:
            print(f"Invoking parser: {parser.name} v{parser.version}...")
            # Some parsers are async, some are sync. In pipeline they are run in executor if sync.
            import functools
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, functools.partial(parser.parse, content, text, filename=filename, content_type=content_type))
            
            print(f"\nStatus: {result.status}")
            print(f"Transactions found: {len(result.transactions)}")
            if result.transactions:
                for tx in result.transactions[:5]:
                    print(f"{tx.date} | {tx.description[:30]:<30} | {tx.amount} | {tx.type}")
        else:
            print(f"Parser '{target_parser_name}' not found in registry.")
    else:
        print(f"No mapped parser in registry for strategy {strategy.name}")

if __name__ == "__main__":
    os.environ["INTERNAL_API_KEY"] = "dev-key"
    asyncio.run(main("Jan.pdf"))
