# run-local.ps1 - Spendsy Local Development Manager (Windows / PowerShell)
# Starts Infrastructure (Docker), Backend Services (Python), and Frontend (Vite)
#
# REQUIREMENTS:
#   - Docker Desktop (running)
#   - Python 3.10+ on PATH
#   - Node.js 18+ on PATH
#   - PowerShell 5.1+  (comes with Windows 10/11)
#
# USAGE (from project root):
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned   # one-time
#   .\run-local.ps1

$ErrorActionPreference = "Stop"

# ── Paths ────────────────────────────────────────────────────────────────────
$PROJECT_ROOT   = Split-Path -Parent $MyInvocation.MyCommand.Path
$SERVICES_ROOT  = Join-Path $PROJECT_ROOT "spendsy\services"

$SERVICES = @("auth-service","finance-service","ai-service","spendsy-ai","spendsy-mcp")
$PORTS    = @(8001, 8002, 8004, 8005, 8006)
$ALL_PORTS = $PORTS + 5173

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Spendsy Local Environment - Windows (PowerShell)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ── Virtual Environment ──────────────────────────────────────────────────────
if (Test-Path "$PROJECT_ROOT\.venv\Scripts\Activate.ps1") {
    $VENV_ROOT = "$PROJECT_ROOT\.venv"
} elseif (Test-Path "$PROJECT_ROOT\venv\Scripts\Activate.ps1") {
    $VENV_ROOT = "$PROJECT_ROOT\venv"
} else {
    Write-Host "Creating virtualenv at $PROJECT_ROOT\venv..." -ForegroundColor Yellow
    python -m venv "$PROJECT_ROOT\venv"
    $VENV_ROOT = "$PROJECT_ROOT\venv"
}

# ── .env Setup ───────────────────────────────────────────────────────────────
if (-not (Test-Path "$PROJECT_ROOT\.env")) {
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item "$PROJECT_ROOT\.env.example" "$PROJECT_ROOT\.env"
}

