cls#!/bin/bash

# run-local.sh - Unified Spendsy Local Development Manager
# Starts Infrastructure (Docker), Backend Services (Python), and Frontend (Vite)

PROJECT_ROOT=$(pwd)
SERVICES=("auth-service" "finance-service" "ai-service" "parser-service")
PORTS=(8001 8002 8004 8003)

echo "🚀 Starting Spendsy Local Environment..."

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Shutting down all services..."
    kill 0
    exit
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Start Infrastructure (Docker)
echo "📦 Starting Database and Redis via Docker..."

# Load root .env variables for startup if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "  Loading environment variables from .env..."
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

cd "$PROJECT_ROOT/infra/docker"
docker compose -f docker-compose.dev.yml up -d postgres redis
cd "$PROJECT_ROOT"

# 2. Launch Backend Services
echo "⏳ Waiting for Database..."
sleep 3

for i in "${!SERVICES[@]}"; do
    SERVICE=${SERVICES[$i]}
    PORT=${PORTS[$i]}
    
    echo "⚡ Launching $SERVICE on port $PORT..."
    
    (
        cd "$PROJECT_ROOT/spendsy/services/$SERVICE"
        
        # Use unified root virtual environment
        source "$PROJECT_ROOT/.venv/bin/activate"
        
        # Environment variables are already exported from the root .env
        
        # Run Service
        exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level warning
    ) &
done

# 3. Launch Frontend
echo "💻 Launching Frontend Developer Server..."
npm run web

# Keep script alive to maintain background processes
wait
