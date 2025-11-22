#!/bin/bash
# Finale Frontend-Fix: Behebt Supervisor Fehler und stellt sicher, dass .env korrekt geladen wird

INSTALL_DIR="/app"
FRONTEND_DIR="${INSTALL_DIR}/frontend"
CRYPTOKING_IP="192.168.178.154"

echo "=== Finale Frontend-Fix ==="
echo ""

# 1. Prüfe welche IP tatsächlich verwendet werden sollte
echo "[INFO] Prüfe Netzwerk-Konfiguration..."
SERVER_IP=$(hostname -I | awk '{print $1}' || echo "$CRYPTOKING_IP")
echo "[INFO] Server IP: $SERVER_IP"
echo "[INFO] Konfigurierte CryptoKing IP: $CRYPTOKING_IP"
echo ""

# 2. Frontend .env Datei erstellen
echo "[INFO] Erstelle Frontend .env Datei..."
cd "$FRONTEND_DIR" || exit 1

cat > .env << EOF
REACT_APP_BACKEND_URL=http://${CRYPTOKING_IP}:8001
EOF

echo "[SUCCESS] Frontend .env erstellt:"
cat .env
echo ""

# 3. Prüfe welche IP tatsächlich für das Backend verwendet werden sollte
echo "[INFO] Prüfe Backend .env..."
if [ -f "${INSTALL_DIR}/backend/.env" ]; then
    BACKEND_IP=$(grep "^REACT_APP_BACKEND_URL\|^BACKEND_URL" "${INSTALL_DIR}/backend/.env" 2>/dev/null | head -1 | cut -d'/' -f3 | cut -d':' -f1 || echo "$CRYPTOKING_IP")
    if [ ! -z "$BACKEND_IP" ]; then
        echo "[INFO] Backend IP aus .env: $BACKEND_IP"
    fi
fi
echo ""

# 4. Prüfe ob Frontend bereits läuft
echo "[INFO] Prüfe laufende Frontend-Prozesse..."
if pgrep -f "craco\|react-scripts\|yarn.*start" > /dev/null; then
    FRONTEND_PID=$(pgrep -f "craco\|react-scripts\|yarn.*start" | head -1)
    echo "[WARNING] Frontend läuft bereits (PID: $FRONTEND_PID)"
    echo "[INFO] Prüfe ob mit korrekter .env gestartet wurde..."
    
    # Prüfe ob die .env korrekt ist
    if [ -f ".env" ] && grep -q "${CRYPTOKING_IP}:8001" .env; then
        echo "[SUCCESS] Frontend .env ist korrekt"
        echo "[INFO] Frontend läuft bereits mit korrekter .env"
        echo "[INFO] Aber: .env wird nur beim Start geladen!"
        echo "[INFO] Frontend muss neu gestartet werden, damit neue .env geladen wird"
    fi
fi
echo ""

# 5. Stoppe alle Frontend-Prozesse
echo "[INFO] Stoppe alle Frontend-Prozesse..."
pkill -f "craco\|react-scripts\|yarn.*start" 2>/dev/null || true
sleep 3

# Prüfe ob noch Prozesse laufen
if pgrep -f "craco\|react-scripts\|yarn.*start" > /dev/null; then
    echo "[WARNING] Noch laufende Prozesse gefunden, beende sie..."
    pgrep -f "craco\|react-scripts\|yarn.*start" | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Prüfe Port 3000
if lsof -i :3000 &> /dev/null; then
    echo "[WARNING] Port 3000 noch belegt, beende Prozess..."
    lsof -ti :3000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

echo "[SUCCESS] Alle Frontend-Prozesse gestoppt"
echo ""

# 6. Supervisor Config prüfen und korrigieren
echo "[INFO] Prüfe Supervisor Config..."
YARN_PATH=$(which yarn 2>/dev/null || echo "/usr/bin/yarn")

