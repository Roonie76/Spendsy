# Contributing to Spendsy

Thank you for contributing! This document covers how to set up your environment, the development workflow, and our code standards.

---

## 🚀 Quick Start (Development Setup)

The easiest way to start Spendsy is using the provided orchestration scripts.

### 1. Prerequisites
- **Git**, **Docker Desktop**, and **Python 3.11+**.
- **Node.js v18+** (for frontend development).
- **Ollama** (required for local TORA reasoning).

### 2. Setup Commands

**Windows (PowerShell):**
```powershell
# Clone and configure
git clone https://github.com/Roonie76/Spendsy.git
cd Spendsy
cp .env.example .env

# Start everything (Frontend + Backend + DB)
.\run-local.ps1
```

**macOS/Linux (Bash):**
```bash
git clone https://github.com/Roonie76/Spendsy.git
cd Spendsy
cp .env.example .env

# Start everything
chmod +x run-local.sh
./run-local.sh
```

### 3. TORA Intelligence Setup
Ensure Ollama is running, then pull the required model:
```powershell
ollama pull gemma:7b
```

---

## 🛠️ Development Workflow

### Backend (Python)
- **Standard**: `python -m venv venv` -> `pip install -r requirements.txt`.
- **Testing**: Run `pytest` from the root or inside `backend/`.
- **Style**: Follow PEP 8. Use type hints and Pydantic schemas.

### Frontend (React)
- **Standard**: `cd frontend` -> `npm install` -> `npm run dev`.
- **Style**: Use functional components and the `apiFetch` wrapper.

---

## 📜 Contribution Rules

1. **Reporting Bugs**: Open an issue with clear reproduction steps and environment details.
2. **Pull Requests**:
    - Create a branch from `main`.
    - Keep PRs focused on a single change.
    - Ensure all tests pass.
3. **Reliability Guidelines**:
    - Use `tenacity` retries for all inter-service calls.
    - Wrap database commits in `try/except` with `db.rollback()`.
    - Use the `Decimal` type for all financial calculations.

---

## 🔧 Troubleshooting
- **Port Conflicts**: Ensure `8080` (Gateway) and `5432` (DB) are free.
- **Database**: If schema is missing, run `alembic upgrade head` in `backend/finance-service`.
- **Ollama**: If TORA is unresponsive, verify `OLLAMA_BASE_URL` in `.env`.

---
*By contributing, you agree that your work will be licensed under the MIT License.*
