"""Pre-LLM stress harness for the TORA Universal Intelligence Engine.

Unlike the LLM-inclusive golden-questions runner, this harness exercises the
resolver / engine / context builder / thinking-gate layers against a generated
corpus of 1000+ realistic user queries. It's offline, deterministic, and
designed to surface:

  - Track 2 queries the resolver misses (biggest bug class)
  - Track 1 queries that accidentally match a plugin
  - Wrong-plugin routing ("e-bike" → electronics instead of mobility)
  - Latency outliers
  - Plugin coverage gaps
  - Token-budget pressure

Run:
    cd backend && python -m tests.tora_eval.stress.simulate --n 1200
    cd backend && python -m tests.tora_eval.stress.report eval_results.jsonl
"""
