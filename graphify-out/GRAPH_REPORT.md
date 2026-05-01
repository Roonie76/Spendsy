# Graph Report - Spendsy  (2026-04-30)

## Corpus Check
- 273 files · ~182,558 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2375 nodes · 5739 edges · 102 communities detected
- Extraction: 46% EXTRACTED · 54% INFERRED · 0% AMBIGUOUS · INFERRED: 3093 edges (avg confidence: 0.59)
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
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
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
- [[_COMMUNITY_Community 142|Community 142]]
- [[_COMMUNITY_Community 143|Community 143]]
- [[_COMMUNITY_Community 144|Community 144]]
- [[_COMMUNITY_Community 145|Community 145]]
- [[_COMMUNITY_Community 146|Community 146]]
- [[_COMMUNITY_Community 147|Community 147]]
- [[_COMMUNITY_Community 148|Community 148]]
- [[_COMMUNITY_Community 149|Community 149]]
- [[_COMMUNITY_Community 150|Community 150]]
- [[_COMMUNITY_Community 151|Community 151]]
- [[_COMMUNITY_Community 152|Community 152]]
- [[_COMMUNITY_Community 153|Community 153]]
- [[_COMMUNITY_Community 154|Community 154]]
- [[_COMMUNITY_Community 155|Community 155]]
- [[_COMMUNITY_Community 156|Community 156]]
- [[_COMMUNITY_Community 157|Community 157]]
- [[_COMMUNITY_Community 158|Community 158]]
- [[_COMMUNITY_Community 159|Community 159]]
- [[_COMMUNITY_Community 160|Community 160]]
- [[_COMMUNITY_Community 161|Community 161]]
- [[_COMMUNITY_Community 162|Community 162]]
- [[_COMMUNITY_Community 163|Community 163]]
- [[_COMMUNITY_Community 164|Community 164]]
- [[_COMMUNITY_Community 165|Community 165]]
- [[_COMMUNITY_Community 166|Community 166]]
- [[_COMMUNITY_Community 167|Community 167]]
- [[_COMMUNITY_Community 168|Community 168]]

## God Nodes (most connected - your core abstractions)
1. `TieringConfig` - 231 edges
2. `TaxInput` - 113 edges
3. `Transaction` - 87 edges
4. `UserContext` - 79 edges
5. `UserProfile` - 70 edges
6. `ComplianceFilter` - 66 edges
7. `Loan` - 65 edges
8. `success_response()` - 65 edges
9. `ITRData` - 62 edges
10. `CreditCard` - 57 edges

## Surprising Connections (you probably didn't know these)
- `Transaction` --uses--> `transfer_reconciler.py ========================  Detect inter-account transfer p`  [INFERRED]
  backend\finance-service\app\models.py → backend\finance-service\app\services\transfer_reconciler.py
- `Transaction` --uses--> `Summary of one reconciliation pass.`  [INFERRED]
  backend\finance-service\app\models.py → backend\finance-service\app\services\transfer_reconciler.py
- `Transaction` --uses--> `Scan the user's un-paired candidates and link matching pairs.      Runs a full p`  [INFERRED]
  backend\finance-service\app\models.py → backend\finance-service\app\services\transfer_reconciler.py
- `Transaction` --uses--> `Remove transfer classification from both sides of a group. Returns     the numbe`  [INFERRED]
  backend\finance-service\app\models.py → backend\finance-service\app\services\transfer_reconciler.py
