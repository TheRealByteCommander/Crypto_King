#!/bin/bash
# Erzwingt komplettes Neuladen des Frontends - löst Cache-Probleme

echo "=== Frontend Force Reload ==="
echo ""

cd /app || { echo "[ERROR] /app Verzeichnis nicht gefunden!"; exit 1; }

# 1. Stoppe Frontend
echo "[1/6] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null
sleep 2

# 2. Stoppe ALLE serve Prozesse
echo "[2/6] Stoppe alle serve Prozesse..."
sudo pkill -9 -f "serve.*frontend" 2>/dev/null || true
sleep 1

# 3. Prüfe und befreie Port 3000
echo "[3/6] Prüfe Port 3000..."
PORT_3000_PID=$(sudo lsof -ti:3000 2>/dev/null || true)
if [ ! -z "$PORT_3000_PID" ]; then
    echo "[INFO] Prozess auf Port 3000 gefunden (PID: $PORT_3000_PID), beende..."
    sudo kill -9 $PORT_3000_PID 2>/dev/null || true
    sleep 2
fi

# 4. Lösche alten Build
echo "[4/6] Lösche alten Build..."
cd /app/frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }
rm -rf build
echo "[SUCCESS] Build-Verzeichnis gelöscht"

# 5. Erstelle neuen Production Build
echo "[5/6] Erstelle neuen Production Build..."
export NODE_ENV=production
yarn build
if [ $? -ne 0 ]; then
    echo "[ERROR] Build fehlgeschlagen!"
    exit 1
fi
echo "[SUCCESS] Build erstellt"

# 6. Prüfe ob Portfolio-Komponente im Build vorhanden ist
echo "[6/6] Prüfe Build-Inhalt..."
if grep -q "Portfolio" build/static/js/*.js 2>/dev/null; then
    echo "[SUCCESS] ✓ Portfolio-Komponente im Build gefunden"
else
    echo "[WARNING] ⚠ Portfolio-Komponente nicht im Build gefunden - möglicherweise zu früh geprüft"
fi

# 7. Konfiguriere Supervisor für serve
echo ""
echo "[7/7] Konfiguriere Supervisor..."
sudo tee /etc/supervisor/conf.d/cyphertrade-frontend.conf > /dev/null <<EOF
[program:cyphertrade-frontend]
directory=/app/frontend
command=/usr/local/bin/serve -s /app/frontend/build -l 3000
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/cyphertrade-frontend-error.log
stdout_logfile=/var/log/supervisor/cyphertrade-frontend.log
user=root
environment=NODE_ENV="production"
EOF

echo "[SUCCESS] Supervisor Config aktualisiert"

# 8. Lade Supervisor neu und starte Frontend
echo ""
echo "[8/8] Starte Frontend neu..."
sudo supervisorctl reread
sudo supervisorctl update cyphertrade-frontend
sleep 2
sudo supervisorctl start cyphertrade-frontend
sleep 2

# 9. Prüfe Status
echo ""
echo "[INFO] Prüfe Frontend Status..."
sudo supervisorctl status cyphertrade-frontend

echo ""
echo "=== Frontend Reload abgeschlossen ==="
echo ""
echo "Hinweise:"
echo "1. Das Frontend sollte jetzt die neueste Version zeigen"
echo "2. Falls nicht, leere den Browser-Cache:"
echo "   - Chrome/Edge: Ctrl+Shift+Delete"
echo "   - Oder: Hard Reload (Ctrl+Shift+R)"
echo "3. Prüfe Logs: tail -f /var/log/supervisor/cyphertrade-frontend.log"

