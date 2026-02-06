# HLMagic One-Line Installer for Windows
# Usage: iex (iwr -useb https://raw.githubusercontent.com/masc0t/hlmagic/main/install.ps1)

$ErrorActionPreference = "Stop"

Write-Host "🪄 HLMagic: Starting Autonomous Setup..." -ForegroundColor Cyan

# 1. Check for WSL
if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) {
    Write-Host "❌ WSL not found. Enabling WSL and installing Ubuntu 24.04..." -ForegroundColor Yellow
    wsl --install -d Ubuntu-24.04
    Write-Host "⚠️ Please RESTART your computer and run this installer again." -ForegroundColor Red
    exit
}

# 2. Check if Ubuntu-24.04 is installed
$distros = wsl --list --quiet | ForEach-Object { $_ -replace "\x00", "" } | Where-Object { $_ -ne "" }
if ($distros -notcontains "Ubuntu-24.04") {
    Write-Host "📦 Installing Ubuntu 24.04..." -ForegroundColor Cyan
    wsl --install -d Ubuntu-24.04
    # Wait for installation to finish (it usually opens a new window)
    Write-Host "⚠️ Ubuntu installation started in a new window. Complete the username/password setup there, then run this installer again." -ForegroundColor Yellow
    exit
}

Write-Host "✅ WSL2 & Ubuntu 24.04 Detected." -ForegroundColor Green

# 3. Prepare the WSL environment
Write-Host "🧠 Injecting HLMagic into WSL..." -ForegroundColor Cyan

$setupScript = @"
#!/bin/bash
set -e
echo "Updating WSL system..."
sudo apt update && sudo apt install -y python3-pip python3-venv git curl pciutils

# Create HLMagic directory
sudo mkdir -p /opt/hlmagic
sudo chown -R `$USER:`$USER /opt/hlmagic

# Clone or Update HLMagic
if [ ! -d "/opt/hlmagic/repo" ]; then
    git clone https://github.com/masc0t/hlmagic.git /opt/hlmagic/repo
else
    cd /opt/hlmagic/repo && git pull
fi

# Setup Virtual Environment
python3 -m venv /opt/hlmagic/venv
source /opt/hlmagic/venv/bin/activate
pip install --upgrade pip
pip install -e /opt/hlmagic/repo

# Run HLMagic Init (non-interactive)
hlmagic init --confirm

# Start the Web Server in the background
nohup hlmagic serve > /opt/hlmagic/server.log 2>&1 &
"@

# Save and run the script inside WSL
$setupScriptLF = $setupScript -replace "`r`n", "`n"
$setupScriptLF | wsl -d Ubuntu-24.04 -u root bash -c "cat > /tmp/hl_setup.sh && chmod +x /tmp/hl_setup.sh"
wsl -d Ubuntu-24.04 bash -c "/tmp/hl_setup.sh"

Write-Host "🚀 HLMagic is now running!" -ForegroundColor Green
Write-Host "🌐 Opening the Web Interface..." -ForegroundColor Cyan

Start-Process "http://localhost:8000"