#!/bin/bash
# Behebt Frontend-Start-Probleme

set -e

echo "=== Frontend Start-Problem beheben ==="
echo ""

# 1. Frontend stoppen
echo "[INFO] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true

# 2. Prüfe und erstelle .env Datei
echo "[INFO] Prüfe Frontend .env..."
cd /app/frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

if [ ! -f ".env" ]; then
    echo "[WARNING] .env nicht gefunden, erstelle sie..."
    cat > .env << EOF
REACT_APP_BACKEND_URL=http://192.168.178.154:8001
GENERATE_SOURCEMAP=false
EOF
    echo "[SUCCESS] .env erstellt"
else
    echo "[SUCCESS] .env vorhanden"
    # Stelle sicher, dass REACT_APP_BACKEND_URL gesetzt ist
    if ! grep -q "REACT_APP_BACKEND_URL" .env; then
        echo "[INFO] Füge REACT_APP_BACKEND_URL hinzu..."
        echo "REACT_APP_BACKEND_URL=http://192.168.178.154:8001" >> .env
    fi
fi

# 3. Prüfe Node.js und Yarn
echo "[INFO] Prüfe Node.js und Yarn..."
if ! command -v node > /dev/null 2>&1; then
    echo "[ERROR] Node.js nicht gefunden!"
    exit 1
fi

if ! command -v yarn > /dev/null 2>&1; then
    echo "[ERROR] Yarn nicht gefunden!"
    exit 1
fi

echo "[SUCCESS] Node.js und Yarn verfügbar"

# 4. Installiere Dependencies falls nötig
if [ ! -d "node_modules" ]; then
    echo "[INFO] Installiere Frontend Dependencies..."
    yarn install --frozen-lockfile
else
    echo "[SUCCESS] node_modules vorhanden"
fi

# 5. Aktualisiere Supervisor Config
echo "[INFO] Aktualisiere Supervisor Config..."
sudo tee /etc/supervisor/conf.d/cyphertrade-frontend.conf > /dev/null << 'EOF'
[program:cyphertrade-frontend]
directory=/app/frontend
command=yarn start
user=root
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/cyphertrade-frontend-error.log
stdout_logfile=/var/log/supervisor/cyphertrade-frontend.log
environment=REACT_APP_BACKEND_URL="http://192.168.178.154:8001",NODE_ENV="production",GENERATE_SOURCEMAP="false"
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
sleep 2
sudo supervisorctl start cyphertrade-frontend

# 8. Prüfe Status
echo ""
echo "[INFO] Frontend Status:"
sleep 2
sudo supervisorctl status cyphertrade-frontend

echo ""
echo "=== Zusammenfassung ==="
echo ""
echo "Frontend sollte jetzt laufen."
echo ""
echo "Falls weiterhin Probleme auftreten:"
echo "  tail -100 /var/log/supervisor/cyphertrade-frontend-error.log"
echo "  tail -100 /var/log/supervisor/cyphertrade-frontend.log"
echo ""

