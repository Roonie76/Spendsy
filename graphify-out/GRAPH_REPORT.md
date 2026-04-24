# Graph Report - .  (2026-04-24)

## Corpus Check
- Large corpus: 253 files · ~140,529 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder, or use --no-semantic to run AST-only.

## Summary
- 2110 nodes · 5519 edges · 102 communities detected
- Extraction: 58% EXTRACTED · 42% INFERRED · 0% AMBIGUOUS · INFERRED: 2327 edges (avg confidence: 0.6)
- Token cost: 1,500 input · 500 output

## Community Hubs (Navigation)
- [[_COMMUNITY_TORA Financial Intelligence|TORA Financial Intelligence]]
- [[_COMMUNITY_Database Models & Schemas|Database Models & Schemas]]
- [[_COMMUNITY_Indian Tax Engine|Indian Tax Engine]]
- [[_COMMUNITY_TORA Plugin Registry & Fetchers|TORA Plugin Registry & Fetchers]]
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
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
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
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 110|Community 110]]
- [[_COMMUNITY_Community 111|Community 111]]
- [[_COMMUNITY_Community 112|Community 112]]
- [[_COMMUNITY_Community 113|Community 113]]
- [[_COMMUNITY_Community 114|Community 114]]
- [[_COMMUNITY_Community 115|Community 115]]
- [[_COMMUNITY_Community 116|Community 116]]
- [[_COMMUNITY_Community 117|Community 117]]
- [[_COMMUNITY_Community 118|Community 118]]
- [[_COMMUNITY_Community 119|Community 119]]

## God Nodes (most connected - your core abstractions)
1. `TieringConfig` - 152 edges
2. `TaxInput` - 114 edges
3. `Transaction` - 74 edges
4. `UserContext` - 67 edges
5. `success_response()` - 66 edges
6. `FreeTierStore` - 58 edges
7. `UserProfile` - 57 edges
8. `ProTierStore` - 55 edges
9. `EnterpriseTierStore` - 55 edges
10. `Loan` - 52 edges

## Surprising Connections (you probably didn't know these)
- `Mirrors Django's auth_user table to preserve existing data.` --uses--> `Base`  [INFERRED]
  D:\Projects\Spendsy\backend\auth-service\app\models.py → D:\Projects\Spendsy\backend\finance-service\app\core\database.py
- `Summary of one reconciliation pass.` --uses--> `Transaction`  [INFERRED]
  D:\Projects\Spendsy\backend\finance-service\app\services\transfer_reconciler.py → D:\Projects\Spendsy\backend\finance-service\app\models.py
- `Scan the user's un-paired candidates and link matching pairs.      Runs a full p` --uses--> `Transaction`  [INFERRED]
  D:\Projects\Spendsy\backend\finance-service\app\services\transfer_reconciler.py → D:\Projects\Spendsy\backend\finance-service\app\models.py
- `Remove transfer classification from both sides of a group. Returns     the numbe` --uses--> `Transaction`  [INFERRED]
  D:\Projects\Spendsy\backend\finance-service\app\services\transfer_reconciler.py → D:\Projects\Spendsy\backend\finance-service\app\models.py
- `When one side of a transfer is deleted, the other side is no longer     validly` --uses--> `Transaction`  [INFERRED]
  D:\Projects\Spendsy\backend\finance-service\app\services\transfer_reconciler.py → D:\Projects\Spendsy\backend\finance-service\app\models.py

## Hyperedges (group relationships)
- **Core Microservices Architecture** — spendsy_auth_service, spendsy_finance_service, spendsy_ai_service [INFERRED 0.90]

## Communities

### Community 0 - "TORA Financial Intelligence"
Cohesion: 0.02
Nodes (227): ABC, build_conversation_context(), ConversationStore, EnterpriseTierStore, format_memory_stats(), FreeTierStore, get_memory_limit(), get_memory_store() (+219 more)

### Community 1 - "Database Models & Schemas"
Cohesion: 0.07
Nodes (167): Standardized security alerting for finance-service., Standardized audit logging for finance-service.     Persists to finance_apiaudi, Base, BaseModel, Base, get_db(), DeclarativeBase, Enum (+159 more)

