#!/bin/bash
# Update Script - Installiert alle neuen Features und Dependencies
# Kurzer Dateiname: up.sh

set -e

echo "=========================================="
echo "Project CypherTrade - Update Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Git Pull (neueste Änderungen)${NC}"
git pull origin main || {
    echo -e "${RED}Git pull failed. Continuing anyway...${NC}"
}

echo ""
echo -e "${YELLOW}Step 2: Installiere neue Python Dependencies${NC}"
cd backend

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -d "../venv" ]; then
    echo "Activating virtual environment..."
    source ../venv/bin/activate
fi

# Install new dependencies
pip install -r requirements.txt --upgrade || {
    echo -e "${RED}Warning: Some dependencies might not have installed correctly${NC}"
}

echo ""
echo -e "${YELLOW}Step 3: Prüfe neue Module${NC}"

# Check if new modules can be imported
python3 -c "import feedparser; import bs4; from coin_analyzer import CoinAnalyzer; print('✓ All new modules imported successfully')" 2>/dev/null || {
    echo -e "${YELLOW}Warning: Some modules might need manual installation${NC}"
    echo "Run: pip install feedparser beautifulsoup4"
}

cd ..

echo ""
echo -e "${YELLOW}Step 4: Backend neu starten (wenn supervisor verfügbar)${NC}"
if command -v supervisorctl &> /dev/null; then
    sudo supervisorctl restart cyphertrade-backend || {
        echo -e "${YELLOW}Warning: Could not restart backend via supervisorctl${NC}"
        echo "You may need to restart the backend manually"
    }
else
    echo -e "${YELLOW}Supervisor not found. Please restart backend manually${NC}"
fi

echo ""
echo -e "${YELLOW}Step 5: Frontend Dependencies (wenn npm verfügbar)${NC}"
if command -v npm &> /dev/null && [ -d "frontend" ]; then
    cd frontend
    npm install 2>/dev/null || {
        echo -e "${YELLOW}Warning: npm install had issues${NC}"
    }
    cd ..
else
    echo -e "${YELLOW}npm not found or frontend directory missing${NC}"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "Update abgeschlossen!"
echo "==========================================${NC}"
echo ""
echo "Neue Features:"
echo "  ✓ Crypto News System für NexusChat"
echo "  ✓ News-Weiterleitung an andere Agents"
echo "  ✓ Autonome Bot-Verwaltung für CypherMind"
echo "  ✓ Coin-Analyse mit Echtzeitkursen + News"
echo ""
echo "Dokumentation:"
echo "  - CRYPTO_NEWS_SYSTEM.md"
echo "  - AUTONOMOUS_BOTS.md"
echo ""
echo -e "${YELLOW}Wichtig:${NC}"
echo "  - Neue Dependencies: feedparser, beautifulsoup4"
echo "  - Backend sollte neu gestartet werden"
echo "  - CypherMind kann jetzt autonome Bots starten"
echo ""

