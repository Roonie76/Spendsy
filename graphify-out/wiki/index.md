# Spendsy Knowledge Graph - Wiki Index

**2110 nodes · 5519 edges · 166 communities**

## God Nodes (most connected)
- `tiering_tieringconfig` — 152 edges
- `str` — 117 edges
- `tax_engine_taxinput` — 114 edges
- `models_transaction` — 74 edges
- `security_usercontext` — 67 edges
- `response_success_response` — 66 edges
- `memory_freetierstore` — 58 edges
- `models_userprofile` — 57 edges
- `memory_protierstore` — 55 edges
- `memory_enterprisetierstore` — 55 edges
- `basemodel` — 54 edges
- `backend_finance_service_app_api_routes_finance_py` — 53 edges
- `d_projects_spendsy_backend_finance_service_app_api_routes_finance_py` — 53 edges
- `models_loan` — 52 edges
- `models_itrdata` — 49 edges
- `database_base` — 44 edges
- `models_creditcard` — 44 edges
- `models_wealthitem` — 43 edges
- `models_taxprofile` — 43 edges
- `backend_finance_service_app_schemas_py` — 42 edges

## Communities (by size)
- **Community 0** (336 nodes): memory.py, ConversationStore, ABC, load_history(), save_turn()...
- **Community 1** (188 nodes): BaseModel, UserContext, Base, ApiAuditLog, SecurityAlert...
- **Community 2** (165 nodes): tax_engine.py, TaxInput, TaxBreakdown, RegimeComparison, _slab_tax()...
- **Community 3** (162 nodes): __init__.py, TORA eval harness — golden-question regression tests.  Run with:     cd backend, entity_resolver.py, _tokenize(), _build_entity_to_plugin_map()...
- **Community 4** (152 nodes): refresh(), str, routes_finance.py, _safe_category(), _safe_type()...
- **Community 5** (112 nodes): HealthResponse, redis.py, get_redis(), append_message(), load_history()...
- **Community 6** (73 nodes): main.py, sqlalchemy_exception_handler(), schemas.py, ChatRequest, ChatResponse...
- **Community 7** (66 nodes): adjust_plan.py, adjust_plan(), Send a POST request to finance-service to adjust an existing financial plan., compare_tax_regimes.py, call_tax_engine_compare()...
- **Community 8** (60 nodes): golden_questions.py, Expect, TypedDict, GoldenQuestion, get_by_id()...
- **Community 9** (57 nodes): App.jsx, App(), TransactionItem.jsx, TransactionItem(), WealthItem.jsx...
- **Community 10** (55 nodes): note_templates.py, render_profile_note(), render_balances_note(), render_goal_note(), render_plan_note()...
- **Community 11** (47 nodes): digital_deterministic_parser.py, Transaction, .to_dict(), ParseResult, .to_dict()...
- **Community 12** (36 nodes): proactive_insights.py, _candidate_user_ids(), _recent_alert_signatures(), _emit_alert(), _check_category_spike()...
- **Community 13** (27 nodes): conftest.py, _restore_env_file(), _compile_jsonb_sqlite(), from_url(), _QueueStub...
- **Community 14** (26 nodes): env.py, include_object(), get_url(), run_migrations_offline(), run_migrations_online()...
- **Community 15** (23 nodes): RuntimeError, gemini_client.py, call_gemini(), Execute the HTTP call to the Google Gemini API using gemini-1.5-flash-latest., llm_router.py...
- **Community 16** (20 nodes): SettingsPage.jsx, loadPrefs(), savePref(), SettingRow(), SettingSection()...
- **Community 17** (19 nodes): api.js, wait(), storage(), getStoredAccessToken(), getStoredRefreshToken()...
- **Community 18** (18 nodes): config.py, Settings, BaseSettings, redis_connection_url(), config.py...
- **Community 19** (18 nodes): tools.py, _is_retryable(), call_finance_internal(), get_summary(), get_transactions()...
- **Community 20** (17 nodes): transfer_reconciler.py, ReconcileResult, .__post_init__(), _description_for(), _is_debit_side_candidate()...
- **Community 21** (16 nodes): useFinance.js, useCurrentUser(), useSummary(), useTransactions(), useFlatTransactions()...
- **Community 22** (16 nodes): ITRPage.jsx, fmt(), fmtNum(), pct(), InfoTooltip()...
- **Community 23** (15 nodes): run-local.ps1, Write-Step(), Invoke-Checked(), Resolve-ExecutablePath(), Start-CleanupWatcher()...
- **Community 24** (12 nodes): Spendsy Platform, TORA Intelligence Engine, Auth Service, Finance Service, AI Service...
- **Community 25** (11 nodes): number_auditor.py, _parse_rupee_match(), _extract_numbers_from_context(), _is_within_tolerance(), audit_numbers()...
- **Community 26** (11 nodes): collect.py, fetch_feedback_rows(), fetch_conversation_for_user(), build_training_triplets(), main()...
- **Community 27** (10 nodes): setupTests.js, ResizeObserver, .observe(), .unobserve(), .disconnect()...
- **Community 28** (9 nodes): ITRCalculator.tsx, calculateOldRegimeTax(), calculateNewRegimeTax(), formatCurrency(), handleNext()...
- **Community 29** (9 nodes): AuthContext.jsx, getGatewayUrl(), useAuth(), AuthProvider(), DataContext.jsx...

## Files → Nodes

### backend/ai-service
- `backend/ai-service/list_models.py` (2 nodes)

