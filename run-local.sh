#!/bin/bash

set -e

# run-local.sh - Unified Spendsy Local Development Manager
# Starts Infrastructure (Docker), Backend Services (Python), and Frontend (Vite)

PROJECT_ROOT=$(cd "$(dirname "$0")" && pwd)
SERVICES_ROOT="$PROJECT_ROOT/spendsy/services"
SERVICES=("auth-service" "finance-service" "ai-service" "parser-service" "spendsy-ai")
PORTS=(8001 8002 8004 8003 8005)

if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    VENV_ROOT="$PROJECT_ROOT/.venv"
elif [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    VENV_ROOT="$PROJECT_ROOT/venv"
else
    echo "🔨 Creating virtualenv at $PROJECT_ROOT/venv..."
    python3 -m venv "$PROJECT_ROOT/venv"
    VENV_ROOT="$PROJECT_ROOT/venv"
fi

echo "🚀 Starting Spendsy Local Environment..."

# 0. Environment Setup
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "📄 Creating .env from .env.example..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
fi

# 1. Install Dependencies
echo "🐍 Installing Python dependencies..."
source "$VENV_ROOT/bin/activate"
pip install -r requirements.txt

echo "📦 Installing Node dependencies..."
npm install

# 2. Infrastructure Setup
echo "🐳 Pulling Docker images..."
cd "$PROJECT_ROOT/infra/docker"
docker compose -f docker-compose.dev.yml pull
cd "$PROJECT_ROOT"

echo "🤖 Pulling Ollama Model (deepseek-r1:1.5b)..."
ollama pull deepseek-r1:1.5b || echo "⚠️ Ollama not found or failed to pull model, skipping..."

# 3. Preflight: Kill any existing processes on the required ports
# Including Vite port 5173 to ensure full environment reset
ALL_PORTS=("${PORTS[@]}" 5173)

echo "🧹 Cleaning up existing service processes on ports: ${ALL_PORTS[*]}"
for PORT in "${ALL_PORTS[@]}"; do
    # Try to kill nicely, then forcefully if it doesn't die immediately
    fuser -k -TERM $PORT/tcp 2>/dev/null || true
done

# Wait for ports to be released by the OS
sleep 2

# Verify ports are actually free
for PORT in "${ALL_PORTS[@]}"; do
    if lsof -i :$PORT >/dev/null 2>&1; then
        echo "⚠️  Warning: Port $PORT is still in use. Attempting forceful kill..."
        fuser -k -9 $PORT/tcp 2>/dev/null || true
        sleep 1
    fi
done

# Cleanup function
CLEANING_UP=false
cleanup() {
    if [ "$CLEANING_UP" = true ]; then return; fi
    CLEANING_UP=true
    
    # Unset all traps immediately to prevent recursion
    trap - SIGINT SIGTERM EXIT
    
    echo ""
    echo "🛑 Shutting down all services..."
    
    # Kill background jobs started by this script
    # jobs -p lists only the PIDs of background jobs
    BGPIDS=$(jobs -p)
    if [ -n "$BGPIDS" ]; then
        kill $BGPIDS 2>/dev/null || true
    fi
    
    # Optional: kill 0 as a fallback, but jobs -p is safer
    # kill 0 2>/dev/null
    
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Start Infrastructure (Docker)
echo "📦 Starting Database and Redis via Docker..."

# Load root .env variables for startup if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "  Loading environment variables from .env..."
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

cd "$PROJECT_ROOT/infra/docker"
docker compose -f docker-compose.dev.yml up -d postgres redis
cd "$PROJECT_ROOT"

# 2. Launch Backend Services
echo "⏳ Waiting for Database..."
sleep 3

# 2. Run service migrations before starting the API processes.
for SERVICE in auth-service finance-service; do
    echo "🧱 Running migrations for $SERVICE..."
    (
        cd "$SERVICES_ROOT/$SERVICE"
        source "$VENV_ROOT/bin/activate"
        export PYTHONPATH="$(pwd):$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
        alembic upgrade head
    )
done

# 3. Launch Backend Services
for i in "${!SERVICES[@]}"; do
    SERVICE=${SERVICES[$i]}
    PORT=${PORTS[$i]}
    
    echo "⚡ Launching $SERVICE on port $PORT..."
    
    (
        # Handle services that are in spendsy/services/ and those at root (spendsy-ai)
        if [ -d "$SERVICES_ROOT/$SERVICE" ]; then
            cd "$SERVICES_ROOT/$SERVICE"
        else
            cd "$PROJECT_ROOT/$SERVICE"
        fi
        
        # Use unified root virtual environment
        source "$VENV_ROOT/bin/activate"
        export PYTHONPATH="$(pwd):$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
        
        # Environment variables are already exported from the root .env
        
        # Run Service
        if [ "$SERVICE" == "spendsy-ai" ]; then
            exec uvicorn main:app --host 0.0.0.0 --port $PORT --log-level warning
        else
            exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level warning
        fi
    ) &
done

# 4. Launch Frontend
echo "💻 Launching Frontend Developer Server..."
npm run web

# Keep script alive to maintain background processes
wait
