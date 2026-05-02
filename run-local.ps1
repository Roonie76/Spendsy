# Spendsy Local Development Runner
# This script orchestrates the Spendsy platform (Docker backend + local Vite frontend).
#
# USAGE:
#   .\run-local.ps1                     # Full start (build + pull + npm install)
#   .\run-local.ps1 -NoBuild            # Skip Docker image rebuilds
#   .\run-local.ps1 -SkipDockerPull     # Skip pulling remote images
#   .\run-local.ps1 -SkipNodeInstall    # Skip npm install
#   .\run-local.ps1 -NoBuild -SkipDockerPull -SkipNodeInstall  # Fastest restart

param(
    [switch]$SkipNodeInstall,
    [switch]$SkipDockerPull,
    [switch]$NoBuild
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$PROJECT_ROOT = $PSScriptRoot
$DOCKER_DIR = Join-Path $PROJECT_ROOT "infra\docker"
$COMPOSE_FILE = Join-Path $DOCKER_DIR "docker-compose.dev.yml"
$BackendServices = @("postgres", "redis", "auth-service", "finance-service", "ai-service", "spendsy-ai", "spendsy-mcp", "obscura", "nginx")
$ManagedPorts = @(5173, 8080)

function Write-Step($Message) {
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Write-Status($Message, $Color = "White") {
    Write-Host "  $Message" -ForegroundColor $Color
}

function Check-Docker {
    try {
        docker info > $null 2>&1
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Stop-PortProcesses($Ports) {
    $currentPid = $PID  # capture PowerShell's auto-variable before the loop
    foreach ($port in $Ports) {
        try {
            $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
            if ($connections) {
                Write-Status "Stopping processes on port $port : $connections" -Color Yellow
                foreach ($owningPid in $connections) {
                    if ($owningPid -gt 0 -and $owningPid -ne $currentPid) {
                        $proc = Get-Process -Id $owningPid -ErrorAction SilentlyContinue
                        if ($proc -and $proc.ProcessName -notmatch "com.docker|Docker") {
                            Stop-Process -Id $owningPid -Force -ErrorAction SilentlyContinue
                        } else {
                            Write-Status "Skipping Docker infrastructure process (PID $owningPid) on port $port" -Color Gray
                        }
                    }
                }
            }
        } catch {
            # Ignore errors during port cleanup
        }
    }
}

# 1. Pre-flight & Port Cleanup
Write-Step "System Pre-flight"

if (-not (Check-Docker)) {
    Write-Host "ERROR: Docker Desktop is not running or not in PATH." -ForegroundColor Red
    Write-Host "Please start Docker and try again." -ForegroundColor Yellow
    exit 1
}
Write-Status "Docker daemon is running" -Color Green

Write-Status "Freeing network ports ($($ManagedPorts -join ', '))..." -Color Gray
Stop-PortProcesses $ManagedPorts

if (-not (Test-Path (Join-Path $PROJECT_ROOT ".env"))) {
    Write-Status "Creating .env from .env.example" -Color Yellow
    if (Test-Path (Join-Path $PROJECT_ROOT ".env.example")) {
        Copy-Item (Join-Path $PROJECT_ROOT ".env.example") (Join-Path $PROJECT_ROOT ".env")
    } else {
        Write-Status "WARNING: .env.example not found. Please create a .env file manually." -Color Red
    }
}

# 2. Dependency Check
if (-not $SkipNodeInstall) {
    Write-Step "Syncing Frontend Dependencies"
    npm install
}

if (-not $SkipDockerPull) {
    Write-Step "Syncing Docker Images"
    try {
        docker compose -f $COMPOSE_FILE pull
    } catch {
        Write-Status "WARNING: Docker pull failed. Using local images if available." -Color Yellow
    }
}

# 3. Backend Orchestration
Write-Step "Launching Backend Services"
if ($NoBuild) {
    docker compose -f $COMPOSE_FILE up -d $BackendServices
} else {
    docker compose -f $COMPOSE_FILE up -d --build $BackendServices
}
Write-Status "Containers started" -Color Green

# 4. Wait for critical services to be healthy
Write-Step "Waiting for Services"
$healthChecks = @(
    @{ Name = "PostgreSQL"; Container = "spendsy_postgres" },
    @{ Name = "Redis";      Container = "spendsy_redis" }
)
foreach ($svc in $healthChecks) {
    Write-Status "Waiting for $($svc.Name)..." -Color Gray
    $healthy = $false
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $status = docker inspect --format '{{.State.Health.Status}}' $svc.Container 2>$null
            if ($status -eq "healthy") {
                Write-Status "$($svc.Name) is healthy" -Color Green
                $healthy = $true
                break
            }
        } catch {
            Write-Status "Waiting for Docker API to respond..." -Color Gray
        }
        Start-Sleep -Seconds 1
    }
    if (-not $healthy) {
        Write-Status "WARNING: $($svc.Name) not healthy after 30s - continuing anyway" -Color Yellow
    }
}

# Quick pause for app services to finish startup (alembic migrations etc.)
Write-Status "Giving app services 5s to run migrations..." -Color Gray
Start-Sleep -Seconds 5

# 4b. Restart gateway so Nginx picks up fresh DNS for all backend services
# (Nginx caches DNS at startup; if the gateway started before services settled,
# it may route to stale IPs.)
Write-Status "Restarting gateway for fresh DNS..." -Color Gray
docker restart spendsy_gateway 2>$null
Write-Status "Gateway restarted" -Color Green

# 5. Database Maintenance
Write-Step "Database Maintenance"
try {
    docker exec spendsy_postgres psql -U smartuser -d spendsy -c "ALTER DATABASE spendsy REFRESH COLLATION VERSION;"
    Write-Status "Collation refresh done" -Color Green
} catch {
    Write-Status "Skipped (DB still initializing)" -Color Yellow
}

# 6. Runtime Output
Write-Step "Spendsy Development Environment"
Write-Host ""
Write-Host "  Frontend:  http://localhost:5173  (Vite HMR)" -ForegroundColor Green
Write-Host "  Gateway:   http://localhost:8080  (nginx)" -ForegroundColor White
Write-Host "  TORA AI:   http://localhost:8004/health" -ForegroundColor White

Write-Host ""
Write-Host "  Ctrl+C to stop everything." -ForegroundColor Yellow
Write-Host ""

$BackendLogs = $null

try {
    # Tail backend logs in the background
    $BackendLogs = Start-Process docker -ArgumentList "compose", "-f", "$COMPOSE_FILE", "logs", "-f", "--tail", "20" -PassThru -NoNewWindow

    # Run Vite in the foreground
    npm run dev -w frontend -- --host 127.0.0.1 --port 5173
}
catch {
    Write-Status "Session ended or interrupted." -Color Yellow
}
finally {
    Write-Step "Cleaning Up"

    if ($BackendLogs -and -not $BackendLogs.HasExited) {
        Write-Status "Stopping log stream..."
        Stop-Process -Id $BackendLogs.Id -Force -ErrorAction SilentlyContinue
    }

    Write-Status "Stopping Docker services..."
    docker compose -f $COMPOSE_FILE stop $BackendServices
    Write-Host "All services stopped." -ForegroundColor Green
}