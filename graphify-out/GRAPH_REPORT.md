# Graph Report - Spendsy  (2026-04-26)

## Corpus Check
- 247 files · ~158,011 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1982 nodes · 4613 edges · 75 communities detected
- Extraction: 48% EXTRACTED · 52% INFERRED · 0% AMBIGUOUS · INFERRED: 2387 edges (avg confidence: 0.6)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 103|Community 103]]
- [[_COMMUNITY_Community 104|Community 104]]
- [[_COMMUNITY_Community 105|Community 105]]
- [[_COMMUNITY_Community 106|Community 106]]
- [[_COMMUNITY_Community 107|Community 107]]
- [[_COMMUNITY_Community 108|Community 108]]
- [[_COMMUNITY_Community 109|Community 109]]
- [[_COMMUNITY_Community 110|Community 110]]
- [[_COMMUNITY_Community 111|Community 111]]
- [[_COMMUNITY_Community 112|Community 112]]
- [[_COMMUNITY_Community 127|Community 127]]
- [[_COMMUNITY_Community 128|Community 128]]
- [[_COMMUNITY_Community 129|Community 129]]
- [[_COMMUNITY_Community 130|Community 130]]
- [[_COMMUNITY_Community 131|Community 131]]
- [[_COMMUNITY_Community 132|Community 132]]
- [[_COMMUNITY_Community 133|Community 133]]
- [[_COMMUNITY_Community 134|Community 134]]
- [[_COMMUNITY_Community 135|Community 135]]
- [[_COMMUNITY_Community 136|Community 136]]
- [[_COMMUNITY_Community 137|Community 137]]
- [[_COMMUNITY_Community 138|Community 138]]
- [[_COMMUNITY_Community 139|Community 139]]
- [[_COMMUNITY_Community 140|Community 140]]
- [[_COMMUNITY_Community 141|Community 141]]

## God Nodes (most connected - your core abstractions)
1. `TieringConfig` - 170 edges
2. `TaxInput` - 113 edges
3. `Transaction` - 73 edges
4. `UserContext` - 65 edges
5. `success_response()` - 65 edges
6. `FreeTierStore` - 57 edges
7. `UserProfile` - 56 edges
8. `ProTierStore` - 54 edges
9. `EnterpriseTierStore` - 54 edges
10. `Loan` - 51 edges

## Surprising Connections (you probably didn't know these)
- `HealthResponse` --calls--> `health()`  [INFERRED]
  backend\finance-service\app\schemas.py → backend\ai-service\app\api\routes_ai.py
- `Mirrors Django's auth_user table to preserve existing data.` --uses--> `Base`  [INFERRED]
  backend\auth-service\app\models.py → backend\finance-service\app\core\database.py
- `Transaction` --uses--> `transfer_reconciler.py ========================  Detect inter-account transfer p`  [INFERRED]
  backend\finance-service\app\models.py → backend\finance-service\app\services\transfer_reconciler.py
- `Transaction` --uses--> `Summary of one reconciliation pass.`  [INFERRED]
  backend\finance-service\app\models.py → backend\finance-service\app\services\transfer_reconciler.py
- `Transaction` --uses--> `Scan the user's un-paired candidates and link matching pairs.      Runs a full p`  [INFERRED]
  backend\finance-service\app\models.py → backend\finance-service\app\services\transfer_reconciler.py

