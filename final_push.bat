@echo off
chcp 65001 >nul
echo ========================================
echo Git Push - Kerzen-Tracking-System
echo ========================================
echo.

cd /d "C:\Users\mschm\Crypto_King"

echo [1] Aktueller Status:
git status --short
echo.

echo [2] Stage alle Dateien...
git add backend/candle_tracker.py
git add backend/bot_manager.py
git add backend/agent_tools.py
git add backend/memory_manager.py
git add backend/agent_configs/cyphermind_config.yaml
git add README.md
git add MEMORY_SYSTEM.md
git add CANDLE_TRACKING_ANALYSE.md
git add CANDLE_TRACKING_IMPLEMENTATION.md
git add POSITION_TRACKING_UPDATE.md
git add CHANGELOG_CANDLE_TRACKING.md
git add COMMIT_ANLEITUNG.md
git add UPDATE_ZUSAMMENFASSUNG.md
git add PUSH_ANLEITUNG_FINAL.md
git add GIT_PUSH_ERGEBNIS.md
git add git_push.ps1
git add commit_candle_tracking.sh
git add push_to_repo.py
git add do_git_push.bat
git add final_push.bat
echo.

echo [3] Status nach add:
git status --short
echo.

echo [4] Committe...
git commit -m "Feat: Kerzen-Tracking-System implementiert"
echo.

echo [5] Push ins Repo...
git push origin main
echo.

echo [6] Finaler Status:
git status
echo.

echo ========================================
echo Fertig!
echo ========================================

