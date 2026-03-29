$results = @()

$services = [ordered]@{
    'Auth Service'    = 'http://localhost:8001/health'
    'Finance Service' = 'http://localhost:8002/health'
    'AI Service'      = 'http://localhost:8004/health'
    'Spendsy AI'      = 'http://localhost:8005/health'
    'Frontend'        = 'http://localhost:5173/'
}

foreach ($item in $services.GetEnumerator()) {
    $name = $item.Key
    $url = $item.Value
    $status = "OFFLINE"
    try {
        $response = Invoke-WebRequest -Uri $url -Method Get -TimeoutSec 2 -ErrorAction Stop
        $status = "ONLINE (200 OK)"
    } catch {
        if ($url -like '*health') {
            $rootUrl = $url -replace '/health', ''
            try {
                $response = Invoke-WebRequest -Uri $rootUrl -Method Get -TimeoutSec 2 -ErrorAction Stop
                $status = "ONLINE (200 OK /root)"
            } catch {
                $status = "OFFLINE"
            }
        }
    }
    $results += "$name`: $status"
}

# Check for MCP process
$mcp_process = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*server.py*" }
if ($mcp_process) {
    $results += "MCP Server: ONLINE (PID: $($mcp_process.Id))"
} else {
    $results += "MCP Server: OFFLINE"
}

Write-Output "--- Service Status ---"
foreach ($r in $results) { Write-Output $r }

Write-Output "`n--- Docker Containers ---"
& docker ps --format "{{.Names}}: {{.Status}}"
