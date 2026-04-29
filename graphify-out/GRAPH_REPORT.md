# Graph Report - Spendsy  (2026-04-29)

## Corpus Check
- 247 files · ~164,762 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1960 nodes · 4639 edges · 63 communities detected
- Extraction: 48% EXTRACTED · 52% INFERRED · 0% AMBIGUOUS · INFERRED: 2390 edges (avg confidence: 0.6)
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
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
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
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 105|Community 105]]
- [[_COMMUNITY_Community 106|Community 106]]
- [[_COMMUNITY_Community 107|Community 107]]
- [[_COMMUNITY_Community 108|Community 108]]
- [[_COMMUNITY_Community 109|Community 109]]
- [[_COMMUNITY_Community 110|Community 110]]
- [[_COMMUNITY_Community 111|Community 111]]
- [[_COMMUNITY_Community 112|Community 112]]
- [[_COMMUNITY_Community 113|Community 113]]
- [[_COMMUNITY_Community 114|Community 114]]

## God Nodes (most connected - your core abstractions)
1. `TieringConfig` - 153 edges
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

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (237): ABC, adjust_plan(), Send a POST request to finance-service to adjust an existing financial plan., compact_extras(), compress_history(), compress_transactions(), compress_trends(), Context compressor — MLA-inspired token reduction for Gemma 4.  OpenMythos uses (+229 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (169): Base, BaseModel, Base, get_db(), DeclarativeBase, ErrorCode, ApiAuditLog, CreditCard (+161 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (162): add_confidence_to_transaction  Revision ID: 0f8f7a931768 Revises: 20260321_01, upgrade(), add_file_metadata_and_document_table  Revision ID: 20260317_05 Revises: f790b, upgrade(), add tier column to finance_userprofile  Revision ID: 20260321_01 Revises: 202, upgrade(), record_audit(), decrypt_string() (+154 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (80): get_itr_form(), run_audit_endpoint(), build_tax_input_from_itr_data(), compare_regimes(), compute_advance_tax_schedule(), _compute_capital_gains_tax(), _compute_house_property_income(), _compute_surcharge() (+72 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (116): Appliances plugin: AC, fridge, washing machine, TV, geyser, microwave., build_fallback_from_yaml(), _plugin_strategy(), Shared helpers for plugin modules.  `build_fallback_from_yaml` constructs a Fetc, Lookup this plugin's declared strategy, defaulting to curated-static.      Calle, Materialise a FetchResult from this plugin's YAML fallback.      The YAML file's, Placeholder async fetcher.      Returns an empty FetchResult. Stage 1 ships with, stub_fetcher() (+108 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (88): Standardized security alerting for finance-service., Standardized audit logging for finance-service.     Persists to finance_apiaudi, record_alert(), _DummyRedisClient, _DummyRedisPipeline, from_url(), Simple in-memory Redis replacement for tests., Register a plugin under its `plugin_id`.      Re-registering the same id is allo (+80 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (25): ActiveLoansPage(), AddPage(), getAuthHeaders(), AlertsBell(), App(), DeductionBar(), BudgetPage(), cn() (+17 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (45): BaseHTTPMiddleware, getEnv(), get_url(), include_object(), run_migrations_offline(), run_migrations_online(), lifespan(), Return structured JSON for Pydantic validation failures. (+37 more)

### Community 8 - "Community 8"
Cohesion: 0.07
Nodes (40): Expect, GoldenQuestion, 50 golden questions for TORA regression testing.  Each question bundles:   - `pr, _format_response_for_judge(), _judge_available(), judge_response(), JudgeResult, LLM judge for soft quality grading of TORA responses.  Pairs with the determinis (+32 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (49): _aggregate_categories(), note_templates.py — Typed note generators for every vault document.  Each functi, Render a single Q&A turn to be appended to the daily conversation note., Render the frontmatter header for a new daily conversation note., Render a monthly summary of transactions., Main profile dashboard — always updated every session., Generate an Obsidian Canvas JSON file linking key vault notes., Convert a title to a safe filename (lowercase, underscores). (+41 more)

### Community 10 - "Community 10"
Cohesion: 0.06
Nodes (40): check_digital(), classify_type(), extract_day_month_no_year(), extract_row_parts(), extract_summary(), group_words_by_row(), is_noise(), is_valid_amount_token() (+32 more)

### Community 11 - "Community 11"
Cohesion: 0.09
Nodes (23): build_prompt(), call_gemini(), GeminiError, generate_text(), Execute the HTTP call to the Google Gemini API using gemini-1.5-flash-latest., call_llm(), check_ollama_health(), Quick connectivity check against Ollama. Returns status dict. (+15 more)

### Community 12 - "Community 12"
Cohesion: 0.1
Nodes (18): access_token(), ai_service(), _alias_app_namespace(), auth_service(), _compile_jsonb_sqlite(), _discover_service_modules(), finance_service(), load_service() (+10 more)

### Community 13 - "Community 13"
Cohesion: 0.09
Nodes (22): Expert, inject_expert_preamble(), Expert router — MoE-inspired prompt routing for Gemma 4.  Instead of switching m, Match question to best expert. Returns None for general queries., Route question → expert, prepend preamble to system prompt.      Returns (augmen, route_to_expert(), detect_ambiguous_goal(), detect_intent() (+14 more)

### Community 14 - "Community 14"
Cohesion: 0.17
Nodes (12): _candidate_user_ids(), _check_category_spike(), _check_large_transactions(), _check_unusual_merchant(), _recent_alert_signatures(), run_nightly_insights(), db_session(), _remap_jsonb_for_sqlite() (+4 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (6): AIFeaturesPage(), AppearancePage(), FinancialSettingsPage(), loadPrefs(), NotificationsPage(), savePref()

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
Cohesion: 0.22
Nodes (6): BaseSettings, db_password_must_be_set(), jwt_secret_must_be_secure(), redis_connection_url(), Settings, sqlalchemy_url()

### Community 22 - "Community 22"
Cohesion: 0.27
Nodes (9): call_tax_engine_compare(), compare_tax_regimes(), Tax Regime Comparison & Simulation Tool - Enables TORA to run "What-if" scenario, Call the tax-service compare_regimes endpoint to get Old vs New regime compariso, Pro tier feature: Simulate custom "What-if" tax scenarios.          Examples:, Simulate tax liability change if the user applies the proposed tax profile chang, Main tool function - Compare Old vs New tax regimes for a user.          Pro t, simulate_tax_profile_change() (+1 more)

### Community 23 - "Community 23"
Cohesion: 0.24
Nodes (9): calculate_investment_allocation(), calculate_tax_impact_of_investments(), Investment & Tax Optimization Simulation Tool - Pro tier feature Enables TORA t, Simulate SIP growth with tax optimization.          Shows post-tax returns for, Recommend tax-efficient investment allocation based on income and risk profile., Comprehensive investment x tax optimization simulation (Pro tier).          Co, Calculate how different investment strategies impact tax liability.          C, simulate_sip_growth_with_tax() (+1 more)

### Community 24 - "Community 24"
Cohesion: 0.24
Nodes (9): apply_tax_profile_update(), get_current_tax_profile(), Tax Profile Update Tool - Enables TORA to suggest and apply tax profile changes., Actually persist the tax profile changes to the database.     Called only AFTER, Fetch the user's current tax profile from finance-service., Main tool function called by TORA agent.          Workflow:     1. Fetch curr, Build a "Confirmation Shield" response that presents proposed tax profile change, suggest_tax_profile_updates() (+1 more)

### Community 25 - "Community 25"
Cohesion: 0.27
Nodes (8): audit_numbers(), audit_structured_output(), _extract_numbers_from_context(), _parse_rupee_match(), Post-generation number auditor.  gemma4:e2b is a strong small model but — like a, Apply audit_numbers to every text field of a TORA structured output.      Handle, Pull every rupee figure and percentage out of the injected context     block so, Audit every ₹ and % figure in `response_text` against `injected_context`.      R

### Community 26 - "Community 26"
Cohesion: 0.2
Nodes (8): build_training_triplets(), fetch_conversation_for_user(), fetch_feedback_rows(), collect.py — Extract high-quality TORA conversations for fine-tuning.  Reads fro, # TODO: Implement full pipeline once ToraFeedback has enough production data., Fetch feedback rows from finance-service internal API.      Returns a list of di, Fetch conversation history for a specific user., Convert conversation turns into training triplets.      Each triplet contains:

### Community 27 - "Community 27"
Cohesion: 0.22
Nodes (2): IntersectionObserver, ResizeObserver

### Community 28 - "Community 28"
Cohesion: 0.39
Nodes (7): build_report(), _classify(), _load_jsonl(), main(), _percentile(), Produce a human-readable report from the JSONL stress-test output.  Usage:     c, Classify each query result into one outcome bucket.      Buckets:       - hit

### Community 30 - "Community 30"
Cohesion: 0.48
Nodes (6): Enum, check_upload_limit(), get_tier(), require_pro(), UserTier, GoalCategory

### Community 31 - "Community 31"
Cohesion: 0.43
Nodes (4): MessageBubble(), renderInlineMarkdown(), renderMarkdown(), SectionCard()

### Community 32 - "Community 32"
Cohesion: 0.29
Nodes (2): useAuth(), DataProvider()

### Community 33 - "Community 33"
Cohesion: 0.47
Nodes (5): _add_columns_if_missing(), downgrade(), _drop_columns_if_present(), add personalization fields to userprofile and balance tracking to creditcard  Re, upgrade()

### Community 34 - "Community 34"
Cohesion: 0.33
Nodes (1): ErrorBoundary

### Community 35 - "Community 35"
Cohesion: 0.5
Nodes (2): Stop-PortProcesses(), Write-Status()

### Community 36 - "Community 36"
Cohesion: 0.5
Nodes (3): _json_type(), create finance base schema  Revision ID: 20260310_00 Revises: Create Date: 2, upgrade()

### Community 38 - "Community 38"
Cohesion: 0.5
Nodes (1): create auth base schema  Revision ID: 20260310_00 Revises: Create Date: 2026

### Community 39 - "Community 39"
Cohesion: 0.5
Nodes (1): add email unique index  Revision ID: 20260316_00 Revises: 20260310_00 Create

### Community 40 - "Community 40"
Cohesion: 0.5
Nodes (1): phase6_goals_tora_conversation  Revision ID: 0e6386aa6927 Revises: 80f9e8b135

### Community 41 - "Community 41"
Cohesion: 0.5
Nodes (1): add transaction ingestion fields  Revision ID: 20260310_01 Revises: 20260310_

### Community 42 - "Community 42"
Cohesion: 0.5
Nodes (1): add raw_description to transaction  Revision ID: 20260310_02 Revises: 2026031

### Community 43 - "Community 43"
Cohesion: 0.5
Nodes (1): add semantic dedupe index on finance_transaction  Revision ID: 20260310_03 Re

### Community 44 - "Community 44"
Cohesion: 0.5
Nodes (1): add transaction fingerprint column and index  Revision ID: 20260310_04 Revise

### Community 45 - "Community 45"
Cohesion: 0.5
Nodes (1): add extended fields to finance_taxprofile for TORA tax integration  Revision ID:

### Community 46 - "Community 46"
Cohesion: 0.5
Nodes (1): add tora_feedback table for thumbs up/down on TORA responses  Revision ID: 20260

### Community 47 - "Community 47"
Cohesion: 0.5
Nodes (1): add date_inferred to finance_transaction  Revision ID: 20260424_02 Revises: 2026

### Community 48 - "Community 48"
Cohesion: 0.5
Nodes (1): add transfer_group_id + is_transfer to finance_transaction  Revision ID: 2026042

### Community 49 - "Community 49"
Cohesion: 0.5
Nodes (1): add_loan_id_to_finance_plan  Revision ID: 2b006fc92769 Revises: 56496704cc52

### Community 50 - "Community 50"
Cohesion: 0.5
Nodes (1): add_bank_name_to_loan  Revision ID: 3be1fbcda5c7 Revises: 2b006fc92769 Creat

### Community 51 - "Community 51"
Cohesion: 0.5
Nodes (1): Add finance_plan table  Revision ID: 56496704cc52 Revises: 8a1528141186 Crea

### Community 52 - "Community 52"
Cohesion: 0.5
Nodes (1): Add phase 1 and 2 models  Revision ID: 6b4b4d46c405 Revises: 20260310_04 Cre

### Community 53 - "Community 53"
Cohesion: 0.5
Nodes (1): Add debit card model and update credit card  Revision ID: 80f9e8b135b5 Revise

### Community 54 - "Community 54"
Cohesion: 0.5
Nodes (1): Add status and reconciliation_flags to Transaction  Revision ID: 8a1528141186

### Community 105 - "Community 105"
Cohesion: 1.0
Nodes (1): Load conversation history for user.

### Community 106 - "Community 106"
Cohesion: 1.0
Nodes (1): Save a single conversation turn.

### Community 107 - "Community 107"
Cohesion: 1.0
Nodes (1): Get conversation limit (None for unlimited).

### Community 108 - "Community 108"
Cohesion: 1.0
Nodes (1): Get the LLM model name for a user tier.

### Community 109 - "Community 109"
Cohesion: 1.0
Nodes (1): Check if tier allows autonomous actions.

### Community 110 - "Community 110"
Cohesion: 1.0
Nodes (1): Get conversation memory turns for tier (0 == unlimited).

### Community 111 - "Community 111"
Cohesion: 1.0
Nodes (1): Get available simulation features for tier.

### Community 112 - "Community 112"
Cohesion: 1.0
Nodes (1): Get available tax features for tier.

### Community 113 - "Community 113"
Cohesion: 1.0
Nodes (1): Check if tier should expose specific PII type.

### Community 114 - "Community 114"
Cohesion: 1.0
Nodes (1): Check if action requires user confirmation for tier.

## Knowledge Gaps
- **271 isolated node(s):** `Return True if the given JTI has been blacklisted (i.e. logged out).`, `Fetch finance context for a given user, with 5-minute Redis cache.`, `create auth base schema  Revision ID: 20260310_00 Revises: Create Date: 2026`, `add email unique index  Revision ID: 20260316_00 Revises: 20260310_00 Create`, `Add SecurityAlert and ApiAuditLog models  Revision ID: dfb75467a0df Revises:` (+266 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 27`** (9 nodes): `setupTests.js`, `IntersectionObserver`, `.disconnect()`, `.observe()`, `.unobserve()`, `ResizeObserver`, `.disconnect()`, `.observe()`, `.unobserve()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (7 nodes): `AuthProvider()`, `getGatewayUrl()`, `useAuth()`, `DataProvider()`, `useData()`, `AuthContext.jsx`, `DataContext.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (6 nodes): `ErrorBoundary`, `.componentDidCatch()`, `.constructor()`, `.getDerivedStateFromError()`, `.render()`, `ErrorBoundary.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (5 nodes): `Check-Docker()`, `run-local.ps1`, `Stop-PortProcesses()`, `Write-Status()`, `Write-Step()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (4 nodes): `downgrade()`, `create auth base schema  Revision ID: 20260310_00 Revises: Create Date: 2026`, `upgrade()`, `20260310_00_create_auth_base.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (4 nodes): `downgrade()`, `add email unique index  Revision ID: 20260316_00 Revises: 20260310_00 Create`, `upgrade()`, `20260316_00_add_email_unique.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (4 nodes): `downgrade()`, `phase6_goals_tora_conversation  Revision ID: 0e6386aa6927 Revises: 80f9e8b135`, `upgrade()`, `0e6386aa6927_phase6_goals_tora_conversation.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (4 nodes): `downgrade()`, `add transaction ingestion fields  Revision ID: 20260310_01 Revises: 20260310_`, `upgrade()`, `20260310_01_add_transaction_ingestion_fields.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (4 nodes): `downgrade()`, `add raw_description to transaction  Revision ID: 20260310_02 Revises: 2026031`, `upgrade()`, `20260310_02_add_transaction_raw_description.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (4 nodes): `downgrade()`, `add semantic dedupe index on finance_transaction  Revision ID: 20260310_03 Re`, `upgrade()`, `20260310_03_add_semantic_dedupe_index.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (4 nodes): `downgrade()`, `add transaction fingerprint column and index  Revision ID: 20260310_04 Revise`, `upgrade()`, `20260310_04_add_transaction_fingerprint.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (4 nodes): `downgrade()`, `add extended fields to finance_taxprofile for TORA tax integration  Revision ID:`, `upgrade()`, `20260413_01_add_tax_profile_extended.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (4 nodes): `downgrade()`, `add tora_feedback table for thumbs up/down on TORA responses  Revision ID: 20260`, `upgrade()`, `20260424_01_add_tora_feedback.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (4 nodes): `downgrade()`, `add date_inferred to finance_transaction  Revision ID: 20260424_02 Revises: 2026`, `upgrade()`, `20260424_02_add_date_inferred_to_transaction.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (4 nodes): `downgrade()`, `add transfer_group_id + is_transfer to finance_transaction  Revision ID: 2026042`, `upgrade()`, `20260424_03_add_transfer_fields.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (4 nodes): `downgrade()`, `add_loan_id_to_finance_plan  Revision ID: 2b006fc92769 Revises: 56496704cc52`, `upgrade()`, `2b006fc92769_add_loan_id_to_finance_plan.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (4 nodes): `downgrade()`, `add_bank_name_to_loan  Revision ID: 3be1fbcda5c7 Revises: 2b006fc92769 Creat`, `upgrade()`, `3be1fbcda5c7_add_bank_name_to_loan.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (4 nodes): `downgrade()`, `Add finance_plan table  Revision ID: 56496704cc52 Revises: 8a1528141186 Crea`, `upgrade()`, `56496704cc52_add_finance_plan_table.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (4 nodes): `downgrade()`, `Add phase 1 and 2 models  Revision ID: 6b4b4d46c405 Revises: 20260310_04 Cre`, `upgrade()`, `6b4b4d46c405_add_phase_1_and_2_models.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (4 nodes): `downgrade()`, `Add debit card model and update credit card  Revision ID: 80f9e8b135b5 Revise`, `upgrade()`, `80f9e8b135b5_add_debit_card_model_and_update_credit_.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (4 nodes): `downgrade()`, `Add status and reconciliation_flags to Transaction  Revision ID: 8a1528141186`, `upgrade()`, `8a1528141186_add_status_and_reconciliation_flags_to_.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 105`** (1 nodes): `Load conversation history for user.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 106`** (1 nodes): `Save a single conversation turn.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 107`** (1 nodes): `Get conversation limit (None for unlimited).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 108`** (1 nodes): `Get the LLM model name for a user tier.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 109`** (1 nodes): `Check if tier allows autonomous actions.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 110`** (1 nodes): `Get conversation memory turns for tier (0 == unlimited).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 111`** (1 nodes): `Get available simulation features for tier.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 112`** (1 nodes): `Get available tax features for tier.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 113`** (1 nodes): `Check if tier should expose specific PII type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 114`** (1 nodes): `Check if action requires user confirmation for tier.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ToraUserTier` connect `Community 0` to `Community 2`, `Community 30`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `TaxInput` connect `Community 3` to `Community 1`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Are the 151 inferred relationships involving `TieringConfig` (e.g. with `QuestionRequest` and `FeedbackRequest`) actually correct?**
  _`TieringConfig` has 151 INFERRED edges - model-reasoned connections that need verification._
- **Are the 117 inferred relationships involving `str` (e.g. with `sqlalchemy_exception_handler()` and `_run_gemini()`) actually correct?**
  _`str` has 117 INFERRED edges - model-reasoned connections that need verification._
- **Are the 110 inferred relationships involving `TaxInput` (e.g. with `TaxComputeRequest` and `ITRFormRequest`) actually correct?**
  _`TaxInput` has 110 INFERRED edges - model-reasoned connections that need verification._
- **Are the 71 inferred relationships involving `Transaction` (e.g. with `Base` and `BulkDeletePayload`) actually correct?**
  _`Transaction` has 71 INFERRED edges - model-reasoned connections that need verification._
- **Are the 61 inferred relationships involving `UserContext` (e.g. with `BulkDeletePayload` and `TransferFlagPayload`) actually correct?**
  _`UserContext` has 61 INFERRED edges - model-reasoned connections that need verification._