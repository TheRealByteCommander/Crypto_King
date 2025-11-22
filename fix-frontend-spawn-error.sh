#!/bin/bash
# Behebt Frontend spawn error

set -e

echo "=== Frontend Spawn Error beheben ==="
echo ""

# 1. Prüfe Frontend Error Logs
echo "[INFO] Prüfe Frontend Error Logs:"
if [ -f "/var/log/supervisor/cyphertrade-frontend-error.log" ]; then
    echo "--- Letzte 30 Zeilen der Error Logs ---"
    tail -30 /var/log/supervisor/cyphertrade-frontend-error.log
else
    echo "  Error-Log-Datei nicht gefunden"
fi
echo ""

# 2. Prüfe Frontend Logs
echo "[INFO] Prüfe Frontend Logs:"
if [ -f "/var/log/supervisor/cyphertrade-frontend.log" ]; then
    echo "--- Letzte 30 Zeilen der Logs ---"
    tail -30 /var/log/supervisor/cyphertrade-frontend.log
else
    echo "  Log-Datei nicht gefunden"
fi
echo ""

# 3. Prüfe ob Yarn verfügbar ist
echo "[INFO] Prüfe Yarn Installation:"
if command -v yarn > /dev/null 2>&1; then
    YARN_VERSION=$(yarn --version 2>&1)
    echo "[SUCCESS] Yarn installiert (Version: $YARN_VERSION)"
else
    echo "[ERROR] Yarn nicht gefunden!"
    exit 1
fi
echo ""

# 4. Prüfe ob Node.js verfügbar ist
echo "[INFO] Prüfe Node.js Installation:"
if command -v node > /dev/null 2>&1; then
    NODE_VERSION=$(node --version 2>&1)
    echo "[SUCCESS] Node.js installiert (Version: $NODE_VERSION)"
else
    echo "[ERROR] Node.js nicht gefunden!"
    exit 1
fi
echo ""

# 5. Prüfe Frontend Verzeichnis
echo "[INFO] Prüfe Frontend Verzeichnis:"
cd /app/frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

if [ ! -f "package.json" ]; then
    echo "[ERROR] package.json nicht gefunden!"
    exit 1
fi

# 6. Installiere Dependencies falls nötig
if [ ! -d "node_modules" ]; then
    echo "[INFO] Installiere Frontend Dependencies..."
    yarn install --frozen-lockfile || yarn install
else
    echo "[SUCCESS] node_modules vorhanden"
fi

# 7. Prüfe .env Datei
echo "[INFO] Prüfe .env Datei:"
if [ ! -f ".env" ]; then
    echo "[WARNING] .env nicht gefunden, erstelle sie..."
    cat > .env << 'ENVEOF'
REACT_APP_BACKEND_URL=http://192.168.178.154:8001
GENERATE_SOURCEMAP=false
ENVEOF
else
    echo "[SUCCESS] .env vorhanden"
    # Stelle sicher, dass REACT_APP_BACKEND_URL gesetzt ist
    if ! grep -q "^REACT_APP_BACKEND_URL" .env; then
        echo "[INFO] Füge REACT_APP_BACKEND_URL hinzu..."
        echo "REACT_APP_BACKEND_URL=http://192.168.178.154:8001" >> .env
    fi
fi

# 8. Teste ob yarn start funktioniert (kurz)
echo "[INFO] Teste yarn start (timeout 10 Sekunden)..."
timeout 10 yarn start || echo "[INFO] yarn start gestartet (normal nach timeout)"

# 9. Aktualisiere Supervisor Config mit absolutem Pfad
echo "[INFO] Aktualisiere Supervisor Config mit absolutem Yarn-Pfad..."
YARN_PATH=$(which yarn)
echo "[INFO] Yarn gefunden bei: $YARN_PATH"

sudo tee /etc/supervisor/conf.d/cyphertrade-frontend.conf > /dev/null << EOF
[program:cyphertrade-frontend]
directory=/app/frontend
command=$YARN_PATH start
user=root
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/cyphertrade-frontend-error.log
stdout_logfile=/var/log/supervisor/cyphertrade-frontend.log
environment=REACT_APP_BACKEND_URL="http://192.168.178.154:8001",NODE_ENV="development",GENERATE_SOURCEMAP="false",PATH="$(echo $PATH)"
stopwaitsecs=10
killasgroup=true
priority=998
EOF

echo "[SUCCESS] Supervisor Config aktualisiert"

# 10. Reload Supervisor
echo "[INFO] Lade Supervisor neu..."
sudo supervisorctl reread
sudo supervisorctl update

# 11. Starte Frontend
echo "[INFO] Starte Frontend..."
sleep 3
sudo supervisorctl start cyphertrade-frontend

# 12. Prüfe Status
echo ""
echo "[INFO] Frontend Status:"
sleep 2
sudo supervisorctl status cyphertrade-frontend

echo ""
echo "=== Zusammenfassung ==="
echo ""
echo "Falls Frontend immer noch nicht startet:"
echo "  tail -50 /var/log/supervisor/cyphertrade-frontend-error.log"
echo "  tail -50 /var/log/supervisor/cyphertrade-frontend.log"
echo ""

