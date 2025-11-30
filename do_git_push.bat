@echo off
echo ========================================
echo Git Push - Kerzen-Tracking-System
echo ========================================
echo.

cd /d C:\Users\mschm\Crypto_King

echo [1/6] Git Status vorher...
git status --short
echo.

echo [2/6] Stage alle Dateien...
git add -A
echo.

echo [3/6] Git Status nach add...
git status --short
echo.

echo [4/6] Committe...
git commit -m "Feat: Kerzen-Tracking-System implementiert - Pre-Trade, During-Trade und Post-Trade Tracking"
echo.

echo [5/6] Letzter Commit...
git log --oneline -1
echo.

echo [6/6] Pushe ins Repo...
git push
echo.

echo ========================================
echo Finaler Status:
echo ========================================
git status --short

echo.
echo ========================================
echo Fertig!
echo ========================================
pause

