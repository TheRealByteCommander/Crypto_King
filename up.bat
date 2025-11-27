@echo off
REM Update Script für Windows - Installiert alle neuen Features und Dependencies
REM Kurzer Dateiname: up.bat

echo ==========================================
echo Project CypherTrade - Update Script
echo ==========================================
echo.

REM Check if we're in the right directory
if not exist "backend" (
    echo Error: Please run this script from the project root directory
    exit /b 1
)

echo Step 1: Git Pull (neueste Änderungen)
git pull origin main
if errorlevel 1 (
    echo Warning: Git pull had issues. Continuing anyway...
)

echo.
echo Step 2: Installiere neue Python Dependencies
cd backend

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else if exist "..\venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call ..\venv\Scripts\activate.bat
)

REM Install new dependencies
pip install -r requirements.txt --upgrade
if errorlevel 1 (
    echo Warning: Some dependencies might not have installed correctly
)

echo.
echo Step 3: Prüfe neue Module
python -c "import feedparser; import bs4; from coin_analyzer import CoinAnalyzer; print('✓ All new modules imported successfully')" 2>nul
if errorlevel 1 (
    echo Warning: Some modules might need manual installation
    echo Run: pip install feedparser beautifulsoup4
)

cd ..

echo.
echo ==========================================
echo Update abgeschlossen!
echo ==========================================
echo.
echo Neue Features:
echo   ✓ Crypto News System für NexusChat
echo   ✓ News-Weiterleitung an andere Agents
echo   ✓ Autonome Bot-Verwaltung für CypherMind
echo   ✓ Coin-Analyse mit Echtzeitkursen + News
echo.
echo Dokumentation:
echo   - CRYPTO_NEWS_SYSTEM.md
echo   - AUTONOMOUS_BOTS.md
echo.
echo Wichtig:
echo   - Neue Dependencies: feedparser, beautifulsoup4
echo   - Backend sollte neu gestartet werden
echo   - CypherMind kann jetzt autonome Bots starten
echo.

pause

