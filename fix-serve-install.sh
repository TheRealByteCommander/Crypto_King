#!/bin/bash
# Installiert/Prüft serve Installation und konfiguriert Supervisor korrekt

echo "=== Serve Installation & Konfiguration ==="
echo ""

cd /app || { echo "[ERROR] /app Verzeichnis nicht gefunden!"; exit 1; }

# 1. Prüfe ob serve installiert ist
echo "[1/5] Prüfe serve Installation..."
SERVE_PATH=$(which serve 2>/dev/null)
if [ -z "$SERVE_PATH" ]; then
    echo "[INFO] serve nicht gefunden, installiere global..."
    npm install -g serve
    SERVE_PATH=$(which serve 2>/dev/null)
    if [ -z "$SERVE_PATH" ]; then
        echo "[ERROR] serve konnte nicht installiert werden!"
        exit 1
    fi
    echo "[SUCCESS] serve installiert bei: $SERVE_PATH"
else
    echo "[SUCCESS] serve gefunden bei: $SERVE_PATH"
fi

# 2. Prüfe ob Build vorhanden ist
echo ""
echo "[2/5] Prüfe Build..."
cd /app/frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

if [ ! -d "build" ] || [ ! -f "build/index.html" ]; then
    echo "[INFO] Build nicht gefunden, erstelle neuen Production Build..."
    export NODE_ENV=production
    yarn build
    if [ $? -ne 0 ]; then
        echo "[ERROR] Build fehlgeschlagen!"
        exit 1
    fi
    echo "[SUCCESS] Build erstellt"
else
    echo "[SUCCESS] Build vorhanden"
fi

# 3. Konfiguriere Supervisor mit korrektem serve-Pfad
echo ""
echo "[3/5] Konfiguriere Supervisor mit serve-Pfad: $SERVE_PATH..."

sudo tee /etc/supervisor/conf.d/cyphertrade-frontend.conf > /dev/null <<EOF
[program:cyphertrade-frontend]
directory=/app/frontend
command=$SERVE_PATH -s /app/frontend/build -l 3000
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/cyphertrade-frontend-error.log
stdout_logfile=/var/log/supervisor/cyphertrade-frontend.log
user=root
environment=NODE_ENV="production"
EOF

echo "[SUCCESS] Supervisor Config aktualisiert"

# 4. Lade Supervisor neu
echo ""
echo "[4/5] Lade Supervisor neu..."
sudo supervisorctl reread
sudo supervisorctl update cyphertrade-frontend

# 5. Starte Frontend
echo ""
echo "[5/5] Starte Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true
sleep 2
sudo supervisorctl start cyphertrade-frontend
sleep 3

# Prüfe Status
echo ""
echo "=== Frontend Status ==="
sudo supervisorctl status cyphertrade-frontend

echo ""
echo "=== Serve Test ==="
sleep 2
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "[SUCCESS] ✓ Frontend antwortet auf Port 3000"
else
    echo "[WARNING] Frontend antwortet nicht - prüfe Logs:"
    echo "  tail -50 /var/log/supervisor/cyphertrade-frontend.log"
fi

echo ""
echo "=== Fertig ==="

