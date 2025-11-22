#!/bin/bash
# Behebt Git-Merge-Problem und aktualisiert Frontend-Config

set -e

echo "=== Git-Merge-Problem beheben ==="
echo ""

# 1. Prüfe Status
echo "[INFO] Prüfe Git-Status..."
cd /app || { echo "[ERROR] Kann nicht nach /app wechseln!"; exit 1; }

# 2. Stashe lokale Änderungen (falls vorhanden)
echo "[INFO] Stashe lokale Änderungen..."
git stash || echo "[WARNING] Keine Änderungen zum Stashen"

# 3. Hole neueste Änderungen
echo "[INFO] Hole neueste Änderungen von GitHub..."
git pull

# 4. Aktualisiere Supervisor Config direkt (ohne Git zu verwenden)
echo "[INFO] Aktualisiere Supervisor Config für Frontend..."
sudo tee /etc/supervisor/conf.d/cyphertrade-frontend.conf > /dev/null << 'EOF'
[program:cyphertrade-frontend]
directory=/app/frontend
command=yarn start
user=root
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/cyphertrade-frontend-error.log
stdout_logfile=/var/log/supervisor/cyphertrade-frontend.log
environment=REACT_APP_BACKEND_URL="http://192.168.178.154:8001",NODE_ENV="development",GENERATE_SOURCEMAP="false"
stopwaitsecs=10
killasgroup=true
priority=998
EOF

echo "[SUCCESS] Supervisor Config aktualisiert"

# 5. Prüfe Frontend .env
echo "[INFO] Prüfe Frontend .env..."
if [ -f "/app/frontend/.env" ]; then
    echo "[SUCCESS] .env vorhanden"
    # Stelle sicher, dass REACT_APP_BACKEND_URL gesetzt ist
    if ! grep -q "^REACT_APP_BACKEND_URL" /app/frontend/.env; then
        echo "[INFO] Füge REACT_APP_BACKEND_URL hinzu..."
        echo "REACT_APP_BACKEND_URL=http://192.168.178.154:8001" >> /app/frontend/.env
    fi
else
    echo "[WARNING] .env nicht gefunden, erstelle sie..."
    cat > /app/frontend/.env << 'ENVEOF'
REACT_APP_BACKEND_URL=http://192.168.178.154:8001
GENERATE_SOURCEMAP=false
ENVEOF
fi

# 6. Reload Supervisor
echo "[INFO] Lade Supervisor neu..."
sudo supervisorctl reread
sudo supervisorctl update

# 7. Starte Frontend
echo "[INFO] Starte Frontend..."
sleep 2
sudo supervisorctl restart cyphertrade-frontend

# 8. Prüfe Status
echo ""
echo "[INFO] Frontend Status:"
sleep 2
sudo supervisorctl status cyphertrade-frontend

echo ""
echo "=== Zusammenfassung ==="
echo ""
echo "Git-Pull erfolgreich durchgeführt"
echo "Supervisor Config aktualisiert (NODE_ENV=development)"
echo "Frontend sollte jetzt ohne React Refresh Error laufen"
echo ""

