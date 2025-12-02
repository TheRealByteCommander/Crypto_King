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

# Prüfe Git-Status und Flag für gestashte Änderungen
HAD_LOCAL_CHANGES=0
GIT_STATUS=$(git status --porcelain 2>/dev/null || echo "")
if [ -n "$GIT_STATUS" ]; then
  HAD_LOCAL_CHANGES=1
  echo -e "${YELLOW}[WARN] Lokale Änderungen gefunden. Diese werden gestasht.${NC}"
  git stash push -m "Auto-stash vor Update $(date +%Y-%m-%d_%H:%M:%S)" || {
    echo -e "${RED}[ERROR] Stash fehlgeschlagen. Bitte manuell prüfen.${NC}"
    exit 1
  }
  echo -e "${GREEN}[OK] Lokale Änderungen wurden gestasht.${NC}"
fi

# Prüfe ob wir auf dem richtigen Branch sind
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
if [ "$CURRENT_BRANCH" != "main" ]; then
  echo -e "${YELLOW}[WARN] Aktueller Branch: $CURRENT_BRANCH (erwartet: main)${NC}"
  echo -e "${YELLOW}[INFO] Wechsle zu main...${NC}"
  git checkout main || {
    echo -e "${RED}[ERROR] Branch-Wechsel fehlgeschlagen.${NC}"
    exit 1
  }
fi

# Git Pull mit Merge-Konflikt-Behandlung
echo "[INFO] Hole neueste Änderungen von origin/main..."
if ! git pull origin main; then
  echo -e "${YELLOW}[WARN] git pull hatte Probleme. Versuche Merge-Konflikt zu lösen...${NC}"
  
  # Prüfe ob es einen laufenden Merge gibt
  if [ -f ".git/MERGE_HEAD" ]; then
    echo "[INFO] Laufender Merge erkannt. Breche Merge ab..."
    git merge --abort 2>/dev/null || true
  fi
  
  # Versuche Reset auf Remote-State (ACHTUNG: überschreibt lokale Änderungen)
  echo "[INFO] Setze auf Remote-State zurück (origin/main)..."
  git fetch origin main || {
    echo -e "${RED}[ERROR] git fetch fehlgeschlagen.${NC}"
    exit 1
  }
  
  git reset --hard origin/main || {
    echo -e "${RED}[ERROR] git reset fehlgeschlagen.${NC}"
    echo ""
    echo -e "${RED}=== MANUELLE LÖSUNG ERFORDERLICH ===${NC}"
    echo "Bitte auf dem Server manuell ausführen:"
    echo "  cd /app"
    echo "  git status"
    echo "  git stash"
    echo "  git pull origin main"
    echo "  # Falls weiterhin Probleme:"
    echo "  git reset --hard origin/main"
    exit 1
  }
  
  echo -e "${GREEN}[OK] Repository erfolgreich auf origin/main zurückgesetzt.${NC}"
fi

echo -e "${GREEN}[OK] Git Pull erfolgreich abgeschlossen.${NC}"
LATEST_COMMIT=$(git log -1 --oneline 2>/dev/null || echo "unknown")
echo "[INFO] Neuester Commit: $LATEST_COMMIT"

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
if [ "$HAD_LOCAL_CHANGES" = "1" ]; then
  echo -e "${YELLOW}⚠ WICHTIG: Lokale Änderungen wurden gestasht!${NC}"
  echo "  Falls du diese Änderungen brauchst, führe aus:"
  echo "    git stash list    # Zeige alle Stashes"
  echo "    git stash pop     # Stelle letzte Änderungen wieder her"
  echo ""
fi

