# Spendsy Project: Architectural Analysis

This document provides a comprehensive technical breakdown of the **Spendsy** ecosystem. It is designed to help new developers understand the system's architecture, data flow, and service interactions.

---

## 1. Project Overview

**Purpose**: Spendsy is a microservices-based personal finance management application tailored for the Indian market. It automates financial tracking, tax planning (ITR), wealth monitoring, and provides AI-driven insights from financial data.

**Tech Stack**:
- **Frontend**: React (Vite), Tailwind CSS, Framer Motion, Lucide Icons.
- **Backend**: Python (FastAPI), SQLAlchemy ORM.
- **Database**: PostgreSQL 15.
- **Caching/Queuing**: Redis.
- **AI**: Google Gemini API, OpenAI API (gpt-4o-mini).
- **Infrastructure**: Docker & Docker Compose, Nginx (API Gateway).

---

## 2. Project Architecture

### High-Level Diagram (Conceptual)
```text
          [ Vite React App ]
                 |
                 | (HTTPS / JSON + Cookies)
                 V
        [ NGINX API Gateway ] (Port 8080)
                 |
   +-------------+-------------+-------------+-------------+
   |             |             |             |             |
[Auth]        [Finance]     [Parser]      [AI]        [Tora]
(8001)        (8002)        (8003)        (8004)        (8005)
   |             |             |             |             |
   +-------------+-------------+-------------+-------------+
                 |             |
          [ PostgreSQL ]    [ Redis ]
```

### Folder Structure
- `apps/web/frontend`: React application source.
- `spendsy/services/`: Microservices (Auth, Finance, AI, Parser).
- `packages/shared/`: Cross-cutting concerns (Constants, Utils).
- `infra/docker/`: Environment orchestration.
- `spendsy-ai/`: Specialized Tora agent service.

### Layer Separation
- **Routes**: Located in `app/api/`, handling endpoint definitions and input/output serialization (Pydantic).
- **Services**: Located in `app/services/` (e.g., `GeminiClient`, `ParserClient`), handling external integrations.
- **Models**: Located in `app/models.py`, defining SQLAlchemy entities.
- **Schemas**: Located in `app/schemas.py`, defining Pydantic data contracts.
- **Core**: Located in `app/core/`, managing infrastructure like database connections, redis, and security.

---

## 3. API Route Analysis

### Auth Service (8001)
| Method | Endpoint | Function | Auth | Description |
|--------|----------|----------|------|-------------|
| POST | `/auth/register` | `register` | None | New user creation + JWT Cookie set |
| POST | `/auth/login` | `login` | None | Credential validation + JWT Cookie set |
| POST | `/auth/refresh` | `refresh` | Cookie | Token rotation |
| GET | `/auth/me` | `me` | JWT | Fetch current session user |
| POST | `/auth/logout` | `logout` | JWT | Token blacklisting & cookie clearing |

### Finance Service (8002)
| Method | Endpoint | Function | Auth | Description |
|--------|----------|----------|------|-------------|
| GET | `/transactions` | `list_transactions` | JWT | Paginated transaction ledger |
| POST | `/transactions` | `create_transaction` | JWT | Manual entry |
| GET | `/wealth` | `list_wealth` | JWT | Assets & Liabilities |
| POST | `/statements/record` | `upload_statement` | JWT | PDF/CSV parsing injection |
| GET | `/debit-cards` | `list_debit_cards` | JWT | Bank account management |
| GET | `/itr` | `get_itr` | JWT | Tax data & regime preferences |
| GET | `/internal/finance-context/{uid}` | `finance_context`| API Key | Inter-service context sharing |

### AI Service (8004)
| Method | Endpoint | Function | Auth | Description |
|--------|----------|----------|------|-------------|
| POST | `/insights` | `insights` | JWT | Gemini-driven spend analysis |
| POST | `/health-score` | `health_score` | JWT | Financial wellness calculation |

---

## 4. CRUD Mapping

| Entity | Create | Read | Update | Delete |
|--------|--------|------|--------|--------|
| **User** | `/auth/register` | `/auth/me` | (N/A) | (N/A) |
| **Transaction** | `/transactions` (POST) | `/transactions` (GET) | `/transactions/{id}` (PUT) | `/transactions/{id}` (DELETE) |
| **Budget** | (UserProfile) | `/profile` (GET) | `/profile` (PATCH) | (N/A) |
| **Wealth** | `/wealth` (POST) | `/wealth` (GET) | `/wealth/{id}` (PUT) | `/wealth/{id}` (DELETE) |
| **Bank Card** | `/debit-cards` (POST) | `/debit-cards` (GET) | `/debit-cards/{id}` (PUT) | `/debit-cards/{id}` (DELETE) |