### backend/ai-service/app
- `backend/ai-service/app/__init__.py` (2 nodes)
- `backend/ai-service/app/main.py` (2 nodes)
- `backend/ai-service/app/schemas.py` (6 nodes): ChatRequest, ChatResponse, AIRequest, AIResponse

### backend/ai-service/app/api
- `backend/ai-service/app/api/__init__.py` (2 nodes)
- `backend/ai-service/app/api/routes_ai.py` (7 nodes): health(), _run_gemini(), insights(), health_score(), forecast()
- `backend/ai-service/app/api/routes_chat.py` (4 nodes): _build_prompt(), chat()

### backend/ai-service/app/core
- `backend/ai-service/app/core/__init__.py` (2 nodes)
- `backend/ai-service/app/core/config.py` (2 nodes)
- `backend/ai-service/app/core/redis.py` (6 nodes): append_message(), load_history(), clear_history(), Return True if the given JTI has been blacklisted (i.e. logged out).
- `backend/ai-service/app/core/security.py` (2 nodes)

### backend/ai-service/app/services
- `backend/ai-service/app/services/__init__.py` (2 nodes)
- `backend/ai-service/app/services/finance_client.py` (4 nodes): fetch_finance_context(), Fetch finance context for a given user, with 5-minute Redis cache.
- `backend/ai-service/app/services/gemini_client.py` (5 nodes): GeminiError, build_prompt(), generate_text()

### backend/auth-service/alembic
- `backend/auth-service/alembic/env.py` (2 nodes)

### backend/auth-service/alembic/versions
- `backend/auth-service/alembic/versions/20260310_00_create_auth_base.py` (5 nodes): upgrade(), downgrade(), create auth base schema  Revision ID: 20260310_00 Revises: Create Date: 2026
- `backend/auth-service/alembic/versions/20260316_00_add_email_unique.py` (5 nodes): upgrade(), downgrade(), add email unique index  Revision ID: 20260316_00 Revises: 20260310_00 Create
- `backend/auth-service/alembic/versions/dfb75467a0df_add_securityalert_and_apiauditlog_models.py` (5 nodes): upgrade(), downgrade(), Add SecurityAlert and ApiAuditLog models  Revision ID: dfb75467a0df Revises:

### backend/auth-service/app
- `backend/auth-service/app/__init__.py` (2 nodes)
- `backend/auth-service/app/main.py` (2 nodes)
- `backend/auth-service/app/models.py` (5 nodes): User, RefreshToken, Mirrors Django's auth_user table to preserve existing data.
- `backend/auth-service/app/schemas.py` (10 nodes): UserCreate, validate_password_strength(), UserLogin, TokenPair, UserOut

### backend/auth-service/app/api
- `backend/auth-service/app/api/__init__.py` (2 nodes)
- `backend/auth-service/app/api/routes_auth.py` (15 nodes): _normalize_username(), _generate_alert(), _record_audit(), _normalize_email(), _get_registration_conflict_detail()
- `backend/auth-service/app/api/routes_health.py` (3 nodes): health()

### backend/auth-service/app/core
- `backend/auth-service/app/core/__init__.py` (2 nodes)
- `backend/auth-service/app/core/config.py` (2 nodes)
- `backend/auth-service/app/core/database.py` (2 nodes)
- `backend/auth-service/app/core/middleware.py` (3 nodes): Middleware that adds security-hardening headers to every response.
- `backend/auth-service/app/core/redis.py` (15 nodes): _get_client_identity(), record_audit_event(), blacklist_token(), increment_failed_login(), is_account_locked()
- `backend/auth-service/app/core/security.py` (10 nodes): hash_password(), verify_password(), create_access_token(), create_refresh_token(), _extract_token()

### backend/auth-service/tests
- `backend/auth-service/tests/routes_auth_regression.py` (11 nodes): stub_auth_dependencies(), db_session(), make_request(), create_user(), test_register_rejects_username_duplicates_after_trimming()

### backend/finance-service/alembic
- `backend/finance-service/alembic/env.py` (6 nodes): include_object(), get_url(), run_migrations_offline(), run_migrations_online()

