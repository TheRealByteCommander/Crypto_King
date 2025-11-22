#!/bin/bash
# Sauberer Neustart des Frontends mit korrekter Konfiguration

INSTALL_DIR="/app"
FRONTEND_DIR="${INSTALL_DIR}/frontend"
CRYPTOKING_IP="192.168.178.154"

echo "=== Frontend Sauberer Neustart ==="
echo ""

# 1. Stoppe alle laufenden Frontend-Prozesse
echo "[INFO] Stoppe alle laufenden Frontend-Prozesse..."
pkill -f "yarn start" 2>/dev/null || true
pkill -f "react-scripts start" 2>/dev/null || true
pkill -f "craco start" 2>/dev/null || true
pkill -f "@craco/craco" 2>/dev/null || true

# Prüfe ob noch Prozesse laufen
if pgrep -f "craco\|react-scripts\|yarn.*start" > /dev/null; then
    echo "[WARNING] Noch laufende Frontend-Prozesse gefunden, beende sie..."
    pgrep -f "craco\|react-scripts\|yarn.*start" | xargs kill -9 2>/dev/null || true
    sleep 2
fi

echo "[SUCCESS] Alle Frontend-Prozesse gestoppt"
echo ""

# 2. Prüfe Port 3000
echo "[INFO] Prüfe Port 3000..."
if lsof -i :3000 &> /dev/null || netstat -tuln 2>/dev/null | grep -q ":3000"; then
    echo "[WARNING] Port 3000 noch belegt, beende Prozess..."
    lsof -ti :3000 | xargs kill -9 2>/dev/null || true
    fuser -k 3000/tcp 2>/dev/null || true
    sleep 2
fi
echo ""

# 3. Frontend .env Datei erstellen/korrigieren
echo "[INFO] Erstelle Frontend .env Datei..."
cd "$FRONTEND_DIR" || exit 1

cat > .env << EOF
REACT_APP_BACKEND_URL=http://${CRYPTOKING_IP}:8001
EOF

echo "[SUCCESS] Frontend .env erstellt:"
cat .env
echo ""

# 4. Prüfe Supervisor Status
echo "[INFO] Prüfe Supervisor Frontend Status..."
if supervisorctl status cyphertrade-frontend 2>&1 | grep -q "RUNNING"; then
    echo "[INFO] Stoppe Frontend über Supervisor..."
    supervisorctl stop cyphertrade-frontend 2>&1 | grep -v "pkg_resources" | grep -v "deprecated" || true
    sleep 2
fi
echo ""

# 5. Aktualisiere Supervisor Config (falls vorhanden)
if [ -f "/etc/supervisor/conf.d/cyphertrade-frontend.conf" ]; then
    echo "[INFO] Aktualisiere Supervisor Config..."
    sudo tee /etc/supervisor/conf.d/cyphertrade-frontend.conf > /dev/null << EOF
[program:cyphertrade-frontend]
directory=${FRONTEND_DIR}
command=$(which yarn) start
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/cyphertrade-frontend.log
stderr_logfile=/var/log/supervisor/cyphertrade-frontend-error.log
environment=PATH="/usr/local/bin:/usr/bin:/bin",REACT_APP_BACKEND_URL="http://${CRYPTOKING_IP}:8001"
EOF
    sudo supervisorctl reread 2>&1 | grep -v "pkg_resources" | grep -v "deprecated" || true
    sudo supervisorctl update 2>&1 | grep -v "pkg_resources" | grep -v "deprecated" || true
fi
echo ""

# 6. Warte kurz
sleep 3

# 7. Starte Frontend über Supervisor (falls verfügbar)
echo "[INFO] Starte Frontend über Supervisor..."
if supervisorctl status cyphertrade-frontend 2>&1 | grep -qE "(STOPPED|FATAL|no such file)"; then
    echo "[INFO] Versuche Frontend über Supervisor zu starten..."
    supervisorctl start cyphertrade-frontend 2>&1 | grep -v "pkg_resources" | grep -v "deprecated" || {
        echo "[WARNING] Frontend konnte nicht über Supervisor gestartet werden"
        echo "[INFO] Starte Frontend manuell..."
        
        # Manueller Start mit korrekter Umgebungsvariable
        cd "$FRONTEND_DIR"
        export REACT_APP_BACKEND_URL="http://${CRYPTOKING_IP}:8001"
        nohup yarn start > /var/log/supervisor/cyphertrade-frontend.log 2>&1 &
        FRONTEND_PID=$!
        echo "[SUCCESS] Frontend manuell gestartet (PID: $FRONTEND_PID)"
    }
else
    echo "[SUCCESS] Frontend wurde über Supervisor gestartet"
fi
echo ""

# 8. Warte bis Frontend gestartet ist
echo "[INFO] Warte 15 Sekunden bis Frontend vollständig gestartet ist..."
sleep 15

# 9. Prüfe Status
echo ""
echo "[INFO] Finaler Status:"
echo ""

# Prüfe ob Frontend läuft
if pgrep -f "craco\|react-scripts\|yarn.*start" > /dev/null; then
    echo "[SUCCESS] Frontend Prozess läuft!"
    pgrep -f "craco\|react-scripts\|yarn.*start"
else
    echo "[ERROR] Frontend Prozess läuft nicht!"
fi

# Prüfe Port 3000
if lsof -i :3000 &> /dev/null || netstat -tuln 2>/dev/null | grep -q ":3000"; then
    echo "[SUCCESS] Port 3000 ist belegt (Frontend läuft)"
else
    echo "[WARNING] Port 3000 ist frei (Frontend startet möglicherweise noch)"
fi

# Prüfe Supervisor Status
echo ""
echo "Supervisor Status:"
supervisorctl status cyphertrade-frontend 2>&1 | grep -v "pkg_resources" | grep -v "deprecated" || echo "Frontend nicht über Supervisor verwaltet"
echo ""

# 10. Zeige Logs
echo "[INFO] Letzte Frontend Logs:"
if [ -f "/var/log/supervisor/cyphertrade-frontend-error.log" ]; then
    tail -10 /var/log/supervisor/cyphertrade-frontend-error.log 2>/dev/null || echo "Keine Fehler-Logs"
fi
echo ""

echo "=== Neustart abgeschlossen ==="
echo ""
echo "Frontend sollte jetzt auf http://${CRYPTOKING_IP}:3000 laufen"
echo "Backend URL: http://${CRYPTOKING_IP}:8001"
echo ""
echo "Prüfen Sie im Browser (F12 → Console) ob jetzt ${CRYPTOKING_IP}:8001 verwendet wird"

