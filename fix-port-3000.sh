#!/bin/bash
# Behebt Port 3000 Problem - beendet alle Prozesse auf Port 3000

set -e

echo "=== Port 3000 Problem beheben ==="
echo ""

# 1. Frontend stoppen
echo "[INFO] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true

# 2. Finde alle Prozesse auf Port 3000
echo "[INFO] Suche Prozesse auf Port 3000..."
PORT_3000_PIDS=$(sudo lsof -ti:3000 2>/dev/null || true)

if [ -n "$PORT_3000_PIDS" ]; then
    echo "[WARNING] Gefundene Prozesse auf Port 3000:"
    sudo lsof -i:3000 | grep LISTEN || true
    echo ""
    echo "[INFO] Beende Prozesse auf Port 3000..."
    for PID in $PORT_3000_PIDS; do
        echo "  Beende Prozess $PID..."
        sudo kill -9 $PID 2>/dev/null || true
    done
    sleep 2
    echo "[SUCCESS] Prozesse auf Port 3000 beendet"
else
    echo "[SUCCESS] Keine Prozesse auf Port 3000 gefunden"
fi

# 3. Prüfe ob Port 3000 jetzt frei ist
echo "[INFO] Prüfe ob Port 3000 frei ist..."
if sudo lsof -ti:3000 > /dev/null 2>&1; then
    echo "[WARNING] Port 3000 ist immer noch belegt!"
    echo "[INFO] Versuche alle Node.js Prozesse zu beenden..."
    sudo pkill -9 node 2>/dev/null || true
    sleep 2
else
    echo "[SUCCESS] Port 3000 ist jetzt frei"
fi

# 4. Prüfe Frontend .env
echo "[INFO] Prüfe Frontend .env..."
cd /app/frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

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

# 5. Prüfe ob Yarn verfügbar ist
echo "[INFO] Prüfe Yarn Installation:"
if ! command -v yarn > /dev/null 2>&1; then
    echo "[ERROR] Yarn nicht gefunden!"
    exit 1
fi
YARN_PATH=$(which yarn)
echo "[SUCCESS] Yarn gefunden bei: $YARN_PATH"

# 6. Aktualisiere Supervisor Config
echo "[INFO] Aktualisiere Supervisor Config..."
sudo tee /etc/supervisor/conf.d/cyphertrade-frontend.conf > /dev/null << EOF
[program:cyphertrade-frontend]
directory=/app/frontend
command=$YARN_PATH start
user=root
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/cyphertrade-frontend-error.log
stdout_logfile=/var/log/supervisor/cyphertrade-frontend.log
environment=REACT_APP_BACKEND_URL="http://192.168.178.154:8001",NODE_ENV="development",GENERATE_SOURCEMAP="false",DISABLE_HOT_RELOAD="true",FAST_REFRESH="false",WDS_SOCKET_HOST="",PATH="$(echo $PATH)"
stopwaitsecs=10
killasgroup=true
priority=998
EOF

echo "[SUCCESS] Supervisor Config aktualisiert"

# 7. Reload Supervisor
echo "[INFO] Lade Supervisor neu..."
sudo supervisorctl reread
sudo supervisorctl update

# 8. Warte kurz
echo "[INFO] Warte 3 Sekunden..."
sleep 3

# 9. Prüfe ob Port 3000 frei ist
if sudo lsof -ti:3000 > /dev/null 2>&1; then
    echo "[ERROR] Port 3000 ist immer noch belegt!"
    echo "[INFO] Versuche alle Node.js Prozesse zu beenden..."
    sudo pkill -9 node 2>/dev/null || true
    sleep 2
fi

# 10. Starte Frontend
echo "[INFO] Starte Frontend..."
sudo supervisorctl start cyphertrade-frontend

# 11. Prüfe Status
echo ""
echo "[INFO] Frontend Status:"
sleep 3
sudo supervisorctl status cyphertrade-frontend

# 12. Prüfe ob Port 3000 jetzt belegt ist (sollte sein wenn Frontend läuft)
echo ""
echo "[INFO] Prüfe Port 3000 Status:"
if sudo lsof -ti:3000 > /dev/null 2>&1; then
    echo "[SUCCESS] Port 3000 ist belegt (Frontend läuft vermutlich)"
    sudo lsof -i:3000 | grep LISTEN || true
else
    echo "[WARNING] Port 3000 ist nicht belegt (Frontend läuft möglicherweise nicht)"
fi

echo ""
echo "=== Zusammenfassung ==="
echo ""
echo "Port 3000 sollte jetzt frei sein und Frontend sollte starten."
echo ""
echo "Falls Frontend immer noch nicht startet:"
echo "  tail -50 /var/log/supervisor/cyphertrade-frontend-error.log"
echo "  tail -50 /var/log/supervisor/cyphertrade-frontend.log"
echo ""

