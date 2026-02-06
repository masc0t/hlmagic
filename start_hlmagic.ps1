# HLMagic Background Starter
# This script ensures the server is running and opens the UI

$ErrorActionPreference = "SilentlyContinue"

Write-Host "🪄 Starting HLMagic..." -ForegroundColor Cyan

# 1. Trigger the background process in WSL via systemd
Write-Host "🧠 Launching HLMagic Service..." -ForegroundColor Cyan
wsl -d Ubuntu-24.04 sudo systemctl start hlmagic

# 2. Wait for the port to become active (max 10 seconds)
$retries = 0
$targetHost = "localhost"
while ($retries -lt 10) {
    # Check localhost first (Best for Mirrored Mode)
    $check = Test-NetConnection -ComputerName $targetHost -Port 8000
    if ($check.TcpTestSucceeded) {
        Write-Host "✅ HLMagic is ready at $targetHost!" -ForegroundColor Green
        break
    }
    
    # Try hlmagic.local fallback
    $checkLocal = Test-NetConnection -ComputerName "hlmagic.local" -Port 8000
    if ($checkLocal.TcpTestSucceeded) {
        $targetHost = "hlmagic.local"
        Write-Host "✅ HLMagic is ready at $targetHost!" -ForegroundColor Green
        break
    }

    Write-Host "⏳ Waiting for server..." -ForegroundColor Gray
    Start-Sleep -Seconds 1
    $retries++
}

# 3. Open the browser
Start-Process "http://$($targetHost):8000"
