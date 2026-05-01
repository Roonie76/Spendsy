# Spendsy — CLAUDE.md

## Caveman Mode

This repo uses the [caveman](https://github.com/JuliusBrussee/caveman) plugin.
Talk like caveman. Drop filler. Keep accuracy. ~75% fewer output tokens, same technical truth.

Trigger: `/caveman` | Stop: `normal mode`
Levels: `lite` (drop filler, keep grammar) · `full` (default grunt) · `ultra` (max compression)
Skills: `/caveman-commit` · `/caveman-review` · `/caveman-compress CLAUDE.md` · `/caveman-stats`

Before reading raw files for architecture questions, check `graphify-out/GRAPH_REPORT.md` first.

---

## What Is Spendsy

Fintech microservices platform — personal wealth tracking + AI-driven insights (TORA agent).
Stack: FastAPI · React/Vite · PostgreSQL 15 · Redis · Nginx · Docker.

---

## Repo Layout

```
Spendsy/
├── backend/
│   ├── auth-service/       FastAPI — JWT, Redis sessions (port 8001)
│   ├── finance-service/    FastAPI — ledger, PDF parsing, PgBouncer (port 8002)
│   ├── spendsy-ai/         TORA agent — Gemini 1.5 Pro + local Ollama (port 8005 → exposed 8004)
│   └── spendsy-mcp/        MCP server for Claude Desktop (port 8006)
├── frontend/               React + Vite SPA (dev: 5173, Docker: 3000)
├── infra/                  Nginx config, Docker helpers
├── docs/
│   ├── ARCHITECTURE.md     Full system diagram + SRS
│   └── CONTRIBUTING.md     Dev setup + code standards
├── graphify-out/           Knowledge graph — read before architecture questions
├── .agents/rules/          Per-agent rules (graphify.md)
├── docker-compose.yml
├── run-local.ps1           Recommended dev start (frontend local + backend Docker)
└── run.ps1                 Pure-Docker mode
```

---

## Architecture

Traffic: React SPA → Nginx (8080) → services by path prefix (`/auth`, `/finance`, `/ai`).

| Service | Port | Tech | Role |
|---|---|---|---|
| auth-service | 8001 | FastAPI, SQLAlchemy, Redis | JWT issuance + HttpOnly cookie sessions |
| finance-service | 8002 | FastAPI, PostgreSQL, pdfplumber | Core ledger, PDF ingestion, wealth tracking |
| spendsy-ai (TORA) | 8004 | FastAPI, Gemini 1.5 Pro, Ollama | AI agent — 4-stage entity resolver + Obsidian vault memory |
| spendsy-mcp | 8006 | Python MCP server | Claude Desktop financial tools |
| PostgreSQL 15 | 5433 (host) | via PgBouncer | Primary DB — two schemas: `auth_user`, `finance_transaction`, `finance_wealth` |
| Redis | — | — | Session store + JWT revocation |

TORA resolver chain: **Exact → Synonym → Fuzzy → Fallback** (98.3% recall).
PDF deduplication: SHA-256 of `{user, date, amount, title}`.
All financial math uses Python `Decimal` — never float.

---

## Dev Workflow

### Start (Windows — recommended)
```powershell
.\run-local.ps1   # frontend on Vite :5173 + all backend in Docker
```

Pure Docker:
```powershell
.\run.ps1
```

### Prerequisites
- Docker Desktop, Python 3.11+, Node 18+, Ollama (for TORA local reasoning)
- Pull Ollama model: `ollama pull gemma:7b`
- Copy env: `cp .env.example .env`

### Frontend
```bash
cd frontend && npm install && npm run dev
```

### Backend (per service)
```bash
python -m venv venv && pip install -r requirements.txt
pytest   # from root or inside backend/
```

### DB Migrations
```bash
# inside backend/finance-service or backend/auth-service
alembic upgrade head
```

---

## Key Conventions

- **Retries**: use `tenacity` for all inter-service HTTP calls.
- **DB safety**: wrap commits in `try/except` with `db.rollback()`.
- **Financials**: always `Decimal`, never `float`.
- **Frontend API calls**: use the `apiFetch` wrapper, not raw fetch.
- **Components**: functional only, no class components.
- **Style**: PEP 8 + type hints + Pydantic schemas on backend; Tailwind on frontend.
- **PRs**: branch from `main`, single focused change, all tests green.

---

## MCP Server (Claude Desktop)

Config location: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "spendsy": {
      "command": "python",
      "args": ["d:/Projects/Spendsy/backend/spendsy-mcp/server.py"],
      "env": {
        "FINANCE_SERVICE_URL": "http://localhost:8002",
        "INTERNAL_API_KEY": "internal-dev-key"
      }
    }
  }
}
```

Restart Claude Desktop after editing. Look for 🔌 icon to confirm tools are active.

---

## Graphify (Codebase Navigation)

Knowledge graph lives in `graphify-out/`.

- Architecture/cross-module questions → read `graphify-out/GRAPH_REPORT.md` first.
- If `graphify-out/wiki/index.md` exists, navigate it instead of raw files.
- If MCP server active: use `query_graph`, `get_node`, `shortest_path` tools.
- If not: `graphify query "<question>"` · `graphify path "<A>" "<B>"` · `graphify explain "<concept>"`
- After modifying code: `graphify update .` to keep graph current (no API cost).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Port conflict | Free up 8080 (Gateway) and 5432 (DB) |
| Missing DB schema | `alembic upgrade head` in `backend/finance-service` |
| TORA unresponsive | Check `OLLAMA_BASE_URL` in `.env`; verify `ollama serve` is running |
| CDP/browser tools | `docker compose --profile cdp up` (opt-in, exposes :9222) |

---

## Caveman Ecosystem (installed)

| Repo | What |
|---|---|
| [caveman](https://github.com/JuliusBrussee/caveman) | Output compression — ~75% fewer tokens |
| [cavemem](https://github.com/JuliusBrussee/cavemem) | Cross-session memory (SQLite + MCP) |
| [cavekit](https://github.com/JuliusBrussee/cavekit) | Spec-driven autonomous build loop |