- `Transaction` --uses--> `When one side of a transfer is deleted, the other side is no longer     validly`  [INFERRED]
  backend\finance-service\app\models.py → backend\finance-service\app\services\transfer_reconciler.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (252): ComplianceFilter, Single entry point: ComplianceFilter.process_response(response, user_profile, qu, compact_extras(), compress_history(), compress_transactions(), compress_trends(), Context compressor — MLA-inspired token reduction for Gemma 4.  OpenMythos uses, Compress plans/loans/goals/cards JSON to minimal representation.      Strips nul (+244 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (160): Appliances plugin: AC, fridge, washing machine, TV, geyser, microwave., BankRates, _build_from_fallback(), build_rates_context_block(), fetch_bank_rates(), fetch_bank_rates_sync(), _fetch_one_bank(), _parse_bank_rates() (+152 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (187): Standardized security alerting for finance-service., Standardized audit logging for finance-service.     Persists to finance_apiaudi, record_alert(), record_audit(), Base, BaseModel, Base, DeclarativeBase (+179 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (162): add_confidence_to_transaction  Revision ID: 0f8f7a931768 Revises: 20260321_01, upgrade(), add_file_metadata_and_document_table  Revision ID: 20260317_05 Revises: f790b, upgrade(), add tier column to finance_userprofile  Revision ID: 20260321_01 Revises: 202, upgrade(), downgrade(), Add pgvector embedding columns to transaction and document tables  Revision ID: (+154 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (80): Tax API Routes — Server-side tax computation endpoints.  Provides:   POST /tax/c, Compute tax from the user's saved ITR data in the database.     This uses the da, Run pre-filing audit checks on the provided data., Compute tax liability under both Old and New regimes.      Accepts income, deduc, build_tax_input_from_itr_data(), compute_advance_tax_schedule(), _compute_capital_gains_tax(), _compute_house_property_income() (+72 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (99): access_token(), ai_service(), _alias_app_namespace(), auth_service(), _compile_jsonb_sqlite(), _discover_service_modules(), _DummyRedisClient, _DummyRedisPipeline (+91 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (82): ABC, build_conversation_context(), ConversationStore, EnterpriseTierStore, format_memory_stats(), FreeTierStore, get_memory_store(), get_tier_memory_limit() (+74 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (86): assign_to_zone(), check_digital(), classify_type(), detect_bank(), extract_day_month_no_year(), extract_summary(), _find_header_row(), group_words_by_row() (+78 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (74): _generate_response(), TORA Dataset Expander v3 ======================== Expands the training corpus fr, run_expansion(), Enum, EvalResult, evaluate(), evaluate_async(), Evaluator — Phase 4 AI trainer loop.  Scores each TORA response after it's sent (+66 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (56): adjust_plan(), Send a POST request to finance-service to adjust an existing financial plan., call_tax_engine_compare(), compare_tax_regimes(), Tax Regime Comparison & Simulation Tool - Enables TORA to run "What-if" scenario, Call the tax-service compare_regimes endpoint to get Old vs New regime compariso, Pro tier feature: Simulate custom "What-if" tax scenarios.          Examples:, Simulate tax liability change if the user applies the proposed tax profile chang (+48 more)

### Community 10 - "Community 10"
Cohesion: 0.03
Nodes (25): ActiveLoansPage(), AddPage(), getAuthHeaders(), AlertsBell(), App(), DeductionBar(), BudgetPage(), cn() (+17 more)

### Community 11 - "Community 11"
Cohesion: 0.04
Nodes (46): BaseHTTPMiddleware, getEnv(), get_url(), include_object(), run_migrations_offline(), run_migrations_online(), build_prompt(), GeminiError (+38 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (40): Expect, GoldenQuestion, 50 golden questions for TORA regression testing.  Each question bundles:   - `pr, _format_response_for_judge(), _judge_available(), judge_response(), JudgeResult, LLM judge for soft quality grading of TORA responses.  Pairs with the determinis (+32 more)

### Community 13 - "Community 13"
Cohesion: 0.08
Nodes (49): _aggregate_categories(), note_templates.py — Typed note generators for every vault document.  Each functi, Render a single Q&A turn to be appended to the daily conversation note., Render the frontmatter header for a new daily conversation note., Render a monthly summary of transactions., Main profile dashboard — always updated every session., Generate an Obsidian Canvas JSON file linking key vault notes., Convert a title to a safe filename (lowercase, underscores). (+41 more)

### Community 14 - "Community 14"
Cohesion: 0.09
Nodes (31): pack_context(), pack_context_for_tora(), Context Packer — Phase 2.  Replaces the rule-based context_compressor with a ret, High-level convenience wrapper called from tora_agent.py.      Runs retrieval +, Merge and trim all context sources into a single prompt-ready block.      Args:, _section(), detect_query_intents(), Retrieval Engine — Phase 2.  Takes query + user financial profile -> searches bo (+23 more)

### Community 15 - "Community 15"
Cohesion: 0.09
Nodes (28): audit_numbers(), audit_structured_output(), _extract_numbers_from_context(), _parse_rupee_match(), Post-generation number auditor.  gemma4:e2b is a strong small model but — like a, Apply audit_numbers to every text field of a TORA structured output.      Handle, Pull every rupee figure and percentage out of the injected context     block so, Audit every ₹ and % figure in `response_text` against `injected_context`.      R (+20 more)

### Community 16 - "Community 16"
Cohesion: 0.14
Nodes (16): _candidate_user_ids(), _check_category_spike(), _check_large_transactions(), _check_unusual_merchant(), _emit_alert(), _recent_alert_signatures(), run_nightly_insights(), db_session() (+8 more)

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (22): build_verifier_note(), compute_emi(), compute_lumpsum_fv(), compute_nps_80ccd1b(), compute_sip_corpus(), compute_tax_saving_80c(), compute_total_interest(), extract_pct_figures() (+14 more)

### Community 18 - "Community 18"
Cohesion: 0.13
Nodes (16): BaseSettings, db_password_must_be_set(), encryption_key_must_be_valid(), internal_api_key_must_be_secure(), jwt_secret_must_be_secure(), redis_connection_url(), Settings, sqlalchemy_url() (+8 more)

### Community 19 - "Community 19"
Cohesion: 0.12
Nodes (6): AIFeaturesPage(), AppearancePage(), FinancialSettingsPage(), loadPrefs(), NotificationsPage(), savePref()

### Community 20 - "Community 20"
Cohesion: 0.15
Nodes (15): budget_recommendation(), call_finance_internal(), create_plan(), delete_plan(), get_summary(), get_transactions(), Invoked by TORA to create a new financial goal/plan., Invoked by TORA to delete an existing financial goal/plan. (+7 more)

### Community 21 - "Community 21"
Cohesion: 0.22
Nodes (15): apiFetch(), buildHeaders(), buildRequestError(), clearStoredAuth(), getStoredAccessToken(), getStoredRefreshToken(), isRefreshExcluded(), persistAuthResponse() (+7 more)

### Community 22 - "Community 22"
Cohesion: 0.16
Nodes (5): fmt(), fmtNum(), generateRecommendations(), ITRPage(), runAuditChecks()

### Community 23 - "Community 23"
Cohesion: 0.14
Nodes (3): useFlatTransactions(), useTaxProfile(), useTransactions()

### Community 24 - "Community 24"
Cohesion: 0.24
Nodes (13): apply_faithfulness(), check_faithfulness(), _collect_ranker_values(), _extract_months(), _extract_pct(), _extract_rupee(), _nearest(), _parse_inr() (+5 more)

### Community 25 - "Community 25"
Cohesion: 0.21
Nodes (10): call_llm(), check_ollama_health(), Quick connectivity check against Ollama. Returns status dict., Route the prompt to local Ollama models.      Chain: primary (model_gemma) → f, call_ollama(), Ollama models often wrap JSON in ```json ... ``` fences despite format=json., Execute a chat completion request to the local Ollama API.      Args:         mo, _strip_code_fences() (+2 more)

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
Cohesion: 0.43
Nodes (4): MessageBubble(), renderInlineMarkdown(), renderMarkdown(), SectionCard()

### Community 31 - "Community 31"
Cohesion: 0.29
Nodes (2): useAuth(), DataProvider()

### Community 32 - "Community 32"
Cohesion: 0.47
Nodes (5): _add_columns_if_missing(), downgrade(), _drop_columns_if_present(), add personalization fields to userprofile and balance tracking to creditcard  Re, upgrade()

### Community 33 - "Community 33"
Cohesion: 0.33
Nodes (1): ErrorBoundary

### Community 34 - "Community 34"
Cohesion: 0.5
Nodes (2): Stop-PortProcesses(), Write-Status()

### Community 35 - "Community 35"
Cohesion: 0.5
Nodes (3): _json_type(), create finance base schema  Revision ID: 20260310_00 Revises: Create Date: 2, upgrade()

### Community 37 - "Community 37"
Cohesion: 0.5
Nodes (1): create auth base schema  Revision ID: 20260310_00 Revises: Create Date: 2026

### Community 38 - "Community 38"
Cohesion: 0.5
Nodes (1): add email unique index  Revision ID: 20260316_00 Revises: 20260310_00 Create

### Community 39 - "Community 39"
Cohesion: 0.5
Nodes (1): phase6_goals_tora_conversation  Revision ID: 0e6386aa6927 Revises: 80f9e8b135

### Community 40 - "Community 40"
Cohesion: 0.5
Nodes (1): add transaction ingestion fields  Revision ID: 20260310_01 Revises: 20260310_

### Community 41 - "Community 41"
Cohesion: 0.5
Nodes (1): add raw_description to transaction  Revision ID: 20260310_02 Revises: 2026031

### Community 42 - "Community 42"
Cohesion: 0.5
Nodes (1): add semantic dedupe index on finance_transaction  Revision ID: 20260310_03 Re

### Community 43 - "Community 43"
Cohesion: 0.5
Nodes (1): add transaction fingerprint column and index  Revision ID: 20260310_04 Revise

### Community 44 - "Community 44"
Cohesion: 0.5
Nodes (1): add extended fields to finance_taxprofile for TORA tax integration  Revision ID:

### Community 45 - "Community 45"
Cohesion: 0.5
Nodes (1): add tora_feedback table for thumbs up/down on TORA responses  Revision ID: 20260

### Community 46 - "Community 46"
Cohesion: 0.5
Nodes (1): add date_inferred to finance_transaction  Revision ID: 20260424_02 Revises: 2026

### Community 47 - "Community 47"
Cohesion: 0.5
Nodes (1): add transfer_group_id + is_transfer to finance_transaction  Revision ID: 2026042

### Community 48 - "Community 48"
Cohesion: 0.5
Nodes (1): add_loan_id_to_finance_plan  Revision ID: 2b006fc92769 Revises: 56496704cc52

### Community 49 - "Community 49"
Cohesion: 0.5
Nodes (1): add_bank_name_to_loan  Revision ID: 3be1fbcda5c7 Revises: 2b006fc92769 Creat

### Community 50 - "Community 50"
Cohesion: 0.5
Nodes (1): Add finance_plan table  Revision ID: 56496704cc52 Revises: 8a1528141186 Crea

### Community 51 - "Community 51"
Cohesion: 0.5
Nodes (1): Add phase 1 and 2 models  Revision ID: 6b4b4d46c405 Revises: 20260310_04 Cre

### Community 52 - "Community 52"
Cohesion: 0.5
Nodes (1): Add debit card model and update credit card  Revision ID: 80f9e8b135b5 Revise

### Community 53 - "Community 53"
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

### Community 129 - "Community 129"
Cohesion: 1.0
Nodes (1): Compliance and Safety Filter for TORA.     Ensures AI advice stays within RBI/SE

### Community 130 - "Community 130"
Cohesion: 1.0
Nodes (1): Applies compliance checks to the TORA response dictionary.

### Community 131 - "Community 131"
Cohesion: 1.0
Nodes (1): Extract structured GoalStruct from query + optional user profile.      Args:

### Community 132 - "Community 132"
Cohesion: 1.0
Nodes (1): 0 warnings → 1.0. Each warning reduces score by 0.2. Floor at 0.0.

### Community 133 - "Community 133"
Cohesion: 1.0
Nodes (1): compliance_filter output: {passed: bool, flags: list}.     passed=True + 0 flags

### Community 134 - "Community 134"
Cohesion: 1.0
Nodes (1): thumbs_up → 1.0 | thumbs_down → 0.0 | None → 0.5 (neutral).

### Community 135 - "Community 135"
Cohesion: 1.0
Nodes (1): Score a TORA response synchronously.     Called from the async wrapper below.

### Community 136 - "Community 136"
Cohesion: 1.0
Nodes (1): Async wrapper. Runs evaluate() in thread pool (non-blocking).     If result is a

### Community 137 - "Community 137"
Cohesion: 1.0
Nodes (1): Execute the HTTP call to the Google Gemini API using gemini-1.5-flash-latest.

### Community 138 - "Community 138"
Cohesion: 1.0
Nodes (1): Execute the HTTP call to the Mistral AI API using mistral-small-latest.

### Community 139 - "Community 139"
Cohesion: 1.0
Nodes (1): Categorizes the user's message as one of:         - 'greeting'        — pure hi

### Community 140 - "Community 140"
Cohesion: 1.0
Nodes (1): Checks if the user's question relates to personal finance topics.     Deprecate

### Community 141 - "Community 141"
Cohesion: 1.0
Nodes (1): Returns a conversational greeting as a simple-mode reply.      is_returning: T

### Community 142 - "Community 142"
Cohesion: 1.0
Nodes (1): Deterministic reply to greetings/acknowledgements — never calls the LLM.

### Community 143 - "Community 143"
Cohesion: 1.0
Nodes (1): Returns TORA's capability summary as a simple-mode markdown reply.

### Community 144 - "Community 144"
Cohesion: 1.0
Nodes (1): Return a canned clarifying question when the ask is obviously incomplete.

### Community 145 - "Community 145"
Cohesion: 1.0
Nodes (1): Wrap `detect_ambiguous_goal` output in the simple-mode JSON envelope.

### Community 146 - "Community 146"
Cohesion: 1.0
Nodes (1): Returns a simple-mode reply for off-topic queries.      Note: this is only use

### Community 147 - "Community 147"
Cohesion: 1.0
Nodes (1): Categorizes the user's message as one of:         - 'greeting'        — pure hi

### Community 148 - "Community 148"
Cohesion: 1.0
Nodes (1): Checks if the user's question relates to personal finance topics.     Deprecate

### Community 149 - "Community 149"
Cohesion: 1.0
Nodes (1): Returns a conversational greeting as a simple-mode reply.      is_returning: T

### Community 150 - "Community 150"
Cohesion: 1.0
Nodes (1): Deterministic reply to greetings/acknowledgements — never calls the LLM.

### Community 151 - "Community 151"
Cohesion: 1.0
Nodes (1): Returns TORA's capability summary as a simple-mode markdown reply.

### Community 152 - "Community 152"
Cohesion: 1.0
Nodes (1): Return a canned clarifying question when the ask is obviously incomplete.

### Community 153 - "Community 153"
Cohesion: 1.0
Nodes (1): Wrap `detect_ambiguous_goal` output in the simple-mode JSON envelope.

### Community 154 - "Community 154"
Cohesion: 1.0
Nodes (1): Returns a simple-mode reply for off-topic queries.      Note: this is only use

### Community 155 - "Community 155"
Cohesion: 1.0
Nodes (1): Returns a dictionary mapping tool names to functions.

### Community 156 - "Community 156"
Cohesion: 1.0
Nodes (1): Pull (day, month) from a token that's missing the year — e.g. '15APR'     or '1

### Community 157 - "Community 157"
Cohesion: 1.0
Nodes (1): Convert DD-MMM-YY, DD/MM/YYYY or corrupted DDMMYYYY to YYYY-MM-DD.      Return

### Community 158 - "Community 158"
Cohesion: 1.0
Nodes (1): Parse Indian-formatted amounts robustly.     Handles: 1,23,456.78 | 902.00 | 60

### Community 159 - "Community 159"
Cohesion: 1.0
Nodes (1): True if the word looks like a transaction amount, not a card number or noise.

### Community 160 - "Community 160"
Cohesion: 1.0
Nodes (1): Determine credit/debit from description keywords. BUG 4 FIX.

### Community 161 - "Community 161"
Cohesion: 1.0
Nodes (1): Group pdfplumber word dicts by their vertical (top) position.

### Community 162 - "Community 162"
Cohesion: 1.0
Nodes (1): Return True if the PDF has extractable text (digital).     Checks up to 10 page

### Community 163 - "Community 163"
Cohesion: 1.0
Nodes (1): Given words from one visual row (sorted by x), split into:       date_str, desc

### Community 164 - "Community 164"
Cohesion: 1.0
Nodes (1): Given list of (raw_text, x0) sorted ascending by x0:       - 0 nums  → (None, N

### Community 165 - "Community 165"
Cohesion: 1.0
Nodes (1): Pull opening and closing balances from free text.

### Community 166 - "Community 166"
Cohesion: 1.0
Nodes (1): Parse one page. Returns:       (logical_rows, raw_page_text)      Each logica

### Community 167 - "Community 167"
Cohesion: 1.0
Nodes (1): Parse a digital bank statement PDF.      Returns ParseResult with all transact

### Community 168 - "Community 168"
Cohesion: 1.0
Nodes (1): Compatibility wrapper for routes_finance.py.     Accepts bytes, parses via temp

## Knowledge Gaps
- **421 isolated node(s):** `Return True if the given JTI has been blacklisted (i.e. logged out).`, `Fetch finance context for a given user, with 5-minute Redis cache.`, `create auth base schema  Revision ID: 20260310_00 Revises: Create Date: 2026`, `add email unique index  Revision ID: 20260316_00 Revises: 20260310_00 Create`, `Add SecurityAlert and ApiAuditLog models  Revision ID: dfb75467a0df Revises:` (+416 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 27`** (9 nodes): `setupTests.js`, `IntersectionObserver`, `.disconnect()`, `.observe()`, `.unobserve()`, `ResizeObserver`, `.disconnect()`, `.observe()`, `.unobserve()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (7 nodes): `AuthProvider()`, `getGatewayUrl()`, `useAuth()`, `DataProvider()`, `useData()`, `AuthContext.jsx`, `DataContext.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (6 nodes): `ErrorBoundary`, `.componentDidCatch()`, `.constructor()`, `.getDerivedStateFromError()`, `.render()`, `ErrorBoundary.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (5 nodes): `Check-Docker()`, `run-local.ps1`, `Stop-PortProcesses()`, `Write-Status()`, `Write-Step()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (4 nodes): `downgrade()`, `create auth base schema  Revision ID: 20260310_00 Revises: Create Date: 2026`, `upgrade()`, `20260310_00_create_auth_base.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (4 nodes): `downgrade()`, `add email unique index  Revision ID: 20260316_00 Revises: 20260310_00 Create`, `upgrade()`, `20260316_00_add_email_unique.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (4 nodes): `downgrade()`, `phase6_goals_tora_conversation  Revision ID: 0e6386aa6927 Revises: 80f9e8b135`, `upgrade()`, `0e6386aa6927_phase6_goals_tora_conversation.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (4 nodes): `downgrade()`, `add transaction ingestion fields  Revision ID: 20260310_01 Revises: 20260310_`, `upgrade()`, `20260310_01_add_transaction_ingestion_fields.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (4 nodes): `downgrade()`, `add raw_description to transaction  Revision ID: 20260310_02 Revises: 2026031`, `upgrade()`, `20260310_02_add_transaction_raw_description.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (4 nodes): `downgrade()`, `add semantic dedupe index on finance_transaction  Revision ID: 20260310_03 Re`, `upgrade()`, `20260310_03_add_semantic_dedupe_index.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (4 nodes): `downgrade()`, `add transaction fingerprint column and index  Revision ID: 20260310_04 Revise`, `upgrade()`, `20260310_04_add_transaction_fingerprint.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (4 nodes): `downgrade()`, `add extended fields to finance_taxprofile for TORA tax integration  Revision ID:`, `upgrade()`, `20260413_01_add_tax_profile_extended.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (4 nodes): `downgrade()`, `add tora_feedback table for thumbs up/down on TORA responses  Revision ID: 20260`, `upgrade()`, `20260424_01_add_tora_feedback.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (4 nodes): `downgrade()`, `add date_inferred to finance_transaction  Revision ID: 20260424_02 Revises: 2026`, `upgrade()`, `20260424_02_add_date_inferred_to_transaction.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (4 nodes): `downgrade()`, `add transfer_group_id + is_transfer to finance_transaction  Revision ID: 2026042`, `upgrade()`, `20260424_03_add_transfer_fields.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (4 nodes): `downgrade()`, `add_loan_id_to_finance_plan  Revision ID: 2b006fc92769 Revises: 56496704cc52`, `upgrade()`, `2b006fc92769_add_loan_id_to_finance_plan.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (4 nodes): `downgrade()`, `add_bank_name_to_loan  Revision ID: 3be1fbcda5c7 Revises: 2b006fc92769 Creat`, `upgrade()`, `3be1fbcda5c7_add_bank_name_to_loan.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (4 nodes): `downgrade()`, `Add finance_plan table  Revision ID: 56496704cc52 Revises: 8a1528141186 Crea`, `upgrade()`, `56496704cc52_add_finance_plan_table.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (4 nodes): `downgrade()`, `Add phase 1 and 2 models  Revision ID: 6b4b4d46c405 Revises: 20260310_04 Cre`, `upgrade()`, `6b4b4d46c405_add_phase_1_and_2_models.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (4 nodes): `downgrade()`, `Add debit card model and update credit card  Revision ID: 80f9e8b135b5 Revise`, `upgrade()`, `80f9e8b135b5_add_debit_card_model_and_update_credit_.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (4 nodes): `downgrade()`, `Add status and reconciliation_flags to Transaction  Revision ID: 8a1528141186`, `upgrade()`, `8a1528141186_add_status_and_reconciliation_flags_to_.py`
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
- **Thin community `Community 129`** (1 nodes): `Compliance and Safety Filter for TORA.     Ensures AI advice stays within RBI/SE`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 130`** (1 nodes): `Applies compliance checks to the TORA response dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 131`** (1 nodes): `Extract structured GoalStruct from query + optional user profile.      Args:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 132`** (1 nodes): `0 warnings → 1.0. Each warning reduces score by 0.2. Floor at 0.0.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 133`** (1 nodes): `compliance_filter output: {passed: bool, flags: list}.     passed=True + 0 flags`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 134`** (1 nodes): `thumbs_up → 1.0 | thumbs_down → 0.0 | None → 0.5 (neutral).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 135`** (1 nodes): `Score a TORA response synchronously.     Called from the async wrapper below.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 136`** (1 nodes): `Async wrapper. Runs evaluate() in thread pool (non-blocking).     If result is a`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 137`** (1 nodes): `Execute the HTTP call to the Google Gemini API using gemini-1.5-flash-latest.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 138`** (1 nodes): `Execute the HTTP call to the Mistral AI API using mistral-small-latest.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 139`** (1 nodes): `Categorizes the user's message as one of:         - 'greeting'        — pure hi`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 140`** (1 nodes): `Checks if the user's question relates to personal finance topics.     Deprecate`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 141`** (1 nodes): `Returns a conversational greeting as a simple-mode reply.      is_returning: T`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 142`** (1 nodes): `Deterministic reply to greetings/acknowledgements — never calls the LLM.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 143`** (1 nodes): `Returns TORA's capability summary as a simple-mode markdown reply.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 144`** (1 nodes): `Return a canned clarifying question when the ask is obviously incomplete.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 145`** (1 nodes): `Wrap `detect_ambiguous_goal` output in the simple-mode JSON envelope.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 146`** (1 nodes): `Returns a simple-mode reply for off-topic queries.      Note: this is only use`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 147`** (1 nodes): `Categorizes the user's message as one of:         - 'greeting'        — pure hi`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 148`** (1 nodes): `Checks if the user's question relates to personal finance topics.     Deprecate`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 149`** (1 nodes): `Returns a conversational greeting as a simple-mode reply.      is_returning: T`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 150`** (1 nodes): `Deterministic reply to greetings/acknowledgements — never calls the LLM.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 151`** (1 nodes): `Returns TORA's capability summary as a simple-mode markdown reply.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 152`** (1 nodes): `Return a canned clarifying question when the ask is obviously incomplete.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 153`** (1 nodes): `Wrap `detect_ambiguous_goal` output in the simple-mode JSON envelope.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 154`** (1 nodes): `Returns a simple-mode reply for off-topic queries.      Note: this is only use`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 155`** (1 nodes): `Returns a dictionary mapping tool names to functions.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 156`** (1 nodes): `Pull (day, month) from a token that's missing the year — e.g. '15APR'     or '1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 157`** (1 nodes): `Convert DD-MMM-YY, DD/MM/YYYY or corrupted DDMMYYYY to YYYY-MM-DD.      Return`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 158`** (1 nodes): `Parse Indian-formatted amounts robustly.     Handles: 1,23,456.78 | 902.00 | 60`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 159`** (1 nodes): `True if the word looks like a transaction amount, not a card number or noise.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 160`** (1 nodes): `Determine credit/debit from description keywords. BUG 4 FIX.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 161`** (1 nodes): `Group pdfplumber word dicts by their vertical (top) position.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 162`** (1 nodes): `Return True if the PDF has extractable text (digital).     Checks up to 10 page`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 163`** (1 nodes): `Given words from one visual row (sorted by x), split into:       date_str, desc`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 164`** (1 nodes): `Given list of (raw_text, x0) sorted ascending by x0:       - 0 nums  → (None, N`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 165`** (1 nodes): `Pull opening and closing balances from free text.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 166`** (1 nodes): `Parse one page. Returns:       (logical_rows, raw_page_text)      Each logica`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 167`** (1 nodes): `Parse a digital bank statement PDF.      Returns ParseResult with all transact`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 168`** (1 nodes): `Compatibility wrapper for routes_finance.py.     Accepts bytes, parses via temp`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TieringConfig` connect `Community 0` to `Community 6`?**
  _High betweenness centrality (0.159) - this node is a cross-community bridge._
- **Why does `generate_financial_strategy()` connect `Community 0` to `Community 1`, `Community 3`, `Community 6`, `Community 8`, `Community 9`, `Community 14`, `Community 15`, `Community 17`, `Community 24`, `Community 25`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Why does `ToraUserTier` connect `Community 0` to `Community 8`, `Community 3`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Are the 229 inferred relationships involving `TieringConfig` (e.g. with `QuestionRequest` and `FeedbackRequest`) actually correct?**
  _`TieringConfig` has 229 INFERRED edges - model-reasoned connections that need verification._
- **Are the 130 inferred relationships involving `str` (e.g. with `sqlalchemy_exception_handler()` and `_run_gemini()`) actually correct?**
  _`str` has 130 INFERRED edges - model-reasoned connections that need verification._
- **Are the 110 inferred relationships involving `TaxInput` (e.g. with `TaxComputeRequest` and `ITRFormRequest`) actually correct?**
  _`TaxInput` has 110 INFERRED edges - model-reasoned connections that need verification._
- **Are the 85 inferred relationships involving `Transaction` (e.g. with `Base` and `BulkDeletePayload`) actually correct?**
  _`Transaction` has 85 INFERRED edges - model-reasoned connections that need verification._