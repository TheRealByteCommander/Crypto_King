#!/bin/bash
# Behebt Frontend Spawn Error - Prüft Logs und startet Frontend korrekt

echo "=== Frontend Spawn Error beheben ==="
echo ""

# 1. Prüfe Error Logs
echo "[INFO] Prüfe Frontend Error Logs (letzte 50 Zeilen):"
tail -50 /var/log/supervisor/cyphertrade-frontend-error.log 2>/dev/null || echo "[WARNING] Error-Log-Datei nicht gefunden"

echo ""
echo "[INFO] Prüfe Frontend Logs (letzte 50 Zeilen):"
tail -50 /var/log/supervisor/cyphertrade-frontend.log 2>/dev/null || echo "[WARNING] Log-Datei nicht gefunden"

echo ""

# 2. Stoppe Frontend sicher
echo "[INFO] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true
pkill -f "yarn start" 2>/dev/null || true
pkill -f "craco start" 2>/dev/null || true
pkill -f "react-scripts" 2>/dev/null || true
sleep 2

# 3. Prüfe Port 3000
echo "[INFO] Prüfe Port 3000..."
if lsof -i :3000 &>/dev/null; then
    echo "[WARNING] Port 3000 noch belegt, beende Prozess..."
    lsof -ti :3000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# 4. Prüfe Frontend-Verzeichnis und Dependencies
echo "[INFO] Prüfe Frontend-Verzeichnis..."
cd /app/frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

echo "[INFO] Prüfe node_modules..."
if [ ! -d "node_modules" ]; then
    echo "[WARNING] node_modules nicht gefunden, installiere Dependencies..."
    yarn install
fi

# 5. Prüfe .env Datei
echo "[INFO] Prüfe .env Datei..."
if [ ! -f ".env" ]; then
    echo "[WARNING] .env nicht gefunden, erstelle sie..."
    cat > .env << 'ENVEOF'
REACT_APP_BACKEND_URL=http://192.168.178.154:8001
GENERATE_SOURCEMAP=false
DISABLE_HOT_RELOAD=true
FAST_REFRESH=false
ENVEOF
fi

# 6. Teste yarn start direkt (mit Timeout)
echo "[INFO] Teste 'yarn start' direkt (10 Sekunden timeout)..."
timeout 10 yarn start 2>&1 | head -20 || echo "[INFO] yarn start beendet (normal nach Timeout)"

echo ""

# 7. Prüfe Supervisor Config
echo "[INFO] Prüfe Supervisor Config..."
if [ -f "/etc/supervisor/conf.d/cyphertrade-frontend.conf" ]; then
    echo "[SUCCESS] Supervisor Config vorhanden"
    cat /etc/supervisor/conf.d/cyphertrade-frontend.conf
else
    echo "[ERROR] Supervisor Config nicht gefunden!"
    exit 1
fi

echo ""

# 8. Versuche Frontend manuell zu starten (ohne Supervisor)
echo "[INFO] Versuche Frontend manuell zu starten (im Hintergrund)..."
cd /app/frontend
export REACT_APP_BACKEND_URL="http://192.168.178.154:8001"
export NODE_ENV="development"
nohup yarn start > /var/log/supervisor/cyphertrade-frontend-manual.log 2>&1 &
MANUAL_PID=$!
echo "[INFO] Frontend manuell gestartet (PID: $MANUAL_PID)"

sleep 5

# 9. Prüfe ob Frontend läuft
echo "[INFO] Prüfe ob Frontend läuft..."
if ps -p $MANUAL_PID > /dev/null; then
    echo "[SUCCESS] Frontend läuft (PID: $MANUAL_PID)"
    echo "[INFO] Logs: tail -f /var/log/supervisor/cyphertrade-frontend-manual.log"
else
    echo "[ERROR] Frontend startete nicht erfolgreich"
    echo "[INFO] Prüfe Logs: cat /var/log/supervisor/cyphertrade-frontend-manual.log"
    cat /var/log/supervisor/cyphertrade-frontend-manual.log 2>/dev/null || echo "Keine Logs verfügbar"
fi

echo ""
echo "=== Zusammenfassung ==="
echo "Falls das Frontend noch nicht läuft, prüfe bitte die Logs:"
echo "  - tail -100 /var/log/supervisor/cyphertrade-frontend-error.log"
echo "  - tail -100 /var/log/supervisor/cyphertrade-frontend.log"
echo "  - tail -100 /var/log/supervisor/cyphertrade-frontend-manual.log"