### backend/finance-service/alembic/versions
- `backend/finance-service/alembic/versions/0e6386aa6927_phase6_goals_tora_conversation.py` (5 nodes): upgrade(), downgrade(), phase6_goals_tora_conversation  Revision ID: 0e6386aa6927 Revises: 80f9e8b135
- `backend/finance-service/alembic/versions/0f8f7a931768_add_confidence_to_transaction.py` (5 nodes): upgrade(), downgrade(), add_confidence_to_transaction  Revision ID: 0f8f7a931768 Revises: 20260321_01
- `backend/finance-service/alembic/versions/20260310_00_create_finance_base.py` (6 nodes): _json_type(), upgrade(), downgrade(), create finance base schema  Revision ID: 20260310_00 Revises: Create Date: 2
- `backend/finance-service/alembic/versions/20260310_01_add_transaction_ingestion_fields.py` (5 nodes): upgrade(), downgrade(), add transaction ingestion fields  Revision ID: 20260310_01 Revises: 20260310_
- `backend/finance-service/alembic/versions/20260310_02_add_transaction_raw_description.py` (5 nodes): upgrade(), downgrade(), add raw_description to transaction  Revision ID: 20260310_02 Revises: 2026031
- `backend/finance-service/alembic/versions/20260310_03_add_semantic_dedupe_index.py` (5 nodes): upgrade(), downgrade(), add semantic dedupe index on finance_transaction  Revision ID: 20260310_03 Re
- `backend/finance-service/alembic/versions/20260310_04_add_transaction_fingerprint.py` (5 nodes): upgrade(), downgrade(), add transaction fingerprint column and index  Revision ID: 20260310_04 Revise
- `backend/finance-service/alembic/versions/20260317_05_add_file_metadata_and_document_table.py` (5 nodes): upgrade(), downgrade(), add_file_metadata_and_document_table  Revision ID: 20260317_05 Revises: f790b
- `backend/finance-service/alembic/versions/20260321_01_add_userprofile_tier.py` (5 nodes): upgrade(), downgrade(), add tier column to finance_userprofile  Revision ID: 20260321_01 Revises: 202
- `backend/finance-service/alembic/versions/20260413_01_add_tax_profile_extended.py` (5 nodes): upgrade(), downgrade(), add extended fields to finance_taxprofile for TORA tax integration  Revision ID:
- `backend/finance-service/alembic/versions/20260423_01_add_personalization_and_card_balance.py` (7 nodes): _add_columns_if_missing(), _drop_columns_if_present(), upgrade(), downgrade(), add personalization fields to userprofile and balance tracking to creditcard  Re
- `backend/finance-service/alembic/versions/20260424_01_add_tora_feedback.py` (5 nodes): upgrade(), downgrade(), add tora_feedback table for thumbs up/down on TORA responses  Revision ID: 20260
- `backend/finance-service/alembic/versions/20260424_02_add_date_inferred_to_transaction.py` (5 nodes): upgrade(), downgrade(), add date_inferred to finance_transaction  Revision ID: 20260424_02 Revises: 2026
- `backend/finance-service/alembic/versions/20260424_03_add_transfer_fields.py` (5 nodes): upgrade(), downgrade(), add transfer_group_id + is_transfer to finance_transaction  Revision ID: 2026042
- `backend/finance-service/alembic/versions/2b006fc92769_add_loan_id_to_finance_plan.py` (5 nodes): upgrade(), downgrade(), add_loan_id_to_finance_plan  Revision ID: 2b006fc92769 Revises: 56496704cc52
- `backend/finance-service/alembic/versions/3be1fbcda5c7_add_bank_name_to_loan.py` (5 nodes): upgrade(), downgrade(), add_bank_name_to_loan  Revision ID: 3be1fbcda5c7 Revises: 2b006fc92769 Creat
- `backend/finance-service/alembic/versions/56496704cc52_add_finance_plan_table.py` (5 nodes): upgrade(), downgrade(), Add finance_plan table  Revision ID: 56496704cc52 Revises: 8a1528141186 Crea
- `backend/finance-service/alembic/versions/6b4b4d46c405_add_phase_1_and_2_models.py` (5 nodes): upgrade(), downgrade(), Add phase 1 and 2 models  Revision ID: 6b4b4d46c405 Revises: 20260310_04 Cre
- `backend/finance-service/alembic/versions/80f9e8b135b5_add_debit_card_model_and_update_credit_.py` (5 nodes): upgrade(), downgrade(), Add debit card model and update credit card  Revision ID: 80f9e8b135b5 Revise
- `backend/finance-service/alembic/versions/8a1528141186_add_status_and_reconciliation_flags_to_.py` (5 nodes): upgrade(), downgrade(), Add status and reconciliation_flags to Transaction  Revision ID: 8a1528141186
- `backend/finance-service/alembic/versions/f790b3d0ee6a_add_securityalert_model.py` (5 nodes): upgrade(), downgrade(), Add SecurityAlert model  Revision ID: f790b3d0ee6a Revises: 0e6386aa6927 Cre

### backend/finance-service/app
- `backend/finance-service/app/__init__.py` (2 nodes)
- `backend/finance-service/app/main.py` (7 nodes): sqlalchemy_exception_handler(), lifespan(), validation_exception_handler(), Return structured JSON for Pydantic validation failures., Catch unhandled SQLAlchemy failures so DB issues surface as structured JSON
- `backend/finance-service/app/models.py` (32 nodes): ApiAuditLog, SecurityAlert, UserProfile, Transaction, WealthItem
- `backend/finance-service/app/schemas.py` (43 nodes): HealthResponse, TransactionCategory, ErrorResponse, UserProfilePayload, TransactionPayload
- `backend/finance-service/app/tasks.py` (2 nodes)

### backend/finance-service/app/api
- `backend/finance-service/app/api/__init__.py` (2 nodes)
- `backend/finance-service/app/api/routes_finance.py` (65 nodes): _safe_category(), _safe_type(), _safe_source(), _safe_confidence(), _safe_date()
- `backend/finance-service/app/api/routes_goals.py` (13 nodes): _goal_to_dict(), list_goals(), create_goal(), update_goal(), delete_goal()
- `backend/finance-service/app/api/routes_internal.py` (44 nodes): trigger_reconciliation(), list_transactions(), get_summary(), finance_context(), _ToraMsgPayload
- `backend/finance-service/app/api/routes_product.py` (12 nodes): get_dashboard(), get_financial_health(), get_recommendations(), get_alerts(), mark_alert_as_read()
- `backend/finance-service/app/api/routes_tax.py` (15 nodes): TaxComputeRequest, ITRFormRequest, compute_tax_endpoint(), compute_from_saved_data(), get_itr_form()

