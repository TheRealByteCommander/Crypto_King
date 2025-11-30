# Git Push Script für Kerzen-Tracking-System
Write-Host "🔄 Git Push Script gestartet..." -ForegroundColor Cyan

# Wechsle ins Verzeichnis
Set-Location "C:\Users\mschm\Crypto_King"

Write-Host "`n📊 Aktueller Git Status:" -ForegroundColor Yellow
git status --short

Write-Host "`n➕ Stage alle Änderungen..." -ForegroundColor Cyan
git add -A

Write-Host "`n📋 Gestaute Dateien:" -ForegroundColor Yellow
git status --short

Write-Host "`n💾 Committe Änderungen..." -ForegroundColor Cyan
$commitMessage = @"
Feat: Kerzen-Tracking-System implementiert - Pre-Trade, During-Trade und Post-Trade Tracking

- CandleTracker Klasse für kontinuierliches Kerzen-Tracking
- Pre-Trade: 200 Kerzen vor jedem Trade
- During-Trade: Alle Kerzen während Position offen ist
- Post-Trade: 200 Kerzen nach jedem Verkauf
- Integration in Bot-Manager und Memory-System
- CypherMind Tool erweitert: get_bot_candles()
- Pattern-Extraktion aus Kerzen-Daten für Learning
- Vollständige Dokumentation aktualisiert
"@

git commit -m $commitMessage

Write-Host "`n📝 Letzter Commit:" -ForegroundColor Yellow
git log --oneline -1

Write-Host "`n🚀 Pushe ins Repo..." -ForegroundColor Cyan
git push

Write-Host "`n✅ Fertig! Status:" -ForegroundColor Green
git status --short

Write-Host "`n📊 Remote Status:" -ForegroundColor Yellow
git remote -v

