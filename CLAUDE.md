# Spendsy — Project Reference

## Project overview

Spendsy is a personal finance management app with an AI agent (TORA — Tax Optimization & Recommendation Agent). Indian tax compliance is a first-class feature. The app targets individual users who want to track spending, manage wealth, file ITR, and get AI-driven financial advice.

## Tech stack

- Frontend: React 18 + Vite, Tailwind CSS, Framer Motion, Recharts, React Query v5, Axios
- Backend: Python FastAPI microservices (auth-service :8001, finance-service :8002, ai-service :8003), Nginx gateway :8080
- Database: PostgreSQL (via SQLAlchemy + Alembic), Redis for caching/queuing
- AI: Google Gemini 1.5 Flash (primary), Mistral (fallback), agentic tool-calling pattern
- Infra: Docker, Nginx reverse proxy, PgBouncer, self-signed SSL for dev

## Architecture

```
frontend/ ─── React SPA (17 pages, ~30 components)
backend/
  auth-service/     ─── JWT auth, refresh tokens, security alerts
  finance-service/  ─── Core CRUD, tax engine, goals, plans, alerts, scheduler
  ai-service/       ─── TORA chat relay to Gemini
  spendsy-ai/       ─── TORA agent (tools, personality, memory, tiering)
  spendsy-mcp/      ─── Model Context Protocol server
shared/             ─── AuthContext, DataContext, constants, helpers, tax utils
infra/              ─── Docker configs, certs, pgbouncer
graphify-out/       ─── Knowledge graph (wiki/, GRAPH_REPORT.md, graph.json)
```

## God nodes (most coupled — touch carefully)

1. TieringConfig (152 edges) — free/pro/enterprise feature gating
2. TaxInput (114 edges) — tax calculation input structure
3. Transaction (74 edges) — core financial record
4. UserContext (67 edges) — auth/security context
5. UserProfile (57 edges) — user settings & preferences
6. Loan (52 edges) — loan/EMI tracking
7. ITRData (49 edges) — tax filing data
8. CreditCard (44 edges) — credit card management
9. WealthItem (43 edges) — assets/liabilities
10. TaxProfile (43 edges) — deduction tracking

## Frontend pages (17 total)

| Page | File | Purpose |
|------|------|---------|
| LoginScreen | pages/LoginScreen.jsx | Auth (login + signup) |
| HomePage | pages/HomePage.jsx | Dashboard: monthly spend, metrics, recent txns |
| HistoryPage | pages/HistoryPage.jsx | Transaction list with filter/search/bulk ops |
| AddPage | pages/AddPage.jsx | Manual entry + PDF statement upload |
| StatsPage | pages/StatsPage.jsx | Charts: category breakdown, trends |
| WealthPage | pages/WealthPage.jsx | Assets/liabilities, net worth chart |
| ProfilePage | pages/ProfilePage.jsx | User info, health score, quick links |
| SettingsPage | pages/SettingsPage.jsx | 10 sub-pages (personal, security, theme, AI, data, etc.) |
| AuditPage | pages/AuditPage.jsx | Tax audit, deduction detection, integrity score |
| ITRPage | pages/ITRPage.jsx | Full ITR form (8 tabs: dashboard, income, deductions, CG, regime, audit, planning, filing) |
| PlannerPage | pages/PlannerPage.jsx | Savings/investment plans with AI recommendations |
| GoalsPage | pages/GoalsPage.jsx | Financial goals with progress tracking |
| BudgetPage | pages/BudgetPage.jsx | Monthly income/budget/daily limit config |
| ActiveLoansPage | pages/ActiveLoansPage.jsx | Loan list with EMI/repayment progress |
| BankAccountsPage | pages/BankAccountsPage.jsx | Navigation hub → debit/credit cards |
| CreditCardsPage | pages/CreditCardsPage.jsx | CC management (add/edit/delete) |
| DebitCardsPage | pages/DebitCardsPage.jsx | Debit card management |

