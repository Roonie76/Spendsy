# 💸 Spendsy: Modern Fintech Microservices Platform

![Spendsy Banner](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge&logo=github)
![Tech Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20React%20%7C%20PostgreSQL%20%7C%20Redis-blue?style=for-the-badge&logo=fastapi)
![License](https://img.shields.io/badge/License-MIT-orange?style=for-the-badge)

Spendsy is a high-performance, open-source fintech platform designed for personal wealth management and transaction analysis. It leverages a modern microservices architecture and AI-driven insights to help users master their financial health.

---

## ✨ Key Features

- **🛡️ Microservices Architecture**: Decoupled, high-performance services for Auth, Finance, Document Parsing, and AI.
- **🔒 Secure by Design**: HttpOnly cookie-based JWT authentication, robust rate-limiting, and IDOR prevention.
- **📊 Financial Intelligence**: Deep transaction tracking, wealth management, and category-based spend analysis.
- **🤖 AI-First Integration**:
    - **Finance Copilot**: Real-time insights and chat-based financial queries.
    - **Spendsy AI Agent**: An autonomous agent capable of complex financial reasoning and tool-calling.
    - **MCP Support**: Native [Model Context Protocol](https://modelcontextprotocol.io/) server to allow any AI (Claude, Gemini, etc.) to securely interact with your financial data.
- **📑 Automated Statement Parsing**: High-fidelity extraction of data from PDF bank statements.
- **🚀 Developer Experience**: Unified `requirements.txt`, Docker-first development, and a single `run-local.sh` for easy setup.

---

## 🏗️ Architecture

The Spendsy ecosystem is built on a resilient service-mesh architecture:

### 🧩 Core Services
- **`auth-service`**: (Port 8001) Identity & Access Management using FastAPI and Redis.
- **`finance-service`**: (Port 8002) Core financial ledger, wealth tracking, and transaction management.
- **`parser-service`**: (Port 8003) Document extraction engine for bank statements.
- **`ai-service`**: (Port 8004) NLP & LLM orchestration for chat-based insights.

### 🔬 Advanced Components
- **`spendsy-mcp`**: A specialized server implementing the Model Context Protocol, enabling AI-to-Service communication.
- **`spendsy-ai`**: A standalone AI reasoning engine/agent powered by modern LLMs.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, Vite, Tailwind CSS, Lucide, Axios |
| **Backend** | Python 3.11+, FastAPI, Pydantic, SQLAlchemy 2.0 |
| **Databases** | PostgreSQL (Persistence), Redis (Caching/Rate-limiting) |
| **Infrastructure** | Docker & Docker Compose, Nginx (Gateway), Alembic |
| **Testing** | Pytest, Vitest |
| **AI/LLM** | Google Gemini (GenAI), MCP Protocol |

---

## 🚀 Getting Started

### 📋 Prerequisites
- [Docker](https://www.docker.com/) and Docker Compose
- Node.js (v18+) & Python (v3.11+)

### ⚡ Quick Start
The simplest way to spin up the entire ecosystem is using the included orchestration script:

```bash
# Clone the repository
git clone https://github.com/Roonie76/Spendsy.git
cd Spendsy

# Start all services (Infrastructure + Microservices + Frontend)
./run-local.sh
```

Alternatively, use Docker Compose directly:
```bash
docker compose -f infra/docker/docker-compose.dev.yml up --build
```

### 📍 Local Endpoints
- **Frontend Dashboard**: `http://localhost:5173`
- **Main API Gateway**: `http://localhost:8080`
- **Interactive API Docs (Auth)**: `http://localhost:8001/docs`
- **Interactive API Docs (Finance)**: `http://localhost:8002/docs`

---

## 📂 Project Organization

```text
.
├── apps/web/frontend/      # Modern React/Vite dashboard
├── spendsy/services/        # Python Microservices
│   ├── ai-service/          # LLM Orchestration
│   ├── auth-service/        # Identity Management
│   ├── finance-service/     # Core Business Logic
│   └── parser-service/      # Document Extraction
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
