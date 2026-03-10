#!/bin/bash

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
        cd "$PROJECT_ROOT/smartspend/services/$SERVICE"
        
        # Virtual Environment Management
        if [ ! -d "venv" ]; then
            echo "  Creating virtual environment for $SERVICE..."
            python3 -m venv venv
        fi
        
        source venv/bin/activate
        pip install -q -r requirements.txt
        
        # Local Development Environment Variables
        export DB_HOST=localhost
        export DB_PORT=5434
        export REDIS_URL=redis://localhost:6379/0
        export DB_NAME=smartspend
        export DB_USER=smartuser
        export DB_PASSWORD=smartpass
        export JWT_SECRET=dev-secret
        export INTERNAL_API_KEY=internal-dev-key
        
        # Internal Service Connectivity Overrides
        export PARSER_SERVICE_URL=http://localhost:8003
        export FINANCE_SERVICE_URL=http://localhost:8002
        
        # Run Service
        exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level warning
    ) &
done

# 3. Launch Frontend
echo "💻 Launching Frontend Developer Server..."
npm run web

# Keep script alive to maintain background processes
wait
