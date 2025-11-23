#!/bin/bash
# Production Build Setup - Erstellt Production Build und konfiguriert Webserver

echo "=== Production Build Setup ==="
echo ""

cd /app || { echo "[ERROR] Kann nicht nach /app wechseln!"; exit 1; }

# 1. Stoppe Frontend
echo "[INFO] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true

# 2. Frontend-Verzeichnis
cd frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

# 3. Prüfe .env für Production
echo "[INFO] Prüfe Production .env..."
cat > .env.production << 'EOF'
REACT_APP_BACKEND_URL=http://192.168.178.154:8001
GENERATE_SOURCEMAP=false
NODE_ENV=production
EOF

# 4. Installiere serve falls nicht vorhanden (für statischen Server)
echo "[INFO] Prüfe 'serve' Installation..."
if ! command -v serve > /dev/null 2>&1; then
    echo "[INFO] Installiere 'serve' global..."
    npm install -g serve || yarn global add serve
else
    echo "[SUCCESS] 'serve' bereits installiert"
fi

# 5. Lösche alten Build
echo "[INFO] Lösche alten Build..."
rm -rf build 2>/dev/null || true

# 6. Erstelle Production Build
echo "[INFO] Erstelle Production Build (das kann einige Minuten dauern)..."
NODE_ENV=production yarn build

if [ $? -ne 0 ]; then
    echo "[ERROR] Build fehlgeschlagen!"
    exit 1
fi

echo "[SUCCESS] Production Build erstellt!"

# 7. Prüfe ob build-Verzeichnis existiert
if [ ! -d "build" ]; then
    echo "[ERROR] Build-Verzeichnis wurde nicht erstellt!"
    exit 1
fi

echo "[SUCCESS] Build-Verzeichnis vorhanden: $(du -sh build | cut -f1)"

# 8. Aktualisiere Supervisor Config für Production
echo "[INFO] Aktualisiere Supervisor Config für Production Build..."
cd /app

# Finde serve-Binary
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

echo "[SUCCESS] Supervisor Config aktualisiert"

# 9. Lade Supervisor neu
echo "[INFO] Lade Supervisor neu..."
sudo supervisorctl reread
sudo supervisorctl update

# 10. Starte Frontend
echo "[INFO] Starte Frontend (Production Build)..."
sudo supervisorctl start cyphertrade-frontend

# 11. Warte und prüfe Status
echo ""
echo "[INFO] Warte 5 Sekunden auf Start..."
sleep 5

echo ""
echo "[INFO] Frontend Status:"
sudo supervisorctl status cyphertrade-frontend

echo ""
echo "=== Fertig ==="
echo ""
if sudo supervisorctl status cyphertrade-frontend | grep -q "RUNNING"; then
    echo "✅ Production Build läuft erfolgreich!"
    echo ""
    echo "Frontend wird jetzt als statischer Build ausgeliefert (viel schneller und stabiler)"
    echo "Bei Änderungen: sudo bash /app/setup-production-build.sh ausführen"
else
    echo "❌ Frontend läuft nicht. Prüfe die Logs:"
    echo "   tail -50 /var/log/supervisor/cyphertrade-frontend-error.log"
fi

