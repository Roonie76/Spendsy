# run.ps1 - Spendsy Docker Launcher
# Builds and runs the entire stack in Docker containers.
#
# REQUIREMENTS: Docker Desktop (running)
#
# USAGE:
#   .\run.ps1           # Start all services
#   .\run.ps1 down      # Stop and remove all containers
#   .\run.ps1 logs      # Tail logs from all services
#   .\run.ps1 status    # Check service health
#   .\run.ps1 rebuild   # Force rebuild all images and restart

$ErrorActionPreference = "Stop"

$PROJECT_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$COMPOSE_FILE = Join-Path $PROJECT_ROOT "infra\docker\docker-compose.dev.yml"
$ACTION = if ($args.Count -gt 0) { $args[0] } else { "up" }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Spendsy - Docker Launcher" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ── Check Docker ────────────────────────────────────────────────────────────
docker version >$null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running. Start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

# ── .env Setup ──────────────────────────────────────────────────────────────
if (-not (Test-Path "$PROJECT_ROOT\.env")) {
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item "$PROJECT_ROOT\.env.example" "$PROJECT_ROOT\.env"
}

# ── Actions ─────────────────────────────────────────────────────────────────
switch ($ACTION) {
    "down" {
        Write-Host "Stopping all containers..." -ForegroundColor Yellow
        docker compose -f $COMPOSE_FILE down
        Write-Host "All containers stopped." -ForegroundColor Green
    }

    "logs" {
        docker compose -f $COMPOSE_FILE logs -f --tail 50
    }

    "status" {
        Write-Host "--- Container Status ---" -ForegroundColor Cyan
        docker compose -f $COMPOSE_FILE ps
        Write-Host ""
        Write-Host "--- Service Health ---" -ForegroundColor Cyan
        $services = [ordered]@{
            "Auth Service"    = "http://localhost:8001/health"
            "Finance Service" = "http://localhost:8002/health"
            "AI Service"      = "http://localhost:8004/health"
            "Gateway"         = "http://localhost:8080"
            "Frontend"        = "http://localhost:3000"
        }
        foreach ($item in $services.GetEnumerator()) {
            try {
                Invoke-WebRequest -Uri $item.Value -Method Get -TimeoutSec 3 -ErrorAction Stop >$null
                Write-Host "  $($item.Key): ONLINE" -ForegroundColor Green
            } catch {
                Write-Host "  $($item.Key): OFFLINE" -ForegroundColor Red
            }
        }
    }

    "rebuild" {
        Write-Host "Rebuilding all images and restarting..." -ForegroundColor Yellow
        docker compose -f $COMPOSE_FILE up --build -d
        if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed." }
        Write-Host ""
        Write-Host "Rebuild complete!" -ForegroundColor Green
    }

    default {
        # ── Start everything ────────────────────────────────────────────
        Write-Host "Building and starting all services..." -ForegroundColor Green
        docker compose -f $COMPOSE_FILE up --build -d
        if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed. Is Docker Desktop running?" }

        Write-Host ""
        Write-Host "============================================================" -ForegroundColor Cyan
        Write-Host "  Spendsy is running!" -ForegroundColor Green
        Write-Host ""
        Write-Host "  Frontend:        http://localhost:3000" -ForegroundColor White
        Write-Host "  Gateway:         http://localhost:8080" -ForegroundColor White
        Write-Host ""
        Write-Host "  Auth Service:    http://localhost:8001" -ForegroundColor DarkGray
        Write-Host "  Finance Service: http://localhost:8002" -ForegroundColor DarkGray
        Write-Host "  AI Service:      http://localhost:8004" -ForegroundColor DarkGray
        Write-Host "  PostgreSQL:      localhost:5434" -ForegroundColor DarkGray
        Write-Host "  Redis:           localhost:6379" -ForegroundColor DarkGray
        Write-Host ""
        Write-Host "  .\run.ps1 status   - Check service health" -ForegroundColor DarkGray
        Write-Host "  .\run.ps1 logs     - Tail all logs" -ForegroundColor DarkGray
        Write-Host "  .\run.ps1 down     - Stop everything" -ForegroundColor DarkGray
        Write-Host "  .\run.ps1 rebuild  - Force rebuild" -ForegroundColor DarkGray
        Write-Host "============================================================" -ForegroundColor Cyan
        Write-Host ""
    }
}
