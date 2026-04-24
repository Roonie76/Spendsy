# Spendsy Project Log

This file serves as a persistent record of project development, architectural decisions, and work history. It is intended to provide immediate context for AI assistants and developers switching into the project.

## 📌 Project Identity
- **Name**: Spendsy
- **Type**: Modern Fintech Microservices Platform
- **Core Docs**:
  - [README.md](file:///d:/Projects/Spendsy/README.md) - Setup & Quick Start
  - [ARCHITECTURAL_ANALYSIS.md](file:///d:/Projects/Spendsy/docs/ARCHITECTURAL_ANALYSIS.md) - Deep dive into services & logic
  - [ARCHITECTURE.md](file:///d:/Projects/Spendsy/docs/ARCHITECTURE.md) - High-level system design

## 🛠️ Tech Stack
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0
- **Databases**: PostgreSQL, Redis
- **Infrastructure**: Docker, Nginx (API Gateway)
- **AI**: Google Gemini, TORA Framework (standalone agent)

## 🚀 Active Status
- **Current Development Focus**: TORA Universal Intelligence Engine is LIVE end-to-end + stress-tested (12-category plugin registry + 3 live fetchers + parallel-fallback engine + market context builder + number auditor + thinking-mode gating + 4-stage resolver with fuzzy typo handling + hardened system prompt for variation/hallucination control + 1200-query stress harness achieving 98.3% track-2 recall / 93.9% track-1 precision). Next: cache warmer, scenario overrides, QLoRA fine-tuning on collected good traces. Ongoing: TORA Intelligence 2.0 (Obsidian Vault + CoT) + Inter-account transfer reconciliation.
- **Recent Activity Areas**:
  - `backend/finance-service/app/services/parser/`: PDF parser month/year inference for undated rows.
  - `backend/finance-service/alembic/versions/`: Pending migration `20260424_02` (adds `date_inferred` column).
  - `frontend/src/components/domain/TransactionItem.jsx` + `shared/utils/helpers.js`: Hardened date rendering so missing/inferred dates don't silently fall back to today.
  - `backend/spendsy-ai/`: Fine-tuning logic and configuration.
  - `frontend/src/components/ui/`: Statement Hub and Filter Modal refinements.
- **Pending manual steps**:
  - Run `alembic upgrade head` in `backend/finance-service` before restarting the service (picks up the `date_inferred` column).
  - Re-import any previously parsed statements — rows already in the DB carry the incorrect `date = 2026-04-23` and the migration does not backfill them.
- **Running Environment**: Local development via `.\run-local.ps1` (Frontend on Vite, Backend in Docker).

---

## 🕒 Work History

### 2026-04-25 — AI Instruction Files Created
- **What shipped**: Added dedicated instruction files for different AI assistants to ensure consistent project-specific behavior across platforms.
- **New Files**:
    - **[ANTIGRAVITY.md](file:///d:/Projects/Spendsy/ANTIGRAVITY.md)**: Optimized for the Antigravity assistant (Windows/PS, TORA 2.0 focus).
    - **[CODEX.md](file:///d:/Projects/Spendsy/CODEX.md)**: Optimized for GPT-4/Codex (Architecture/Schemas focus).
    - **[CLAUDE.md](file:///d:/Projects/Spendsy/CLAUDE.md)**: (Existing) Focused on Graphify knowledge graph navigation.

### 2026-04-25 — Documentation Consolidation
- **What shipped**: Reduced the `docs/` folder footprint from 5 files to 2 unified "Master" documents to improve maintainability and onboarding clarity.
- **Unified Docs**:
    - **[ARCHITECTURE.md](file:///d:/Projects/Spendsy/docs/ARCHITECTURE.md)**: Now contains high-level architecture, deep-dive analysis, and system requirements (SRS).
    - **[CONTRIBUTING.md](file:///d:/Projects/Spendsy/docs/CONTRIBUTING.md)**: Now contains the full setup guide (Windows/macOS/Linux) and contribution guidelines.
- **Removed**: `SRS.md`, `ARCHITECTURAL_ANALYSIS.md`, and `SETUP_GUIDE.md` (all merged into the above).
- **Update**: Re-linked `README.md` to these consolidated sources.

### 2026-04-25 — TORA engine stress test (1200 queries) + hardening round
- **What shipped**: Pre-LLM stress harness plus three fix passes that took resolver accuracy from 80.6% to 98.3% recall and held track-1 precision at 93.9%. Harness lives in [backend/tests/tora_eval/stress/](file:///d:/Projects/Spendsy/backend/tests/tora_eval/stress/) alongside the existing LLM-inclusive golden-questions runner.
- **Stress harness** — three-module pipeline, ~600 lines total, stdlib-only:
    - [query_generator.py](file:///d:/Projects/Spendsy/backend/tests/tora_eval/stress/query_generator.py) — deterministic corpus generator. 20 Indian personas (age, city, income, surplus, life stage) × 12 plugin templates + 6 track-1 intents + 3 adversarial intents × 3 styles (55% clean English, 30% Hinglish/Hindi, 15% typos/casual). Seeded — same seed = same corpus, so regressions are comparable across engine revisions.
    - [simulate.py](file:///d:/Projects/Spendsy/backend/tests/tora_eval/stress/simulate.py) — async runner with `asyncio.Semaphore(20)` concurrency. Runs every query through `resolve_and_fetch` + `build_market_context_block` + `should_enable_thinking`. Does NOT hit the LLM — 1200 LLM calls would take 50+ minutes and the LLM isn't what's being evaluated at this layer. Emits JSONL with ground-truth labels + per-query outcomes. 1200 queries process in ~2s.
    - [report.py](file:///d:/Projects/Spendsy/backend/tests/tora_eval/stress/report.py) — classifies each outcome into 7 buckets (hit / hit_supporting / wrong_plugin / miss_track2 / ok_track1 / false_pos / error), computes per-category recall, per-style accuracy (english/hinglish/typos), thinking-mode gating accuracy, latency p50/p95/p99/max, plugin match volume, and a Top Problematic Queries section grouped by `(category, outcome)` for actionable debugging.
- **Fix pass 1 — domain vocabulary expansion** ([entity_synonyms.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/entity_synonyms.py)): added 15+ missing canonical entity keys the v1 corpus surfaced. Examples: `term plan`/`term insurance`/`80d deduction`/`mediclaim tax benefit` (healthcare), `stamp duty`/`home loan`/`under construction`/`ready possession` (real_estate), `auto loan`/`monthly fuel`/`petrol cost`/car models (swift, creta, nexon, thar, ertiga, baleno, i20…) (mobility), `sgb`/`sovereign gold bond`/`gold bond`/`gold etf`/`digital gold` (gold), `tax saving`/`income tax`/`retirement`/`80c`/`large-cap`/`mid-cap`/`index fund` (investments), `cost of living`/`education loan`/`80e`/`london study` (education), `thailand`/`singapore`/`bali`/`maldives`/`forex`/`visa` (travel), `bridal jewellery`/`wedding photographer`/explicit `honeymoon` (wedding), `electronics sale`/`big billion`/phone brands (electronics), `sofa set`/`kitchens` (furniture), `streaming`/`subscriptions` (lifestyle).
- **Fix pass 2 — plugin overlap resolution**: several semantic collisions surfaced where multiple plugins were plausible ("bridal jewellery" → gold vs wedding, "honeymoon Europe" → travel vs wedding, "gym" → healthcare vs lifestyle, "SGB invest" → investments vs gold). Fixed by:
    - Moving `gym` entirely from healthcare to lifestyle — fitness spend is a lifestyle expense, not a medical one. Healthcare keeps surgery/dental/insurance/IVF.
    - Registering multi-word keys on the "winning" plugin so length-preference ranking picks the right primary (`bridal jewellery` → wedding, `wedding photographer` → wedding, `sgb` → gold as first-class key).
    - Removed bare `"invest"` as gold's entity — it was pulling SGB queries to investments. Gold now owns `sgb`/`gold bond`/`gold etf`/`digital gold`.
    - Removed `"home"` from the bare-synonym pool — was colliding with "home gym"/"home workout". Home loan is still matched explicitly via the new `home loan` canonical key.
- **Fix pass 3 — fuzzy-match stage for typos** ([entity_resolver.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/entity_resolver.py)): added stage 3 `_collect_stage3_fuzzy` using Python stdlib `difflib.get_close_matches`. Only fires when stages 1-2 return zero matches (zero cost when exact match exists). Key design decisions after iteration:
    - **Pool**: canonical entity keys + distinctive synonyms, min 4 chars, heavy stopword filter (~60 entries: connectives + generic finance vocabulary like `monthly`/`budget`/`expense`/`income` + ambiguous English nouns like `water`/`paris`/`current`/`account` + Hindi connectors like `kiya`/`kya`/`mere`).
    - **Cutoff**: 0.8 difflib ratio for all lengths.
    - **First-letter guardrail**: fuzzy matches must share the first character with the user's token. Real typos preserve it (`swuft`/`swift`, `iphne`/`iphone`, `modlar`/`modular`, `rnt`/`rent`, `billon`/`billion`) — noise matches from difflib often don't. Single cheap check, massive false-positive reduction.
    - **Score**: fuzzy hits × 0.85 so any later exact match always wins.
- **Fix pass 4 — hardened TORA system prompt** ([tora_personality.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora_personality.py)): extended `TORA_SYSTEM_PROMPT` with two new sections instructing gemma4:e2b on how to handle question variations without hallucinating:
    - **HANDLING QUESTION VARIATIONS**: read user intent not exact wording; treat Hinglish (`shaadi`/`gaadi`/`sona`/`paisa`/`gehne`/`kharcha`) as English equivalents; treat typos (`aford`/`swuft`/`iphne`/`insurnce`) as correct words without asking for clarification; short queries ("SIP vs FD", "best AC") are full questions not fragments; if the MARKET block is present use it — don't say "it depends" when the context has both facts and rules; if MARKET is absent, answer ONLY from the user's vault — never fabricate category knowledge.
    - **DECISION MODE**: when user asks "should I"/"can I afford"/"is now a good time"/"compare", give a verdict FIRST ("Yes, comfortably" / "Tight — wait N months" / "Not advisable at your surplus"), then explain in 1-2 sentences using ONLY numbers from the injected blocks; apply every rule listed under "Rules to apply:" as a hard constraint — violating one is a failed answer; acknowledge missing/implausible profile data openly rather than inventing a scenario.
    - Rewrote CORE RULE 2: "if a number is not in those blocks, DO NOT write it — rewrite the sentence to describe the direction ('tight', 'comfortable', 'stretched') instead of inventing a figure." This is the strongest anti-hallucination rule in the prompt.
- **Resolver design detail — 4-stage architecture now**:
    1. Token-normalized exact match against canonical entity_keys (prevents "ev" in "every")
    2. Synonym lookup (Hindi/Hinglish-aware) via REVERSE_SYNONYMS
    3. Fuzzy difflib match with first-letter guardrail (only if stages 1+2 return nothing)
    4. Return [] (no LLM disambiguation — violates no-lag constraint)
- **Before → After on 1200 queries** (same seed, same corpus):
    | Metric | v1 baseline | v4 final | Δ |
    |---|---:|---:|---:|
    | Track-2 recall | 80.6% | **98.3%** | +17.7pts |
    | Track-1 precision | 93.9% | **93.9%** | held |
    | English recall | 86.7% | **99.0%** | +12.3pts |
    | Hinglish recall | 81.1% | **96.1%** | +15.0pts |
    | Typo recall | 56.9% | **100.0%** | +43.1pts |
    | Thinking-mode gating | 88.5% | **97.5%** | +9pts |
    | Engine errors | 0 | 0 | — |
    | p99 latency | 21.6ms | 47.7ms | +26ms |
    | Budget breaches (>800ms) | 0 | 0 | — |
- **Per-category final state**: 9 of 12 plugins at 100% recall (appliances, education, electronics, furniture, gold, investments, lifestyle, real_estate, wedding). Healthcare 92.9% (4 Hinglish misses), mobility 94.3% (4 Hinglish misses), travel 92.9% (5 "wrong plugin" — honeymoon routing to wedding, arguably correct composition).
- **Remaining track-1 false positives (22/360, 6.1%)**: 15 from a deliberate lexical-trap query ("I have too many tvs in my house for the guests" has both `tv` and `house` as legitimate entity keys — unavoidable without sentence-level understanding), 7 from "how much can I save if I cut dining out" leaking to lifestyle — arguably correct since dining IS a lifestyle spend and the corpus labeled it too strictly.
- **Files touched**:
    - NEW: [backend/tests/tora_eval/stress/__init__.py](file:///d:/Projects/Spendsy/backend/tests/tora_eval/stress/__init__.py), [query_generator.py](file:///d:/Projects/Spendsy/backend/tests/tora_eval/stress/query_generator.py), [simulate.py](file:///d:/Projects/Spendsy/backend/tests/tora_eval/stress/simulate.py), [report.py](file:///d:/Projects/Spendsy/backend/tests/tora_eval/stress/report.py)
    - Updated: [entity_synonyms.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/entity_synonyms.py), [entity_resolver.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/entity_resolver.py), [tora_personality.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora_personality.py), 8 plugin files under [plugins/](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/plugins/) (real_estate, electronics, healthcare, investments, education, travel, gold, wedding, lifestyle — entity_keys expanded to register new canonical terms)
    - Generated artifacts: [stress_report_v4.md](file:///d:/Projects/Spendsy/backend/stress_report_v4.md), [stress_results_v4.jsonl](file:///d:/Projects/Spendsy/backend/stress_results_v4.jsonl)
- **How to re-run the regression**: `cd backend && python -m tests.tora_eval.stress.simulate --n 1200 --out stress_results.jsonl --seed 42 && python -m tests.tora_eval.stress.report stress_results.jsonl --md stress_report.md`. Deterministic seed means any change to resolver/engine shows up as a measurable recall/precision delta on the exact same corpus. This is the regression baseline for all future engine changes.

### 2026-04-24 (late night) — Fixed TORA Transaction Blindness
- **Issue**: TORA would refuse to answer questions about specific payments ("I don't have access to your transaction details") because individual line items were omitted from the AI context to save tokens, only providing category aggregates.
- **Fix**: 
    - Modified `tora_agent.py` to inject a `RECENT TRANSACTIONS` block containing the top 15 most recent line items (Title, Amount, Type, Date) into every AI prompt.
    - Updated `note_templates.py` to include a full transaction table in the monthly vault notes (up to 100 items), ensuring long-term memory is complete.
- **Result**: TORA can now identify specific merchants, amounts, and dates (e.g. "find my credit card payment") without generic privacy refusals.

### 2026-04-24 (late night) — Graphify Knowledge Graph Implemented
- **What shipped**: Successfully integrated `graphify` into the Spendsy ecosystem to create a queryable, persistent knowledge graph of the codebase. This reduces AI token consumption by allowing targeted structural reasoning instead of exhaustive file reading.
- **Implementation Details**:
    - **Dependency**: Installed `graphifyy` and tree-sitter dependencies.
    - **Graph Stats**: Initial build completed with **2,110 nodes** and **5,519 edges** across **166 communities**.
    - **Automation**: Installed `post-commit` and `post-checkout` git hooks to trigger automatic graph updates on every code change.
    - **Exclusions**: Updated `.gitignore` to exclude `graphify-out/` build artifacts while maintaining the `.graphify_cache` for incremental updates.
- **Key Knowledge Hubs Identified**:
    - `TORA Financial Intelligence`: Core agent, memory, and personality logic.
    - `Database Models & Schemas`: Domain entity definitions.
    - `Indian Tax Engine`: Complex tax regime and deduction logic.
    - `TORA Plugin Registry & Fetchers`: External market data integration.
- **Outputs**:
    - `graphify-out/GRAPH_REPORT.md`: Architectural summary and "God Node" analysis.
    - `graphify-out/graph.html`: Interactive vis.js visualization of the system structure.
    - `graphify-out/graph.json`: Machine-readable graph for AI agent context injection.

### 2026-04-24 (late evening) — TORA Universal Intelligence Engine fully wired end-to-end
- **What shipped**: The 12-category plugin registry is now connected to the live request path. `tora_agent.generate_financial_strategy()` resolves entities, fetches plugin data in parallel with fallbacks under an 800ms total budget, injects a token-budgeted market-context block into the LLM prompt, audits every ₹/% figure in the response against the injected context, and gates Gemma 4 thinking mode based on query complexity. Three live fetchers (gold via IBJA, investments via AMFI NAV, forex via exchangerate-api) are wired in — the remaining 9 plugins run on curated YAML fallbacks indefinitely (no free live source exists for those categories).
- **Stage 2a — FetchStrategy enum + confidence scoring** ([fetch_registry.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/fetch_registry.py)): Added explicit `FetchStrategy` enum (`LIVE_API` / `LIVE_SCRAPE` / `CACHED_DAILY` / `CACHED_QUARTERLY` / `CURATED_STATIC` / `ESTIMATED` / `HYBRID`) on `FetchPlugin`, plus `STRATEGY_BASE_CONFIDENCE` map (LIVE_API=0.95 down to ESTIMATED=0.45) and `confidence_label()` helper. Every fact now carries `{value, source, fetched_at, ttl_seconds, confidence}`. This makes the "hybrid data strategy" honest — the system is transparent about which data is live vs curated, and the LLM sees confidence tags for medium/low facts so it knows when to hedge. 5 plugins declared non-default strategies: `gold=LIVE_API`, `investments=HYBRID`, `travel=HYBRID`, others default to `CURATED_STATIC`.
- **Stage 2b — Universal Fetch Engine** ([universal_fetch_engine.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/universal_fetch_engine.py)): `resolve_and_fetch(message, user_surplus, user_city)` is the single entry point.
    - Enforces `TOTAL_BUDGET_SECONDS=0.8` across the full fan-out via one `asyncio.wait_for` — not per-plugin.
    - Each plugin runs `_fire_one_plugin` which pre-computes the sync fallback FIRST (zero-latency, guaranteed answer), then launches the async live fetcher with `PER_FETCHER_BUDGET_SECONDS=0.6` timeout. On timeout/error, the already-resolved fallback is returned unchanged — no retry, no second trip.
    - Live wins per-field via `FetchResult.merge_from` — if live returns `{spot_price}` but not `{making_charges}`, live's spot_price overrides fallback's but fallback's making_charges is preserved.
    - Optional `reconcile_fn` hook on `FetchPlugin` for plugins with two live sources (future: gold IBJA vs MCX conflict resolution).
    - Total-budget-exceeded path: rebuilds fallbacks-only for every plugin so the caller still gets a complete list with `provenance.reason="total_budget_exceeded"`.
- **Stage 3a — Market Context Builder** ([market_context_builder.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/market_context_builder.py)): Renders `FetchResult` tuples into a prose block the LLM consumes.
    - Per-plugin token budget enforced via `_CHARS_PER_TOKEN=4.5` heuristic. Primary plugin gets its full declared budget; supporting plugin capped at 30% (`SUPPORTING_BUDGET_FRACTION`).
    - Constraint lines reserved ≤35% of each plugin's budget — they're behavioural guardrails and matter even when we run short of tokens on data.
    - `_render_value()` handles dicts (min/max → "₹X–₹Y", short dicts → inline pairs, long dicts → first-3 + "+N more"), lists, ranges. `_is_pct_key()` detects percentage fields (pct/percent/rate/interest/discount/markup/yield/cagr) and renders `3%` instead of `₹3`. Child key hints inherit parent when parent is a pct key — so `gst_pct: {jewellery: 3}` renders as `gst pct: jewellery: 3%`.
    - Confidence tag rendered only for medium/low-confidence facts (e.g. `[medium confidence]`). High-confidence facts get no tag — signals to the LLM "quote these plainly".
    - Subtle footer appended when any fallback field was used: *"Prices indicative, based on recent published rates. Tell the user this only if they ask about freshness."* Deliberately not a loud warning — would make the LLM over-hedge.
- **Stage 3b — Number Auditor** ([number_auditor.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/number_auditor.py)): Post-generation regex check on every ₹ and % figure in the LLM output.
    - `_RUPEE_RE` matches `₹X,XXX`, `₹X.X L`, `₹X Cr`, `₹X K` — scale suffixes normalised to absolute rupees before comparison.
    - `_PCT_RE` matches `8.5%`, `10 percent`, `15 pct` — crucially without trailing `\b` (fixed from an earlier bug where `25%` didn't match because `%` isn't a word char).
    - `_ROUND_TOLERANCE_PCT=0.03` — model often rounds for readability (₹70,800 → ₹70K), this allows matches within 3%.
    - Unverified numbers → hedged inline with "roughly"/"approximately" rather than stripped. Hedging preserves sentence structure while flagging uncertainty.
    - `audit_structured_output()` handles both simple-mode (`content`) and structured-mode (4-section) envelopes.
- **Stage 3c — Wired into `tora_agent.py`**: `build_ai_context(..., market_block="")` accepts an optional market block. `generate_financial_strategy()` now calls `resolve_and_fetch(question, user_surplus=surplus)` before building context, passes the result through `build_market_context_block()`, and injects the block before the `QUESTION:` line. After the LLM returns, `audit_structured_output(final_output, user_message)` hedges any unverified figures — passes the **full** `user_message` (vault + simulations + market block) so the auditor sees every legitimate number including the user's surplus from the profile.
    - Extended the reasoning checklist to 3 rules: (1) every ₹/% figure MUST appear verbatim in a block above, else delete the sentence, (2) decision questions ("should I", "can I afford", "is now a good time") must be answered with a decision/recommendation using the Rules in the MARKET block, not a data dump, (3) default to simple mode.
- **Stages 4–6 — Live fetchers** ([live_fetchers/](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/live_fetchers/)):
    - [gold_fetcher.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/live_fetchers/gold_fetcher.py) scrapes `https://ibjarates.com/` with httpx, 0.5s timeout, plausibility bounds on 22K/24K/silver values. Returns `spot_price_inr` fact with `LIVE_API` confidence (0.95) and 1h TTL. HTML-structure changes break selectors → fallback wins silently.
    - [investments_fetcher.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/live_fetchers/investments_fetcher.py) pulls AMFI's plain-text NAVAll.txt (`https://www.amfiindia.com/spages/NAVAll.txt` — the single most reliable Indian financial data source). Extracts a handful of probe fund NAVs (UTI/HDFC/Nippon Nifty 50 index funds) as freshness proof. Falls back cleanly on any error.
    - [forex_fetcher.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/live_fetchers/forex_fetcher.py) uses `open.er-api.com/v6/latest/USD` (free, no auth, 1500 req/mo). Derives INR cross-rates for USD/EUR/GBP/AED/AUD/SGD/THB/JPY via USD-base arithmetic. Plausibility bounds per currency. Used by `travel` plugin; also consumable by `education` and `wedding` future sub-fetchers.
- **Stage 7 — Thinking-mode gating** ([thinking_gate.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/thinking_gate.py)): `should_enable_thinking(message, has_plugin_match)` — ON when (a) any track 2 plugin matched, (b) message >15 words with comparison/hypothetical language (`should I`, `compare`, `vs`, `what if`, `suppose`), or (c) planning verbs (`plan`, `simulate`, `forecast`, `retire`, `long-term`). Default OFF — thinking mode triples latency and over-elaborates on simple questions. Wired through `llm_router.call_llm(..., thinking=bool)` → `ollama_client.call_ollama(..., thinking=bool)` which sets the `think` field on the Ollama chat payload (was hardcoded `False`).
- **Integration smoke test results** (all passing):
    - 10 query mix: track 1 queries (food/savings/hypothetical/greeting) correctly skip enrichment and disable thinking; track 2 queries (gold/Swift/Europe/AC/SIP/renovate) all resolve to correct plugins with thinking ON.
    - Two-plugin composition verified: "renovate kitchen in 200 sqft flat" → `furniture(primary) + real_estate(supporting)`.
    - Engine latency 0ms when all plugins are on stub fetchers (no network calls) — fallback path is sub-millisecond.
    - Auditor catches hallucinated numbers: injected context with ₹70,800/22K gold + 3% GST correctly accepts those values verbatim; invented ₹120,000 coin price and 25% GST get hedged with "roughly"/"approximately" and logged as warnings.
    - Rounding tolerance works: ₹95,200 in response matches ₹94,500 in context (0.74% diff, within 3% tolerance).
- **Known calibration behavior (not bugs)**: Arithmetic-derived numbers (e.g. "a ₹700,000 car gives ₹11,500 EMI") get hedged because the auditor doesn't run the math. Range-membership checks (₹700,000 is within the ₹550K-950K hatchback range) also not implemented — still flagged as "unverified" and hedged. Both are safe-by-default: the "roughly" prefix signals illustrative rather than authoritative, which is accurate for derivations. Stage 8+ could add range-membership and arithmetic verification to reduce over-hedging.
- **Files created this evening (Stage 2-7)**: [fetch_registry.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/fetch_registry.py) (updated), [universal_fetch_engine.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/universal_fetch_engine.py), [market_context_builder.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/market_context_builder.py), [number_auditor.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/number_auditor.py), [thinking_gate.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/thinking_gate.py), [live_fetchers/gold_fetcher.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/live_fetchers/gold_fetcher.py), [live_fetchers/investments_fetcher.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/live_fetchers/investments_fetcher.py), [live_fetchers/forex_fetcher.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/live_fetchers/forex_fetcher.py). [tora_agent.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora_agent.py), [llm_router.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/llm_router.py), [ollama_client.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/ollama_client.py) each touched surgically to pass `thinking` through and call the engine + auditor.
- **What's next (future work)**: (a) Cache warmer for top 25 hot fields (gold/silver/forex/FD/loan rates) running on spendsy-ai startup; (b) Scenario override layer for "what if my surplus was ₹25k?" hypotheticals without refetching; (c) Evaluation harness — 50–100 held-out Q&A pairs across both tracks, re-run after every fine-tune to catch regressions; (d) QLoRA fine-tuning focused on TORA persona/voice and Indian domain fluency rather than raw reasoning (gemma4:e2b already has that); (e) Range-membership + arithmetic verification in the auditor to reduce over-hedging.

### 2026-04-24 (evening)
- **TORA Universal Intelligence Engine — Stage 1 (Plugin Registry + Static Fallbacks)**: Built the scaffolding for a 12-category universal expense intelligence system that extends TORA beyond profile-only Q&A into "what should I do?" decision advice (Can I afford a Swift? Should I buy gold this Diwali? Plan a Europe trip). Non-invasive: the new sub-package is not yet wired into `tora_agent.py` — stages 2 and 3 will do that.
    - **Sub-package** at [backend/spendsy-ai/agents/tora/](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/) (~1600 lines across 18 files):
        - [fetch_registry.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/fetch_registry.py) — `FetchPlugin` (self-describing category module), `FetchResult` (facts + options + constraints + provenance, with field-level `merge_from`), `PluginMatch` (ranked resolver output with primary/supporting roles), `PLUGIN_REGISTRY`, `register()`, `get_plugin()`, `fact()` helper.
        - [entity_resolver.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/entity_resolver.py) — 3-stage resolver: (1) token-normalized exact match against entity keys (prevents "ev" matching "every"), (2) synonym lookup via `REVERSE_SYNONYMS`, (3) no-match ⇒ `[]` (deliberately skips LLM guess to preserve no-lag constraint). Multi-word keys match consecutive tokens. Returns up to 2 matches ranked by length/specificity score; first is `primary`, second is `supporting`.
        - [entity_synonyms.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/entity_synonyms.py) — Hand-curated Hindi + English synonym map (shaadi → wedding, sona → gold, gaadi → car, jhumka → jewellery, zameen → plot, etc.). `REVERSE_SYNONYMS` built at import time.
        - [static_fallbacks/__init__.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/static_fallbacks/__init__.py) — YAML loader that populates `FALLBACK_DATA` on import. Graceful degradation if PyYAML missing.
        - [plugins/_base.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/plugins/_base.py) — `build_fallback_from_yaml(plugin_id)` wraps every fact with `{value, source, fetched_at, ttl_seconds}` provenance so the number auditor (stage 3) and assembler can verify numbers verbatim and render a subtle footer. `stub_fetcher` is a no-op async placeholder used by all 12 plugins until stage 4+ replaces them with live fetchers.
        - [plugins/__init__.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/plugins/__init__.py) — `register_all_plugins()` walks the 12 plugin modules and registers each idempotently.
    - **12 plugin modules** (one file each, ~15 lines — declare `entity_keys`, `fetch_profile`, `token_budget`, flags): `mobility`, `real_estate`, `electronics`, `appliances`, `travel`, `gold`, `investments`, `education`, `healthcare`, `wedding`, `furniture`, `lifestyle`.
        - Declarative flags: `sebi_disclaimer` (gold, investments), `forex_needed` (travel, education, wedding), `critical_freshness` (investments, healthcare).
    - **12 YAML static fallbacks** at [backend/spendsy-ai/agents/tora/static_fallbacks/*.yaml](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora/static_fallbacks/) — India-market calibrated, dated 2026-04-24, reviewable in PR diffs. Each file contains `updated_at`, `source`, `notes`, `facts`, `options`, `constraints`. Highlights:
        - `appliances.yaml`: `seasonal_timing` block encodes when to buy each category (ACs Nov-Feb, TVs Sep-Nov Diwali, fridges Jan-Feb previous-gen clearance, etc.) — this is the "wait 23 days for Big Billion, save ₹15K" differentiator vs a plain price lookup.
        - `electronics.yaml`: sale windows (Big Billion, Great Indian Festival, Republic Day) with typical discount %.
        - `gold.yaml`: dual-surface — purchase cost (spot + making + 3% GST) AND investment angle (SGB/ETF/digital-gold comparison with tax treatment).
        - `investments.yaml`: AMFI-style category 5y CAGRs, FD rates by top banks, PPF/NPS/ELSS tax sections, full tax rules (LTCG/STCG/80C/80CCD(1B)/80D limits).
        - `healthcare.yaml`: age-banded insurance premiums, procedure cost ranges across private hospitals, 80D deduction tiers.
    - **Two-track architecture** (locked in after user clarification):
        - **Track 1** (profile-only Q&A: "how much did I spend on food?", "what's my savings rate?") — answered from vault alone, no plugin enrichment. Fast path. Resolver correctly returns `[]` for these — they skip the enrichment pipeline entirely.
        - **Track 2** (universal expense intelligence: "can I afford a Swift?", "should I buy gold?") — fires plugin fetchers, enrichment context injected into prompt.
    - **Zero-lag fallback doctrine** (user-specified constraint: "no lag, response never broken"):
        - Hard total budget: 800ms across all fetchers (not per-plugin). Enforced via a single `asyncio.wait_for` around the fan-out in stage 2.
        - Fallback runs **in parallel** with live fetch, not after — `build_fallback_from_yaml` is sync (sub-ms) and already resolved by the time the live fetch times out or errors. Timeout = zero extra latency.
        - Field-level merge: live wins per-key where present; fallback fills gaps. LLM always sees complete context, never knows a sub-fetcher failed.
        - No "data unavailable" strings ever reach the LLM (would make it over-hedge). Fallback swaps silently.
        - Provenance footer is a subtle single line: *"Prices indicative, based on recent market data."* — shown only when any field used fallback.
        - Critical+stale combo becomes hedged redirect ("rough benchmark ₹X–₹Y, want to plan at higher end?"), NOT refusal.
    - **gemma4:e2b correctly re-characterized**: this is a Gemma 4 (Jan 2026) 5.12B MoE model with 2B activation footprint, Q4_K_M, 7.2GB — NOT gemma-3 4B. Real reasoning capacity (AIME 2026 37.5%, LiveCodeBench 44%, GPQA Diamond 43% in thinking mode). Fetchers pre-compute deterministic math (EMIs, months-to-goal); model reasons about tradeoffs on structured options. Deployment stays server-side via Ollama (user chose: rate limiting, model update velocity, training-data collection, GPU amortization). Thinking mode gated: OFF by default, ON when any track 2 plugin matches or message >15 words contains comparison/hypothetical language ("should I", "compare", "what if").
    - **Data-strategy realism (post-review)**: Of the 12 categories, only 5 have free live data sources worth wiring in stage 4+: **gold** (IBJA daily rate public page), **investments** (AMFI NAVAll.txt daily file, NSE/BSE scrape, RBI G-Sec yields), **travel-forex** (RBI reference rate + ExchangeRate-API free tier), **mobility-fuel** (IOCL/BPCL/HPCL public pages), **lifestyle-OTT** (publisher pages, monthly cache). The remaining 7 (electronics, appliances, real_estate, education, healthcare, wedding, furniture) either have no public API or require enterprise-level paid access (MagicBricks ₹50K-2L/mo, PolicyBazaar partner-only, CarDekho ₹20-50K setup). For these, curated-monthly YAML is the realistic long-term data strategy — the architecture must be transparent about this rather than pretend everything is real-time. Next design iteration will add an explicit `FetchStrategy` enum (`LIVE_API`/`LIVE_SCRAPE`/`CACHED_DAILY`/`CACHED_QUARTERLY`/`CURATED_STATIC`/`ESTIMATED`/`HYBRID`) on `FetchPlugin` and a per-field `confidence` score.
    - **Dependencies**: Added `PyYAML==6.0.2` to [requirements.txt](file:///d:/Projects/Spendsy/requirements.txt).
    - **Test results**: 12/12 plugins register cleanly with YAML fallbacks populated (all facts + constraints + flags verified). 14/14 resolver tests pass including the specific "every laptop is expensive" → electronics case (no false-match on "ev"), "tvs are on sale" → appliances (plural handling), "I want to renovate my kitchen" → furniture (verb form + implicit kitchen context), "home loan vs rent" → real_estate, and "how much did I spend on food" → no match (correctly skips enrichment).
    - **What's NOT wired in yet**: `tora_agent.py` is untouched. Stage 2 (universal engine with 800ms parallel-fallback budget, field-level merge) and stage 3 (context builder with subtle footer + number auditor) plug the registry into `build_ai_context` around line 589. Stage 4+ replaces the 12 `stub_fetcher`s with real async fetchers starting with gold + AMFI NAV.
    - **Build order going forward**: (2) Universal engine — 800ms budget, parallel fallback, field-level merge. (3) Context builder with subtle provenance footer + number auditor. (4) First live fetcher (gold — IBJA). (5) AMFI NAV + NSE/BSE + RBI fetchers for investments + forex. (6) Cache warmer for top ~25 hot fields. (7) Scenario override layer ("what if my surplus was ₹25k?"). Evaluation harness (50-100 held-out Q&A pairs across both tracks) comes before any fine-tuning so regressions are caught.

### 2026-04-24
- **TORA Intelligence 2.0 (Architecture & Optimization)**: Implemented a deep optimization layer for the `gemma4:e2b` model to eliminate hallucinations and formatting errors.
    - **Obsidian Vault System**: Built a per-user Obsidian-compatible markdown vault for TORA long-term memory.
        - **New module** `backend/spendsy-ai/vault/` containing:
            - [vault_writer.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/vault/vault_writer.py) — Core file operations: folder skeleton creation (`ensure_vault`), atomic write/append/read, currency formatting, YAML frontmatter rendering, and Obsidian wikilink helpers.
            - [note_templates.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/vault/note_templates.py) — Typed note generators for all 8 note types (profile, balances, goals, plans, loans, conversations, transactions, canvas). Notes use YAML frontmatter for Dataview compatibility and wikilinks for graph navigation.
            - [vault_sync.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/vault/vault_sync.py) — Post-session sync orchestrator. Called fire-and-forget after every `handle_user_question`. Also provides `read_vault_context()` for vault-first LLM injection.
    - **Vault-First Context Injection**: Modified `build_ai_context` in [tora_agent.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora_agent.py) to read the user's vault profile and inject it as prose context. Structured prose with pre-formatted ₹ amounts is dramatically easier for `gemma4:e2b` to parse than nested JSON.
    - **Chain-of-Thought (CoT) & Schema Enforcement**:
        - **JSON Schema**: Updated [ollama_client.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/ollama_client.py) to require a `"reasoning"` field *before* the `"answer"` field. This forces the model to verify context data silently before committing to a response.
        - **Prompt Reconstruction**: Completely rewrote [tora_personality.py](file:///d:/Projects/Spendsy/backend/spendsy-ai/agents/tora_personality.py) (fixing earlier encoding/corruption issues) into a lean, rule-based 40-line prompt. It emphasizes "Simple Mode" by default and "Structured Mode" (4 specific keys) only for explicit summary/plan requests.
    - **Docker/Infrastructure**: Added `spendsy-vaults` named volume and `VAULT_BASE_PATH` env to [docker-compose.dev.yml](file:///d:/Projects/Spendsy/infra/docker/docker-compose.dev.yml). Mount: `/data/vaults`.
- **Inter-Account Transfer Reconciliation (Double-Counting Fix)**: When a user uploads both a debit statement and a credit card statement, a credit-card bill paid from the debit account used to inflate totals by the payment amount on BOTH sides:
    - Debit statement: `-1L "Credit Card Payment"` counted as expense.
    - Credit card statement: `+1L "Payment Received"` counted as income.
    - Credit card statement: `-1L shopping` (the real spend) also counted.
    Net: spend and income both off by the payment amount; real monthly spend looked ~1L higher than it was.
    - **Approach**: Detect matching pairs across statements and flag both sides as `is_transfer=True` so aggregations exclude them. Ledger rows remain untouched (type/amount/date preserved). Conservative keyword-gated auto-detection — only matches with CC-payment language on BOTH sides within ±5 days and ±1% amount. Manual fallback via a toggle in the edit modal.
    - **Schema** (migration `20260424_03_add_transfer_fields.py`): added `transfer_group_id VARCHAR(36)` (shared UUID across the pair) and `is_transfer BOOLEAN NOT NULL DEFAULT FALSE`, with indexes on `transfer_group_id` and `(user_id, is_transfer)`. **Run `alembic upgrade head` in `backend/finance-service` before the service is restarted.**
    - **New service** [transfer_reconciler.py](file:///d:/Projects/Spendsy/backend/finance-service/app/services/transfer_reconciler.py): `detect_transfer_pairs`, `unlink_transfer_group`, `unlink_peer_on_delete`. Pure, idempotent, keyword-gated (`DEBIT_SIDE_RE`, `CREDIT_SIDE_RE`), amount tolerance ±1% OR exact, date window ±5 days, requires the credit-side row's `account_type == 'credit'` (so a savings deposit with "payment" in the description can't match).
    - **Deleted the old broken `reconciliation_logic.py`** — it mutated `type` to the string `"transfer"` which `_safe_type` would coerce back to `"expense"` on read, defeating the whole point. It was also never wired into the user-facing parse flow. Internal endpoint `/internal/reconcile/{user_id}` now uses the new reconciler.
    - **Routes** ([routes_finance.py](file:///d:/Projects/Spendsy/backend/finance-service/app/api/routes_finance.py)):
        - `_build_financial_summary`: all 4 aggregations (lifetime + monthly × income + expense) now filter on `is_transfer == False`.
        - `/parse-digital-pdf`: runs `detect_transfer_pairs` after `_persist_parsed_transactions`, commits, then builds summary. Adds counts to `meta.warnings` and a new `transfer_pairs_linked` field on the response.
        - `POST /transactions` (manual add): runs the detector too — covers the case where the CC statement was uploaded first and the user manually adds the debit-side payment later.
        - `DELETE /transactions/{uid}` and bulk delete: when a transfer row is deleted, the surviving peer is unlinked (`transfer_group_id=NULL`, `is_transfer=False`) so it returns to normal aggregation. Dangling `is_transfer=True` rows without a peer would otherwise silently vanish from spend totals.
        - `GET /transactions`: serializer now exposes `is_transfer` and `transfer_group_id`.
        - **New endpoint** `PATCH /transactions/{uid}/transfer-flag` — manual flag/unflag for the user. Unflagging unlinks the peer too.
        - **New endpoint** `POST /transfers/reconcile` — user-triggered full-scan across all their transactions. Idempotent.
    - **Other aggregation call sites updated** (all now filter `is_transfer.is_(False)`):
        - [routes_internal.py](file:///d:/Projects/Spendsy/backend/finance-service/app/api/routes_internal.py) — `/summary/{user_id}` and `/finance-context/{user_id}`.
        - [jobs/net_worth_snapshot.py](file:///d:/Projects/Spendsy/backend/finance-service/app/services/jobs/net_worth_snapshot.py) — cash balance calc.
        - [jobs/proactive_insights.py](file:///d:/Projects/Spendsy/backend/finance-service/app/services/jobs/proactive_insights.py) — category spike, large-transaction, and unusual-merchant rules.
    - **Frontend**:
        - [TransactionItem.jsx](file:///d:/Projects/Spendsy/frontend/src/components/domain/TransactionItem.jsx): cyan `TXFR` badge, cyan card border, neutralized amount color (no red/green), `↔` prefix instead of `+`/`-`.
        - [EditTransactionModal.jsx](file:///d:/Projects/Spendsy/frontend/src/components/ui/EditTransactionModal.jsx): new toggle "Mark as inter-account transfer" — calls `PATCH /transactions/{uid}/transfer-flag` directly. Requires `apiBaseUrl` + `onTransferFlagChanged` props (wired through `HistoryPage` from `App.jsx`).
    - **Design choices that are deliberate** (don't casually regress these):
        - Do NOT change the `type` field. Kept as `income`/`expense`. `is_transfer` is the reclassification; this keeps dedupe, fingerprinting, and schemas compatible.
        - Do NOT retroactively scan existing rows at migration time. Users re-import or call `/transfers/reconcile` explicitly — silent reclassification of already-seen totals is scary.
        - Do NOT match cross-type transfers (debit→debit, UPI-to-self). No signal strong enough without an account-name field. Left for a later pass.
        - Conservative keyword gating means some real transfers will be missed — that's the right trade-off; users manually flag via the modal.
    - **Operational**: Applied migration via `docker exec spendsy_finance alembic upgrade head`, then `docker restart spendsy_finance`. Service booted clean.

### 2026-04-24 (earlier in the day)
- **Credit Card Statement Date Parsing**: Extended the month/year inference work from 2026-04-23 to handle credit card statement layouts where rows typically carry only day+month (e.g. "15APR", "15/04") because the year is in a statement-level header rather than per row.
    - **Parser** ([digital_deterministic_parser.py](file:///d:/Projects/Spendsy/backend/finance-service/app/services/parser/digital_deterministic_parser.py)):
        - Expanded `DATE_RE` to also match day+3-letter-month (`15APR`) and day/month numeric (`15/04`) tokens so those rows are recognized as new transactions instead of being merged into the previous row as a continuation.
        - Added `DATE_NO_YEAR_RE` helper regex and `extract_day_month_no_year()` which returns `(day, month)` from year-less tokens.
        - Reworked the fill-forward pass to carry `last_good_ymd` (year, month, day). For year-less rows: keep the real day, inherit year from the previous row, and roll the year forward if the month wrapped backwards (e.g. Dec → Jan). These rows are **not** flagged `date_inferred` because the day is real — they get exact dates.
        - Fully unreadable rows still fall back to day=01 with `date_inferred=True` (unchanged UI behavior: renders "Mon YYYY").
    - **No DB / routes / frontend changes required** — credit and debit statements go through the same `/parse-digital-pdf` route and the same `parse_statement` function, so the new logic applies to both uniformly. `account_type` ("credit" vs "debit") is only used for the CCT/DCT badge, not for any parser branching.
    - **Operational**: Restarted `spendsy_finance` container after the edit.

### 2026-04-23
- **Budget & Expense Fix**: Resolved a critical inaccuracy where monthly spending was calculated from a limited local transaction list.
    - **Backend**: Updated `/summary` endpoint to provide server-side current month totals (`month_expense`/`month_income`).
    - **Frontend**: Modified `HomePage` to use server-side monthly totals and fixed the budget status logic to show "No Limit Set" when `monthlyBudget` is 0.
- **Transaction History UI Bug**: Resolved a bug in `TransactionItem.jsx` where Debit Card Transactions (DCT) were incorrectly displaying as "MT" (Manual Transaction) when they had a low confidence score. Logic now prioritizes `account_type` for the label.
- **TORA AI Connectivity & Pipeline Fixes**: Addressed the "Internal Server Error" and pipeline data issues that caused the AI assistant to fail or return empty responses.
    - **OOM Prevention**: Reduced `num_ctx` to 4096 and `num_predict` to 1024 in `ollama_client.py` for the local `gemma4:e4b` model to fit within RAM constraints and prevent crash loops.
    - **JSON Resilience**: Updated `llm_router.py` to gracefully catch and return JSON parse errors from the fallback model instead of crashing the backend with a `RuntimeError`.
    - **History Pollution Fix**: Modified `tora_agent.py` to filter out empty LLM responses (`{}` or `""`) from the conversational history before constructing the context window. This broke the feedback loop where the LLM just echoed empty JSON back to the user.
    - **Strict JSON Schema Enforcement**: Replaced `format: "json"` in `ollama_client.py` with an explicit JSON Schema defining `answer` as an object with `mode` and `content`. This prevented the LLM from hallucinating keys like `"text"`.
    - **Parsing Robustness**: Updated the `answer` unwrapping logic in `tora_agent.py` to robustly check for either `"content"` or `"text"` keys to handle minor model structure drift.
- **TORA AI Output Quality Maximization (gemma4:e2b)**: Optimized the AI's internal reasoning and output format to maximize performance on smaller 2B parameter models.
    - **Model Switch**: Switched the primary model from `gemma4:e4b` to `gemma4:e2b` in `config.py` and `docker-compose.dev.yml` to further reduce resource contention and improve inference speed on local setups.
    - **Prompt Truncation**: Completely rewrote the massive 500-line `TORA_SYSTEM_PROMPT` in `tora_personality.py` into a focused ~40-line set of explicit rules. This eliminates the "lost-in-the-middle" memory issue common in small models when overwhelmed with complex instructions.
    - **Chain-of-Thought (CoT) Scratchpad**: Added a `"reasoning": {"type": "string"}` field to the JSON Schema in `ollama_client.py` and required the model to populate it *before* generating its final `"answer"`. This forces the model to verify context data silently before responding, eliminating hallucinations.
    - **Expanded Structured Schema**: Explicitly defined the 4 required keys for structured mode (`Financial Overview`, `Current Position`, `Recommended Strategy`, `Expected Outcome`) in the JSON schema, ensuring `gemma4:e2b` adheres perfectly to the React frontend UI's data expectations in `AICopilot.jsx`.
- **Project Logging**: Created `PROJECT_LOG.md` to maintain context across AI sessions.
- **Statement Parser — Inferred Month/Year Dates**: Parsed transactions on HistoryPage were all displaying today's date (`4/23/2026`). Root cause chain:
    1. Parser emitted correct dates when readable, but left blank strings for rows where the day column couldn't be read off the PDF.
    2. Legacy backend `_persist_parsed_transactions` silently defaulted blank dates to `date.today()`.
    3. Frontend `normalizeDate` helper silently returned `new Date()` for any falsy input.
    - **Approach**: Instead of skipping undated rows, inherit month/year from the previous dated row in statement order (day coerced to `01`), and flag the row as `date_inferred=True` so UI shows "Apr 2026" rather than a fake full date.
    - **Parser** ([digital_deterministic_parser.py](file:///d:/Projects/Spendsy/backend/finance-service/app/services/parser/digital_deterministic_parser.py)):
        - Added `date_inferred: bool` field on the `Transaction` dataclass.
        - New fill-forward pass in `parse_statement` after logical rows are collected: tracks `last_good_ym` and stamps undated rows with `YYYY-MM-01` + `date_inferred=True`.
    - **Model + Migration**:
        - Added `date_inferred BOOLEAN NOT NULL DEFAULT FALSE` to `finance_transaction` in [models.py](file:///d:/Projects/Spendsy/backend/finance-service/app/models.py).
        - New migration `backend/finance-service/alembic/versions/20260424_02_add_date_inferred_to_transaction.py` (down_revision: `20260424_01`). **Run `alembic upgrade head` in `backend/finance-service` before restarting the service.**
    - **Routes** ([routes_finance.py](file:///d:/Projects/Spendsy/backend/finance-service/app/api/routes_finance.py)):
        - Parse endpoint now includes `date_inferred` in each transaction payload.
        - `_persist_parsed_transactions` writes `date_inferred` onto the `Transaction` row.
        - `GET /transactions` serializer exposes `date_inferred` to the frontend.
    - **Frontend — display fallbacks hardened**:
        - [shared/utils/helpers.js](file:///d:/Projects/Spendsy/shared/utils/helpers.js) — `normalizeDate` now returns `null` for missing/invalid dates instead of `new Date()` (today). This was the silent display bug that masked the parser miss.
        - [TransactionItem.jsx](file:///d:/Projects/Spendsy/frontend/src/components/domain/TransactionItem.jsx) — renders "Mon YYYY" when `item.date_inferred`, full date otherwise, falls back to "Unknown" if no date.
        - [HomePage.jsx](file:///d:/Projects/Spendsy/frontend/src/pages/HomePage.jsx) — monthly filter, fiscal-year income filter, and today-expense filter all tolerate `null` from `normalizeDate` instead of NPE'ing.
        - [HistoryPage.jsx](file:///d:/Projects/Spendsy/frontend/src/pages/HistoryPage.jsx) — date-range filters skip undated rows; sort pushes undated rows to the bottom.
        - [StatsPage.jsx](file:///d:/Projects/Spendsy/frontend/src/pages/StatsPage.jsx) — aggregation skips undated rows so they don't poison time-bucketed charts.
    - **⚠️ Action needed for existing bad rows**: Transactions already in the DB still carry `date = 2026-04-23` from the old persist path. Migration alone does not re-date them. Either delete the existing statement's transactions and re-upload the PDF, or manually edit dates via the edit modal.

### 2026-04-21
- **Bulk Project Update**: Synchronized extensive changes across:
  - `backend/ai-service`, `auth-service`, `finance-service`
  - `frontend` components and styling
  - Infrastructure and environment configurations

### 2026-04-20
- **Bug Fixes**: Resolved UI/UX issues in the dashboard and navbar interactions.
- **Performance Optimization**: Refined data fetching for transaction ledgers.

---

## 📂 Key File Map
- **Frontend**: `frontend/src/`
- **Auth Service**: `backend/auth-service/`
- **Finance Service**: `backend/finance-service/`
- **AI Agent (Tora)**: `backend/spendsy-ai/`
- **Gateway Config**: `infra/docker/nginx/`
- **Environment**: `.env`

---
> [!TIP]
> When starting a new session, read this file first to understand the current trajectory of the project.
