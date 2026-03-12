# 📖 Spendsy Setup Guide & Instruction Manual

This manual provides step-by-step instructions to get the Spendsy microservices platform running on any laptop (Linux, macOS, or Windows with WSL2).

---

## 🛠️ 1. Prerequisites

Before you begin, ensure you have the following installed:

- **Git**: For version control.
- **Docker & Docker Compose**: To run the database, cache, and poolers.
- **Node.js (v18+)**: To run the frontend developer server.
- **Python (3.11+)**: To run the backend microservices.
- **Bash**: (Standard on Linux/macOS; use Git Bash or WSL2 on Windows).

---

## 🚀 2. Quick Start (Recommended)

The easiest way to start Spendsy is using the provided orchestration script.

### Step A: Clone the Repository
```bash
git clone https://github.com/Roonie76/Spendsy.git
cd Spendsy
```

### Step B: Configure Environment
Copy the example environment file and customize it if necessary.
```bash
cp .env.example .env
```
> [!NOTE]
> The default values in `.env.example` are pre-configured to work with the `run-local.sh` script.

### Step C: Initialize Python Environment
Create a virtual environment and load all dependencies.
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step D: Launch!
Run the master script to spin up Docker infrastructure, backend services, and the frontend.
```bash
chmod +x run-local.sh
./run-local.sh
```

---

## 🏗️ 3. Execution Methods

### Method 1: Hybrid Development (run-local.sh)
- **Infra**: Runs PostgreSQL, Redis, and PgBouncer in Docker.
- **Backend**: Runs Python services natively on your host for faster debugging.
- **Frontend**: Runs Vite dev server natively.
- **Best for**: Active development and debugging.

### Method 2: Pure Docker Deployment
If you don't want to install Node or Python locally, you can run everything in containers.
```bash
docker compose -f infra/docker/docker-compose.dev.yml up --build
```
- **Access**:
    - **Dashboard**: `http://localhost:5173`
    - **Gateway**: `http://localhost:8080`

---

## 📍 4. Accessing the System

Once services are running, you can access the following:

| Component | URL |
| :--- | :--- |
| **Frontend UI** | `http://localhost:5173` |
| **API Gateway** | `http://localhost:8080` |
| **Auth Service Docs** | `http://localhost:8001/docs` |
| **Finance Service Docs** | `http://localhost:8002/docs` |
| **AI Service Docs** | `http://localhost:8004/docs` |

---

## 🔧 5. Troubleshooting

### Port Conflicts
If you get a "Port already in use" error, check if another service is running on:
- `5173` (Frontend)
- `8080` (Gateway)
- `5434` (PostgreSQL Host Port)
- `6432` (PgBouncer)

### Database Migrations
If the database schema is empty, run migrations manually:
```bash
cd spendsy/services/finance-service
alembic upgrade head
```

### Docker Logs
To check the health of the infrastructure:
```bash
docker compose -f infra/docker/docker-compose.dev.yml logs -f
```

---

*Built for speed, reliability, and financial intelligence.*
