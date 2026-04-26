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

## Audit findings (2026-04-26)

247 issues found across 17 pages. Summary by severity: 32 critical, 52 high, 96 medium, 67 low.

### Critical issues (must fix)

- LoginScreen: No password reset flow, no email verification, debug "Hard Reset" button in production
- ITRPage: FY/AY hardcoded to 2025-26 (breaks next year), advance tax dates hardcoded to 2025, no unsaved changes warning
- SettingsPage: localStorage calls crash in private browsing (no try/catch), 2FA is decorative (no implementation), delete-all needs stronger safeguard
- StatsPage: Watchdog AI section fully coded but commented out (~120 lines), Net Worth History chart commented out (~60 lines)
- CreditCardsPage: Card type hardcoded "PLATINUM", "Active Protection" badge is decorative
- HomePage: Tax calc hardcoded for FY 2025-26 with no regime toggle
- WealthPage: "+2.4%" net worth change is hardcoded (never calculated)
- ProfilePage: Risk Level always "Low", health score uses oversimplified formula
- PlannerPage: Success rate (85%) and AI influence (62%) are hardcoded fakes
- AuditPage: AI Consultant section fully implemented but commented out
- ActiveLoansPage: "Explore Refinance" button has no onClick handler

### Cross-cutting gaps

- 14/17 pages have no loading skeletons
- 15/17 pages silently swallow API errors (console.error only)
- No form has debounce/throttle on submit buttons
- No page has an error boundary
- Currency symbol ₹ hardcoded everywhere (not configurable)
- No accessibility: missing <label> elements, no aria-labels, no keyboard nav
- No i18n support

### Commented-out features (ready to re-enable)

1. StatsPage: Watchdog AI (lines 347-407) — anomaly detection insights
2. StatsPage: Net Worth History chart (lines 556-613) — historical net worth line chart
3. AuditPage: AI Consultant section (lines 495-559) — AI-powered tax advice

### Half-built features (need completion)

1. SettingsPage: Personal info fields are display-only (no edit UI)
2. SettingsPage: Change Password button has no handler
3. SettingsPage: Profile picture upload has no file picker
4. SettingsPage: Active Sessions shows button but no session list
5. SettingsPage: Subscription card hardcoded as "Pro Member" regardless of tier
6. ITRPage: House Property fields defined in code but never rendered
7. ITRPage: Profile completeness reaches 100% with minimal data
8. PlannerPage: ProTierFeatures has TODO — simulation handler not implemented
9. PlannerPage: Recommendations engine is hardcoded, not AI-driven
10. PlannerPage: "Archived Plans" section always shows empty placeholder
11. AddPage: draftTransactions state declared but never used (dead code)
12. GoalsPage: Quick-add only has preset amounts (₹1K/5K/10K), no custom input
13. BudgetPage: Single global budget only — no category-level breakdown
14. ActiveLoansPage: No loan interaction (edit, details, payment)

### Missing features that would add polish

1. Password reset / forgot password flow
2. Social login (Google/GitHub)
3. Email verification on signup
4. Category-level budgets (not just one global number)
5. Budget vs. actual comparison on BudgetPage
6. Loan amortization schedule on ActiveLoansPage
7. Portfolio allocation pie chart on WealthPage
8. Month-over-month / YoY comparison on StatsPage
9. Drill-down from charts to underlying transactions
10. Export options on StatsPage (chart data, insights)
11. Undo/confirmation on destructive actions (bulk delete, quick-add)
12. Date range selector on HomePage (locked to current month)
13. Search debouncing on HistoryPage
14. Terms & Conditions acceptance on signup
15. Real financial health score (debt-to-income, savings rate, emergency fund ratio)
