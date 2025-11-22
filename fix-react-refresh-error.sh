#!/bin/bash
# Behebt React Refresh Error im Production Bundle

set -e

echo "=== React Refresh Error beheben ==="
echo ""

# 1. Frontend stoppen
echo "[INFO] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true

# 2. Aktualisiere Supervisor Config mit korrektem NODE_ENV
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
environment=REACT_APP_BACKEND_URL="http://192.168.178.154:8001",NODE_ENV="development",GENERATE_SOURCEMAP="false"
stopwaitsecs=10
killasgroup=true
priority=998
EOF

echo "[SUCCESS] Supervisor Config aktualisiert"
echo "[INFO] NODE_ENV auf 'development' gesetzt (da yarn start Development-Server ist)"

# 3. Reload Supervisor
echo "[INFO] Lade Supervisor neu..."
sudo supervisorctl reread
sudo supervisorctl update

# 4. Starte Frontend
echo "[INFO] Starte Frontend..."
sleep 2
sudo supervisorctl start cyphertrade-frontend

# 5. Prüfe Status
echo ""
echo "[INFO] Frontend Status:"
sleep 2
sudo supervisorctl status cyphertrade-frontend

echo ""
echo "=== Zusammenfassung ==="
echo ""
echo "Frontend läuft jetzt im Development-Modus (yarn start)."
echo "React Refresh Error sollte behoben sein."
echo ""
echo "Hinweis:"
echo "- Development-Modus (yarn start): NODE_ENV=development ✓"
echo "- Production-Modus würde yarn build && serve benötigen"
echo ""

