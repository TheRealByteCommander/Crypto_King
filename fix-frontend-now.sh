#!/bin/bash
# Sofort-Fix für Frontend-Backend Verbindungsproblem

INSTALL_DIR="/app"
FRONTEND_DIR="${INSTALL_DIR}/frontend"
CRYPTOKING_IP="192.168.178.154"

echo "=== Frontend-Backend Verbindungs-Fix ==="
echo ""

# 1. Frontend .env Datei korrigieren
echo "[INFO] Korrigiere Frontend .env Datei..."
cd "$FRONTEND_DIR" || exit 1

# Erstelle/überschreibe .env Datei
cat > .env << EOF
REACT_APP_BACKEND_URL=http://${CRYPTOKING_IP}:8001
EOF

echo "[SUCCESS] Frontend .env erstellt:"
cat .env
echo ""

# 2. Prüfe ob Backend läuft
echo "[INFO] Prüfe Backend Status..."
if supervisorctl status cyphertrade-backend 2>/dev/null | grep -q "RUNNING"; then
    echo "[SUCCESS] Backend läuft"
else
    echo "[ERROR] Backend läuft NICHT!"
    echo "[INFO] Starte Backend..."
    supervisorctl start cyphertrade-backend 2>/dev/null || true
    sleep 5
fi
echo ""

# 3. Teste Backend Verfügbarkeit
echo "[INFO] Teste Backend Verfügbarkeit..."
if curl -s --connect-timeout 3 "http://${CRYPTOKING_IP}:8001/api/health" > /dev/null 2>&1; then
    echo "[SUCCESS] Backend ist erreichbar auf ${CRYPTOKING_IP}:8001"
else
    echo "[WARNING] Backend nicht erreichbar (läuft möglicherweise noch)"
fi
echo ""

# 4. Stoppe Frontend komplett
echo "[INFO] Stoppe Frontend..."
supervisorctl stop cyphertrade-frontend 2>/dev/null || true

# Warte bis Frontend gestoppt ist
sleep 3

# Prüfe ob noch Prozesse laufen
pkill -f "yarn start" 2>/dev/null || true
pkill -f "react-scripts start" 2>/dev/null || true
sleep 2

echo "[SUCCESS] Frontend gestoppt"
echo ""

# 5. Prüfe Supervisor Config
echo "[INFO] Prüfe Supervisor Config..."
if [ -f "/etc/supervisor/conf.d/cyphertrade-frontend.conf" ]; then
    echo "[SUCCESS] Supervisor Config vorhanden"
    # Prüfe ob REACT_APP_BACKEND_URL in Supervisor Config gesetzt ist
    if ! grep -q "REACT_APP_BACKEND_URL" /etc/supervisor/conf.d/cyphertrade-frontend.conf; then
        echo "[WARNING] REACT_APP_BACKEND_URL nicht in Supervisor Config!"
        echo "[INFO] Aktualisiere Supervisor Config..."
        # Backup
        cp /etc/supervisor/conf.d/cyphertrade-frontend.conf /etc/supervisor/conf.d/cyphertrade-frontend.conf.backup
        
        # Erstelle neue Config mit Umgebungsvariable
        cat > /etc/supervisor/conf.d/cyphertrade-frontend.conf << EOF
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
        echo "[SUCCESS] Supervisor Config aktualisiert"
        supervisorctl reread
        supervisorctl update
    fi
else
    echo "[ERROR] Supervisor Config nicht gefunden!"
    echo "[INFO] Erstelle Supervisor Config..."
    cat > /etc/supervisor/conf.d/cyphertrade-frontend.conf << EOF
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
    supervisorctl reread
    supervisorctl update
fi
echo ""

# 6. Starte Frontend neu
echo "[INFO] Starte Frontend neu..."
supervisorctl start cyphertrade-frontend 2>/dev/null || supervisorctl restart cyphertrade-frontend 2>/dev/null || true

echo "[INFO] Warte 10 Sekunden bis Frontend gestartet ist..."
sleep 10

# 7. Prüfe Status
echo ""
echo "[INFO] Prüfe Frontend Status..."
if supervisorctl status cyphertrade-frontend 2>/dev/null | grep -q "RUNNING"; then
    echo "[SUCCESS] Frontend läuft!"
else
    echo "[WARNING] Frontend Status:"
    supervisorctl status cyphertrade-frontend 2>&1 || echo "Service nicht gefunden"
fi
echo ""

# 8. Zeige Logs (letzte Zeilen)
echo "[INFO] Frontend Logs (letzte 10 Zeilen):"
if [ -f "/var/log/supervisor/cyphertrade-frontend-error.log" ]; then
    tail -10 /var/log/supervisor/cyphertrade-frontend-error.log 2>/dev/null || echo "Keine Fehler-Logs"
fi
echo ""

echo "=== Fix abgeschlossen ==="
echo ""
echo "Nächste Schritte:"
echo "1. Warten Sie 30-60 Sekunden, bis das Frontend vollständig gestartet ist"
echo "2. Im Browser: Hard Refresh (Ctrl + Shift + R) oder Seite komplett neu laden"
echo "3. Öffnen Sie: http://${CRYPTOKING_IP}:3000"
echo "4. Prüfen Sie die Browser Console (F12) - sollte jetzt ${CRYPTOKING_IP}:8001 verwenden"
echo ""
echo "Falls es immer noch nicht funktioniert:"
echo "  tail -f /var/log/supervisor/cyphertrade-frontend-error.log"

