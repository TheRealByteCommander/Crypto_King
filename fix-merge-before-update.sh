#!/bin/bash
# Behebt Git Merge-Konflikte BEVOR up.sh ausgeführt wird
# Kurzer Dateiname für einfache Ausführung

set -e

echo "=========================================="
echo "Git Merge-Konflikt beheben (vor Update)"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Versuche automatisch in /app zu wechseln
if [ -d "/app/backend" ] && [ -d "/app/frontend" ]; then
  cd /app
  ROOT_DIR="/app"
else
  ROOT_DIR="$(pwd)"
fi

# Prüfe ob wir im richtigen Verzeichnis sind
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
  echo -e "${RED}[ERROR] Bitte aus dem Projekt-Root ausführen (enthält backend/ und frontend/)${NC}"
  exit 1
fi

echo -e "${YELLOW}Step 1: Prüfe Git-Status${NC}"
git status --short || {
  echo -e "${RED}[ERROR] Git-Status konnte nicht abgerufen werden.${NC}"
  exit 1
}

echo ""
echo -e "${YELLOW}Step 2: Stashe lokale Änderungen${NC}"
GIT_STATUS=$(git status --porcelain 2>/dev/null || echo "")
if [ -n "$GIT_STATUS" ]; then
  echo "[INFO] Lokale Änderungen gefunden. Stashe sie..."
  git stash push -m "Auto-stash vor Update $(date +%Y-%m-%d_%H:%M:%S)" || {
    echo -e "${RED}[ERROR] Stash fehlgeschlagen.${NC}"
    exit 1
  }
  echo -e "${GREEN}[OK] Lokale Änderungen wurden gestasht.${NC}"
else
  echo "[INFO] Keine lokalen Änderungen gefunden."
fi

echo ""
echo -e "${YELLOW}Step 3: Prüfe Branch${NC}"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
if [ "$CURRENT_BRANCH" != "main" ]; then
  echo -e "${YELLOW}[WARN] Aktueller Branch: $CURRENT_BRANCH (erwartet: main)${NC}"
  echo "[INFO] Wechsle zu main..."
  git checkout main || {
    echo -e "${RED}[ERROR] Branch-Wechsel fehlgeschlagen.${NC}"
    exit 1
  }
  echo -e "${GREEN}[OK] Auf Branch 'main' gewechselt.${NC}"
else
  echo -e "${GREEN}[OK] Bereits auf Branch 'main'.${NC}"
fi

echo ""
echo -e "${YELLOW}Step 4: Breche laufende Merges ab (falls vorhanden)${NC}"
if [ -f ".git/MERGE_HEAD" ]; then
  echo "[INFO] Laufender Merge erkannt. Breche ab..."
  git merge --abort 2>/dev/null || true
  echo -e "${GREEN}[OK] Merge abgebrochen.${NC}"
else
  echo "[INFO] Kein laufender Merge gefunden."
fi

echo ""
echo -e "${YELLOW}Step 5: Hole neueste Änderungen${NC}"
echo "[INFO] Führe git fetch aus..."
git fetch origin main || {
  echo -e "${RED}[ERROR] git fetch fehlgeschlagen.${NC}"
  exit 1
}

echo ""
echo "[INFO] Setze auf Remote-State zurück (origin/main)..."
git reset --hard origin/main || {
  echo -e "${RED}[ERROR] git reset fehlgeschlagen.${NC}"
  echo ""
  echo -e "${RED}=== MANUELLE LÖSUNG ERFORDERLICH ===${NC}"
  echo "Bitte manuell ausführen:"
  echo "  cd $ROOT_DIR"
  echo "  git status"
  echo "  git stash"
  echo "  git fetch origin main"
  echo "  git reset --hard origin/main"
  exit 1
}

echo ""
echo -e "${GREEN}[OK] Repository erfolgreich auf origin/main zurückgesetzt.${NC}"
LATEST_COMMIT=$(git log -1 --oneline 2>/dev/null || echo "unknown")
echo "[INFO] Neuester Commit: $LATEST_COMMIT"

echo ""
echo -e "${GREEN}=========================================="
echo "Merge-Konflikt behoben!"
echo "==========================================${NC}"
echo ""
if [ -n "$GIT_STATUS" ]; then
  echo -e "${YELLOW}⚠ HINWEIS: Lokale Änderungen wurden gestasht!${NC}"
  echo "  Falls du diese Änderungen brauchst, führe aus:"
  echo "    git stash list    # Zeige alle Stashes"
  echo "    git stash pop     # Stelle letzte Änderungen wieder her"
  echo ""
fi
echo "Du kannst jetzt ./up.sh ausführen, um das Update fortzusetzen."
echo ""

