#!/bin/bash
# Frontend Update mit Trading Mode - Stellt sicher, dass Trading Mode sichtbar ist

echo "=== Frontend Update - Trading Mode aktivieren ==="
echo ""

cd /app || { echo "[ERROR] Kann nicht nach /app wechseln!"; exit 1; }

# 1. Git Pull
echo "[INFO] Hole neueste Änderungen von GitHub..."
git stash 2>/dev/null || true
git pull origin main

if [ $? -ne 0 ]; then
    echo "[ERROR] Git pull fehlgeschlagen!"
    exit 1
fi

echo "[SUCCESS] Neueste Änderungen geladen"
echo ""

# 2. Prüfe ob Trading Mode im Code ist
echo "[INFO] Prüfe ob Trading Mode im Frontend Code vorhanden ist..."
if grep -q "tradingMode" frontend/src/components/BotControl.js 2>/dev/null; then
    echo "[SUCCESS] Trading Mode Code gefunden ✓"
else
    echo "[ERROR] Trading Mode Code NICHT gefunden!"
    echo "[INFO] Prüfe ob Frontend Code aktualisiert wurde..."
    exit 1
fi
echo ""

# 3. Frontend-Verzeichnis
cd frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

# 4. Installiere/Update Dependencies
echo "[INFO] Installiere/Update Frontend Dependencies..."
yarn install --silent 2>/dev/null || yarn install
echo "[SUCCESS] Dependencies aktualisiert"
echo ""

# 5. Prüfe ob Production Build existiert
BUILD_EXISTS=false
if [ -d "build" ]; then
    BUILD_EXISTS=true
    echo "[INFO] Production Build vorhanden - wird aktualisiert"
else
    echo "[INFO] Kein Production Build vorhanden - Development Modus"
fi

# 6. Stoppe Frontend
echo "[INFO] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true
sleep 2

# 7. Lösche alten Build (falls vorhanden)
if [ "$BUILD_EXISTS" = true ]; then
    echo "[INFO] Lösche alten Production Build..."
    rm -rf build
    echo "[SUCCESS] Alter Build gelöscht"
fi

# 8. Erstelle Production Build
echo "[INFO] Erstelle Production Build (kann einige Minuten dauern)..."
cat > .env.production << 'EOF'
REACT_APP_BACKEND_URL=http://192.168.178.154:8001
GENERATE_SOURCEMAP=false
NODE_ENV=production
EOF

NODE_ENV=production yarn build

if [ $? -ne 0 ]; then
    echo "[ERROR] Build fehlgeschlagen!"
    echo "[INFO] Versuche Development-Modus..."
    
    # Fallback zu Development
    cat > .env << EOF
REACT_APP_BACKEND_URL=http://192.168.178.154:8001
GENERATE_SOURCEMAP=false
EOF
    
    cd /app
    sudo tee /etc/supervisor/conf.d/cyphertrade-frontend.conf > /dev/null << 'EOF'
[program:cyphertrade-frontend]
directory=/app/frontend
command=yarn start
user=root
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/cyphertrade-frontend-error.log
stdout_logfile=/var/log/supervisor/cyphertrade-frontend.log
environment=REACT_APP_BACKEND_URL="http://192.168.178.154:8001",NODE_ENV="development"
stopwaitsecs=10
killasgroup=true
priority=998
EOF
    
    sudo supervisorctl reread
    sudo supervisorctl update
    sudo supervisorctl start cyphertrade-frontend
    
    echo "[INFO] Frontend läuft im Development-Modus"
    exit 0
fi

echo "[SUCCESS] Production Build erstellt!"
echo ""

# 9. Prüfe ob Trading Mode im Build ist
echo "[INFO] Prüfe ob Trading Mode im Build vorhanden ist..."
if grep -r "tradingMode\|Trading Mode" build/static/js/*.js 2>/dev/null | head -1 > /dev/null; then
    echo "[SUCCESS] Trading Mode im Build gefunden ✓"
else
    echo "[WARNING] Trading Mode möglicherweise nicht im Build (kann bei Minification normal sein)"
fi
echo ""

# 10. Konfiguriere Supervisor für Production Build
cd /app
echo "[INFO] Konfiguriere Supervisor für Production Build..."

# Installiere serve falls nötig
if ! command -v serve > /dev/null 2>&1; then
    echo "[INFO] Installiere 'serve'..."
    npm install -g serve 2>/dev/null || yarn global add serve 2>/dev/null || true
fi

SERVE_PATH=$(which serve || echo "/usr/local/bin/serve")

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

echo "[SUCCESS] Supervisor konfiguriert"
echo ""

# 11. Starte Frontend
echo "[INFO] Starte Frontend..."
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start cyphertrade-frontend

# 12. Warte und prüfe Status
echo ""
echo "[INFO] Warte 5 Sekunden auf Start..."
sleep 5

FRONTEND_STATUS=$(sudo supervisorctl status cyphertrade-frontend | grep -o "RUNNING\|STOPPED\|FATAL\|ERROR" || echo "UNBEKANNT")
echo ""
echo "[INFO] Frontend Status: $FRONTEND_STATUS"
echo ""

# 13. Zusammenfassung
echo "=== Update abgeschlossen ==="
echo ""
if [ "$FRONTEND_STATUS" = "RUNNING" ]; then
    echo "✅ Frontend läuft erfolgreich!"
    echo ""
    echo "Nächste Schritte:"
    echo "1. Browser-Cache leeren:"
    echo "   - Drücke Strg + Shift + R (Hard Reload)"
    echo "   - Oder: Strg + F5"
    echo ""
    echo "2. Prüfe 'Start New Bot' Formular:"
    echo "   - Trading Mode sollte zwischen 'Timeframe' und 'Amount' sein"
    echo ""
    echo "3. Falls Trading Mode immer noch nicht sichtbar:"
    echo "   - Browser komplett neu starten"
    echo "   - Cache komplett leeren (F12 → Application → Clear Storage)"
else
    echo "❌ Frontend läuft nicht!"
    echo ""
    echo "Prüfe Logs:"
    echo "  tail -50 /var/log/supervisor/cyphertrade-frontend-error.log"
fi
echo ""

