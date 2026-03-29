$body = '{"username":"testuser99","email":"testuser99@test.com","password":"testpass123"}'

Write-Host "=== Test 1: Direct to auth-service port 8001 ===" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "http://localhost:8001/register" -Method POST -Body $body -ContentType "application/json" -ErrorAction Stop
    Write-Host "PASS: HTTP $($r.StatusCode)" -ForegroundColor Green
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    Write-Host "Got HTTP $code (non-2xx)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Test 2: Through gateway port 8080/auth/register ===" -ForegroundColor Cyan
try {
    $r2 = Invoke-WebRequest -Uri "http://localhost:8080/auth/register" -Method POST -Body $body -ContentType "application/json" -ErrorAction Stop
    Write-Host "PASS: HTTP $($r2.StatusCode)" -ForegroundColor Green
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    Write-Host "Got HTTP $code (non-2xx)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Nginx config in container ===" -ForegroundColor Cyan
docker exec spendsy_gateway cat /etc/nginx/nginx.conf
