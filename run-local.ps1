param(
    [switch]$SkipNodeInstall,
    [switch]$SkipDockerPull
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$PROJECT_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$DOCKER_DIR = Join-Path $PROJECT_ROOT "infra\docker"
$COMPOSE_FILE = Join-Path $DOCKER_DIR "docker-compose.dev.yml"
$BackendServices = @("postgres", "redis", "auth-service", "finance-service", "ai-service", "spendsy-ai", "spendsy-mcp", "nginx")
$ManagedPorts = @(3000, 5173)

# Track long-running processes so we can cleanly stop them on exit
$script:ViteSession = $null
$script:BackendLogsSession = $null
$script:ManagedContainerIds = @()
$script:CleanupSignalFile = $null
$script:CleanupWatcherScriptPath = $null
$script:ShutdownInitiated = $false
$script:CanUseConsoleKeyPolling = $true

function Write-Step {
    param(
        [string]$Message
    )

    Write-Host ""
    Write-Host $Message -ForegroundColor Cyan
}

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory = $PROJECT_ROOT
    )

    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed: $FilePath $($Arguments -join ' ')"
        }
    }
    finally {
        Pop-Location
    }
}

function Resolve-ExecutablePath {
    param(
        [string]$Command
    )

    if ([string]::IsNullOrWhiteSpace($Command)) {
        throw "Command path cannot be empty."
    }

    if ([System.IO.Path]::IsPathRooted($Command)) {
        return (Resolve-Path -LiteralPath $Command).ProviderPath
    }

    $resolvedCommand = Get-Command $Command -ErrorAction Stop | Select-Object -First 1
    $resolvedPath = $resolvedCommand.Path
    if (-not $resolvedPath) {
        $resolvedPath = $resolvedCommand.Definition
    }

    if (-not $resolvedPath) {
        throw "Unable to resolve executable path for '$Command'."
    }

    return $resolvedPath
}

