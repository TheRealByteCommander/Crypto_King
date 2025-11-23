#!/bin/bash
# Behebt WDS_SOCKET_HOST Problem - entfernt leeren WDS_SOCKET_HOST aus .env

set -e

echo "=== WDS_SOCKET_HOST Problem beheben ==="
echo ""

# 1. Frontend stoppen
echo "[INFO] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true

# 2. Befreie Port 3000
echo "[INFO] Befreie Port 3000..."
PORT_3000_PIDS=$(sudo lsof -ti:3000 2>/dev/null || true)
if [ -n "$PORT_3000_PIDS" ]; then
    for PID in $PORT_3000_PIDS; do
        echo "  Beende Prozess $PID..."
        sudo kill -9 $PID 2>/dev/null || true
    done
    sleep 2
fi

# 3. Prüfe Frontend .env
echo "[INFO] Prüfe und aktualisiere Frontend .env..."
cd /app/frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

if [ -f ".env" ]; then
    echo "[INFO] Entferne WDS_SOCKET_HOST aus .env..."
    # Entferne WDS_SOCKET_HOST Zeile (auch wenn leer)
    sed -i '/^WDS_SOCKET_HOST/d' .env
    sed -i '/^WDS_SOCKET_HOST=/d' .env
    
    # Stelle sicher, dass wichtige Variablen vorhanden sind
    if ! grep -q "^REACT_APP_BACKEND_URL" .env; then
        echo "REACT_APP_BACKEND_URL=http://192.168.178.154:8001" >> .env
    fi
    if ! grep -q "^DISABLE_HOT_RELOAD" .env; then
        echo "DISABLE_HOT_RELOAD=true" >> .env
    fi
    if ! grep -q "^FAST_REFRESH" .env; then
        echo "FAST_REFRESH=false" >> .env
    fi
    
    echo "[SUCCESS] .env aktualisiert (WDS_SOCKET_HOST entfernt)"
    echo "[INFO] Aktuelle .env Inhalte:"
    cat .env
else
    echo "[WARNING] .env nicht gefunden, erstelle sie..."
    cat > .env << 'ENVEOF'
REACT_APP_BACKEND_URL=http://192.168.178.154:8001
GENERATE_SOURCEMAP=false
DISABLE_HOT_RELOAD=true
FAST_REFRESH=false
ENVEOF
fi

# 4. Prüfe ob Yarn verfügbar ist
if ! command -v yarn > /dev/null 2>&1; then
    echo "[ERROR] Yarn nicht gefunden!"
    exit 1
fi
YARN_PATH=$(which yarn)

# 5. Aktualisiere Supervisor Config (ohne WDS_SOCKET_HOST)
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
environment=REACT_APP_BACKEND_URL="http://192.168.178.154:8001",NODE_ENV="development",GENERATE_SOURCEMAP="false",DISABLE_HOT_RELOAD="true",FAST_REFRESH="false",PATH="$(echo $PATH)"
stopwaitsecs=10
killasgroup=true
priority=998
EOF

echo "[SUCCESS] Supervisor Config aktualisiert (WDS_SOCKET_HOST entfernt)"

# 6. Reload Supervisor
echo "[INFO] Lade Supervisor neu..."
sudo supervisorctl reread
sudo supervisorctl update

# 7. Warte kurz
sleep 3

# 8. Prüfe ob Port 3000 frei ist
if sudo lsof -ti:3000 > /dev/null 2>&1; then
    echo "[WARNING] Port 3000 ist immer noch belegt!"
    sudo lsof -i:3000 | grep LISTEN || true
    sudo pkill -9 -f "node.*craco\|node.*react-scripts" 2>/dev/null || true
    sleep 2
fi

# 9. Starte Frontend
echo "[INFO] Starte Frontend..."
sudo supervisorctl start cyphertrade-frontend

# 10. Warte und prüfe Status
sleep 5
echo ""
echo "[INFO] Frontend Status:"
sudo supervisorctl status cyphertrade-frontend

echo ""
echo "=== Zusammenfassung ==="
echo ""
echo "WDS_SOCKET_HOST wurde aus .env entfernt."
echo "Frontend sollte jetzt ohne WebSocket-Konfigurationsfehler starten."
echo ""
echo "Falls Frontend immer noch nicht startet:"
echo "  tail -50 /var/log/supervisor/cyphertrade-frontend-error.log"
echo ""

