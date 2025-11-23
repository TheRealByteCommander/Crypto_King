#!/bin/bash
# Fix: Trading Mode sichtbar machen - Erstellt neuen Production Build und konfiguriert richtig

echo "=== Trading Mode sichtbar machen ==="
echo ""

cd /app || { echo "[ERROR] Kann nicht nach /app wechseln!"; exit 1; }

# 1. Git Pull (sicherstellen dass neueste Version da ist)
echo "[INFO] Hole neueste Änderungen..."
git pull origin main
echo ""

# 2. Stoppe Frontend
echo "[INFO] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true
sleep 2

# 3. Frontend Verzeichnis
cd frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

# 4. Prüfe ob Trading Mode im Code ist
echo "[INFO] Prüfe Trading Mode im Code..."
if ! grep -q "tradingMode" src/components/BotControl.js 2>/dev/null; then
    echo "[ERROR] Trading Mode nicht im Code gefunden!"
    exit 1
fi
echo "[SUCCESS] Trading Mode im Code vorhanden ✓"
echo ""

# 5. Installiere Dependencies
echo "[INFO] Installiere/Update Dependencies..."
yarn install --silent 2>/dev/null || yarn install
echo ""

# 6. Lösche alten Build komplett
echo "[INFO] Lösche alten Build..."
rm -rf build .cache 2>/dev/null || true
echo "[SUCCESS] Alter Build gelöscht"
echo ""

# 7. Erstelle .env.production
echo "[INFO] Erstelle .env.production..."
cat > .env.production << 'EOF'
REACT_APP_BACKEND_URL=http://192.168.178.154:8001
GENERATE_SOURCEMAP=false
NODE_ENV=production
EOF

# 8. Erstelle neuen Production Build
echo "[INFO] Erstelle Production Build (kann 2-3 Minuten dauern)..."
echo "      Bitte warten..."
NODE_ENV=production yarn build

if [ $? -ne 0 ]; then
    echo "[ERROR] Build fehlgeschlagen!"
    echo "[INFO] Prüfe Logs oben für Fehler"
    exit 1
fi

# 9. Prüfe ob Build erstellt wurde
if [ ! -d "build" ] || [ ! -f "build/index.html" ]; then
    echo "[ERROR] Build-Verzeichnis wurde nicht erstellt!"
    exit 1
fi

echo "[SUCCESS] Production Build erstellt ✓"
BUILD_SIZE=$(du -sh build | cut -f1)
echo "[INFO] Build-Größe: $BUILD_SIZE"
echo ""

# 10. Prüfe ob Trading Mode im Build ist
echo "[INFO] Prüfe Trading Mode im Build..."
BUILD_FILES=$(find build/static/js -name "*.js" 2>/dev/null | head -1)
if [ -n "$BUILD_FILES" ]; then
    if grep -q "tradingMode\|Trading Mode" "$BUILD_FILES" 2>/dev/null; then
        echo "[SUCCESS] Trading Mode im Build gefunden ✓"
    else
        echo "[WARNING] Trading Mode nicht in Build-JS gefunden (kann bei Minification normal sein)"
    fi
fi
echo ""

# 11. Installiere serve falls nötig
echo "[INFO] Prüfe 'serve' Installation..."
if ! command -v serve > /dev/null 2>&1; then
    echo "[INFO] Installiere 'serve'..."
    npm install -g serve 2>/dev/null || yarn global add serve 2>/dev/null
fi

SERVE_PATH=$(which serve || echo "/usr/local/bin/serve")
echo "[INFO] Serve-Pfad: $SERVE_PATH"
echo ""

# 12. Konfiguriere Supervisor für Production Build
cd /app
echo "[INFO] Konfiguriere Supervisor für Production Build..."

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

echo "[SUCCESS] Supervisor Config aktualisiert"
echo ""

# 13. Lade Supervisor neu
echo "[INFO] Lade Supervisor neu..."
sudo supervisorctl reread 2>/dev/null | grep -v "pkg_resources" || true
sudo supervisorctl update 2>/dev/null | grep -v "pkg_resources" || true
echo ""

# 14. Starte Frontend
echo "[INFO] Starte Frontend..."
sudo supervisorctl start cyphertrade-frontend

# 15. Warte und prüfe
echo ""
echo "[INFO] Warte 5 Sekunden..."
sleep 5

FRONTEND_STATUS=$(sudo supervisorctl status cyphertrade-frontend 2>/dev/null | grep -o "RUNNING\|STOPPED\|FATAL\|ERROR" || echo "UNBEKANNT")

echo ""
echo "=== Ergebnis ==="
echo ""
echo "Frontend Status: $FRONTEND_STATUS"
echo ""

if [ "$FRONTEND_STATUS" = "RUNNING" ]; then
    echo "✅ Frontend läuft!"
    echo ""
    echo "=== WICHTIG: Browser-Cache leeren ==="
    echo ""
    echo "1. Im Browser:"
    echo "   - Drücke: Strg + Shift + R (Hard Reload)"
    echo "   - Oder: Strg + F5"
    echo ""
    echo "2. Falls das nicht hilft:"
    echo "   - Browser komplett schließen"
    echo "   - Browser neu öffnen"
    echo "   - Strg + Shift + R drücken"
    echo ""
    echo "3. Oder Cache komplett leeren:"
    echo "   - F12 → Application Tab → Clear Storage"
    echo "   - 'Clear site data' klicken"
    echo ""
    echo "=== Prüfen ==="
    echo ""
    echo "Im 'Start New Bot' Formular sollte jetzt erscheinen:"
    echo "  - Strategy: [Dropdown]"
    echo "  - Symbol: [Input]"
    echo "  - Timeframe: [Dropdown]"
    echo "  - Trading Mode: [Dropdown] ← NEU!"
    echo "  - Amount: [Input]"
    echo ""
else
    echo "❌ Frontend läuft nicht!"
    echo ""
    echo "Prüfe Logs:"
    echo "  tail -50 /var/log/supervisor/cyphertrade-frontend-error.log"
    echo "  tail -50 /var/log/supervisor/cyphertrade-frontend.log"
fi
echo ""

