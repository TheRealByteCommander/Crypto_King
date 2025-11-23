#!/bin/bash
# FINAL FIX - Trading Mode sichtbar machen - Komplette Lösung

set -e  # Exit on error

echo "═══════════════════════════════════════════════════════════"
echo "  FINAL FIX: Trading Mode sichtbar machen"
echo "═══════════════════════════════════════════════════════════"
echo ""

cd /app || { echo "[ERROR] Kann nicht nach /app wechseln!"; exit 1; }

# ============================================
# 1. Prüfe Frontend-Mode
# ============================================
echo "[1/8] Prüfe Frontend-Mode..."
SUPERVISOR_CONFIG="/etc/supervisor/conf.d/cyphertrade-frontend.conf"
if [ -f "$SUPERVISOR_CONFIG" ]; then
    if grep -q "serve.*build" "$SUPERVISOR_CONFIG"; then
        echo "  ✓ Frontend läuft mit 'serve' (Production Mode)"
    else
        echo "  ⚠ Frontend läuft NICHT im Production Mode!"
        echo "  → Wird im Script korrigiert..."
    fi
else
    echo "  ⚠ Supervisor Config nicht gefunden"
fi
echo ""

# ============================================
# 2. Stoppe Frontend und alle Prozesse
# ============================================
echo "[2/8] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true

# Töte alle Frontend-Prozesse
pkill -f "yarn start" 2>/dev/null || true
pkill -f "craco start" 2>/dev/null || true
pkill -f "react-scripts" 2>/dev/null || true
sleep 3
echo "  ✓ Frontend gestoppt"
echo ""

# ============================================
# 3. Git Pull (neueste Version)
# ============================================
echo "[3/8] Hole neueste Version vom Repository..."
git pull origin main
echo "  ✓ Git Pull abgeschlossen"
echo ""

# ============================================
# 4. Prüfe Code-Version
# ============================================
echo "[4/8] Prüfe Code-Version..."
cd frontend

if ! grep -q "const \[tradingMode, setTradingMode\]" src/components/BotControl.js 2>/dev/null; then
    echo "  ✗ Trading Mode State nicht im Code gefunden!"
    exit 1
fi

if ! grep -q "grid-cols-1 md:grid-cols-3" src/components/BotControl.js 2>/dev/null; then
    echo "  ✗ Neues Grid-Layout (3 Spalten) nicht im Code gefunden!"
    exit 1
fi

if ! grep -q "Trading Mode.*SPOT/MARGIN/FUTURES" src/components/BotControl.js 2>/dev/null; then
    echo "  ✗ Trading Mode Label nicht im Code gefunden!"
    exit 1
fi

echo "  ✓ Code-Version korrekt (neue Version mit Trading Mode)"
echo ""

# ============================================
# 5. Lösche ALLES (Build, Cache, etc.)
# ============================================
echo "[5/8] Lösche Build und alle Caches..."
rm -rf build .cache node_modules/.cache 2>/dev/null || true
yarn cache clean 2>/dev/null || true
echo "  ✓ Alles gelöscht"
echo ""

# ============================================
# 6. Installiere Dependencies
# ============================================
echo "[6/8] Installiere Dependencies..."
yarn install --silent 2>/dev/null || yarn install
echo "  ✓ Dependencies installiert"
echo ""

# ============================================
# 7. Erstelle neuen Production Build
# ============================================
echo "[7/8] Erstelle neuen Production Build..."
echo "  → Dies kann 2-3 Minuten dauern..."
echo ""

# Setze Environment Variables
export NODE_ENV=production
export GENERATE_SOURCEMAP=false

# Erstelle .env.production
cat > .env.production << 'EOF'
REACT_APP_BACKEND_URL=http://192.168.178.154:8001
GENERATE_SOURCEMAP=false
NODE_ENV=production
EOF

# Build
yarn build

if [ $? -ne 0 ]; then
    echo "  ✗ Build fehlgeschlagen!"
    exit 1
fi

