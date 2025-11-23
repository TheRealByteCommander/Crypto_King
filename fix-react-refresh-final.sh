#!/bin/bash
# Behebt React Refresh Error endgültig

set -e

echo "=== React Refresh Error endgültig beheben ==="
echo ""

# 1. Frontend stoppen
echo "[INFO] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true

# 2. Aktualisiere Frontend .env mit DISABLE_HOT_RELOAD
echo "[INFO] Aktualisiere Frontend .env..."
cd /app/frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

# Füge DISABLE_HOT_RELOAD und FAST_REFRESH hinzu
if [ -f ".env" ]; then
    # Entferne alte Zeilen falls vorhanden
    sed -i '/^DISABLE_HOT_RELOAD/d' .env
    sed -i '/^FAST_REFRESH/d' .env
    sed -i '/^WDS_SOCKET_HOST/d' .env
    # Füge neue hinzu
    echo "DISABLE_HOT_RELOAD=true" >> .env
    echo "FAST_REFRESH=false" >> .env
    echo "WDS_SOCKET_HOST=" >> .env
else
    cat > .env << 'ENVEOF'
REACT_APP_BACKEND_URL=http://192.168.178.154:8001
GENERATE_SOURCEMAP=false
DISABLE_HOT_RELOAD=true
FAST_REFRESH=false
WDS_SOCKET_HOST=
ENVEOF
fi

echo "[SUCCESS] .env aktualisiert (DISABLE_HOT_RELOAD=true)"

# 3. Lösche build Verzeichnis falls vorhanden (entfernt gecachte Production Bundles)
echo "[INFO] Lösche build Verzeichnis..."
rm -rf build dist 2>/dev/null || true
echo "[SUCCESS] Build-Verzeichnis gelöscht"

# 4. Prüfe ob Yarn verfügbar ist
echo "[INFO] Prüfe Yarn Installation:"
if ! command -v yarn > /dev/null 2>&1; then
    echo "[ERROR] Yarn nicht gefunden!"
    exit 1
fi
YARN_PATH=$(which yarn)
echo "[SUCCESS] Yarn gefunden bei: $YARN_PATH"

# 5. Aktualisiere Supervisor Config
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

# 6. Reload Supervisor
echo "[INFO] Lade Supervisor neu..."
sudo supervisorctl reread
sudo supervisorctl update

# 7. Starte Frontend
echo "[INFO] Starte Frontend..."
sleep 3
sudo supervisorctl start cyphertrade-frontend

# 8. Prüfe Status
echo ""
echo "[INFO] Frontend Status:"
sleep 3
sudo supervisorctl status cyphertrade-frontend

echo ""
echo "=== Zusammenfassung ==="
echo ""
echo "Frontend wurde neu konfiguriert:"
echo "- DISABLE_HOT_RELOAD=true gesetzt"
echo "- Build-Verzeichnis gelöscht (entfernt gecachte Bundles)"
echo "- NODE_ENV=development gesetzt"
echo ""
echo "WICHTIG: Bitte Browser-Cache leeren (Strg+Shift+R oder Strg+F5)"
echo "oder im Browser DevTools > Network > Disable cache aktivieren"
echo ""
echo "Falls Frontend immer noch nicht startet:"
echo "  tail -50 /var/log/supervisor/cyphertrade-frontend-error.log"
echo ""

