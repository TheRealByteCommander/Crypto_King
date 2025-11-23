#!/bin/bash
# Endgültiger Frontend-Fix - Behebt alle bekannten spawn errors

echo "=== Frontend Final Fix ==="
echo ""

cd /app || { echo "[ERROR] Kann nicht nach /app wechseln!"; exit 1; }

# 1. Stoppe Frontend komplett
echo "[INFO] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true
sleep 2

# 2. Töte alle Frontend-bezogenen Prozesse
echo "[INFO] Beende alle Frontend-Prozesse..."
pkill -f "yarn start" 2>/dev/null || true
pkill -f "craco start" 2>/dev/null || true
pkill -f "react-scripts" 2>/dev/null || true
pkill -f "webpack" 2>/dev/null || true
sleep 2

# 3. Port 3000 komplett freigeben
echo "[INFO] Prüfe Port 3000..."
if lsof -i :3000 > /dev/null 2>&1; then
    echo "[INFO] Beende alle Prozesse auf Port 3000..."
    sudo lsof -ti :3000 | xargs sudo kill -9 2>/dev/null || true
    sleep 3
fi

# 4. Frontend-Verzeichnis prüfen
cd frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

# 5. Prüfe .env Datei
echo "[INFO] Prüfe .env Datei..."
if [ ! -f ".env" ]; then
    echo "[WARNING] .env nicht gefunden, erstelle sie..."
    cat > .env << 'EOF'
REACT_APP_BACKEND_URL=http://192.168.178.154:8001
GENERATE_SOURCEMAP=false
DISABLE_HOT_RELOAD=true
FAST_REFRESH=false
NODE_ENV=development
EOF
    echo "[SUCCESS] .env erstellt"
else
    echo "[SUCCESS] .env vorhanden"
    # Stelle sicher, dass wichtige Variablen gesetzt sind
    if ! grep -q "REACT_APP_BACKEND_URL" .env; then
        echo "REACT_APP_BACKEND_URL=http://192.168.178.154:8001" >> .env
    fi
    if ! grep -q "DISABLE_HOT_RELOAD" .env; then
        echo "DISABLE_HOT_RELOAD=true" >> .env
    fi
fi

# 6. Prüfe node_modules
echo "[INFO] Prüfe node_modules..."
if [ ! -d "node_modules" ] || [ $(find node_modules -maxdepth 1 -type d | wc -l) -lt 10 ]; then
    echo "[WARNING] node_modules fehlt oder unvollständig, installiere..."
    yarn install --frozen-lockfile || yarn install
else
    echo "[SUCCESS] node_modules vorhanden"
fi

# 7. Prüfe Supervisor Config
echo "[INFO] Prüfe Supervisor Config..."
if [ ! -f "/etc/supervisor/conf.d/cyphertrade-frontend.conf" ]; then
    echo "[ERROR] Supervisor Config nicht gefunden!"
    exit 1
fi

# 8. Teste yarn start manuell (kurz)
echo "[INFO] Teste yarn start (5 Sekunden)..."
timeout 5 yarn start 2>&1 | head -20 || echo "[INFO] Timeout erreicht (normal)"

# 9. Starte über Supervisor
echo ""
echo "[INFO] Starte Frontend über Supervisor..."
cd /app
sudo supervisorctl start cyphertrade-frontend

# 10. Warte und prüfe Status
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
    echo "✅ Frontend läuft erfolgreich!"
else
    echo "❌ Frontend läuft nicht. Prüfe die Logs:"
    echo "   tail -50 /var/log/supervisor/cyphertrade-frontend-error.log"
    echo "   tail -50 /var/log/supervisor/cyphertrade-frontend.log"
fi
