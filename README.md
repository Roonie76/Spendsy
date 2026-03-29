# 💸 Spendsy: Modern Fintech Microservices Platform

![Spendsy Banner](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge&logo=github)
![Tech Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20React%20%7C%20PostgreSQL%20%7C%20Redis-blue?style=for-the-badge&logo=fastapi)
![License](https://img.shields.io/badge/License-MIT-orange?style=for-the-badge)

Spendsy is a high-performance, open-source fintech platform designed for personal wealth management and transaction analysis. It leverages a modern microservices architecture and AI-driven insights to help users master their financial health.

---

## ✨ Key Features

- **🛡️ Microservices Architecture**: Decoupled, high-performance services for Auth, Finance, and AI.
- **🔒 Secure by Design**: HttpOnly cookie-based JWT authentication, robust rate-limiting, and IDOR prevention.
- **📊 Financial Intelligence**: Deep transaction tracking, wealth management, and category-based spend analysis.
- **💳 Bank Account Portal**: NEW dedicated management for debit and credit cards with automated limit tracking.
- **⚙️ Profile & Settings**: Comprehensive user management, personal info updates, and app preference controls.
- **🤖 AI-First Integration**:
    - **Finance Copilot**: Real-time insights and chat-based financial queries.
    - **Spendsy AI Agent**: An autonomous agent (Tora) for complex reasoning and tool-calling.
    - **MCP Support**: Native [Model Context Protocol](https://modelcontextprotocol.io/) server for external AI integration.
- **📑 Automated Statement Parsing**: High-fidelity deterministic extraction from digital PDF bank statements.
- **🚀 Developer Experience**: Docker-first development with the unified `run-local.sh` orchestrator.

---

## 🏗️ Architecture

The Spendsy ecosystem is built on a resilient service-mesh architecture:

### 🧩 Core Services
- **`auth-service`**: (Port 8001) Identity & Access Management using FastAPI and Redis.
- **`finance-service`**: (Port 8002) Core financial ledger, wealth tracking, and deterministic transaction parsing.
- **`ai-service`**: (Port 8004) NLP & LLM orchestration for chat-based insights.

### 🔬 Advanced Components
- **`spendsy-mcp`**: A specialized server implementing the Model Context Protocol, enabling AI-to-Service communication.
- **`spendsy-ai`**: A standalone AI reasoning engine/agent powered by modern LLMs.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, Vite, Tailwind CSS, Lucide |
| **Backend** | Python 3.11+, FastAPI, Pydantic, SQLAlchemy 2.0 |
| **Databases** | PostgreSQL, Redis, PgBouncer (Pooling) |
| **Infrastructure** | Docker & Docker Compose, Nginx (Gateway), Alembic |
| **Reliability** | Tenacity (Retries), Standardized Error Handlers |
| **AI/LLM** | Google Gemini (GenAI), MCP Protocol |

---

## 🚀 Getting Started

### 📋 Prerequisites
- [Docker Desktop](https://www.docker.com/) (must be running)
- Windows: PowerShell 5.1+

### ⚡ Quick Start (Windows)

```powershell
# 1. Clone the repository
git clone https://github.com/Roonie76/Spendsy.git
cd Spendsy

# 2. Create your environment file
cp .env.example .env

# 3. Start everything (one command!)
.\docker-run.ps1
```

That's it! Docker will build all images and start every service automatically.

### 📍 Local Endpoints
| Service | URL |
| :--- | :--- |
| **Frontend** | http://localhost:3000 |
| **API Gateway** | http://localhost:8080 |
| **Auth Service Docs** | http://localhost:8001/docs |
| **Finance Service Docs** | http://localhost:8002/docs |
| **AI Service Docs** | http://localhost:8004/docs |

---

## 📂 Project Organization

```text
.
├── apps/web/frontend/      # Modern React/Vite dashboard
├── spendsy/services/        # Python Microservices
│   ├── ai-service/          # LLM Orchestration
│   ├── auth-service/        # Identity Management
│   └── finance-service/     # Core Business Logic & Parsing
├── spendsy-mcp/             # Model Context Protocol Server
├── spendsy-ai/              # Standalone AI Agent
├── infra/docker/            # Orchestration & Gateway configurations
└── requirements.txt         # Unified project dependencies
```

---

## 🤝 Contributing

We love contributions! Whether it's adding a new service, fixing a bug, or improving the documentation.
1. Check out our [CONTRIBUTING.md](./CONTRIBUTING.md).
2. Look for "Good First Issues".
3. Join our developer discussions!

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*Built with ❤️ for financial freedom.*
