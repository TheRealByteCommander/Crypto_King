#!/bin/bash
# Fix Backend Spawn Error - Installiert fehlende Dependencies

set -e

echo "=========================================="
echo "Backend Spawn Error Fix"
echo "=========================================="
echo ""

BACKEND_DIR="/app/backend"

if [ ! -d "$BACKEND_DIR" ]; then
    BACKEND_DIR="./backend"
    if [ ! -d "$BACKEND_DIR" ]; then
        echo "Error: Backend directory not found"
        exit 1
    fi
fi

cd "$BACKEND_DIR" || exit 1

echo "Step 1: Installiere fehlende Dependencies..."
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

# Installiere neue Dependencies
pip install feedparser beautifulsoup4 --upgrade || {
    echo "Warning: Could not install some dependencies"
}

echo ""
echo "Step 2: Prüfe Imports..."
python3 -c "
try:
    import feedparser
    print('✓ feedparser OK')
except ImportError as e:
    print(f'✗ feedparser fehlt: {e}')

try:
    from bs4 import BeautifulSoup
    print('✓ beautifulsoup4 OK')
except ImportError as e:
    print(f'✗ beautifulsoup4 fehlt: {e}')

try:
    from crypto_news_fetcher import get_news_fetcher
    print('✓ crypto_news_fetcher OK')
except ImportError as e:
    print(f'✗ crypto_news_fetcher Import fehlgeschlagen: {e}')

try:
    from coin_analyzer import CoinAnalyzer
    print('✓ coin_analyzer OK')
except ImportError as e:
    print(f'✗ coin_analyzer Import fehlgeschlagen: {e}')

try:
    from agent_tools import AgentTools
    print('✓ agent_tools OK')
except ImportError as e:
    print(f'✗ agent_tools Import fehlgeschlagen: {e}')

try:
    from agents import AgentManager
    print('✓ agents OK')
except ImportError as e:
    print(f'✗ agents Import fehlgeschlagen: {e}')

try:
    import server
    print('✓ server OK')
except ImportError as e:
    print(f'✗ server Import fehlgeschlagen: {e}')
" || {
    echo "Error: Import check failed"
    exit 1
}

echo ""
echo "Step 3: Prüfe Syntax..."
python3 -m py_compile agent_tools.py crypto_news_fetcher.py coin_analyzer.py server.py 2>&1 || {
    echo "Error: Syntax errors found"
    exit 1
}

echo ""
echo "Step 4: Backend neu starten (wenn supervisor verfügbar)..."
if command -v supervisorctl &> /dev/null; then
    sudo supervisorctl restart cyphertrade-backend || {
        echo "Warning: Could not restart via supervisorctl"
    }
else
    echo "Supervisor not found. Please restart backend manually"
fi

echo ""
echo "=========================================="
echo "Fix abgeschlossen!"
echo "=========================================="
echo ""
echo "Falls der Fehler weiterhin besteht, prüfe:"
echo "  tail -50 /var/log/supervisor/cyphertrade-backend-error.log"
echo ""