### Community 2 - "Indian Tax Engine"
Cohesion: 0.03
Nodes (78): build_tax_input_from_itr_data(), compare_regimes(), compute_advance_tax_schedule(), _compute_capital_gains_tax(), _compute_house_property_income(), _compute_surcharge(), compute_tax(), determine_itr_form() (+70 more)

### Community 3 - "TORA Plugin Registry & Fetchers"
Cohesion: 0.03
Nodes (105): Appliances plugin: AC, fridge, washing machine, TV, geyser, microwave., build_fallback_from_yaml(), _plugin_strategy(), Shared helpers for plugin modules.  `build_fallback_from_yaml` constructs a Fetc, Lookup this plugin's declared strategy, defaulting to curated-static.      Calle, Materialise a FetchResult from this plugin's YAML fallback.      The YAML file's, Placeholder async fetcher.      Returns an empty FetchResult. Stage 1 ships with, stub_fetcher() (+97 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (132): record_alert(), record_audit(), decrypt_string(), encrypt_string(), get_aesgcm(), _get_key_bytes(), check_database_connection(), Lightweight connectivity probe used by health/readiness endpoints.     Keeps fa (+124 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (78): _DummyRedisClient, _DummyRedisPipeline, Simple in-memory Redis replacement for tests., Register a plugin under its `plugin_id`.      Re-registering the same id is allo, register(), fetch_finance_context(), Fetch finance context for a given user, with 5-minute Redis cache., Mirrors Django's auth_user table to preserve existing data. (+70 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (49): BaseHTTPMiddleware, build_prompt(), GeminiError, generate_text(), FeedbackRequest, fetch_user_tier(), handle_ask_tora(), health_check() (+41 more)

### Community 7 - "Community 7"
Cohesion: 0.05
Nodes (48): adjust_plan(), Send a POST request to finance-service to adjust an existing financial plan., call_tax_engine_compare(), compare_tax_regimes(), Tax Regime Comparison & Simulation Tool - Enables TORA to run "What-if" scenario, Call the tax-service compare_regimes endpoint to get Old vs New regime compariso, Pro tier feature: Simulate custom "What-if" tax scenarios.          Examples:, Simulate tax liability change if the user applies the proposed tax profile chang (+40 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (49): Expect, get_by_id(), GoldenQuestion, 50 golden questions for TORA regression testing.  Each question bundles:   - `pr, average(), _format_response_for_judge(), _judge_available(), judge_response() (+41 more)

### Community 9 - "Community 9"
Cohesion: 0.05
Nodes (29): ActiveLoansPage(), buildUrl(), getAuthHeaders(), AlertsBell(), timeAgo(), App(), AuditPage(), DeductionBar() (+21 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (49): _aggregate_categories(), note_templates.py — Typed note generators for every vault document.  Each functi, Render a single Q&A turn to be appended to the daily conversation note., Render the frontmatter header for a new daily conversation note., Render a monthly summary of transactions., Main profile dashboard — always updated every session., Generate an Obsidian Canvas JSON file linking key vault notes., Convert a title to a safe filename (lowercase, underscores). (+41 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (40): check_digital(), classify_type(), extract_day_month_no_year(), extract_row_parts(), extract_summary(), group_words_by_row(), is_noise(), is_valid_amount_token() (+32 more)

### Community 12 - "Community 12"
Cohesion: 0.12
Nodes (21): _candidate_user_ids(), _check_category_spike(), _check_large_transactions(), _check_unusual_merchant(), _emit_alert(), Nightly proactive-insights engine.  Walks every user and runs a set of determini, Compare last-30-day spend per category to prior 30 days., Flag any expense ≥ 3× the user's median, floor ₹5k. (+13 more)

### Community 13 - "Community 13"
Cohesion: 0.14
Nodes (23): access_token(), ai_client(), ai_service(), _alias_app_namespace(), auth_client(), auth_service(), _compile_jsonb_sqlite(), _discover_service_modules() (+15 more)

### Community 14 - "Community 14"
Cohesion: 0.13
Nodes (16): getEnv(), get_url(), include_object(), run_migrations_offline(), run_migrations_online(), _cache_key(), clear_cache(), fetch_context_via_mcp() (+8 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (13): call_gemini(), Execute the HTTP call to the Google Gemini API using gemini-1.5-flash-latest., call_llm(), Route the prompt to specialized local models via Ollama with reasoning fallback., call_mistral(), Execute the HTTP call to the Mistral AI API using mistral-small-latest., call_ollama(), Ollama models often wrap JSON in ```json ... ``` fences despite format=json. (+5 more)

### Community 16 - "Community 16"
Cohesion: 0.22
Nodes (18): AboutPage(), AIFeaturesPage(), AppearancePage(), ComingSoonBadge(), DataManagementPage(), FinancialSettingsPage(), HelpSupportPage(), loadPrefs() (+10 more)

### Community 17 - "Community 17"
Cohesion: 0.26
Nodes (15): apiFetch(), buildHeaders(), buildRequestError(), clearStoredAuth(), getStoredAccessToken(), getStoredRefreshToken(), isRefreshExcluded(), persistAuthResponse() (+7 more)

### Community 18 - "Community 18"
Cohesion: 0.22
Nodes (8): BaseSettings, db_password_must_be_set(), encryption_key_must_be_valid(), internal_api_key_must_be_secure(), jwt_secret_must_be_secure(), redis_connection_url(), Settings, sqlalchemy_url()

### Community 19 - "Community 19"
Cohesion: 0.2
Nodes (16): budget_recommendation(), call_finance_internal(), create_plan(), delete_plan(), get_summary(), get_transactions(), _is_retryable(), Invoked by TORA to create a new financial goal/plan. (+8 more)

### Community 20 - "Community 20"
Cohesion: 0.24
Nodes (14): _amounts_match(), _dates_within_window(), _description_for(), detect_transfer_pairs(), _is_credit_side_candidate(), _is_debit_side_candidate(), transfer_reconciler.py ========================  Detect inter-account transfer p, Scan the user's un-paired candidates and link matching pairs.      Runs a full p (+6 more)

### Community 21 - "Community 21"
Cohesion: 0.24
Nodes (14): useAddTransaction(), useAddWealth(), useCurrentUser(), useDeleteTransaction(), useDeleteWealth(), useFlatTransactions(), useProfile(), useSummary() (+6 more)

### Community 22 - "Community 22"
Cohesion: 0.27
Nodes (14): AlertBox(), computeFullTax(), CurrencyInput(), determineITRForm(), fmt(), fmtNum(), generateRecommendations(), InfoTooltip() (+6 more)

### Community 23 - "Community 23"
Cohesion: 0.34
Nodes (13): Complete-CleanupWatcher(), Format-CommandArgument(), Get-ComposeContainerIds(), Import-DotEnv(), Invoke-Checked(), Remove-LogSubscription(), Resolve-ExecutablePath(), Start-CleanupWatcher() (+5 more)

### Community 24 - "Community 24"
Cohesion: 0.17
Nodes (12): Deterministic PDF Parser, Transfer Reconciler, Gemma 4 MoE, AI Service, Auth Service, Finance Service, Frontend App, Spendsy Platform (+4 more)

### Community 25 - "Community 25"
Cohesion: 0.33
Nodes (9): audit_numbers(), audit_structured_output(), _extract_numbers_from_context(), _is_within_tolerance(), _parse_rupee_match(), Post-generation number auditor.  gemma4:e2b is a strong small model but — like a, Apply audit_numbers to every text field of a TORA structured output.      Handle, Pull every rupee figure and percentage out of the injected context     block so (+1 more)

### Community 26 - "Community 26"
Cohesion: 0.27
Nodes (9): build_training_triplets(), fetch_conversation_for_user(), fetch_feedback_rows(), main(), collect.py — Extract high-quality TORA conversations for fine-tuning.  Reads fro, # TODO: Implement full pipeline once ToraFeedback has enough production data., Fetch feedback rows from finance-service internal API.      Returns a list of di, Fetch conversation history for a specific user. (+1 more)

### Community 27 - "Community 27"
Cohesion: 0.22
Nodes (2): IntersectionObserver, ResizeObserver

### Community 28 - "Community 28"
Cohesion: 0.39
Nodes (7): calculateNewRegimeTax(), calculateOldRegimeTax(), formatCurrency(), handleBack(), handleNext(), handleReset(), handleSubmitITR()

### Community 29 - "Community 29"
Cohesion: 0.31
Nodes (5): AuthProvider(), getGatewayUrl(), useAuth(), DataProvider(), useData()

### Community 30 - "Community 30"
Cohesion: 0.54
Nodes (6): FeedbackBar(), MessageBubble(), renderInlineMarkdown(), renderMarkdown(), SectionCard(), ToolCallConfirmCard()

### Community 31 - "Community 31"
Cohesion: 0.57
Nodes (5): _add_columns_if_missing(), downgrade(), _drop_columns_if_present(), add personalization fields to userprofile and balance tracking to creditcard  Re, upgrade()

### Community 32 - "Community 32"
Cohesion: 0.6
Nodes (4): downgrade(), _json_type(), create finance base schema  Revision ID: 20260310_00 Revises: Create Date: 2, upgrade()

### Community 33 - "Community 33"
Cohesion: 0.53
Nodes (4): ConfirmationDialog(), ErrorScreen(), Loading(), Toast()

### Community 34 - "Community 34"
Cohesion: 0.6
Nodes (3): downgrade(), create auth base schema  Revision ID: 20260310_00 Revises: Create Date: 2026, upgrade()

### Community 35 - "Community 35"
Cohesion: 0.6
Nodes (3): downgrade(), add email unique index  Revision ID: 20260316_00 Revises: 20260310_00 Create, upgrade()

### Community 36 - "Community 36"
Cohesion: 0.6
Nodes (3): downgrade(), Add SecurityAlert and ApiAuditLog models  Revision ID: dfb75467a0df Revises:, upgrade()

### Community 37 - "Community 37"
Cohesion: 0.6
Nodes (3): downgrade(), phase6_goals_tora_conversation  Revision ID: 0e6386aa6927 Revises: 80f9e8b135, upgrade()

### Community 38 - "Community 38"
Cohesion: 0.6
Nodes (3): downgrade(), add_confidence_to_transaction  Revision ID: 0f8f7a931768 Revises: 20260321_01, upgrade()

### Community 39 - "Community 39"
Cohesion: 0.6
Nodes (3): downgrade(), add transaction ingestion fields  Revision ID: 20260310_01 Revises: 20260310_, upgrade()

### Community 40 - "Community 40"
Cohesion: 0.6
Nodes (3): downgrade(), add raw_description to transaction  Revision ID: 20260310_02 Revises: 2026031, upgrade()

### Community 41 - "Community 41"
Cohesion: 0.6
Nodes (3): downgrade(), add semantic dedupe index on finance_transaction  Revision ID: 20260310_03 Re, upgrade()

### Community 42 - "Community 42"
Cohesion: 0.6
Nodes (3): downgrade(), add transaction fingerprint column and index  Revision ID: 20260310_04 Revise, upgrade()

### Community 43 - "Community 43"
Cohesion: 0.6
Nodes (3): downgrade(), add_file_metadata_and_document_table  Revision ID: 20260317_05 Revises: f790b, upgrade()

### Community 44 - "Community 44"
Cohesion: 0.6
Nodes (3): downgrade(), add tier column to finance_userprofile  Revision ID: 20260321_01 Revises: 202, upgrade()

### Community 45 - "Community 45"
Cohesion: 0.6
Nodes (3): downgrade(), add extended fields to finance_taxprofile for TORA tax integration  Revision ID:, upgrade()

### Community 46 - "Community 46"
Cohesion: 0.6
Nodes (3): downgrade(), add tora_feedback table for thumbs up/down on TORA responses  Revision ID: 20260, upgrade()

### Community 47 - "Community 47"
Cohesion: 0.6
Nodes (3): downgrade(), add date_inferred to finance_transaction  Revision ID: 20260424_02 Revises: 2026, upgrade()

### Community 48 - "Community 48"
Cohesion: 0.6
Nodes (3): downgrade(), add transfer_group_id + is_transfer to finance_transaction  Revision ID: 2026042, upgrade()

### Community 49 - "Community 49"
Cohesion: 0.6
Nodes (3): downgrade(), add_loan_id_to_finance_plan  Revision ID: 2b006fc92769 Revises: 56496704cc52, upgrade()

### Community 50 - "Community 50"
Cohesion: 0.6
Nodes (3): downgrade(), add_bank_name_to_loan  Revision ID: 3be1fbcda5c7 Revises: 2b006fc92769 Creat, upgrade()

### Community 51 - "Community 51"
Cohesion: 0.6
Nodes (3): downgrade(), Add finance_plan table  Revision ID: 56496704cc52 Revises: 8a1528141186 Crea, upgrade()

### Community 52 - "Community 52"
Cohesion: 0.6
Nodes (3): downgrade(), Add phase 1 and 2 models  Revision ID: 6b4b4d46c405 Revises: 20260310_04 Cre, upgrade()

### Community 53 - "Community 53"
Cohesion: 0.6
Nodes (3): downgrade(), Add debit card model and update credit card  Revision ID: 80f9e8b135b5 Revise, upgrade()

### Community 54 - "Community 54"
Cohesion: 0.6
Nodes (3): downgrade(), Add status and reconciliation_flags to Transaction  Revision ID: 8a1528141186, upgrade()

### Community 55 - "Community 55"
Cohesion: 0.6
Nodes (3): downgrade(), Add SecurityAlert model  Revision ID: f790b3d0ee6a Revises: 0e6386aa6927 Cre, upgrade()

### Community 56 - "Community 56"
Cohesion: 0.6
Nodes (3): FeatureComparison(), ProFeatureGate(), TierBadge()

### Community 57 - "Community 57"
Cohesion: 0.67
Nodes (2): chat(), get_summary()

### Community 58 - "Community 58"
Cohesion: 0.67
Nodes (2): trigger_tora_workflow(), verify_plan_in_finance_service()

### Community 59 - "Community 59"
Cohesion: 0.67
Nodes (2): createTransaction(), fetchTransactions()

### Community 60 - "Community 60"
Cohesion: 0.67
Nodes (1): verify_internal_api_key()

### Community 61 - "Community 61"
Cohesion: 0.67
Nodes (1): AIChatPanel()

### Community 62 - "Community 62"
Cohesion: 0.67
Nodes (1): AICopilot()

### Community 63 - "Community 63"
Cohesion: 0.67
Nodes (1): FloatingAIButton()

### Community 64 - "Community 64"
Cohesion: 0.67
Nodes (1): TypingIndicator()

### Community 65 - "Community 65"
Cohesion: 0.67
Nodes (1): UnitSelector()

### Community 66 - "Community 66"
Cohesion: 0.67
Nodes (1): WelcomeWizard()

### Community 67 - "Community 67"
Cohesion: 0.67
Nodes (1): AIRecommendations()

### Community 68 - "Community 68"
Cohesion: 0.67
Nodes (1): CreatePlanModal()

### Community 69 - "Community 69"
Cohesion: 0.67
Nodes (1): PlanCard()

### Community 70 - "Community 70"
Cohesion: 0.67
Nodes (1): PlanDetailsDrawer()

### Community 71 - "Community 71"
Cohesion: 0.67
Nodes (1): PlannerHeader()

### Community 72 - "Community 72"
Cohesion: 0.67
Nodes (1): ProTierFeatures()

### Community 73 - "Community 73"
Cohesion: 0.67
Nodes (1): CustomDeletePanel()

### Community 74 - "Community 74"
Cohesion: 0.67
Nodes (1): EditTransactionModal()

### Community 75 - "Community 75"
Cohesion: 0.67
Nodes (1): FilterModal()

### Community 76 - "Community 76"
Cohesion: 0.67
Nodes (1): Navigation()

### Community 77 - "Community 77"
Cohesion: 0.67
Nodes (1): StatementHub()

### Community 78 - "Community 78"
Cohesion: 0.67
Nodes (1): OcrUnsupportedModal()

### Community 79 - "Community 79"
Cohesion: 0.67
Nodes (1): ReviewSkippedModal()

### Community 80 - "Community 80"
Cohesion: 0.67
Nodes (1): AddPage()

### Community 81 - "Community 81"
Cohesion: 0.67
Nodes (1): BankAccountsPage()

### Community 82 - "Community 82"
Cohesion: 0.67
Nodes (1): BudgetPage()

### Community 83 - "Community 83"
Cohesion: 0.67
Nodes (1): DebitCardsPage()

### Community 84 - "Community 84"
Cohesion: 0.67
Nodes (1): HistoryPage()

### Community 85 - "Community 85"
Cohesion: 0.67
Nodes (1): LoginScreen()

### Community 86 - "Community 86"
Cohesion: 0.67
Nodes (1): PlannerPage()

### Community 87 - "Community 87"
Cohesion: 0.67
Nodes (1): ProfilePage()

### Community 88 - "Community 88"
Cohesion: 0.67
Nodes (1): fillTransactionForm()

### Community 89 - "Community 89"
Cohesion: 0.67
Nodes (1): detectPdfType()

### Community 90 - "Community 90"
Cohesion: 0.67
Nodes (1): getITRFormType()

### Community 91 - "Community 91"
Cohesion: 0.67
Nodes (1): downloadCSV()

### Community 110 - "Community 110"
Cohesion: 1.0
Nodes (1): Load conversation history for user.

### Community 111 - "Community 111"
Cohesion: 1.0
Nodes (1): Save a single conversation turn.

### Community 112 - "Community 112"
Cohesion: 1.0
Nodes (1): Get conversation limit (None for unlimited).

### Community 113 - "Community 113"
Cohesion: 1.0
Nodes (1): Get the LLM model name for a user tier.

### Community 114 - "Community 114"
Cohesion: 1.0
Nodes (1): Check if tier allows autonomous actions.

### Community 115 - "Community 115"
Cohesion: 1.0
Nodes (1): Get conversation memory turns for tier (0 == unlimited).

### Community 116 - "Community 116"
Cohesion: 1.0
Nodes (1): Get available simulation features for tier.

### Community 117 - "Community 117"
Cohesion: 1.0
Nodes (1): Get available tax features for tier.

### Community 118 - "Community 118"
Cohesion: 1.0
Nodes (1): Check if tier should expose specific PII type.

### Community 119 - "Community 119"
Cohesion: 1.0
Nodes (1): Check if action requires user confirmation for tier.

## Knowledge Gaps
- **215 isolated node(s):** `Return True if the given JTI has been blacklisted (i.e. logged out).`, `Fetch finance context for a given user, with 5-minute Redis cache.`, `Middleware that adds security-hardening headers to every response.`, `Prefer X-Forwarded-For over request.client.host (fixes proxy rate-limit key).`, `Extract real IP from FastAPI Request object, proxy-safe.` (+210 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 27`** (10 nodes): `setupTests.js`, `setupTests.js`, `IntersectionObserver`, `.disconnect()`, `.observe()`, `.unobserve()`, `ResizeObserver`, `.disconnect()`, `.observe()`, `.unobserve()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (4 nodes): `gemini_client.py`, `gemini_client.py`, `chat()`, `get_summary()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (4 nodes): `verify_tora_e2e.py`, `verify_tora_e2e.py`, `trigger_tora_workflow()`, `verify_plan_in_finance_service()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (4 nodes): `transactionsAPI.test.js`, `transactionsAPI.test.js`, `createTransaction()`, `fetchTransactions()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (3 nodes): `internal_auth.py`, `internal_auth.py`, `verify_internal_api_key()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (3 nodes): `AIChatPanel()`, `AIChatPanel.jsx`, `AIChatPanel.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (3 nodes): `AICopilot()`, `AICopilot.jsx`, `AICopilot.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (3 nodes): `FloatingAIButton.jsx`, `FloatingAIButton()`, `FloatingAIButton.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (3 nodes): `TypingIndicator.jsx`, `TypingIndicator.jsx`, `TypingIndicator()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 65`** (3 nodes): `UnitSelector.jsx`, `UnitSelector.jsx`, `UnitSelector()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (3 nodes): `WelcomeWizard.jsx`, `WelcomeWizard.jsx`, `WelcomeWizard()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (3 nodes): `AIRecommendations()`, `AIRecommendations.jsx`, `AIRecommendations.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (3 nodes): `CreatePlanModal()`, `CreatePlanModal.jsx`, `CreatePlanModal.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (3 nodes): `PlanCard.jsx`, `PlanCard.jsx`, `PlanCard()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (3 nodes): `PlanDetailsDrawer.jsx`, `PlanDetailsDrawer.jsx`, `PlanDetailsDrawer()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (3 nodes): `PlannerHeader.jsx`, `PlannerHeader.jsx`, `PlannerHeader()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (3 nodes): `ProTierFeatures.jsx`, `ProTierFeatures.jsx`, `ProTierFeatures()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (3 nodes): `CustomDeletePanel()`, `CustomDeletePanel.jsx`, `CustomDeletePanel.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (3 nodes): `EditTransactionModal.jsx`, `EditTransactionModal()`, `EditTransactionModal.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (3 nodes): `FilterModal.jsx`, `FilterModal()`, `FilterModal.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (3 nodes): `Navigation.jsx`, `Navigation.jsx`, `Navigation()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (3 nodes): `StatementHub.jsx`, `StatementHub.jsx`, `StatementHub()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (3 nodes): `OcrUnsupportedModal.jsx`, `OcrUnsupportedModal.jsx`, `OcrUnsupportedModal()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 79`** (3 nodes): `ReviewSkippedModal.jsx`, `ReviewSkippedModal.jsx`, `ReviewSkippedModal()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 80`** (3 nodes): `AddPage()`, `AddPage.jsx`, `AddPage.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 81`** (3 nodes): `BankAccountsPage()`, `BankAccountsPage.jsx`, `BankAccountsPage.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 82`** (3 nodes): `BudgetPage()`, `BudgetPage.jsx`, `BudgetPage.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 83`** (3 nodes): `DebitCardsPage.jsx`, `DebitCardsPage()`, `DebitCardsPage.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 84`** (3 nodes): `HistoryPage.jsx`, `HistoryPage.jsx`, `HistoryPage()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 85`** (3 nodes): `LoginScreen.jsx`, `LoginScreen.jsx`, `LoginScreen()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 86`** (3 nodes): `PlannerPage.jsx`, `PlannerPage.jsx`, `PlannerPage()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 87`** (3 nodes): `ProfilePage.jsx`, `ProfilePage.jsx`, `ProfilePage()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 88`** (3 nodes): `fillTransactionForm()`, `AddTransaction.test.jsx`, `AddTransaction.test.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 89`** (3 nodes): `detectPdfType.js`, `detectPdfType()`, `detectPdfType.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 90`** (3 nodes): `taxService.js`, `taxService.js`, `getITRFormType()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 91`** (3 nodes): `exportUtils.js`, `downloadCSV()`, `exportUtils.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 110`** (1 nodes): `Load conversation history for user.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 111`** (1 nodes): `Save a single conversation turn.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 112`** (1 nodes): `Get conversation limit (None for unlimited).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 113`** (1 nodes): `Get the LLM model name for a user tier.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 114`** (1 nodes): `Check if tier allows autonomous actions.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 115`** (1 nodes): `Get conversation memory turns for tier (0 == unlimited).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 116`** (1 nodes): `Get available simulation features for tier.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 117`** (1 nodes): `Get available tax features for tier.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 118`** (1 nodes): `Check if tier should expose specific PII type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 119`** (1 nodes): `Check if action requires user confirmation for tier.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FetchStrategy` connect `TORA Plugin Registry & Fetchers` to `Database Models & Schemas`, `Community 4`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `TieringConfig` connect `TORA Financial Intelligence` to `Community 6`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Why does `handle_user_question()` connect `TORA Financial Intelligence` to `Community 8`, `Community 10`, `Community 4`, `Community 6`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 149 inferred relationships involving `TieringConfig` (e.g. with `QuestionRequest` and `FeedbackRequest`) actually correct?**
  _`TieringConfig` has 149 INFERRED edges - model-reasoned connections that need verification._
- **Are the 112 inferred relationships involving `str` (e.g. with `sqlalchemy_exception_handler()` and `_run_gemini()`) actually correct?**
  _`str` has 112 INFERRED edges - model-reasoned connections that need verification._
- **Are the 110 inferred relationships involving `TaxInput` (e.g. with `TaxComputeRequest` and `ITRFormRequest`) actually correct?**
  _`TaxInput` has 110 INFERRED edges - model-reasoned connections that need verification._
- **Are the 71 inferred relationships involving `Transaction` (e.g. with `Base` and `BulkDeletePayload`) actually correct?**
  _`Transaction` has 71 INFERRED edges - model-reasoned connections that need verification._