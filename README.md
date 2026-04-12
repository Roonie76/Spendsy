# Spendsy: Modern Fintech Microservices Platform

![Spendsy Banner](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge&logo=github)
![Tech Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20React%20%7C%20PostgreSQL%20%7C%20Redis-blue?style=for-the-badge&logo=fastapi)
![License](https://img.shields.io/badge/License-MIT-orange?style=for-the-badge)

Spendsy is a high-performance, open-source fintech platform designed for personal wealth management and transaction analysis. It leverages a modern microservices architecture and AI-driven insights to help users master their financial health.

---

## How to Run

### Starting the Project

1. **Ensure Docker Desktop is running** on your Windows machine.

2. **Navigate to the project root**:
```powershell
cd d:\Projects\Spendsy
```

3. **Run the orchestration script**:
```powershell
.\run.ps1
```

This will:
- Build all Docker images for frontend, backend services, and databases
- Start PostgreSQL, Redis, and PgBouncer
- Launch auth-service, finance-service, ai-service, and frontend
- Configure Nginx as the API gateway

### Verifying Services are Running

Once the script completes, verify all services are healthy:

```powershell
# Check Docker containers
docker ps

# Expected output should show 7+ containers running:
# - spendsy_frontend
# - spendsy_auth_service
# - spendsy_finance_service
# - spendsy_ai_service
# - spendsy_postgres
# - spendsy_redis
# - spendsy_nginx
```

Access the frontend at http://localhost:3000 to verify the UI loads.

### Viewing Logs

```powershell
# View logs from all running containers
docker-compose logs -f

# View logs from a specific service
docker-compose logs -f auth-service
docker-compose logs -f finance-service
docker-compose logs -f ai-service

# View last 50 lines of a service
docker-compose logs --tail=50 finance-service
```

### Stopping the Project

```powershell
# Stop all services gracefully
docker-compose down

# Stop and remove all volumes (WARNING: deletes data)
docker-compose down -v
```
---

## Key Features

- **Microservices Architecture**: Decoupled, high-performance services for Auth, Finance, and AI.
- **Secure by Design**: HttpOnly cookie-based JWT authentication, robust rate-limiting, and IDOR prevention.
- **Financial Intelligence**: Deep transaction tracking, wealth management, and category-based spend analysis.
- **Bank Account Portal**: Dedicated management for debit and credit cards with automated limit tracking.
- **Profile & Settings**: Comprehensive user management, personal info updates, and app preference controls.
- **AI-First Integration**:
    - **Finance Copilot**: Real-time insights and chat-based financial queries.
    - **Spendsy AI Agent**: An autonomous agent (Tora) for complex reasoning and tool-calling.
    - **MCP Support**: Native [Model Context Protocol](https://modelcontextprotocol.io/) server for external AI integration.
- **Automated Statement Parsing**: High-fidelity deterministic extraction from digital PDF bank statements.
- **Developer Experience**: Docker-first development with unified orchestration via `run.ps1`.

---

## Architecture

The Spendsy ecosystem is built on a resilient service-mesh architecture:

### Core Services
- **auth-service** (Port 8001): Identity & Access Management using FastAPI and Redis.
- **finance-service** (Port 8002): Core financial ledger, wealth tracking, and deterministic transaction parsing.
- **ai-service** (Port 8004): NLP & LLM orchestration for chat-based insights.

### Advanced Components
- **spendsy-mcp**: A specialized server implementing the Model Context Protocol, enabling AI-to-Service communication.
- **spendsy-ai**: A standalone AI reasoning engine/agent powered by modern LLMs.

---

## Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, Vite, Tailwind CSS, Lucide |
| **Backend** | Python 3.11+, FastAPI, Pydantic, SQLAlchemy 2.0 |
| **Databases** | PostgreSQL, Redis, PgBouncer (Pooling) |
| **Infrastructure** | Docker & Docker Compose, Nginx (Gateway), Alembic |
| **Reliability** | Tenacity (Retries), Standardized Error Handlers |
| **AI/LLM** | Google Gemini (GenAI), MCP Protocol |

---

## Getting Started

### Prerequisites
- [Docker Desktop](https://www.docker.com/) (must be running)
- Windows: PowerShell 5.1+

### Quick Start (Windows)

```powershell
# 1. Clone the repository
git clone https://github.com/Roonie76/Spendsy.git
cd Spendsy

# 2. Create your environment file
cp .env.example .env

# 3. Start everything (one command!)
.\run.ps1
```

That's it! Docker will build all images and start every service automatically.

### Local Endpoints
| Service | URL |
| :--- | :--- |
| **Frontend** | http://localhost:3000 |
| **API Gateway** | http://localhost:8080 |
| **Auth Service Docs** | http://localhost:8001/docs |
| **Finance Service Docs** | http://localhost:8002/docs |
| **AI Service Docs** | http://localhost:8004/docs |

---

### Environment Configuration

The project uses a `.env` file for configuration. Create or update `.env` in the project root:

```env
# Database Configuration
DATABASE_URL=postgresql://user:password@postgres:5432/spendsy
REDIS_URL=redis://redis:6379
DEBUG=False

# Auth Service
AUTH_SERVICE_SECRET_KEY=your_secret_key_here
AUTH_SERVICE_ALGORITHM=HS256

# AI Service
GEMINI_API_KEY=your_gemini_api_key
MISTRAL_API_KEY=your_mistral_api_key

# Frontend
VITE_API_URL=http://localhost:8080
```

### Common Issues & Troubleshooting

**Issue: Port already in use**
```powershell
# Find process using port (e.g., 3000)
netstat -ano | findstr :3000

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

**Issue: Docker containers won't start**
```powershell
# Clean rebuild
docker-compose down -v
docker-compose build --no-cache
.\run.ps1
```

**Issue: Database connection errors**
```powershell
# Check PostgreSQL is running
docker exec spendsy_postgres psql -U postgres -c "SELECT 1;"

# View database logs
docker-compose logs postgres
```

**Issue: Services can't communicate**
- Ensure all containers are on the same Docker network (internal network created by docker-compose)
- Check service names in `.env` match container names

### Development Workflow

For active development, you can run services individually:

```powershell
# Start only database and cache
docker-compose up postgres redis

# In another terminal, run backend service locally
cd backend/finance-service
pip install -r requirements.txt
python -m app.main

# In another terminal, run frontend locally
cd frontend
npm install
npm run dev
```

---

## Project Organization

```text
.
├── frontend/                # Modern React/Vite dashboard
├── backend/                 # Python Microservices
│   ├── ai-service/          # LLM Orchestration
│   ├── auth-service/        # Identity Management
│   ├── finance-service/     # Core Business Logic & Parsing
│   ├── spendsy-mcp/         # Model Context Protocol Server
│   └── spendsy-ai/          # Standalone AI Agent
├── infra/docker/            # Orchestration & Gateway configurations
├── docs/                    # Documentation
├── tests/                   # Integration tests
└── requirements.txt         # Unified project dependencies
```

---

## Contributing

We love contributions! Whether it's adding a new service, fixing a bug, or improving the documentation.
1. Check out our [CONTRIBUTING.md](./CONTRIBUTING.md).
2. Look for "Good First Issues".
3. Join our developer discussions!

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
Built with determination for financial freedom.