## Backend models (finance-service, 23 tables)

Core: UserProfile, Transaction, WealthItem, TaxProfile, ITRData
Banking: CreditCard, DebitCard, Loan, StatementRecord
Planning: FinancePlan, FinanceGoal, NetWorthSnapshot
AI: ToraConversation, ToraFeedback, SmartRecommendation
Insights: UserAlert, FinancialHealth, FinancialInsight
Meta: ApiAuditLog, SecurityAlert, Document

## TORA agent tools

create_plan, adjust_plan, create_loan_repayment_plan, compare_tax_regimes,
simulate_tax_efficient_investment, sync_credit_card_payments, update_tax_profile

## Tiering model

- Free: basic chat, no tool calling, 20-msg memory, ad banner
- Pro: tool calling, 100-msg memory, email reports, no ads
- Enterprise: unlimited memory, priority support, custom integrations

## Conventions

- Currency: ₹ (Indian Rupee), formatted with formatIndianCompact() helper
- Fiscal year: April–March (month < 3 = previous FY)
- State management: React Query for server state, localStorage for UI/auth
- API client: centralized apiFetch() with auto-refresh, rate-limit handling
- Routing: tab-based (TABS constant in App.jsx), no react-router
- Theme: dark/light toggle via Tailwind classes
- Testing: Vitest + React Testing Library (frontend), pytest (backend)

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)

## Audit findings (2026-04-26) — verified against source

247 issues originally found. Re-verified 2026-04-26. Status reflects actual code state.

### Critical issues — current status

| Issue | Status |
|-------|--------|
| LoginScreen: No password reset flow | ✅ FIXED — `mode="forgot"` branch in `handleAuth` |
| LoginScreen: No email verification | ✅ FIXED — toast on signup; simulated only (no backend flow) |
| LoginScreen: Debug "Hard Reset" button | ✅ FIXED — `clearSiteData()` exists but button removed from JSX |
| ITRPage: FY/AY hardcoded to 2025-26 | ✅ FIXED — `getDynamicYears()` used throughout |
| ITRPage: Advance tax dates hardcoded to 2025 | ✅ FIXED — `isPast` check now uses `ADV_YR` from `getDynamicYears()` |
| ITRPage: No unsaved changes warning | ✅ FIXED — `beforeunload` dirty-state guard implemented |
| SettingsPage: localStorage crash in private browsing | ✅ FIXED — try/catch in `loadPrefs`/`savePref` |
| SettingsPage: 2FA is decorative | ⚠️ PARTIAL — toggle UI exists, no real OTP/backend |
| StatsPage: Watchdog AI commented out | ✅ FIXED — fully live code |
| StatsPage: Net Worth History chart commented out | ✅ FIXED — MoM/YoY cards and chart are rendered |
| AuditPage: AI Consultant commented out | ✅ FIXED — fully rendered |
| CreditCardsPage: Card type hardcoded "PLATINUM" | ✅ FIXED — dropdown implemented in form |
| HomePage: Tax calc hardcoded FY 2025-26 | ✅ FIXED — uses `getCurrentFinancialYear()` |
| WealthPage: "+2.4%" hardcoded | ✅ FIXED — computed from `netWorthHistory` snapshots |
| ProfilePage: Risk Level always "Low" | ✅ FIXED — DTI/savings/emergency fund formula |
| ProfilePage: Health score oversimplified | ✅ FIXED — 3-factor weighted score (40/30/30) |
| PlannerPage: Success rate 85% hardcoded | ✅ FIXED — `completedPlans / total * 100` |
| PlannerPage: AI influence 62% hardcoded | ✅ FIXED — `aiSourcedPlans / total * 100` |
| ActiveLoansPage: "Explore Refinance" no handler | ✅ FIXED — `onClick={() => setActiveTab(TABS.CHAT)}` |

### Cross-cutting gaps — current status

