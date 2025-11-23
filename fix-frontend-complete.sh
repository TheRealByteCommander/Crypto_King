#!/bin/bash
# Komplette Frontend-Fix - befreit Port 3000 und startet Frontend neu

set -e

echo "=== Komplette Frontend-Fix ==="
echo ""

# 1. Frontend stoppen
echo "[INFO] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true

# 2. Alle Prozesse auf Port 3000 beenden
echo "[INFO] Beende alle Prozesse auf Port 3000..."
PORT_3000_PIDS=$(sudo lsof -ti:3000 2>/dev/null || true)
if [ -n "$PORT_3000_PIDS" ]; then
    for PID in $PORT_3000_PIDS; do
        echo "  Beende Prozess $PID..."
        sudo kill -9 $PID 2>/dev/null || true
    done
    sleep 2
fi

# 3. Alle Node.js Prozesse beenden (nur falls nötig)
echo "[INFO] Prüfe Node.js Prozesse..."
NODE_PROCS=$(pgrep -f "node.*craco\|node.*react-scripts\|node.*yarn" || true)
if [ -n "$NODE_PROCS" ]; then
    echo "[INFO] Beende Node.js Prozesse..."
    sudo pkill -9 -f "node.*craco\|node.*react-scripts\|node.*yarn" 2>/dev/null || true
    sleep 2
fi

# 4. Prüfe Frontend Verzeichnis
echo "[INFO] Prüfe Frontend Verzeichnis..."
cd /app/frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

# 5. Prüfe und erstelle .env
echo "[INFO] Prüfe .env Datei..."
if [ ! -f ".env" ]; then
    echo "[WARNING] .env nicht gefunden, erstelle sie..."
    cat > .env << 'ENVEOF'
REACT_APP_BACKEND_URL=http://192.168.178.154:8001
GENERATE_SOURCEMAP=false
DISABLE_HOT_RELOAD=true
FAST_REFRESH=false
WDS_SOCKET_HOST=
ENVEOF
fi

# 6. Installiere Dependencies falls nötig
if [ ! -d "node_modules" ]; then
    echo "[INFO] Installiere Frontend Dependencies..."
    yarn install --frozen-lockfile || yarn install
fi

# 7. Prüfe ob Yarn verfügbar ist
if ! command -v yarn > /dev/null 2>&1; then
    echo "[ERROR] Yarn nicht gefunden!"
    exit 1
fi
YARN_PATH=$(which yarn)

# 8. Teste yarn start kurz (um Fehler zu sehen)
echo "[INFO] Teste yarn start (5 Sekunden)..."
cd /app/frontend
export REACT_APP_BACKEND_URL="http://192.168.178.154:8001"
export NODE_ENV="development"
export GENERATE_SOURCEMAP="false"
export DISABLE_HOT_RELOAD="true"
export FAST_REFRESH="false"
export WDS_SOCKET_HOST=""

# Führe yarn start aus und fange ersten Fehler
timeout 5 yarn start 2>&1 | head -50 || {
    echo "[INFO] yarn start beendet (normal nach timeout oder Fehler)"
}

# 9. Aktualisiere Supervisor Config mit startretries=0 für besseres Debugging
echo "[INFO] Aktualisiere Supervisor Config..."
sudo tee /etc/supervisor/conf.d/cyphertrade-frontend.conf > /dev/null << EOF
[program:cyphertrade-frontend]
directory=/app/frontend
command=$YARN_PATH start
user=root
autostart=true
autorestart=true
startretries=3
startsecs=5
stderr_logfile=/var/log/supervisor/cyphertrade-frontend-error.log
stdout_logfile=/var/log/supervisor/cyphertrade-frontend.log
environment=REACT_APP_BACKEND_URL="http://192.168.178.154:8001",NODE_ENV="development",GENERATE_SOURCEMAP="false",DISABLE_HOT_RELOAD="true",FAST_REFRESH="false",WDS_SOCKET_HOST="",PATH="$(echo $PATH)"
stopwaitsecs=10
killasgroup=true
priority=998
EOF

# 10. Reload Supervisor
echo "[INFO] Lade Supervisor neu..."
sudo supervisorctl reread
sudo supervisorctl update

# 11. Warte kurz
sleep 3

# 12. Prüfe ob Port 3000 frei ist
if sudo lsof -ti:3000 > /dev/null 2>&1; then
    echo "[WARNING] Port 3000 ist immer noch belegt!"
    sudo lsof -i:3000 | grep LISTEN || true
    echo "[INFO] Versuche alle Node.js Prozesse zu beenden..."
    sudo pkill -9 -f "node.*craco\|node.*react-scripts" 2>/dev/null || true
    sleep 2
fi

# 13. Starte Frontend
echo "[INFO] Starte Frontend..."
sudo supervisorctl start cyphertrade-frontend

# 14. Warte und prüfe Status
sleep 5
echo ""
echo "[INFO] Frontend Status:"
sudo supervisorctl status cyphertrade-frontend

# 15. Prüfe Logs
echo ""
echo "[INFO] Letzte 20 Zeilen aus Error Logs:"
tail -20 /var/log/supervisor/cyphertrade-frontend-error.log 2>/dev/null || echo "  Keine Error-Logs"

echo ""
echo "[INFO] Letzte 20 Zeilen aus Logs:"
tail -20 /var/log/supervisor/cyphertrade-frontend.log 2>/dev/null || echo "  Keine Logs"

echo ""
echo "=== Zusammenfassung ==="
echo ""
echo "Falls Frontend immer noch nicht startet, prüfe die Logs:"
echo "  tail -100 /var/log/supervisor/cyphertrade-frontend-error.log"
echo "  tail -100 /var/log/supervisor/cyphertrade-frontend.log"
echo ""
echo "Oder führe yarn start manuell aus:"
echo "  cd /app/frontend"
echo "  export REACT_APP_BACKEND_URL='http://192.168.178.154:8001'"
echo "  export NODE_ENV='development'"
echo "  yarn start"
echo ""