if [ ! -d "build" ] || [ ! -f "build/index.html" ]; then
    echo "  ✗ Build-Verzeichnis wurde nicht erstellt!"
    exit 1
fi

BUILD_SIZE=$(du -sh build | cut -f1)
echo "  ✓ Build erstellt ($BUILD_SIZE)"
echo ""

# Prüfe Trading Mode im Build
MAIN_JS=$(find build/static/js -name "main.*.js" | head -1)
if [ -n "$MAIN_JS" ]; then
    if grep -q "tradingMode\|Trading Mode" "$MAIN_JS" 2>/dev/null; then
        echo "  ✓ Trading Mode im Build gefunden"
    else
        echo "  ⚠ Trading Mode im Build nicht gefunden (kann bei Minification sein)"
    fi
    
    # Prüfe Grid-Layout im Build
    if grep -q "md:grid-cols-3" "$MAIN_JS" 2>/dev/null; then
        echo "  ✓ Neues Grid-Layout (3+2) im Build gefunden"
    else
        echo "  ⚠ Grid-Layout könnte alt sein"
    fi
fi
echo ""

# ============================================
# 8. Konfiguriere und starte Frontend
# ============================================
echo "[8/8] Konfiguriere und starte Frontend..."
cd /app

# Installiere serve falls nötig
if ! command -v serve > /dev/null 2>&1; then
    echo "  → Installiere 'serve'..."
    npm install -g serve 2>/dev/null || yarn global add serve 2>/dev/null
fi

SERVE_PATH=$(which serve || echo "/usr/local/bin/serve")

# Erstelle Supervisor Config für Production
sudo tee /etc/supervisor/conf.d/cyphertrade-frontend.conf > /dev/null << EOF
[program:cyphertrade-frontend]
directory=/app/frontend/build
command=$SERVE_PATH -s /app/frontend/build -l 3000
user=root
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/cyphertrade-frontend-error.log
stdout_logfile=/var/log/supervisor/cyphertrade-frontend.log
stopwaitsecs=10
killasgroup=true
priority=998
EOF

echo "  ✓ Supervisor Config aktualisiert"

# Lade Supervisor neu
sudo supervisorctl reread 2>/dev/null | grep -v "pkg_resources" || true
sudo supervisorctl update 2>/dev/null | grep -v "pkg_resources" || true

# Starte Frontend
sudo supervisorctl start cyphertrade-frontend

sleep 5

FRONTEND_STATUS=$(sudo supervisorctl status cyphertrade-frontend 2>/dev/null | grep -o "RUNNING\|STOPPED\|FATAL\|ERROR" || echo "UNBEKANNT")

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ERGEBNIS"
echo "═══════════════════════════════════════════════════════════"
echo ""

if [ "$FRONTEND_STATUS" = "RUNNING" ]; then
    echo "✅ Frontend Status: RUNNING"
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  WICHTIG: Browser-Cache leeren!"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "1. Browser komplett schließen (ALLE Tabs)"
    echo "2. Browser neu öffnen"
    echo "3. Strg + Shift + R (Hard Reload)"
    echo ""
    echo "ODER:"
    echo ""
    echo "1. F12 → Application Tab → Clear Storage"
    echo "2. 'Clear site data' klicken"
    echo "3. Seite neu laden (F5)"
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  Erwartetes Ergebnis"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "Im 'Start New Bot' Formular sollte jetzt erscheinen:"
    echo ""
    echo "  Zeile 1: Strategy | Symbol | Timeframe"
    echo "  Zeile 2: Trading Mode | Amount  ← NEU!"
    echo ""
    echo "═══════════════════════════════════════════════════════════"
else
    echo "❌ Frontend Status: $FRONTEND_STATUS"
    echo ""
    echo "Prüfe Logs:"
    echo "  tail -50 /var/log/supervisor/cyphertrade-frontend-error.log"
    echo "  tail -50 /var/log/supervisor/cyphertrade-frontend.log"
fi
echo ""