| Gap | Status |
|-----|--------|
| Loading skeletons (14/17 pages) | ⚠️ PARTIAL — WealthSkeleton done; PlannerPage pulse; others missing |
| Silent API errors (15/17 pages) | ⚠️ PARTIAL — Planner/Loans/Wealth show toasts; others still console.error |
| No debounce on submit | ⚠️ PARTIAL — LoginScreen locked with `SUBMIT_LOCK_MS`; other forms open |
| No error boundary | ✅ FIXED — `ErrorBoundary` in `App.jsx` |
| ₹ hardcoded everywhere | ⚠️ PARTIAL — `CURRENCY_SYMBOL` constant exists; not adopted everywhere |
| No accessibility | ❌ OPEN — no `id`/`htmlFor`/`aria-label` on most forms |
| No i18n | ❌ OPEN |

### Commented-out features — current status

1. StatsPage: Watchdog AI — ✅ LIVE (uncommenting done)
2. StatsPage: Net Worth History chart — ✅ LIVE (uncommenting done)
3. AuditPage: AI Consultant section — ✅ LIVE (uncommenting done)

### Half-built features — current status

| # | Feature | Status |
|---|---------|--------|
| 1 | SettingsPage: Personal info edit | ❌ OPEN |
| 2 | SettingsPage: Change Password handler | ❌ OPEN |
| 3 | SettingsPage: Profile picture upload | ❌ OPEN |
| 4 | SettingsPage: Active Sessions list | ❌ OPEN |
| 5 | SettingsPage: Subscription hardcoded "Pro Member" | ✅ FIXED — `TIER_CONFIG` + `tier` prop wired |
| 6 | ITRPage: House Property never rendered | ✅ FIXED — Expandable section with multi-property support |
| 7 | ITRPage: Profile completeness too easy | ❌ OPEN |
| 8 | PlannerPage: Simulation handler TODO | ⚠️ PARTIAL — console.log placeholder |
| 9 | PlannerPage: Recommendations hardcoded | ✅ FIXED — computed from real plan data |
| 10 | PlannerPage: Archived plans always empty | ⚠️ DESIGN GAP — placeholder text only |
| 11 | AddPage: draftTransactions dead code | ❓ NOT VERIFIED |
| 12 | GoalsPage: No custom quick-add amount | ❓ NOT VERIFIED |
| 13 | BudgetPage: Single global budget only | ✅ FIXED — `categoryBudgets` + actual spend comparison |
| 14 | ActiveLoansPage: No loan interaction | ✅ FIXED — amortization schedule modal |
| 15 | AI Observability / Reinforcement Learning | ✅ DONE — Microsoft Agent Lightning integrated |


### Missing polish features — current status

| # | Feature | Status |
|---|---------|--------|
| 1 | Password reset / forgot flow | ✅ DONE (simulated) |
| 2 | Social login | ❌ OPEN |
| 3 | Email verification on signup | ⚠️ Toast only |
| 4 | Category-level budgets | ✅ DONE |
| 5 | Budget vs. actual comparison | ✅ DONE |
| 6 | Loan amortization schedule | ✅ DONE |
| 7 | Portfolio allocation pie chart | ✅ DONE (WealthPage) |
| 8 | MoM / YoY comparison on StatsPage | ✅ DONE |
| 9 | Drill-down from charts | ⚠️ PARTIAL — category click highlights, no HistoryPage link |
| 10 | Export options on StatsPage | ✅ DONE (CSV export) |
| 11 | Undo/confirmation on destructive actions | ⚠️ PARTIAL — `triggerConfirm` in some places |
| 12 | Date range selector on HomePage | ❓ NOT VERIFIED |
| 13 | Search debouncing on HistoryPage | ⚠️ PARTIAL — loader icon only |
| 14 | T&C acceptance on signup | ✅ DONE |
| 15 | Real financial health score | ✅ DONE |