---

## 5. Database Layer

**ORM**: SQLAlchemy 2.0 (Declarative Base).

**Core Models**:
1. `User` (`auth_user`): Stores credentials (hashed), email, and state.
2. `UserProfile`: Monthly income, budget, and business status.
3. `Transaction`: Ledger storing amounts, categories, and "fingerprints" for deduplication.
4. `WealthItem`: Portfolio entries (Asset/Liability).
5. `ITRData`: JSONB storage for complex tax return snapshots.
6. `StatementRecord`: Metadata for uploaded financial files.
7. `ApiAuditLog`: Tracking sensitive actions for security.

**Relationships**: Most entities are loosely coupled by `user_id` (BigInteger) to support future service horizontal scaling.

---

## 6. Request → Response Workflow

### Example 1: Creating a Transaction
1. **Client**: User clicks "Add Salary" in the React UI.
2. **Route**: `POST /finance/transactions` (Port 8002).
3. **Security**: `get_current_user` dependency validates JWT from cookie.
4. **Validation**: Pydantic `TransactionPayload` ensures amount > 0.
5. **Logic**: `routes_finance.py` calculates a transaction **fingerprint** (SHA256) to prevent double-entry.
6. **Database**: SQLAlchemy commits to `finance_transaction`.
7. **Response**: 201 Created with JSON representation.

### Example 2: AI Insights
1. **Client**: User triggers "Generate AI Insights" on Stats Page.
2. **Route**: `POST /ai/insights` (Port 8004).
3. **Service Context**: AI Service calls Finance Service `/internal/finance-context/{uid}` using an **Internal API Key**.
4. **Logic**: AI Service builds a prompt containing recent spending habits.
5. **AI API**: Send prompt to Google Gemini.
6. **Response**: Insights are parsed and returned to the client.

---

## 7. Business Logic Layer

Core logic is primarily located in the **Route Handlers** (`routes_finance.py`) and dedicated **Parser Engines** (`parser.py`).
- **Deduplication Logic**: Uses hashing of {user, date, amount, title} to manage statement overlaps.
- **Categorization**: A hybrid approach using regex patterns and AI-based inference.
- **Tax Calculation**: Implements Indian New/Old tax regime slabs in `packages/shared/config/constants.js`.

---

## 8. Security & Validation

- **Authentication**: JWT-based. Tokens are stored in **HttpOnly, SameSite=Lax** cookies to mitigate XSS/CSRF.
- **Password Hashing**: BCrypt (via `passlib`).
- **Internal Auth**: Service-to-service calls are authenticated via a static `INTERNAL_API_KEY` cross-checked in the `.env`.
- **Validation**: Strict Pydantic schemas enforce type safety before hitting the logic layer.

---

## 9. External Services

- **Redis**: Used for rate-limiting, task queuing, and temporary session blacklisting.
- **Gemini Pro**: The primary brain for financial advice and categorization refinement.
- **OpenAI (TORA)**: Powers the dedicated financial intelligence agent.
- **PDFPlumber/Tesseract**: Heavy-lifting engines for parsing messy bank PDFs and images.

---

## 10. Potential Architecture Issues

1. **Large Route Files**: `routes_finance.py` is over 1,000 lines, blending routing logic with thick business logic.
2. **Direct DB Dependency**: Services directly query the database in routes, lacking a Repository Pattern; this makes unit testing harder.
3. **Shared Database**: While services are conceptually separate, they often target the same PostgreSQL instance/pool, creating a single point of failure.
4. **Synchronous Parsing**: Heavy statement parsing currently runs mostly in-request; very large files could time out the gateway.

---

## 11. Improvement Suggestions

1. **Pattern Implementation**: Refactor `finance-service` to use the **Repository Pattern** to decouple database logic from HTTP transport.
2. **Async Workers**: Offload statement parsing to a background worker (like **Celery** or **ARQ**) and use WebSockets/Polling for status updates.
3. **Internal SDK**: Create a shared internal Python library for inter-service communication instead of raw `api_fetch` calls.
4. **API Versioning**: Introduce `/v1/` prefixes to routes now to avoid breaking the frontend during future breaking changes.

---
*Generated by the Spendsy Architectural Review Board.*
