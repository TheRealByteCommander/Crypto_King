# PowerShell Script zum Prüfen und Pushen
$ErrorActionPreference = "Continue"
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Git Push - Kerzen-Tracking-System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Set-Location "C:\Users\mschm\Crypto_King"

Write-Host "`n[1] Prüfe Git Status..." -ForegroundColor Yellow
$status = git status --short 2>&1
Write-Host $status

Write-Host "`n[2] Stage alle Dateien..." -ForegroundColor Yellow
git add backend/candle_tracker.py 2>&1 | Out-Null
git add backend/bot_manager.py 2>&1 | Out-Null
git add backend/agent_tools.py 2>&1 | Out-Null
git add backend/memory_manager.py 2>&1 | Out-Null
git add backend/agent_configs/cyphermind_config.yaml 2>&1 | Out-Null
git add README.md 2>&1 | Out-Null
git add MEMORY_SYSTEM.md 2>&1 | Out-Null
git add CANDLE_TRACKING*.md 2>&1 | Out-Null
git add POSITION_TRACKING*.md 2>&1 | Out-Null
git add CHANGELOG*.md 2>&1 | Out-Null
git add *.ps1 *.sh *.bat *.py 2>&1 | Out-Null
Write-Host "Dateien gestaged" -ForegroundColor Green

Write-Host "`n[3] Status nach git add..." -ForegroundColor Yellow
git status --short 2>&1

Write-Host "`n[4] Committe..." -ForegroundColor Yellow
$commitResult = git commit -m "Feat: Kerzen-Tracking-System implementiert - Pre-Trade, During-Trade und Post-Trade Tracking" 2>&1
Write-Host $commitResult

Write-Host "`n[5] Letzter Commit..." -ForegroundColor Yellow
git log --oneline -1 2>&1

Write-Host "`n[6] Push ins Repo..." -ForegroundColor Yellow
$pushResult = git push origin main 2>&1
Write-Host $pushResult

Write-Host "`n[7] Finaler Status..." -ForegroundColor Yellow
git status 2>&1

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Fertig!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

