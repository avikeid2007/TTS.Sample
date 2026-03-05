# run.ps1 — start the IndicF5 TTS web app
# Usage:  .\run.ps1 [port]

param(
    [int]$Port = 8000,
    [switch]$Reload   # pass -Reload for hot-reload during development
)

$reloadFlag = if ($Reload) { "--reload" } else { "" }

Write-Host ""
Write-Host "  IndicF5 TTS Web App" -ForegroundColor Cyan
Write-Host "  Starting on  http://localhost:$Port" -ForegroundColor Green
Write-Host ""

uvicorn main:app --host 0.0.0.0 --port $Port $reloadFlag