## Hyperedges (group relationships)
- **Core Microservices Architecture** — spendsy_auth_service, spendsy_finance_service, spendsy_ai_service [INFERRED 0.90]

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (173): compact_extras(), compress_history(), compress_transactions(), compress_trends(), Context compressor — MLA-inspired token reduction for Gemma 4.  OpenMythos uses, Compress conversation history.      Keep last `keep_recent` turns verbatim (they, Compress verbose trend descriptions into dense deltas.      Input might be multi, Compress transaction list into a dense block.      Instead of 15 individual line (+165 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (183): Standardized security alerting for finance-service., Standardized audit logging for finance-service.     Persists to finance_apiaudi, record_alert(), record_audit(), Base, BaseModel, Base, DeclarativeBase (+175 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (143): add_confidence_to_transaction  Revision ID: 0f8f7a931768 Revises: 20260321_01, upgrade(), add_file_metadata_and_document_table  Revision ID: 20260317_05 Revises: f790b, upgrade(), add tier column to finance_userprofile  Revision ID: 20260321_01 Revises: 202, upgrade(), decrypt_string(), encrypt_string() (+135 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (78): build_tax_input_from_itr_data(), compare_regimes(), compute_advance_tax_schedule(), _compute_capital_gains_tax(), _compute_house_property_income(), _compute_surcharge(), compute_tax(), determine_itr_form() (+70 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (123): Appliances plugin: AC, fridge, washing machine, TV, geyser, microwave., build_fallback_from_yaml(), _plugin_strategy(), Shared helpers for plugin modules.  `build_fallback_from_yaml` constructs a Fetc, Lookup this plugin's declared strategy, defaulting to curated-static.      Calle, Materialise a FetchResult from this plugin's YAML fallback.      The YAML file's, Placeholder async fetcher.      Returns an empty FetchResult. Stage 1 ships with, stub_fetcher() (+115 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (93): access_token(), ai_service(), _alias_app_namespace(), auth_service(), _compile_jsonb_sqlite(), _discover_service_modules(), _DummyRedisClient, _DummyRedisPipeline (+85 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (78): ABC, build_conversation_context(), ConversationStore, EnterpriseTierStore, format_memory_stats(), FreeTierStore, get_memory_store(), inject_memory_into_system_prompt() (+70 more)

### Community 7 - "Community 7"
Cohesion: 0.03
Nodes (62): adjust_plan(), Send a POST request to finance-service to adjust an existing financial plan., call_tax_engine_compare(), compare_tax_regimes(), Tax Regime Comparison & Simulation Tool - Enables TORA to run "What-if" scenario, Call the tax-service compare_regimes endpoint to get Old vs New regime compariso, Pro tier feature: Simulate custom "What-if" tax scenarios.          Examples:, Simulate tax liability change if the user applies the proposed tax profile chang (+54 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (46): BaseHTTPMiddleware, getEnv(), get_url(), include_object(), run_migrations_offline(), run_migrations_online(), health_check(), lifespan() (+38 more)

### Community 9 - "Community 9"
Cohesion: 0.07
Nodes (40): Expect, GoldenQuestion, 50 golden questions for TORA regression testing.  Each question bundles:   - `pr, _format_response_for_judge(), _judge_available(), judge_response(), JudgeResult, LLM judge for soft quality grading of TORA responses.  Pairs with the determinis (+32 more)

### Community 10 - "Community 10"
Cohesion: 0.08
Nodes (49): _aggregate_categories(), note_templates.py — Typed note generators for every vault document.  Each functi, Render a single Q&A turn to be appended to the daily conversation note., Render the frontmatter header for a new daily conversation note., Render a monthly summary of transactions., Main profile dashboard — always updated every session., Generate an Obsidian Canvas JSON file linking key vault notes., Convert a title to a safe filename (lowercase, underscores). (+41 more)

### Community 11 - "Community 11"
Cohesion: 0.04
Nodes (21): ActiveLoansPage(), AddPage(), getAuthHeaders(), AlertsBell(), App(), DeductionBar(), BudgetPage(), cn() (+13 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (39): check_digital(), classify_type(), extract_day_month_no_year(), extract_row_parts(), extract_summary(), group_words_by_row(), is_noise(), is_valid_amount_token() (+31 more)

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (19): _candidate_user_ids(), _check_category_spike(), _check_large_transactions(), _check_unusual_merchant(), _emit_alert(), Nightly proactive-insights engine.  Walks every user and runs a set of determini, Compare last-30-day spend per category to prior 30 days., Flag any expense ≥ 3× the user's median, floor ₹5k. (+11 more)

### Community 14 - "Community 14"
Cohesion: 0.1
Nodes (21): build_prompt(), call_gemini(), GeminiError, generate_text(), Execute the HTTP call to the Google Gemini API using gemini-1.5-flash-latest., call_llm(), Route the prompt to specialized local models via Ollama with reasoning fallback., call_mistral() (+13 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (5): AIFeaturesPage(), loadPrefs(), NotificationsPage(), savePref(), Toggle()

### Community 16 - "Community 16"
Cohesion: 0.17
Nodes (16): generate_corpus(), GeneratedQuery, Persona, QueryLabel, Realistic Indian-user query generator for TORA stress testing.  Produces ~1200 q, A realistic Indian user persona. Used to template surplus/city/age     into quer, Produce a deterministic corpus of ~`n_target` queries.      Split roughly:, Quick inventory of what we generated — handy for the report header. (+8 more)

### Community 17 - "Community 17"
Cohesion: 0.15
Nodes (15): budget_recommendation(), call_finance_internal(), create_plan(), delete_plan(), get_summary(), get_transactions(), Invoked by TORA to create a new financial goal/plan., Invoked by TORA to delete an existing financial goal/plan. (+7 more)

### Community 18 - "Community 18"
Cohesion: 0.22
Nodes (15): apiFetch(), buildHeaders(), buildRequestError(), clearStoredAuth(), getStoredAccessToken(), getStoredRefreshToken(), isRefreshExcluded(), persistAuthResponse() (+7 more)

### Community 19 - "Community 19"
Cohesion: 0.16
Nodes (5): fmt(), fmtNum(), generateRecommendations(), ITRPage(), runAuditChecks()

### Community 20 - "Community 20"
Cohesion: 0.14
Nodes (3): useFlatTransactions(), useTaxProfile(), useTransactions()

### Community 21 - "Community 21"
Cohesion: 0.25
Nodes (11): Complete-CleanupWatcher(), Format-CommandArgument(), Get-ComposeContainerIds(), Remove-LogSubscription(), Resolve-ExecutablePath(), Start-CleanupWatcher(), Start-LoggedProcess(), Stop-Everything() (+3 more)

### Community 22 - "Community 22"
Cohesion: 0.22
Nodes (6): BaseSettings, db_password_must_be_set(), jwt_secret_must_be_secure(), redis_connection_url(), Settings, sqlalchemy_url()

### Community 23 - "Community 23"
Cohesion: 0.27
Nodes (8): audit_numbers(), audit_structured_output(), _extract_numbers_from_context(), _parse_rupee_match(), Post-generation number auditor.  gemma4:e2b is a strong small model but — like a, Apply audit_numbers to every text field of a TORA structured output.      Handle, Pull every rupee figure and percentage out of the injected context     block so, Audit every ₹ and % figure in `response_text` against `injected_context`.      R

### Community 24 - "Community 24"
Cohesion: 0.2
Nodes (8): build_training_triplets(), fetch_conversation_for_user(), fetch_feedback_rows(), collect.py — Extract high-quality TORA conversations for fine-tuning.  Reads fro, # TODO: Implement full pipeline once ToraFeedback has enough production data., Fetch feedback rows from finance-service internal API.      Returns a list of di, Fetch conversation history for a specific user., Convert conversation turns into training triplets.      Each triplet contains:

### Community 25 - "Community 25"
Cohesion: 0.22
Nodes (2): IntersectionObserver, ResizeObserver

### Community 26 - "Community 26"
Cohesion: 0.39
Nodes (7): build_report(), _classify(), _load_jsonl(), main(), _percentile(), Produce a human-readable report from the JSONL stress-test output.  Usage:     c, Classify each query result into one outcome bucket.      Buckets:       - hit

### Community 28 - "Community 28"
Cohesion: 0.43
Nodes (4): MessageBubble(), renderInlineMarkdown(), renderMarkdown(), SectionCard()

### Community 29 - "Community 29"
Cohesion: 0.29
Nodes (2): useAuth(), DataProvider()

### Community 30 - "Community 30"
Cohesion: 0.47
Nodes (5): _add_columns_if_missing(), downgrade(), _drop_columns_if_present(), add personalization fields to userprofile and balance tracking to creditcard  Re, upgrade()

### Community 31 - "Community 31"
Cohesion: 0.33
Nodes (1): ErrorBoundary

### Community 32 - "Community 32"
Cohesion: 0.5
Nodes (3): _json_type(), create finance base schema  Revision ID: 20260310_00 Revises: Create Date: 2, upgrade()

### Community 34 - "Community 34"
Cohesion: 0.5
Nodes (1): create auth base schema  Revision ID: 20260310_00 Revises: Create Date: 2026

### Community 35 - "Community 35"
Cohesion: 0.5
Nodes (1): add email unique index  Revision ID: 20260316_00 Revises: 20260310_00 Create

### Community 36 - "Community 36"
Cohesion: 0.5
Nodes (1): phase6_goals_tora_conversation  Revision ID: 0e6386aa6927 Revises: 80f9e8b135

### Community 37 - "Community 37"
Cohesion: 0.5
Nodes (1): add transaction ingestion fields  Revision ID: 20260310_01 Revises: 20260310_

### Community 38 - "Community 38"
Cohesion: 0.5
Nodes (1): add raw_description to transaction  Revision ID: 20260310_02 Revises: 2026031

### Community 39 - "Community 39"
Cohesion: 0.5
Nodes (1): add semantic dedupe index on finance_transaction  Revision ID: 20260310_03 Re

### Community 40 - "Community 40"
Cohesion: 0.5
Nodes (1): add transaction fingerprint column and index  Revision ID: 20260310_04 Revise

### Community 41 - "Community 41"
Cohesion: 0.5
Nodes (1): add extended fields to finance_taxprofile for TORA tax integration  Revision ID:

### Community 42 - "Community 42"
Cohesion: 0.5
Nodes (1): add tora_feedback table for thumbs up/down on TORA responses  Revision ID: 20260

### Community 43 - "Community 43"
Cohesion: 0.5
Nodes (1): add date_inferred to finance_transaction  Revision ID: 20260424_02 Revises: 2026

### Community 44 - "Community 44"
Cohesion: 0.5
Nodes (1): add transfer_group_id + is_transfer to finance_transaction  Revision ID: 2026042

### Community 45 - "Community 45"
Cohesion: 0.5
Nodes (1): add_loan_id_to_finance_plan  Revision ID: 2b006fc92769 Revises: 56496704cc52

### Community 46 - "Community 46"
Cohesion: 0.5
Nodes (1): add_bank_name_to_loan  Revision ID: 3be1fbcda5c7 Revises: 2b006fc92769 Creat

### Community 47 - "Community 47"
Cohesion: 0.5
Nodes (1): Add finance_plan table  Revision ID: 56496704cc52 Revises: 8a1528141186 Crea

### Community 48 - "Community 48"
Cohesion: 0.5
Nodes (1): Add phase 1 and 2 models  Revision ID: 6b4b4d46c405 Revises: 20260310_04 Cre

### Community 49 - "Community 49"
Cohesion: 0.5
Nodes (1): Add debit card model and update credit card  Revision ID: 80f9e8b135b5 Revise

### Community 50 - "Community 50"
Cohesion: 0.5
Nodes (1): Add status and reconciliation_flags to Transaction  Revision ID: 8a1528141186

### Community 85 - "Community 85"
Cohesion: 1.0
Nodes (2): Gemma 4 MoE, TORA Intelligence Engine

### Community 103 - "Community 103"
Cohesion: 1.0
Nodes (1): Load conversation history for user.

### Community 104 - "Community 104"
Cohesion: 1.0
Nodes (1): Save a single conversation turn.

### Community 105 - "Community 105"
Cohesion: 1.0
Nodes (1): Get conversation limit (None for unlimited).

### Community 106 - "Community 106"
Cohesion: 1.0
Nodes (1): Get the LLM model name for a user tier.

### Community 107 - "Community 107"
Cohesion: 1.0
Nodes (1): Check if tier allows autonomous actions.

### Community 108 - "Community 108"
Cohesion: 1.0
Nodes (1): Get conversation memory turns for tier (0 == unlimited).

### Community 109 - "Community 109"
Cohesion: 1.0
Nodes (1): Get available simulation features for tier.

### Community 110 - "Community 110"
Cohesion: 1.0
Nodes (1): Get available tax features for tier.

### Community 111 - "Community 111"
Cohesion: 1.0
Nodes (1): Check if tier should expose specific PII type.

### Community 112 - "Community 112"
Cohesion: 1.0
Nodes (1): Check if action requires user confirmation for tier.

### Community 127 - "Community 127"
Cohesion: 1.0
Nodes (1): Categorizes the user's message as one of:         - 'greeting'        — pure hi

### Community 128 - "Community 128"
Cohesion: 1.0
Nodes (1): Checks if the user's question relates to personal finance topics.     Deprecate

### Community 129 - "Community 129"
Cohesion: 1.0
Nodes (1): Returns a conversational greeting as a simple-mode reply.      is_returning: T

### Community 130 - "Community 130"
Cohesion: 1.0
Nodes (1): Deterministic reply to greetings/acknowledgements — never calls the LLM.

### Community 131 - "Community 131"
Cohesion: 1.0
Nodes (1): Returns TORA's capability summary as a simple-mode markdown reply.

### Community 132 - "Community 132"
Cohesion: 1.0
Nodes (1): Return a canned clarifying question when the ask is obviously incomplete.

### Community 133 - "Community 133"
Cohesion: 1.0
Nodes (1): Wrap `detect_ambiguous_goal` output in the simple-mode JSON envelope.

### Community 134 - "Community 134"
Cohesion: 1.0
Nodes (1): Returns a simple-mode reply for off-topic queries.      Note: this is only use

### Community 135 - "Community 135"
Cohesion: 1.0
Nodes (1): Build a synonym → canonical lookup.      Lowercases everything. If a phrase appe

### Community 136 - "Community 136"
Cohesion: 1.0
Nodes (1): Register every plugin module's PLUGIN object. Idempotent.

### Community 137 - "Community 137"
Cohesion: 1.0
Nodes (1): Generate an Obsidian Canvas JSON file linking key vault notes.

### Community 138 - "Community 138"
Cohesion: 1.0
Nodes (1): Convert a title to a safe filename (lowercase, underscores).

### Community 139 - "Community 139"
Cohesion: 1.0
Nodes (1): Group transactions by category and return sorted (cat, total) pairs.

### Community 140 - "Community 140"
Cohesion: 1.0
Nodes (1): Spendsy Platform

### Community 141 - "Community 141"
Cohesion: 1.0
Nodes (1): AUDIT_MASTER_2026_04_26

## Knowledge Gaps
- **312 isolated node(s):** `Return True if the given JTI has been blacklisted (i.e. logged out).`, `Fetch finance context for a given user, with 5-minute Redis cache.`, `create auth base schema  Revision ID: 20260310_00 Revises: Create Date: 2026`, `add email unique index  Revision ID: 20260316_00 Revises: 20260310_00 Create`, `Add SecurityAlert and ApiAuditLog models  Revision ID: dfb75467a0df Revises:` (+307 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 25`** (9 nodes): `setupTests.js`, `IntersectionObserver`, `.disconnect()`, `.observe()`, `.unobserve()`, `ResizeObserver`, `.disconnect()`, `.observe()`, `.unobserve()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (7 nodes): `AuthProvider()`, `getGatewayUrl()`, `useAuth()`, `DataProvider()`, `useData()`, `AuthContext.jsx`, `DataContext.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (6 nodes): `ErrorBoundary`, `.componentDidCatch()`, `.constructor()`, `.getDerivedStateFromError()`, `.render()`, `ErrorBoundary.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (4 nodes): `downgrade()`, `create auth base schema  Revision ID: 20260310_00 Revises: Create Date: 2026`, `upgrade()`, `20260310_00_create_auth_base.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (4 nodes): `downgrade()`, `add email unique index  Revision ID: 20260316_00 Revises: 20260310_00 Create`, `upgrade()`, `20260316_00_add_email_unique.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (4 nodes): `downgrade()`, `phase6_goals_tora_conversation  Revision ID: 0e6386aa6927 Revises: 80f9e8b135`, `upgrade()`, `0e6386aa6927_phase6_goals_tora_conversation.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (4 nodes): `downgrade()`, `add transaction ingestion fields  Revision ID: 20260310_01 Revises: 20260310_`, `upgrade()`, `20260310_01_add_transaction_ingestion_fields.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (4 nodes): `downgrade()`, `add raw_description to transaction  Revision ID: 20260310_02 Revises: 2026031`, `upgrade()`, `20260310_02_add_transaction_raw_description.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (4 nodes): `downgrade()`, `add semantic dedupe index on finance_transaction  Revision ID: 20260310_03 Re`, `upgrade()`, `20260310_03_add_semantic_dedupe_index.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (4 nodes): `downgrade()`, `add transaction fingerprint column and index  Revision ID: 20260310_04 Revise`, `upgrade()`, `20260310_04_add_transaction_fingerprint.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (4 nodes): `downgrade()`, `add extended fields to finance_taxprofile for TORA tax integration  Revision ID:`, `upgrade()`, `20260413_01_add_tax_profile_extended.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (4 nodes): `downgrade()`, `add tora_feedback table for thumbs up/down on TORA responses  Revision ID: 20260`, `upgrade()`, `20260424_01_add_tora_feedback.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (4 nodes): `downgrade()`, `add date_inferred to finance_transaction  Revision ID: 20260424_02 Revises: 2026`, `upgrade()`, `20260424_02_add_date_inferred_to_transaction.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (4 nodes): `downgrade()`, `add transfer_group_id + is_transfer to finance_transaction  Revision ID: 2026042`, `upgrade()`, `20260424_03_add_transfer_fields.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (4 nodes): `downgrade()`, `add_loan_id_to_finance_plan  Revision ID: 2b006fc92769 Revises: 56496704cc52`, `upgrade()`, `2b006fc92769_add_loan_id_to_finance_plan.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (4 nodes): `downgrade()`, `add_bank_name_to_loan  Revision ID: 3be1fbcda5c7 Revises: 2b006fc92769 Creat`, `upgrade()`, `3be1fbcda5c7_add_bank_name_to_loan.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (4 nodes): `downgrade()`, `Add finance_plan table  Revision ID: 56496704cc52 Revises: 8a1528141186 Crea`, `upgrade()`, `56496704cc52_add_finance_plan_table.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (4 nodes): `downgrade()`, `Add phase 1 and 2 models  Revision ID: 6b4b4d46c405 Revises: 20260310_04 Cre`, `upgrade()`, `6b4b4d46c405_add_phase_1_and_2_models.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (4 nodes): `downgrade()`, `Add debit card model and update credit card  Revision ID: 80f9e8b135b5 Revise`, `upgrade()`, `80f9e8b135b5_add_debit_card_model_and_update_credit_.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (4 nodes): `downgrade()`, `Add status and reconciliation_flags to Transaction  Revision ID: 8a1528141186`, `upgrade()`, `8a1528141186_add_status_and_reconciliation_flags_to_.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 85`** (2 nodes): `Gemma 4 MoE`, `TORA Intelligence Engine`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 103`** (1 nodes): `Load conversation history for user.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 104`** (1 nodes): `Save a single conversation turn.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 105`** (1 nodes): `Get conversation limit (None for unlimited).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 106`** (1 nodes): `Get the LLM model name for a user tier.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 107`** (1 nodes): `Check if tier allows autonomous actions.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 108`** (1 nodes): `Get conversation memory turns for tier (0 == unlimited).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 109`** (1 nodes): `Get available simulation features for tier.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 110`** (1 nodes): `Get available tax features for tier.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 111`** (1 nodes): `Check if tier should expose specific PII type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 112`** (1 nodes): `Check if action requires user confirmation for tier.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 127`** (1 nodes): `Categorizes the user's message as one of:         - 'greeting'        — pure hi`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 128`** (1 nodes): `Checks if the user's question relates to personal finance topics.     Deprecate`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 129`** (1 nodes): `Returns a conversational greeting as a simple-mode reply.      is_returning: T`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 130`** (1 nodes): `Deterministic reply to greetings/acknowledgements — never calls the LLM.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 131`** (1 nodes): `Returns TORA's capability summary as a simple-mode markdown reply.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 132`** (1 nodes): `Return a canned clarifying question when the ask is obviously incomplete.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 133`** (1 nodes): `Wrap `detect_ambiguous_goal` output in the simple-mode JSON envelope.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 134`** (1 nodes): `Returns a simple-mode reply for off-topic queries.      Note: this is only use`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 135`** (1 nodes): `Build a synonym → canonical lookup.      Lowercases everything. If a phrase appe`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 136`** (1 nodes): `Register every plugin module's PLUGIN object. Idempotent.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 137`** (1 nodes): `Generate an Obsidian Canvas JSON file linking key vault notes.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 138`** (1 nodes): `Convert a title to a safe filename (lowercase, underscores).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 139`** (1 nodes): `Group transactions by category and return sorted (cat, total) pairs.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 140`** (1 nodes): `Spendsy Platform`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 141`** (1 nodes): `AUDIT_MASTER_2026_04_26`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TieringConfig` connect `Community 0` to `Community 6`?**
  _High betweenness centrality (0.135) - this node is a cross-community bridge._
- **Why does `ToraUserTier` connect `Community 0` to `Community 1`, `Community 2`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `TaxInput` connect `Community 3` to `Community 1`, `Community 2`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 168 inferred relationships involving `TieringConfig` (e.g. with `QuestionRequest` and `FeedbackRequest`) actually correct?**
  _`TieringConfig` has 168 INFERRED edges - model-reasoned connections that need verification._
- **Are the 114 inferred relationships involving `str` (e.g. with `sqlalchemy_exception_handler()` and `_run_gemini()`) actually correct?**
  _`str` has 114 INFERRED edges - model-reasoned connections that need verification._
- **Are the 110 inferred relationships involving `TaxInput` (e.g. with `TaxComputeRequest` and `ITRFormRequest`) actually correct?**
  _`TaxInput` has 110 INFERRED edges - model-reasoned connections that need verification._
- **Are the 71 inferred relationships involving `Transaction` (e.g. with `Base` and `BulkDeletePayload`) actually correct?**
  _`Transaction` has 71 INFERRED edges - model-reasoned connections that need verification._