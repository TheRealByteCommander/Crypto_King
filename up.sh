#!/bin/bash
# Vollständiges Update-Skript - aktualisiert Backend & Frontend
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

ROOT_DIR="$(pwd)"

# Versuche automatisch in /app zu wechseln, falls dort installiert
if [ -d "/app/backend" ] && [ -d "/app/frontend" ]; then
  cd /app
  ROOT_DIR="/app"
fi

# Check if we're in the right directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
  echo -e "${RED}[ERROR] Bitte aus dem Projekt-Root ausführen (enthält backend/ und frontend/)${NC}"
  exit 1
fi

echo -e "${YELLOW}Step 1: Git Pull (neueste Änderungen)${NC}"
git pull origin main || {
  echo -e "${RED}[WARN] git pull fehlgeschlagen. Bitte manuell prüfen.${NC}"
}

echo ""
echo -e "${YELLOW}Step 2: Python Dependencies aktualisieren (Backend)${NC}"
cd "${ROOT_DIR}/backend"

# Check if virtual environment exists
if [ -d "venv" ]; then
  echo "[INFO] Aktiviere backend/venv ..."
  # shellcheck disable=SC1091
  source venv/bin/activate
elif [ -d "../venv" ]; then
  echo "[INFO] Aktiviere ../venv ..."
  # shellcheck disable=SC1091
  source ../venv/bin/activate
else
  echo -e "${YELLOW}[INFO] Keine virtuelle Umgebung gefunden – verwende System-Python.${NC}"
fi

echo "[INFO] Installiere/aktualisiere Python-Dependencies ..."
pip install --upgrade pip >/dev/null 2>&1 || true
pip install -r requirements.txt --upgrade || {
  echo -e "${RED}[WARN] Einige Python-Dependencies konnten nicht installiert werden.${NC}"
  echo "       Bitte ggf. manuell prüfen: backend/requirements.txt"
}

echo ""
echo -e "${YELLOW}Step 3: Schnellcheck neue Backend-Module (optional)${NC}"
python3 - << 'EOF' 2>/dev/null || echo -e "${YELLOW}[WARN] Optionaler Modul-Check fehlgeschlagen (kein harter Fehler).${NC}"
try:
    import feedparser
    import bs4  # beautifulsoup4
    import httpx
    from coin_analyzer import CoinAnalyzer
    from crypto_news_fetcher import CryptoNewsFetcher
    print("✓ Neue Backend-Module erfolgreich importiert")
except Exception as e:
    print(f"[WARN] Modul-Check: {e}")
EOF

cd "${ROOT_DIR}"

echo ""
echo -e "${YELLOW}Step 4: Frontend Dependencies aktualisieren${NC}"

if [ -d "frontend" ]; then
  cd frontend

  if command -v yarn >/dev/null 2>&1; then
    echo "[INFO] Aktualisiere Frontend-Dependencies mit yarn ..."
    yarn install --silent || echo -e "${YELLOW}[WARN] yarn install hatte Probleme – bitte Logs prüfen.${NC}"
  elif command -v npm >/dev/null 2>&1; then
    echo "[INFO] Aktualisiere Frontend-Dependencies mit npm ..."
    npm install --silent || echo -e "${YELLOW}[WARN] npm install hatte Probleme – bitte Logs prüfen.${NC}"
  else
    echo -e "${YELLOW}[WARN] Weder yarn noch npm verfügbar – Frontend-Dependencies wurden nicht aktualisiert.${NC}"
  fi

  cd "${ROOT_DIR}"
else
  echo -e "${YELLOW}[WARN] frontend/ Verzeichnis nicht gefunden – überspringe Frontend-Update.${NC}"
fi

echo ""
echo -e "${YELLOW}Step 5: Services neu starten (falls supervisor verfügbar)${NC}"
if command -v supervisorctl >/dev/null 2>&1; then
  echo "[INFO] Starte Backend neu ..."
  sudo supervisorctl restart cyphertrade-backend || echo -e "${YELLOW}[WARN] Backend konnte nicht über supervisorctl neu gestartet werden.${NC}"

  echo "[INFO] Starte Frontend neu ..."
  sudo supervisorctl restart cyphertrade-frontend || echo -e "${YELLOW}[WARN] Frontend konnte nicht über supervisorctl neu gestartet werden.${NC}"
else
  echo -e "${YELLOW}[INFO] supervisorctl nicht gefunden – bitte Backend & Frontend manuell neu starten.${NC}"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "Update abgeschlossen!"
echo "==========================================${NC}"
echo ""
echo "Aktualisierte Komponenten:"
echo "  ✓ Backend (Python-Code, Strategien, Autonome Bots, 24h-Stats)"
echo "  ✓ Frontend (React-Dashboard, neue Strategien & Anzeigen)"
echo ""
echo "Wichtige Features im aktuellen Stand:"
echo "  - Sicheres Krypto-News-System für NexusChat"
echo "  - Autonome Bot-Verwaltung & Coin-Analyse für CypherMind"
echo "  - Grid Trading Strategie"
echo "  - 24h-basierte Profit/Loss- und Volumen-Statistiken im Dashboard"
echo ""
echo "Hinweise:"
echo "  - Backend-Dependencies: siehe backend/requirements.txt"
echo "  - Für Produktions-Builds des Frontends gibt es zusätzliche Skripte wie:"
echo "      rebuild-frontend-now.sh, reload-frontend-now.sh"
echo "  - Nach dem Update Browser-Cache ggf. mit Strg+Shift+R leeren."
echo ""