# Load .env into current session (skip comments and blank lines)
Write-Host "Loading environment variables from .env..." -ForegroundColor DarkGray
Get-Content "$PROJECT_ROOT\.env" | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#")) {
        $parts = $line -split "=", 2
        if ($parts.Length -eq 2) {
            $key   = $parts[0].Trim()
            $value = $parts[1].Trim().Trim('"')
            [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

# Map POSTGRES_* → DB_* which the backend services expect
$env:DB_HOST     = "localhost"
$env:DB_PORT     = "5434"           # host-side port Docker maps to Postgres
$env:DB_NAME     = $env:POSTGRES_DB       ?? "spendsy"
$env:DB_USER     = $env:POSTGRES_USER     ?? "smartuser"
$env:DB_PASSWORD = $env:POSTGRES_PASSWORD ?? "smartpass"

# ── Install Dependencies ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "[1/5] Installing Python dependencies..." -ForegroundColor Green
& "$VENV_ROOT\Scripts\pip.exe" install -r "$PROJECT_ROOT\requirements.txt" -q
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

Write-Host "[2/5] Installing Node dependencies..." -ForegroundColor Green
Set-Location $PROJECT_ROOT
npm install --silent
if ($LASTEXITCODE -ne 0) { throw "npm install failed" }

# ── Kill Existing Processes on Required Ports ────────────────────────────────
Write-Host "[3/5] Clearing ports: $($ALL_PORTS -join ', ')..." -ForegroundColor Green
foreach ($port in $ALL_PORTS) {
    $connections = netstat -ano | Select-String ":$port\s.*LISTENING"
    foreach ($conn in $connections) {
        $pid = ($conn -split "\s+")[-1]
        if ($pid -match "^\d+$" -and $pid -ne "0") {
            try {
                Stop-Process -Id ([int]$pid) -Force -ErrorAction SilentlyContinue
                Write-Host "  Killed PID $pid on port $port" -ForegroundColor DarkGray
            } catch {}
        }
    }
}
Start-Sleep -Seconds 2

# ── Docker Infrastructure ────────────────────────────────────────────────────
Write-Host "[4/5] Starting Docker (Postgres + Redis)..." -ForegroundColor Green
Set-Location "$PROJECT_ROOT\infra\docker"
docker compose -f docker-compose.dev.yml up -d postgres redis
if ($LASTEXITCODE -ne 0) { throw "Docker failed to start. Is Docker Desktop running?" }
Set-Location $PROJECT_ROOT

Write-Host "  Waiting for database to be ready..." -ForegroundColor DarkGray
Start-Sleep -Seconds 5

# ── Alembic Migrations ───────────────────────────────────────────────────────
Write-Host "[5/5] Running database migrations..." -ForegroundColor Green
$DATABASE_URL = "postgresql://$($env:DB_USER):$($env:DB_PASSWORD)@$($env:DB_HOST):$($env:DB_PORT)/$($env:DB_NAME)"

foreach ($svc in @("auth-service","finance-service")) {
    $svcPath = Join-Path $SERVICES_ROOT $svc
    Write-Host "  Migrating $svc..." -ForegroundColor DarkGray
    Push-Location $svcPath
    $env:DATABASE_URL = $DATABASE_URL
    $env:PYTHONPATH   = "$svcPath;$PROJECT_ROOT"
    & "$VENV_ROOT\Scripts\alembic.exe" upgrade head
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  WARNING: Migration failed for $svc" -ForegroundColor Yellow
    }
    Pop-Location
}

# ── Helper: Launch a service in a new terminal window ────────────────────────
function Start-Service {
    param(
        [string]$Title,
        [string]$WorkDir,
        [string]$Command
    )
    $activate = "$VENV_ROOT\Scripts\activate.bat"
    $fullCmd  = "title $Title && cd /d `"$WorkDir`" && call `"$activate`" && $Command"
    Start-Process "cmd.exe" -ArgumentList "/k", $fullCmd -WindowStyle Normal
}

# ── Launch Backend Services ──────────────────────────────────────────────────
Write-Host ""
Write-Host "Starting backend services..." -ForegroundColor Cyan

# auth-service (8001)
Start-Service "auth-service [8001]" "$SERVICES_ROOT\auth-service" `
    "set PYTHONPATH=$SERVICES_ROOT\auth-service;$PROJECT_ROOT && uvicorn app.main:app --host 0.0.0.0 --port 8001 --log-level warning --reload"

# finance-service (8002)
Start-Service "finance-service [8002]" "$SERVICES_ROOT\finance-service" `
    "set PYTHONPATH=$SERVICES_ROOT\finance-service;$PROJECT_ROOT && uvicorn app.main:app --host 0.0.0.0 --port 8002 --log-level warning --reload"

# ai-service (8004) — only launch if the folder exists
if (Test-Path "$SERVICES_ROOT\ai-service") {
    Start-Service "ai-service [8004]" "$SERVICES_ROOT\ai-service" `
        "set PYTHONPATH=$SERVICES_ROOT\ai-service;$PROJECT_ROOT && uvicorn app.main:app --host 0.0.0.0 --port 8004 --log-level warning --reload"
}

# spendsy-ai (8005)
if (Test-Path "$PROJECT_ROOT\spendsy-ai") {
    Start-Service "spendsy-ai [8005]" "$PROJECT_ROOT\spendsy-ai" `
        "set PYTHONPATH=$PROJECT_ROOT\spendsy-ai;$PROJECT_ROOT && set FINANCE_SERVICE_URL=http://127.0.0.1:8002 && uvicorn main:app --host 0.0.0.0 --port 8005 --log-level warning --reload"
}

# spendsy-mcp (stdio server)
if (Test-Path "$PROJECT_ROOT\spendsy-mcp") {
    Start-Service "spendsy-mcp [8006]" "$PROJECT_ROOT\spendsy-mcp" `
        "set PYTHONPATH=$PROJECT_ROOT\spendsy-mcp;$PROJECT_ROOT && python server.py"
}

# Short delay before frontend
Start-Sleep -Seconds 3

# ── Frontend ─────────────────────────────────────────────────────────────────
Write-Host "Starting frontend (Vite)..." -ForegroundColor Cyan
Start-Process "cmd.exe" -ArgumentList "/k", "title frontend [5173] && cd /d `"$PROJECT_ROOT`" && npm run web" -WindowStyle Normal

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  All services launched in separate windows!" -ForegroundColor Green
Write-Host ""
Write-Host "  Auth Service:    http://localhost:8001" -ForegroundColor White
Write-Host "  Finance Service: http://localhost:8002" -ForegroundColor White
Write-Host "  AI Service:      http://localhost:8004" -ForegroundColor White
Write-Host "  Spendsy AI:      http://localhost:8005" -ForegroundColor White
Write-Host "  MCP Server:      (stdio - see spendsy-mcp window)" -ForegroundColor White
Write-Host "  Frontend:        http://localhost:5173" -ForegroundColor White
Write-Host ""
Write-Host "  Close individual service windows to stop each service." -ForegroundColor DarkGray
Write-Host "  To stop Docker: docker compose -f infra\docker\docker-compose.dev.yml down" -ForegroundColor DarkGray
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Read-Host "Press Enter to exit this launcher..."
