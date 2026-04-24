# CODEX: Instructions for GPT-based Assistants

This file provides context for **GPT-4 / Codex** based assistants when interacting with the Spendsy platform.

## 🏗️ Architecture Awareness
- **Pattern**: Microservices orchestrated via Nginx.
- **Service Mesh**: Services communicate via internal Docker network or `localhost` (Port 8080 gateway).
- **Contracts**: Strictly adhere to Pydantic v2 schemas in `app/schemas.py`.

## 📜 Coding Patterns
- **Database**: Use SQLAlchemy 2.0 Async sessions.
- **Parsing**: Transaction parsing must remain **deterministic** (regex/coordinate-based), NOT probabilistic (LLM-based), to ensure financial accuracy.
- **Frontend**: React 19 + Vite. Use TanStack Query for state and Framer Motion for premium animations.

## 📍 Key Entry Points
- **Auth**: `backend/auth-service/app/main.py`
- **Finance**: `backend/finance-service/app/main.py`
- **AI Agent**: `backend/spendsy-ai/agents/tora_agent.py`

## 🧠 Reasoning Focus
- **Tax Laws**: Refer to `shared/config/constants.js` for 2024 Indian Tax slabs.
- **TORA Logic**: When implementing new features, ensure they hook into the **Obsidian Vault** persistence layer to preserve user context.

---
*Optimized for GPT-4o / Codex.*
