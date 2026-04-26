# Audit Master Node (2026-04-26)

**247 issues · 17 pages · 32 critical · 52 high · 96 medium · 67 low**

## Fixed pages
- HomePage (19 issues → all fixed)
- AddPage (15 issues → all fixed)

## Pages by severity (descending)
- **SettingsPage** — 42 issues (5C/12H/18M/7L) [PENDING]
- **ITRPage** — 35 issues (4C/10H/16M/5L) [PENDING]
- **CreditCardsPage** — 28 issues (3C/8H/12M/5L) [PENDING]
- **LoginScreen** — 26 issues (3C/8H/10M/5L) [PENDING]
- **StatsPage** — 22 issues (2C/6H/10M/4L) [PENDING]
- **HomePage** — 19 issues (2C/5H/8M/4L) [FIXED]
- **AuditPage** — 18 issues (2C/5H/8M/3L) [PENDING]
- **WealthPage** — 18 issues (2C/5H/7M/4L) [PENDING]
- **GoalsPage** — 18 issues (1C/5H/8M/4L) [PENDING]
- **AddPage** — 15 issues (1C/4H/7M/3L) [FIXED]
- **ProfilePage** — 15 issues (2C/4H/6M/3L) [PENDING]
- **PlannerPage** — 14 issues (1C/4H/6M/3L) [PENDING]
- **ActiveLoansPage** — 14 issues (2C/3H/5M/4L) [PENDING]
- **HistoryPage** — 13 issues (1C/3H/6M/3L) [PENDING]
- **BudgetPage** — 12 issues (1C/3H/5M/3L) [PENDING]
- **DebitCardsPage** — 12 issues (1C/3H/5M/3L) [PENDING]
- **BankAccountsPage** — 3 issues (0C/1H/1M/1L) [PENDING]

## Cross-cutting gaps
- 14/17 pages have no loading skeletons
- 15/17 pages silently swallow API errors (console.error only)
- No form has debounce/throttle on submit buttons
- No page has an error boundary
- Currency symbol hardcoded everywhere (not configurable)
- No accessibility: missing <label> elements, no aria-labels, no keyboard nav
- No i18n support

## Commented-out features (ready to re-enable)
- StatsPage: Watchdog AI (lines 347-407) — Anomaly detection insights
- StatsPage: Net Worth History chart (lines 556-613) — Historical net worth line chart
- AuditPage: AI Consultant section (lines 495-559) — AI-powered tax advice

## Half-built features
- SettingsPage: Personal info fields display-only (no edit UI)
- SettingsPage: Change Password button has no handler
- SettingsPage: Profile picture upload has no file picker
- SettingsPage: Active Sessions shows button but no session list
- SettingsPage: Subscription card hardcoded 'Pro Member' regardless of tier
- ITRPage: House Property fields defined but never rendered
- ITRPage: Profile completeness reaches 100% with minimal data
- PlannerPage: ProTierFeatures has TODO — simulation handler not implemented
- PlannerPage: Recommendations engine hardcoded, not AI-driven
- PlannerPage: Archived Plans section always empty placeholder
- GoalsPage: Quick-add only preset amounts, no custom input
- BudgetPage: Single global budget only — no category-level breakdown
- ActiveLoansPage: No loan interaction (edit, details, payment)

## Polish features missing
- Password reset / forgot password flow
- Social login (Google/GitHub)
- Email verification on signup
- Category-level budgets
- Budget vs. actual comparison on BudgetPage
- Loan amortization schedule on ActiveLoansPage
- Portfolio allocation pie chart on WealthPage
- Month-over-month / YoY comparison on StatsPage
- Drill-down from charts to underlying transactions
- Export options on StatsPage
- Undo/confirmation on destructive actions
- Date range selector on HomePage
- Search debouncing on HistoryPage
- Terms & Conditions acceptance on signup
- Real financial health score (debt-to-income, savings rate, emergency fund ratio)

---
Query this node in graph.json at id: `audit_master_2026_04_26`
All per-page issues are in the `meta.issues_by_page` field with critical/high arrays.
