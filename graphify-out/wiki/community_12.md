# Community 12

**36 nodes**

## Nodes
- **proactive_insights.py** (`backend/finance-service/app/services/jobs/proactive_insights.py` L1) → proactive_insights_candidate_user_ids, proactive_insights_recent_alert_signatures, proactive_insights_emit_alert
- **_candidate_user_ids()** (`backend/finance-service/app/services/jobs/proactive_insights.py` L56) → proactive_insights_run_nightly_insights, d_projects_spendsy_backend_finance_service_app_services_jobs_proactive_insights_py
- **_recent_alert_signatures()** (`backend/finance-service/app/services/jobs/proactive_insights.py` L61) → proactive_insights_run_nightly_insights, proactive_insights_rationale_62, test_proactive_insights_testdedupesignatures_test_recent_signatures_returned
- **_emit_alert()** (`backend/finance-service/app/services/jobs/proactive_insights.py` L75) → proactive_insights_check_category_spike, proactive_insights_check_large_transactions, proactive_insights_check_unusual_merchant
- **_check_category_spike()** (`backend/finance-service/app/services/jobs/proactive_insights.py` L105) → proactive_insights_run_nightly_insights, proactive_insights_rationale_111, test_proactive_insights_testcategoryspike_test_fires_on_30pct_increase
- **_check_large_transactions()** (`backend/finance-service/app/services/jobs/proactive_insights.py` L176) → proactive_insights_run_nightly_insights, proactive_insights_rationale_182, test_proactive_insights_testlargetransaction_test_fires_on_3x_median_recent
- **_check_unusual_merchant()** (`backend/finance-service/app/services/jobs/proactive_insights.py` L231) → proactive_insights_run_nightly_insights, proactive_insights_rationale_237, test_proactive_insights_testunusualmerchant_test_fires_for_new_merchant_2_plus_hits
- **run_nightly_insights()** (`backend/finance-service/app/services/jobs/proactive_insights.py` L298) → d_projects_spendsy_backend_finance_service_app_services_jobs_proactive_insights_py
- **Nightly proactive-insights engine.  Walks every user and runs a set of determini** (`backend/finance-service/app/services/jobs/proactive_insights.py` L1) → d_projects_spendsy_backend_finance_service_app_services_jobs_proactive_insights_py
- **All (alert_type, signature) pairs this user saw in the dedupe window.** (`backend/finance-service/app/services/jobs/proactive_insights.py` L62)
- **Insert a UserAlert row. Caller is responsible for dedupe checks.** (`backend/finance-service/app/services/jobs/proactive_insights.py` L85)
- **Compare last-30-day spend per category to prior 30 days.** (`backend/finance-service/app/services/jobs/proactive_insights.py` L111)
- **Flag any expense ≥ 3× the user's median, floor ₹5k.** (`backend/finance-service/app/services/jobs/proactive_insights.py` L182)
- **Merchant unseen in last 90 days now appears 2+ times in last 7.** (`backend/finance-service/app/services/jobs/proactive_insights.py` L237)
- **test_proactive_insights.py** (`backend/tests/test_proactive_insights.py` L1) → test_proactive_insights_remap_jsonb_for_sqlite, test_proactive_insights_db_session, test_proactive_insights_tx
- **_remap_jsonb_for_sqlite()** (`backend/tests/test_proactive_insights.py` L40) → test_proactive_insights_db_session, test_proactive_insights_rationale_41, d_projects_spendsy_backend_tests_test_proactive_insights_py
- **db_session()** (`backend/tests/test_proactive_insights.py` L49) → d_projects_spendsy_backend_tests_test_proactive_insights_py
- **_tx()** (`backend/tests/test_proactive_insights.py` L62) → test_proactive_insights_testcategoryspike_test_fires_on_30pct_increase, test_proactive_insights_testcategoryspike_test_does_not_fire_for_small_delta, test_proactive_insights_testcategoryspike_test_dedupes_within_7_day_window
- **TestCategorySpike** (`backend/tests/test_proactive_insights.py` L78) → test_proactive_insights_testcategoryspike_test_fires_on_30pct_increase, test_proactive_insights_testcategoryspike_test_does_not_fire_for_small_delta, test_proactive_insights_testcategoryspike_test_dedupes_within_7_day_window
- **.test_fires_on_30pct_increase()** (`backend/tests/test_proactive_insights.py` L79)
- **.test_does_not_fire_for_small_delta()** (`backend/tests/test_proactive_insights.py` L99)
- **.test_dedupes_within_7_day_window()** (`backend/tests/test_proactive_insights.py` L110)
- **.test_severity_danger_for_60pct()** (`backend/tests/test_proactive_insights.py` L121)
- **TestLargeTransaction** (`backend/tests/test_proactive_insights.py` L139) → test_proactive_insights_testlargetransaction_test_fires_on_3x_median_recent, test_proactive_insights_testlargetransaction_test_does_not_fire_on_old_large_tx, test_proactive_insights_testlargetransaction_test_no_median_without_history
- **.test_fires_on_3x_median_recent()** (`backend/tests/test_proactive_insights.py` L140)
- **.test_does_not_fire_on_old_large_tx()** (`backend/tests/test_proactive_insights.py` L155)
- **.test_no_median_without_history()** (`backend/tests/test_proactive_insights.py` L165)
- **TestUnusualMerchant** (`backend/tests/test_proactive_insights.py` L181) → test_proactive_insights_testunusualmerchant_test_fires_for_new_merchant_2_plus_hits, test_proactive_insights_testunusualmerchant_test_does_not_fire_for_1_hit, test_proactive_insights_testunusualmerchant_test_does_not_fire_if_merchant_existed_before
- **.test_fires_for_new_merchant_2_plus_hits()** (`backend/tests/test_proactive_insights.py` L182)
- **.test_does_not_fire_for_1_hit()** (`backend/tests/test_proactive_insights.py` L198)
- **.test_does_not_fire_if_merchant_existed_before()** (`backend/tests/test_proactive_insights.py` L205)
- **TestDedupeSignatures** (`backend/tests/test_proactive_insights.py` L220) → test_proactive_insights_testdedupesignatures_test_recent_signatures_returned, d_projects_spendsy_backend_tests_test_proactive_insights_py
- **.test_recent_signatures_returned()** (`backend/tests/test_proactive_insights.py` L221)
- **Tests for the nightly proactive insights engine.  Each rule is tested against a** (`backend/tests/test_proactive_insights.py` L1) → d_projects_spendsy_backend_tests_test_proactive_insights_py
- **proactive_insights.py** (`backend/finance-service/app/services/jobs/proactive_insights.py` L1)
- **test_proactive_insights.py** (`backend/tests/test_proactive_insights.py` L1)