### backend/finance-service/app/core
- `backend/finance-service/app/core/__init__.py` (2 nodes)
- `backend/finance-service/app/core/audit.py` (6 nodes): record_alert(), record_audit(), Standardized security alerting for finance-service., Standardized audit logging for finance-service.     Persists to finance_apiaudi
- `backend/finance-service/app/core/config.py` (8 nodes): redis_connection_url(), db_password_must_be_set(), jwt_secret_must_be_secure(), sqlalchemy_url(), internal_api_key_must_be_secure()
- `backend/finance-service/app/core/cryptography.py` (6 nodes): _get_key_bytes(), get_aesgcm(), encrypt_string(), decrypt_string()
- `backend/finance-service/app/core/database.py` (6 nodes): Base, get_db(), check_database_connection(), Lightweight connectivity probe used by health/readiness endpoints.     Keeps fa
- `backend/finance-service/app/core/internal_auth.py` (3 nodes): verify_internal_api_key()
- `backend/finance-service/app/core/middleware.py` (8 nodes): SecurityHeadersMiddleware, .dispatch(), RequestLoggingMiddleware, .dispatch(), Middleware that:     1. Ensures every request has an X-Request-ID (generates on
- `backend/finance-service/app/core/product_tiers.py` (9 nodes): UserTier, TierConfig, TierEnforcer, get_tier(), check_upload_limit()
- `backend/finance-service/app/core/redis.py` (14 nodes): get_redis(), is_token_blacklisted(), get_identity_from_request(), is_rate_limited(), enqueue_task()
- `backend/finance-service/app/core/security.py` (9 nodes): UserContext, decode_token(), get_current_user(), .__init__(), RequireRole

### backend/finance-service/app/services
- `backend/finance-service/app/services/__init__.py` (2 nodes)
- `backend/finance-service/app/services/product_engines.py` (14 nodes): HealthEngine, compute_score(), InsightEngine, generate_monthly_insight(), ToraEngine
- `backend/finance-service/app/services/scheduler.py` (17 nodes): _is_enabled(), _register_jobs(), _safely(), start_scheduler(), stop_scheduler()
- `backend/finance-service/app/services/tax_engine.py` (31 nodes): TaxInput, TaxBreakdown, RegimeComparison, _slab_tax(), _compute_surcharge()
- `backend/finance-service/app/services/transfer_reconciler.py` (17 nodes): ReconcileResult, .__post_init__(), _description_for(), _is_debit_side_candidate(), _is_credit_side_candidate()

### backend/finance-service/app/services/jobs
- `backend/finance-service/app/services/jobs/__init__.py` (2 nodes)
- `backend/finance-service/app/services/jobs/net_worth_snapshot.py` (9 nodes): _candidate_user_ids(), _snapshot_for_user(), run_daily_net_worth_snapshot(), Daily net-worth snapshot job.  For every user with any finance data, write exact, Every user with at least one finance row worth snapshotting.
- `backend/finance-service/app/services/jobs/proactive_insights.py` (15 nodes): _candidate_user_ids(), _recent_alert_signatures(), _emit_alert(), _check_category_spike(), _check_large_transactions()

### backend/finance-service/app/services/parser
- `backend/finance-service/app/services/parser/__init__.py` (2 nodes)
- `backend/finance-service/app/services/parser/digital_deterministic_parser.py` (34 nodes): Transaction, .to_dict(), ParseResult, .to_dict(), extract_day_month_no_year()

### backend/finance-service/app/utils
- `backend/finance-service/app/utils/__init__.py` (2 nodes)
- `backend/finance-service/app/utils/error_codes.py` (3 nodes): ErrorCode
- `backend/finance-service/app/utils/files.py` (6 nodes): sanitize_filename(), validate_file_security(), Sanitize filename by removing potentially dangerous characters.     Simplified, Verify file size, extension, and MIME type.     Raises HTTPException if insecur
- `backend/finance-service/app/utils/response.py` (5 nodes): request_id_from_request(), success_response(), error_response()

### backend/finance-service/app/utils/pdf
- `backend/finance-service/app/utils/pdf/__init__.py` (2 nodes)

### backend/finance-service/tests
- `backend/finance-service/tests/test_tax_engine.py` (63 nodes): .test_zero_income(), .test_below_basic_exemption_new(), .test_at_basic_exemption_new(), .test_simple_slab_new(), .test_full_slabs_new()

### backend/spendsy-ai
- `backend/spendsy-ai/config.py` (2 nodes)
- `backend/spendsy-ai/main.py` (11 nodes): health_check(), QuestionRequest, FeedbackRequest, fetch_user_tier(), handle_ask_tora()
- `backend/spendsy-ai/mcp_connector.py` (15 nodes): _cache_key(), invalidate_user_cache(), clear_cache(), MCPConnector, .__init__()
- `backend/spendsy-ai/memory.py` (53 nodes): ConversationStore, load_history(), save_turn(), get_memory_limit(), FreeTierStore
- `backend/spendsy-ai/tiering.py` (21 nodes): ToraUserTier, TieringConfig, get_model_for_tier(), can_act_autonomously(), get_memory_limit()
- `backend/spendsy-ai/tools.py` (18 nodes): _is_retryable(), call_finance_internal(), get_summary(), get_transactions(), spending_insights()

### backend/spendsy-ai/agents
- `backend/spendsy-ai/agents/gemini_client.py` (4 nodes): call_gemini(), Execute the HTTP call to the Google Gemini API using gemini-1.5-flash-latest.
- `backend/spendsy-ai/agents/llm_router.py` (4 nodes): call_llm(), Route the prompt to specialized local models via Ollama with reasoning fallback.
- `backend/spendsy-ai/agents/mistral_client.py` (4 nodes): call_mistral(), Execute the HTTP call to the Mistral AI API using mistral-small-latest.
- `backend/spendsy-ai/agents/ollama_client.py` (6 nodes): _strip_code_fences(), call_ollama(), Ollama models often wrap JSON in ```json ... ``` fences despite format=json., Execute a chat completion request to the local Ollama API.      Args:         mo
- `backend/spendsy-ai/agents/tora_agent.py` (32 nodes): fetch_financial_summary(), run_financial_simulations(), sanitize_financial_data(), build_ai_context(), _summarize_trends()
- `backend/spendsy-ai/agents/tora_personality.py` (18 nodes): detect_intent(), is_finance_related(), get_greeting_response(), get_small_talk_response(), get_capability_response()

### backend/spendsy-ai/agents/tools
- `backend/spendsy-ai/agents/tools/adjust_plan.py` (4 nodes): adjust_plan(), Send a POST request to finance-service to adjust an existing financial plan.
- `backend/spendsy-ai/agents/tools/compare_tax_regimes.py` (11 nodes): call_tax_engine_compare(), simulate_tax_profile_change(), compare_tax_regimes(), simulate_tax_whatif(), Tax Regime Comparison & Simulation Tool - Enables TORA to run "What-if" scenario
- `backend/spendsy-ai/agents/tools/create_loan_repayment_plan.py` (4 nodes): create_loan_repayment_plan(), Send a POST request to finance-service to create a new financial plan specifical
- `backend/spendsy-ai/agents/tools/create_plan.py` (4 nodes): create_plan(), Send a POST request to finance-service to create a new financial plan.     Hand
- `backend/spendsy-ai/agents/tools/simulate_loan_repayment.py` (13 nodes): calculate_loan_amortization(), simulate_extra_payment_impact(), simulate_multi_loan_payoff_strategy(), simulate_loan_consolidation(), simulate_loan_repayment()
- `backend/spendsy-ai/agents/tools/simulate_tax_efficient_investment.py` (11 nodes): calculate_investment_allocation(), calculate_tax_impact_of_investments(), simulate_sip_growth_with_tax(), simulate_tax_efficient_investment_plan(), Investment & Tax Optimization Simulation Tool - Pro tier feature Enables TORA t
- `backend/spendsy-ai/agents/tools/sync_credit_card_payments.py` (4 nodes): sync_credit_card_payments(), Sync tool wrapper for TORA.     This calls the MCP tool asynchronously.
- `backend/spendsy-ai/agents/tools/tool_registry.py` (4 nodes): get_tool_registry(), Returns a dictionary mapping tool names to functions.
- `backend/spendsy-ai/agents/tools/update_tax_profile.py` (11 nodes): get_current_tax_profile(), suggest_tax_profile_updates(), apply_tax_profile_update(), update_tax_profile(), Tax Profile Update Tool - Enables TORA to suggest and apply tax profile changes.

### backend/spendsy-ai/agents/tora
- `backend/spendsy-ai/agents/tora/__init__.py` (2 nodes)
- `backend/spendsy-ai/agents/tora/entity_resolver.py` (18 nodes): _tokenize(), _build_entity_to_plugin_map(), _find_consecutive_match(), _score_match(), _collect_stage1()
- `backend/spendsy-ai/agents/tora/entity_synonyms.py` (5 nodes): build_reverse_map(), Hand-curated synonym map: user phrase → canonical entity key.  Includes Hindi/Hi, Build a synonym → canonical lookup.      Lowercases everything. If a phrase appe
- `backend/spendsy-ai/agents/tora/fetch_registry.py` (20 nodes): FetchStrategy, confidence_label(), FetchResult, .merge_from(), FetchPlugin
- `backend/spendsy-ai/agents/tora/market_context_builder.py` (15 nodes): build_market_context_block(), _render_section(), _render_fact_line(), _render_value(), _is_pct_key()
- `backend/spendsy-ai/agents/tora/number_auditor.py` (11 nodes): _parse_rupee_match(), _extract_numbers_from_context(), _is_within_tolerance(), audit_numbers(), audit_structured_output()
- `backend/spendsy-ai/agents/tora/thinking_gate.py` (5 nodes): should_enable_thinking(), Thinking-mode gating.  Gemma 4's thinking mode trades latency (roughly 3x slower, Return True when the query warrants thinking mode.      Called once per query by
- `backend/spendsy-ai/agents/tora/universal_fetch_engine.py` (11 nodes): _fire_one_plugin(), resolve_and_fetch(), _safe_fallback(), summarize_fetch_outcome(), Universal Intelligence Engine.  Takes a user message, resolves it to plugin matc

### backend/spendsy-ai/agents/tora/live_fetchers
- `backend/spendsy-ai/agents/tora/live_fetchers/__init__.py` (2 nodes)
- `backend/spendsy-ai/agents/tora/live_fetchers/forex_fetcher.py` (9 nodes): _fetch_exchangerate_json(), _usd_rate_to_inr(), _build_live_fact(), fetch_travel_live(), Live forex fetcher (used by travel plugin; also useful for education/wedding).
- `backend/spendsy-ai/agents/tora/live_fetchers/gold_fetcher.py` (8 nodes): _parse_int(), _fetch_ibja_html(), _build_live_fact(), fetch_gold_live(), Live gold/silver fetcher.  Strategy: scrape IBJA (India Bullion and Jewellers As
- `backend/spendsy-ai/agents/tora/live_fetchers/investments_fetcher.py` (9 nodes): _fetch_amfi_text(), _parse_nav_row(), _build_live_fact(), fetch_investments_live(), Live investments fetcher.  Strategy: AMFI publishes every mutual-fund NAV in Ind

### backend/spendsy-ai/agents/tora/plugins
- `backend/spendsy-ai/agents/tora/plugins/__init__.py` (4 nodes): register_all_plugins(), Register every plugin module's PLUGIN object. Idempotent.
- `backend/spendsy-ai/agents/tora/plugins/_base.py` (9 nodes): _plugin_strategy(), build_fallback_from_yaml(), stub_fetcher(), Shared helpers for plugin modules.  `build_fallback_from_yaml` constructs a Fetc, Lookup this plugin's declared strategy, defaulting to curated-static.      Calle
- `backend/spendsy-ai/agents/tora/plugins/appliances.py` (3 nodes): Appliances plugin: AC, fridge, washing machine, TV, geyser, microwave.
- `backend/spendsy-ai/agents/tora/plugins/education.py` (3 nodes): Education plugin: college, MBA, BTech, study abroad, coaching, certifications.
- `backend/spendsy-ai/agents/tora/plugins/electronics.py` (3 nodes): Electronics plugin: laptops, phones, tablets, cameras, monitors.
- `backend/spendsy-ai/agents/tora/plugins/furniture.py` (3 nodes): Furniture & home improvement plugin: furniture, renovation, kitchen, bathroom.
- `backend/spendsy-ai/agents/tora/plugins/gold.py` (3 nodes): Gold & jewellery plugin: gold, silver, diamond, platinum, SGB, ETFs.
- `backend/spendsy-ai/agents/tora/plugins/healthcare.py` (3 nodes): Healthcare plugin: insurance, surgery, dental, IVF, gym, medicine.
- `backend/spendsy-ai/agents/tora/plugins/investments.py` (3 nodes): Investments plugin: stocks, MF, FD, SIP, NPS, bonds, PPF, ELSS.
- `backend/spendsy-ai/agents/tora/plugins/lifestyle.py` (3 nodes): Lifestyle & recurring plugin: OTT, music subs, gym, dining, clubs, SaaS.
- `backend/spendsy-ai/agents/tora/plugins/mobility.py` (3 nodes): Mobility plugin: cars, bikes, EVs, commercial vehicles.
- `backend/spendsy-ai/agents/tora/plugins/real_estate.py` (3 nodes): Real estate plugin: buy, rent, plot, commercial.
- `backend/spendsy-ai/agents/tora/plugins/travel.py` (3 nodes): Travel plugin: flights, hotels, international trips, visa, insurance.
- `backend/spendsy-ai/agents/tora/plugins/wedding.py` (3 nodes): Wedding & events plugin: wedding, reception, anniversary, birthday, events.

### backend/spendsy-ai/agents/tora/static_fallbacks
- `backend/spendsy-ai/agents/tora/static_fallbacks/__init__.py` (6 nodes): _load_all(), get_fallback(), Populate FALLBACK_DATA from every *.yaml file in this directory., Return the raw fallback blob for a plugin, or an empty dict.      Returning {} (

### backend/spendsy-ai/fine_tuning
- `backend/spendsy-ai/fine_tuning/collect.py` (11 nodes): fetch_feedback_rows(), fetch_conversation_for_user(), build_training_triplets(), main(), collect.py — Extract high-quality TORA conversations for fine-tuning.  Reads fro
- `backend/spendsy-ai/fine_tuning/export.py` (12 nodes): to_gemma(), to_llama(), to_openai(), estimate_tokens(), main()

### backend/spendsy-ai/vault
- `backend/spendsy-ai/vault/__init__.py` (2 nodes)
- `backend/spendsy-ai/vault/note_templates.py` (21 nodes): render_profile_note(), render_balances_note(), render_goal_note(), render_plan_note(), render_loan_note()
- `backend/spendsy-ai/vault/vault_sync.py` (11 nodes): _safe_filename(), sync_vault_after_session(), read_vault_context(), _strip_frontmatter(), vault_sync.py — Post-session vault synchronization.  Called at the end of every
- `backend/spendsy-ai/vault/vault_writer.py` (23 nodes): _vault_root(), ensure_vault(), _write_note(), _read_note(), _append_to_note()

### backend/spendsy-mcp
- `backend/spendsy-mcp/config.py` (3 nodes): Settings
- `backend/spendsy-mcp/gemini_client.py` (4 nodes): get_summary(), chat()
- `backend/spendsy-mcp/server.py` (34 nodes): _is_retryable(), call_finance_internal(), get_transactions(), get_summary(), monthly_spend()

### backend/tests
- `backend/tests/test_integration_tora_tiering.py` (77 nodes): TestFreeTierEndToEnd, .test_free_tier_question_flow(), .test_free_tier_simulation_restricted(), .test_free_tier_data_sanitization(), .test_free_tier_requires_confirmation()
- `backend/tests/test_memory_and_authorization.py` (77 nodes): TestMemoryStoreSelection, .test_free_tier_store_selection(), .test_pro_tier_store_selection(), .test_enterprise_tier_store_selection(), .test_invalid_tier_defaults_to_free()
- `backend/tests/test_ollama_integration.py` (4 nodes): test_phi_math(), test_qwen_tools()
- `backend/tests/test_proactive_insights.py` (22 nodes): _remap_jsonb_for_sqlite(), db_session(), _tx(), TestCategorySpike, .test_fires_on_30pct_increase()
- `backend/tests/test_tax_engine.py` (71 nodes): TestSlabTax, TestSurcharge, .test_no_surcharge_below_50L(), TestCapitalGains, TestRegimeComparison
- `backend/tests/test_tora_tiering.py` (67 nodes): TestTieringConfig, .test_tier_enum_values(), .test_model_selection_free_tier(), .test_model_selection_pro_tier(), .test_model_selection_enterprise_tier()
- `backend/tests/verify_tora_e2e.py` (4 nodes): trigger_tora_workflow(), verify_plan_in_finance_service()

### backend/tests/tora_eval
- `backend/tests/tora_eval/__init__.py` (3 nodes): TORA eval harness — golden-question regression tests.  Run with:     cd backend
- `backend/tests/tora_eval/golden_questions.py` (7 nodes): Expect, GoldenQuestion, count(), get_by_id(), 50 golden questions for TORA regression testing.  Each question bundles:   - `pr
- `backend/tests/tora_eval/judge.py` (14 nodes): JudgeResult, average(), out_of_5(), normalized(), _judge_available()
- `backend/tests/tora_eval/runner.py` (12 nodes): stubbed_agent(), _run_one(), _select(), run_all(), _build_report()
- `backend/tests/tora_eval/scorer.py` (22 nodes): CheckResult, ScoreResult, passed_count(), total_count(), score()
- `backend/tests/tora_eval/test_golden_questions.py` (5 nodes): _ollama_up(), test_golden_question(), pytest entry point for the TORA golden-question eval.  Runs each golden question

### frontend
- `frontend/eslint.config.js` (2 nodes)
- `frontend/postcss.config.js` (2 nodes)
- `frontend/tailwind.config.js` (2 nodes)
- `frontend/vite.config.js` (2 nodes)
- `frontend/vitest.config.js` (2 nodes)

### frontend/src
- `frontend/src/App.jsx` (3 nodes): App()
- `frontend/src/api.js` (16 nodes): wait(), storage(), getStoredAccessToken(), getStoredRefreshToken(), storeToken()
- `frontend/src/main.jsx` (2 nodes)

### frontend/src/components/ai
- `frontend/src/components/ai/AIChatPanel.jsx` (3 nodes): AIChatPanel()
- `frontend/src/components/ai/AICopilot.jsx` (3 nodes): AICopilot()
- `frontend/src/components/ai/FloatingAIButton.jsx` (3 nodes): FloatingAIButton()
- `frontend/src/components/ai/MessageBubble.jsx` (8 nodes): renderInlineMarkdown(), renderMarkdown(), SectionCard(), MessageBubble(), FeedbackBar()
- `frontend/src/components/ai/TypingIndicator.jsx` (3 nodes): TypingIndicator()

### frontend/src/components/domain
- `frontend/src/components/domain/ITRCalculator.tsx` (9 nodes): calculateOldRegimeTax(), calculateNewRegimeTax(), formatCurrency(), handleNext(), handleBack()
- `frontend/src/components/domain/TransactionItem.jsx` (3 nodes): TransactionItem()
- `frontend/src/components/domain/UnitSelector.jsx` (3 nodes): UnitSelector()
- `frontend/src/components/domain/WealthItem.jsx` (3 nodes): WealthItem()

### frontend/src/components/onboarding
- `frontend/src/components/onboarding/WelcomeWizard.jsx` (3 nodes): WelcomeWizard()

### frontend/src/components/planner
- `frontend/src/components/planner/AIRecommendations.jsx` (3 nodes): AIRecommendations()
- `frontend/src/components/planner/CreatePlanModal.jsx` (3 nodes): CreatePlanModal()
- `frontend/src/components/planner/PlanCard.jsx` (3 nodes): PlanCard()
- `frontend/src/components/planner/PlanDetailsDrawer.jsx` (3 nodes): PlanDetailsDrawer()
- `frontend/src/components/planner/PlannerHeader.jsx` (3 nodes): PlannerHeader()
- `frontend/src/components/planner/ProTierFeatures.jsx` (3 nodes): ProTierFeatures()

### frontend/src/components/ui
- `frontend/src/components/ui/AlertsBell.jsx` (4 nodes): timeAgo(), AlertsBell()
- `frontend/src/components/ui/CustomDeletePanel.jsx` (3 nodes): CustomDeletePanel()
- `frontend/src/components/ui/EditTransactionModal.jsx` (3 nodes): EditTransactionModal()
- `frontend/src/components/ui/FilterModal.jsx` (3 nodes): FilterModal()
- `frontend/src/components/ui/Navigation.jsx` (3 nodes): Navigation()
- `frontend/src/components/ui/Shared.jsx` (6 nodes): Toast(), Loading(), ErrorScreen(), ConfirmationDialog()
- `frontend/src/components/ui/StatementHub.jsx` (3 nodes): StatementHub()
- `frontend/src/components/ui/TierBadge.jsx` (5 nodes): TierBadge(), ProFeatureGate(), FeatureComparison()

### frontend/src/components/upload
- `frontend/src/components/upload/OcrUnsupportedModal.jsx` (3 nodes): OcrUnsupportedModal()
- `frontend/src/components/upload/ReviewSkippedModal.jsx` (3 nodes): ReviewSkippedModal()

### frontend/src/hooks
- `frontend/src/hooks/useFinance.js` (16 nodes): useCurrentUser(), useSummary(), useTransactions(), useFlatTransactions(), useWealth()

### frontend/src/pages
- `frontend/src/pages/ActiveLoansPage.jsx` (3 nodes): ActiveLoansPage()
- `frontend/src/pages/AddPage.jsx` (3 nodes): AddPage()
- `frontend/src/pages/AuditPage.jsx` (6 nodes): DeductionBar(), TaxActionCard(), ProfileWizard(), AuditPage()
- `frontend/src/pages/BankAccountsPage.jsx` (3 nodes): BankAccountsPage()
- `frontend/src/pages/BudgetPage.jsx` (3 nodes): BudgetPage()
- `frontend/src/pages/CreditCardsPage.jsx` (3 nodes): CreditCardsPage()
- `frontend/src/pages/DebitCardsPage.jsx` (3 nodes): DebitCardsPage()
- `frontend/src/pages/GoalsPage.jsx` (5 nodes): AddGoalModal(), GoalCard(), GoalsPage()
- `frontend/src/pages/HistoryPage.jsx` (3 nodes): HistoryPage()
- `frontend/src/pages/HomePage.jsx` (3 nodes): HomePage()
- `frontend/src/pages/ITRPage.jsx` (16 nodes): fmt(), fmtNum(), pct(), InfoTooltip(), CurrencyInput()
- `frontend/src/pages/LoginScreen.jsx` (3 nodes): LoginScreen()
- `frontend/src/pages/PlannerPage.jsx` (3 nodes): PlannerPage()
- `frontend/src/pages/ProfilePage.jsx` (3 nodes): ProfilePage()
- `frontend/src/pages/SettingsPage.jsx` (20 nodes): loadPrefs(), savePref(), SettingRow(), SettingSection(), PageHeader()
- `frontend/src/pages/StatsPage.jsx` (5 nodes): CustomTooltip(), InsightCard(), StatsPage()
- `frontend/src/pages/WealthPage.jsx` (3 nodes): WealthPage()

### frontend/src/services
- `frontend/src/services/parser.js` (3 nodes): parseDigitalPdfUpload()

### frontend/src/tests
- `frontend/src/tests/components.tier.test.jsx` (2 nodes)
- `frontend/src/tests/setupTests.js` (10 nodes): ResizeObserver, .observe(), .unobserve(), .disconnect(), IntersectionObserver

### frontend/src/tests/api
- `frontend/src/tests/api/transactionsAPI.test.js` (4 nodes): fetchTransactions(), createTransaction()

### frontend/src/tests/components
- `frontend/src/tests/components/AddTransaction.test.jsx` (3 nodes): fillTransactionForm()
- `frontend/src/tests/components/Dashboard.test.jsx` (2 nodes)
- `frontend/src/tests/components/LoginScreen.test.jsx` (2 nodes)
- `frontend/src/tests/components/TransactionHistory.test.jsx` (2 nodes)

### frontend/src/tests/performance
- `frontend/src/tests/performance/apiLatency.test.js` (2 nodes)
- `frontend/src/tests/performance/failureRate.test.js` (2 nodes)

### frontend/src/utils/pdf
- `frontend/src/utils/pdf/detectPdfType.js` (3 nodes): detectPdfType()

### other
- `` (10 nodes): BaseModel, BaseSettings, RuntimeError, Base, DeclarativeBase
- `PROJECT_LOG.md` (2 nodes): TORA Intelligence Engine, Gemma 4 MoE
- `README.md` (1 nodes): Spendsy Platform
- `backend/ai-service/app/main.py` (1 nodes): AI Service
- `backend/auth-service/app/main.py` (1 nodes): Auth Service
- `backend/finance-service/app/main.py` (1 nodes): Finance Service
- `backend/finance-service/app/services/parser/digital_deterministic_parser.py` (1 nodes): Deterministic PDF Parser
- `backend/finance-service/app/services/transfer_reconciler.py` (1 nodes): Transfer Reconciler
- `backend/spendsy-ai/agents/tora/fetch_registry.py` (1 nodes): TORA Plugin Registry
- `backend/spendsy-ai/agents/tora/thinking_gate.py` (1 nodes): Thinking Mode Gating
- `backend/spendsy-ai/vault/vault_writer.py` (1 nodes): TORA Obsidian Vault
- `frontend/src/App.jsx` (1 nodes): Frontend App

### root
- `patch.py` (2 nodes)
- `run-local.ps1` (15 nodes): Write-Step(), Invoke-Checked(), Resolve-ExecutablePath(), Start-CleanupWatcher(), Complete-CleanupWatcher()
- `run.ps1` (2 nodes)

### shared/config
- `shared/config/constants.js` (3 nodes): getEnv()

### shared/context
- `shared/context/AuthContext.jsx` (5 nodes): getGatewayUrl(), useAuth(), AuthProvider()
- `shared/context/DataContext.jsx` (4 nodes): useData(), DataProvider()

### shared/services
- `shared/services/aiService.js` (4 nodes): getAuthHeaders(), buildUrl()
- `shared/services/taxForensics.js` (2 nodes)
- `shared/services/taxService.js` (3 nodes): getITRFormType()

### shared/utils
- `shared/utils/cn.ts` (3 nodes): cn()
- `shared/utils/exportUtils.js` (3 nodes): downloadCSV()
- `shared/utils/helpers.js` (9 nodes): generateId(), normalizeDate(), loadScript(), formatIndianCompact(), getCurrentFinancialYear()

### tests
- `tests/conftest.py` (43 nodes): _restore_env_file(), _compile_jsonb_sqlite(), _DummyRedisClient, .__init__(), from_url()
