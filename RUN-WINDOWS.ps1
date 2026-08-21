$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "Gurucul ThreatIntel Platform" -ForegroundColor Cyan
Write-Host "Preparing backend..." -ForegroundColor Green

Set-Location "$root\backend"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

Set-Location $root
& ".\backend\.venv\Scripts\python.exe" "scripts\seed_demo.py"

Write-Host "Starting backend..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root'; & '.\backend\.venv\Scripts\python.exe' -m uvicorn backend.app.main:app --reload --port 8001"

Write-Host "Preparing frontend..." -ForegroundColor Green
Set-Location "$root\frontend"
if (-not (Test-Path "node_modules")) {
    npm install
}

Write-Host "Starting frontend..." -ForegroundColor Green
npm run dev -- --host 127.0.0.1