function Start-CleanupWatcher {
    param(
        [int[]]$ProcessIds,
        [string[]]$ContainerIds = @()
    )

    if ($script:CleanupSignalFile -or -not $ProcessIds) {
        return
    }

    $watcherProcessIds = @($ProcessIds | Where-Object { $_ -and $_ -gt 0 } | Select-Object -Unique)
    $watcherContainerIds = @($ContainerIds | Where-Object { $_ } | Select-Object -Unique)
    if (-not $watcherProcessIds -and -not $watcherContainerIds) {
        return
    }

    $script:CleanupSignalFile = Join-Path ([System.IO.Path]::GetTempPath()) "spendsy-run-local-$PID.signal"
    $script:CleanupWatcherScriptPath = Join-Path ([System.IO.Path]::GetTempPath()) "spendsy-run-local-watcher-$PID.ps1"

    Set-Content -LiteralPath $script:CleanupSignalFile -Value "armed" -Encoding Ascii

    $watcherScript = @'
param(
    [int]$ParentPid,
    [string]$SignalFilePath,
    [string]$ProcessIdsCsv,
    [string]$ContainerIdsCsv,
    [string]$DockerExecutablePath
)

$ErrorActionPreference = "SilentlyContinue"

while (Get-Process -Id $ParentPid -ErrorAction SilentlyContinue) {
    Start-Sleep -Milliseconds 500
}

$status = "armed"
if (Test-Path -LiteralPath $SignalFilePath) {
    $status = (Get-Content -LiteralPath $SignalFilePath -Raw).Trim()
}

if ($status -ne "completed") {
    foreach ($processIdText in ($ProcessIdsCsv -split ",")) {
        if (-not $processIdText) {
            continue
        }

        $processId = 0
        if ([int]::TryParse($processIdText, [ref]$processId) -and $processId -gt 0) {
            taskkill /PID $processId /T /F 2>$null | Out-Null
        }
    }

    $containerIds = @($ContainerIdsCsv -split "," | Where-Object { $_ })
    if ($containerIds -and $DockerExecutablePath) {
        & $DockerExecutablePath @("rm", "-f") @($containerIds) 2>$null | Out-Null
    }
}

Remove-Item -LiteralPath $SignalFilePath, $MyInvocation.MyCommand.Path -Force -ErrorAction SilentlyContinue
'@

    Set-Content -LiteralPath $script:CleanupWatcherScriptPath -Value $watcherScript -Encoding Ascii

    $shellPath = (Get-Process -Id $PID).Path
    Start-Process `
        -FilePath $shellPath `
        -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            $script:CleanupWatcherScriptPath,
            "-ParentPid",
            $PID,
            "-SignalFilePath",
            $script:CleanupSignalFile,
            "-ProcessIdsCsv",
            ($watcherProcessIds -join ","),
            "-ContainerIdsCsv",
            ($watcherContainerIds -join ","),
            "-DockerExecutablePath",
            (Resolve-ExecutablePath -Command "docker")
        ) `
        -WindowStyle Hidden | Out-Null
}

function Complete-CleanupWatcher {
    if (-not $script:CleanupSignalFile) {
        return
    }

    Set-Content -LiteralPath $script:CleanupSignalFile -Value "completed" -Encoding Ascii -ErrorAction SilentlyContinue
}

function Get-ComposeContainerIds {
    $dockerPath = Resolve-ExecutablePath -Command "docker"
    $containerIds = & $dockerPath @("compose", "-f", $COMPOSE_FILE, "ps", "-q") @($BackendServices)
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to resolve Docker container IDs for cleanup."
    }

    return @($containerIds | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

function Format-CommandArgument {
    param(
        [string]$Argument
    )

    if ($null -eq $Argument) {
        return '""'
    }

    if ($Argument -notmatch '[\s"]') {
        return $Argument
    }

    $escaped = $Argument -replace '(\\*)"', '$1$1\"'
    $escaped = $escaped -replace '(\\+)$', '$1$1'
    return '"' + $escaped + '"'
}

function Remove-LogSubscription {
    param(
        [string]$SourceIdentifier
    )

    if (-not $SourceIdentifier) {
        return
    }

    Unregister-Event -SourceIdentifier $SourceIdentifier -ErrorAction SilentlyContinue
    Get-Job -Name $SourceIdentifier -ErrorAction SilentlyContinue | Remove-Job -Force -ErrorAction SilentlyContinue
}

function Stop-LoggedSession {
    param(
        [pscustomobject]$Session,
        [string]$Label
    )

    if (-not $Session) {
        return
    }

    foreach ($sourceIdentifier in $Session.SubscriptionIds) {
        Remove-LogSubscription -SourceIdentifier $sourceIdentifier
    }

    if ($Session.Process -and -not $Session.Process.HasExited) {
        if ($Label) {
            Write-Host "Stopping $Label (PID $($Session.Process.Id))..." -ForegroundColor Yellow
        }

        taskkill /PID $Session.Process.Id /T /F 2>$null | Out-Null
        $Session.Process.WaitForExit()
    }

    if ($Session.Process) {
        $Session.Process.Dispose()
    }
}

function Start-LoggedProcess {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory = $PROJECT_ROOT,
        [ConsoleColor]$Color = [ConsoleColor]::Gray,
        [switch]$PassRawOutput
    )

    $resolvedFilePath = Resolve-ExecutablePath -Command $FilePath

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $resolvedFilePath
    $startInfo.Arguments = (($Arguments | ForEach-Object { Format-CommandArgument -Argument $_ }) -join " ")
    $startInfo.WorkingDirectory = $WorkingDirectory
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.CreateNoWindow = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    $process.EnableRaisingEvents = $true

    $stdoutId = "spendsy-$Name-stdout-$([guid]::NewGuid().ToString())"
    $stderrId = "spendsy-$Name-stderr-$([guid]::NewGuid().ToString())"
    $messageData = @{
        Name = $Name
        Color = $Color
        PassRawOutput = [bool]$PassRawOutput
    }

    Register-ObjectEvent -InputObject $process -EventName OutputDataReceived -SourceIdentifier $stdoutId -MessageData $messageData -Action {
        $line = $Event.SourceEventArgs.Data
        if ([string]::IsNullOrWhiteSpace($line)) {
            return
        }

        if ($Event.MessageData.PassRawOutput) {
            Write-Host $line -ForegroundColor $Event.MessageData.Color
            return
        }

        Write-Host ("[{0}] {1}" -f $Event.MessageData.Name, $line) -ForegroundColor $Event.MessageData.Color
    } | Out-Null

    Register-ObjectEvent -InputObject $process -EventName ErrorDataReceived -SourceIdentifier $stderrId -MessageData $messageData -Action {
        $line = $Event.SourceEventArgs.Data
        if ([string]::IsNullOrWhiteSpace($line)) {
            return
        }

        if ($Event.MessageData.PassRawOutput) {
            Write-Host $line -ForegroundColor Red
            return
        }

        Write-Host ("[{0}] {1}" -f $Event.MessageData.Name, $line) -ForegroundColor Red
    } | Out-Null

    if (-not $process.Start()) {
        foreach ($sourceIdentifier in @($stdoutId, $stderrId)) {
            Remove-LogSubscription -SourceIdentifier $sourceIdentifier
        }

        throw "Failed to start process: $resolvedFilePath"
    }

    $process.BeginOutputReadLine()
    $process.BeginErrorReadLine()

    return [pscustomobject]@{
        Name = $Name
        Process = $process
        SubscriptionIds = @($stdoutId, $stderrId)
    }
}

function Import-DotEnv {
    param(
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        return
    }

    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }

        $separatorIndex = $line.IndexOf("=")
        if ($separatorIndex -lt 1) {
            return
        }

        $name = $line.Substring(0, $separatorIndex).Trim()
        $value = $line.Substring($separatorIndex + 1).Trim()

        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        Set-Item -Path "Env:$name" -Value $value
    }
}

function Stop-PortProcesses {
    param(
        [int[]]$Ports
    )

    foreach ($port in $Ports) {
        $connections = @(Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
        if (-not $connections) {
            continue
        }

        Write-Host "Stopping local processes on port ${port}: $($connections -join ', ')" -ForegroundColor Yellow
        foreach ($processId in $connections) {
            if ($processId -and $processId -ne $PID) {
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
            }
        }
    }

    Start-Sleep -Seconds 1
}

function Stop-Everything {
    if ($script:ShutdownInitiated) {
        return
    }

    $script:ShutdownInitiated = $true
    Complete-CleanupWatcher

    Write-Host ""
    Write-Step "Shutting down everything..."

    Stop-LoggedSession -Session $script:BackendLogsSession -Label "backend log tail"
    $script:BackendLogsSession = $null

    Stop-LoggedSession -Session $script:ViteSession -Label "Vite"
    $script:ViteSession = $null

    # Kill anything still on frontend ports
    Stop-PortProcesses -Ports $ManagedPorts

    # Tear down all Docker containers
    Write-Host "Stopping Docker containers..." -ForegroundColor Yellow
    docker compose -f $COMPOSE_FILE down --remove-orphans 2>$null | Out-Null
    $script:ManagedContainerIds = @()

    Write-Host "All services stopped." -ForegroundColor Green
}

# Standard Ctrl+C behavior will trigger the 'finally' block automatically in most PS environments.
$script:CanUseConsoleKeyPolling = $true
try {
    # Test if we are in an interactive console
    $null = [Console]::KeyAvailable
}
catch {
    $script:CanUseConsoleKeyPolling = $false
}

Write-Step "Starting Spendsy with Docker backend + local frontend"

if (-not (Test-Path (Join-Path $PROJECT_ROOT ".env"))) {
    Write-Host "Creating .env from .env.example" -ForegroundColor Yellow
    Copy-Item (Join-Path $PROJECT_ROOT ".env.example") (Join-Path $PROJECT_ROOT ".env")
}

if (-not $SkipNodeInstall) {
    Write-Step "Installing Node dependencies"
    Invoke-Checked -FilePath "npm.cmd" -Arguments @("install")
}

if (-not $SkipDockerPull) {
    Write-Step "Pulling backend Docker images"
    Invoke-Checked -FilePath "docker" -Arguments @("compose", "-f", $COMPOSE_FILE, "pull") -WorkingDirectory $PROJECT_ROOT
}

Write-Step "Freeing frontend ports"
Stop-PortProcesses -Ports $ManagedPorts

Write-Step "Starting backend services in Docker"
Invoke-Checked -FilePath "docker" -Arguments (@("compose", "-f", $COMPOSE_FILE, "up", "-d") + $BackendServices) -WorkingDirectory $PROJECT_ROOT
$script:ManagedContainerIds = Get-ComposeContainerIds

Write-Step "Launching Vite locally"
Write-Host "Frontend:     http://localhost:5173" -ForegroundColor Green
Write-Host "Gateway:      http://localhost:8080" -ForegroundColor DarkGray
Write-Host "Tora:         http://localhost:8080/tora/" -ForegroundColor DarkGray
Write-Host "MCP SSE:      http://localhost:8080/mcp/sse" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Streaming backend + frontend logs below. Press Ctrl+C to stop everything." -ForegroundColor Yellow

# Stream Docker logs in this terminal while the services keep running in detached mode.
$script:BackendLogsSession = Start-LoggedProcess `
    -Name "backend" `
    -FilePath "docker" `
    -Arguments (@("compose", "-f", $COMPOSE_FILE, "logs", "-f", "--tail", "20") + $BackendServices) `
    -WorkingDirectory $PROJECT_ROOT `
    -Color DarkGray `
    -PassRawOutput

# Start Vite with stdout/stderr wired into this same terminal.
$script:ViteSession = Start-LoggedProcess `
    -Name "vite" `
    -FilePath "npm.cmd" `
    -Arguments @("run", "-w", "frontend", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort") `
    -WorkingDirectory $PROJECT_ROOT `
    -Color Cyan

Start-CleanupWatcher -ProcessIds @(
    $script:BackendLogsSession.Process.Id,
    $script:ViteSession.Process.Id
) -ContainerIds $script:ManagedContainerIds

# Poll for Ctrl+C while Vite is running
try {
    while (-not $script:ViteSession.Process.HasExited) {
        if ($script:CanUseConsoleKeyPolling -and [Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true)
            # Exit on 'Q', 'X', or ESC as fallbacks to Ctrl+C
            if ($key.Key -eq "Q" -or $key.Key -eq "X" -or $key.Key -eq "Escape") {
                Write-Host "Exit signal received..." -ForegroundColor Yellow
                break
            }
        }
        Start-Sleep -Milliseconds 500
    }
} finally {
    Stop-Everything
}
