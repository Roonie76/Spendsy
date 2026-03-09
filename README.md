# Spendsy: Modern Fintech Microservices Platform

![Spendsy Banner](https://img.shields.io/badge/Status-Active-brightgreen)
![Tech Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20React%20%7C%20PostgreSQL%20%7C%20Redis-blue)
![License](https://img.shields.io/badge/License-MIT-orange)

Spendsy is a high-performance, open-source fintech platform designed for personal wealth management and transaction analysis. It leverages a microservices architecture to provide a secure, scalable, and responsive user experience.

## ✨ Key Features

- **Microservices Architecture**: Decoupled services for Auth, Finance, PDF Parsing, and AI.
- **Secure Authentication**: HttpOnly cookie-based JWT authentication with rate-limiting and persistence via Redis.
- **Financial Intelligence**: Detailed transaction tracking, wealth management, and category-based analysis.
- **AI Copilot**: Integrated AI to provide insights and answer queries about your financial data.
- **Automated Statement Parsing**: Upload bank statements (PDFs) to automatically import transactions.
- **Production-Grade Reliability**: Observability, structured logging, and robust error handling.

## 🏗️ Architecture

The platform is divided into several specialized services:

- **`auth-service`**: Handles user registration, login (JWT), and session management.
- **`finance-service`**: Core business logic for transactions, wealth tracking, and financial summaries.
- **`parser-service`**: PDF parsing engine that extracts structured data from bank statements.
- **`ai-service`**: LLM-integrated service providing financial advice and data analysis.
- **`frontend` (React)**: Modern, responsive dashboard built with Vite, Tailwind CSS, and Lucide icons.
- **`gateway` (Nginx)**: Centralized entry point for routing API requests.

For more details, see [ARCHITECTURE.md](./ARCHITECTURE.md).

## 🚀 Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose
- Node.js (for local frontend development)
- Python 3.11+ (for local service development)

### Quick Start with Docker

The easiest way to get the entire stack running is via Docker Compose:

```bash
# Clone the repository
git clone https://github.com/Roonie76/Spendsy.git
cd Spendsy

# Start all services
docker compose -f infra/docker/docker-compose.dev.yml up --build
```

The services will be available at:
- **Frontend**: `http://localhost:5173`
- **Gateway (API)**: `http://localhost:8080`
- **Auth Docs**: `http://localhost:8001/docs`
- **Finance Docs**: `http://localhost:8002/docs`

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React, Vite, Tailwind CSS, Lucide, Axios |
| **Backend** | Python, FastAPI, Pydantic, SQLAlchemy |
| **Databases** | PostgreSQL (Primary), Redis (Caching/Rate-limiting) |
| **Infrastructure** | Docker, Nginx, Alembic (Migrations) |
| **Testing** | Pytest, Vitest |

## 📂 Project Structure

```text
.
├── apps/web/frontend/      # React/Vite Frontend
├── smartspend/services/    # Microservices (Python/FastAPI)
│   ├── ai-service/         # NLP & LLM integration
│   ├── auth-service/       # Identity & Access Management
│   ├── finance-service/    # Core business logic
│   └── parser-service/     # Document extraction
├── infra/docker/           # Orchestration & Gateway config
└── packages/shared/        # Shared code/utilities
```

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for our code of conduct and the process for submitting pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
