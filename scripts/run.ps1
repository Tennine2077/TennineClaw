# TennineClaw - Intelligent Terminal Assistant
# Start the Web API server

Write-Host "="*60
Write-Host "  TennineClaw - Intelligent Terminal Assistant"
Write-Host "="*60
Write-Host ""

# Switch to project root (parent of scripts/)
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  NOTE: API config is now managed via Web UI." -ForegroundColor Cyan
Write-Host "  Open the browser after starting, use top-right model" -ForegroundColor Cyan
Write-Host "  settings to configure API Key / Base URL / Model." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Start server
Write-Host "[STARTING] TennineClaw Web API..." -ForegroundColor Green
Write-Host ""
python -m src.web_api

pause