if [ -f "/etc/supervisor/conf.d/cyphertrade-frontend.conf" ]; then
    echo "[INFO] Supervisor Config vorhanden"
    # Prüfe ob REACT_APP_BACKEND_URL in Supervisor Config ist
    if ! grep -q "REACT_APP_BACKEND_URL" /etc/supervisor/conf.d/cyphertrade-frontend.conf; then
        echo "[WARNING] REACT_APP_BACKEND_URL nicht in Supervisor Config!"
        echo "[INFO] Aktualisiere Supervisor Config..."
    fi
else
    echo "[WARNING] Supervisor Config nicht gefunden!"
    echo "[INFO] Erstelle Supervisor Config..."
fi

# Aktualisiere Supervisor Config
sudo tee /etc/supervisor/conf.d/cyphertrade-frontend.conf > /dev/null << EOF
[program:cyphertrade-frontend]
directory=${FRONTEND_DIR}
command=${YARN_PATH} start
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/cyphertrade-frontend.log
stderr_logfile=/var/log/supervisor/cyphertrade-frontend-error.log
environment=PATH="/usr/local/bin:/usr/bin:/bin",REACT_APP_BACKEND_URL="http://${CRYPTOKING_IP}:8001"
EOF

echo "[SUCCESS] Supervisor Config aktualisiert"
echo ""

# 7. Supervisor neu laden
echo "[INFO] Lade Supervisor Config neu..."
supervisorctl reread 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true
supervisorctl update 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true
echo ""

# 8. Prüfe Supervisor Status
echo "[INFO] Prüfe Supervisor Frontend Status..."
if supervisorctl status cyphertrade-frontend 2>&1 | grep -qE "(STOPPED|FATAL|ERROR)"; then
    echo "[WARNING] Frontend Service hat Fehler!"
    supervisorctl status cyphertrade-frontend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true
    
    # Prüfe Logs
    if [ -f "/var/log/supervisor/cyphertrade-frontend-error.log" ]; then
        echo "[INFO] Letzte Fehler-Logs:"
        tail -20 /var/log/supervisor/cyphertrade-frontend-error.log
    fi
fi
echo ""

# 9. Starte Frontend über Supervisor
echo "[INFO] Starte Frontend über Supervisor..."
supervisorctl start cyphertrade-frontend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || {
    echo "[ERROR] Frontend konnte nicht über Supervisor gestartet werden!"
    echo "[INFO] Starte Frontend manuell..."
    
    cd "$FRONTEND_DIR"
    export REACT_APP_BACKEND_URL="http://${CRYPTOKING_IP}:8001"
    nohup yarn start > /var/log/supervisor/cyphertrade-frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "[SUCCESS] Frontend manuell gestartet (PID: $FRONTEND_PID)"
}

sleep 10

# 10. Prüfe Status
echo ""
echo "[INFO] Finaler Status:"
echo ""

if pgrep -f "craco\|react-scripts\|yarn.*start" > /dev/null; then
    echo "[SUCCESS] Frontend läuft!"
    pgrep -f "craco\|react-scripts\|yarn.*start"
else
    echo "[ERROR] Frontend läuft NICHT!"
fi

if lsof -i :3000 &> /dev/null; then
    echo "[SUCCESS] Port 3000 ist belegt (Frontend läuft)"
    echo "[INFO] Verbindungen:"
    lsof -i :3000 | grep ESTABLISHED | head -5
else
    echo "[WARNING] Port 3000 ist frei (Frontend startet möglicherweise noch)"
fi

supervisorctl status cyphertrade-frontend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true

echo ""
echo "=== Zusammenfassung ==="
echo ""
echo "Frontend sollte jetzt auf http://${CRYPTOKING_IP}:3000 laufen"
echo "Backend URL: http://${CRYPTOKING_IP}:8001"
echo ""
echo "Die IP 192.168.178.188 ist die Client-IP (Ihr Gerät/Browser)."
echo "Das ist normal - das sind Verbindungen vom Browser zum Server."
echo ""
echo "Bitte prüfen Sie im Browser:"
echo "1. Hard Refresh (Ctrl + Shift + R)"
echo "2. Console (F12) - sollte keine Fehler mehr zu localhost:8001 zeigen"
echo "3. Network Tab - Requests sollten zu ${CRYPTOKING_IP}:8001 gehen"

