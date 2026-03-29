# docker-run.ps1 - Spendsy Full Docker Deployment
# Starts everything (Infrastructure, Backend Services, and Frontend) in Docker containers

$PROJECT_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$PROJECT_ROOT\infra\docker"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Spendsy Full Docker Deployment" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting Spendsy containers (this may take a few minutes on first run)..." -ForegroundColor Green

# Ensure Docker is running
docker version >$null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running. Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

# Run Docker Compose
docker compose -f docker-compose.dev.yml up --build -d

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  Success! Spendsy is now running in Docker." -ForegroundColor Green
    Write-Host ""
    Write-Host "  Frontend (Direct): http://localhost:3000" -ForegroundColor White
    Write-Host "  Gateway (Unified): http://localhost:8080" -ForegroundColor White
    Write-Host ""
    Write-Host "  To view logs:   docker compose logs -f" -ForegroundColor DarkGray
    Write-Host "  To stop:        docker compose down" -ForegroundColor DarkGray
    Write-Host "============================================================" -ForegroundColor Cyan
} else {
    Write-Host "ERROR: Docker Compose failed to start." -ForegroundColor Red
}

Set-Location $PROJECT_ROOT
