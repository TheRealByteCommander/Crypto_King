#!/bin/bash
# Komplettes Frontend-Reload mit Build-Neuaufbau

echo "=== Frontend komplett neu laden ==="
echo ""

cd /app || { echo "[ERROR] /app Verzeichnis nicht gefunden!"; exit 1; }

# 1. Prüfe und installiere serve falls nötig
echo "[1/7] Prüfe serve Installation..."
if ! command -v serve &> /dev/null; then
    echo "[INFO] serve nicht gefunden, installiere..."
    npm install -g serve
fi
SERVE_PATH=$(which serve)
echo "[SUCCESS] serve gefunden bei: $SERVE_PATH"

# 2. Stoppe Frontend
echo ""
echo "[2/7] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true
sleep 2

# 3. Töte alle serve Prozesse
echo "[3/7] Töte alle serve Prozesse..."
sudo pkill -9 -f "serve" 2>/dev/null || true
sleep 2

# 4. Befreie Port 3000
echo "[4/7] Befreie Port 3000..."
PORT_PID=$(sudo lsof -ti:3000 2>/dev/null || true)
if [ ! -z "$PORT_PID" ]; then
    sudo kill -9 $PORT_PID 2>/dev/null || true
    sleep 2
fi

# 5. Lösche alten Build
echo "[5/7] Lösche alten Build..."
cd /app/frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }
rm -rf build node_modules/.cache
echo "[SUCCESS] Build und Cache gelöscht"

# 6. Erstelle neuen Production Build
echo ""
echo "[6/7] Erstelle neuen Production Build..."
export NODE_ENV=production
yarn build
if [ $? -ne 0 ]; then
    echo "[ERROR] Build fehlgeschlagen!"
    exit 1
fi
echo "[SUCCESS] Build erstellt"

# 7. Prüfe ob Asset-Anzeige im Build vorhanden ist
echo ""
echo "[7/7] Prüfe Build-Inhalt..."
MAIN_JS=$(find build/static/js -name "main.*.js" | head -1)
if [ -z "$MAIN_JS" ]; then
    echo "[WARNING] Main JS nicht gefunden"
else
    if grep -q "asset\|Current Asset\|Quantity" "$MAIN_JS" 2>/dev/null; then
        echo "[SUCCESS] ✓ Asset-Anzeige im Build gefunden"
    else
        echo "[WARNING] Asset-Anzeige möglicherweise nicht im Build"
    fi
fi

# 8. Konfiguriere Supervisor
echo ""
echo "[8/8] Konfiguriere Supervisor..."
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

# 9. Starte Frontend
echo ""
echo "[9/9] Starte Frontend..."
sudo supervisorctl reread
sudo supervisorctl update cyphertrade-frontend
sleep 2
sudo supervisorctl start cyphertrade-frontend
sleep 3

# 10. Prüfe Status
echo ""
echo "=== Frontend Status ==="
sudo supervisorctl status cyphertrade-frontend

echo ""
echo "=== Test ==="
sleep 2
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "[SUCCESS] ✓ Frontend antwortet auf Port 3000"
else
    echo "[WARNING] Frontend antwortet nicht"
    echo "[INFO] Prüfe Logs: tail -50 /var/log/supervisor/cyphertrade-frontend.log"
fi

echo ""
echo "=== Fertig ==="
echo ""
echo "WICHTIG: Browser-Cache leeren!"
echo "1. Hard Reload: Ctrl+Shift+R (Windows/Linux) oder Cmd+Shift+R (Mac)"
echo "2. Oder: DevTools (F12) → Application → Clear Storage → Clear site data"
echo "3. Oder: Ctrl+Shift+Delete → Cached images and files → Clear"

