#!/bin/bash
# Fix für Frontend Supervisor Config

INSTALL_DIR="/app"
FRONTEND_DIR="${INSTALL_DIR}/frontend"
CRYPTOKING_IP="192.168.178.154"

echo "=== Frontend Supervisor Config Fix ==="
echo ""

# 1. Prüfe ob Frontend Verzeichnis existiert
echo "[INFO] Prüfe Frontend Verzeichnis..."
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "[ERROR] Frontend Verzeichnis nicht gefunden: $FRONTEND_DIR"
    exit 1
else
    echo "[SUCCESS] Frontend Verzeichnis vorhanden: $FRONTEND_DIR"
fi
echo ""

# 2. Prüfe ob Yarn vorhanden ist
echo "[INFO] Prüfe Yarn Installation..."
YARN_PATH=$(which yarn 2>/dev/null || echo "/usr/bin/yarn")
if [ -f "$YARN_PATH" ] || command -v yarn &> /dev/null; then
    echo "[SUCCESS] Yarn gefunden: $YARN_PATH"
else
    echo "[ERROR] Yarn nicht gefunden!"
    echo "[INFO] Installiere Yarn..."
    npm install -g yarn 2>/dev/null || true
    YARN_PATH=$(which yarn 2>/dev/null || echo "/usr/bin/yarn")
fi
echo ""

# 3. Erstelle Frontend .env Datei
echo "[INFO] Erstelle Frontend .env Datei..."
cd "$FRONTEND_DIR" || exit 1
cat > .env << EOF
REACT_APP_BACKEND_URL=http://${CRYPTOKING_IP}:8001
EOF
echo "[SUCCESS] Frontend .env erstellt:"
cat .env
echo ""

# 4. Erstelle Supervisor Config
echo "[INFO] Erstelle Supervisor Config..."
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

echo "[SUCCESS] Supervisor Config erstellt:"
cat /etc/supervisor/conf.d/cyphertrade-frontend.conf
echo ""

# 5. Prüfe Supervisor Config Syntax
echo "[INFO] Prüfe Supervisor Config Syntax..."
if supervisorctl reread 2>&1 | grep -q "error"; then
    echo "[ERROR] Supervisor Config Syntax-Fehler!"
    supervisorctl reread 2>&1
else
    echo "[SUCCESS] Supervisor Config Syntax OK"
fi
echo ""

# 6. Supervisor neu laden
echo "[INFO] Lade Supervisor Config neu..."
supervisorctl reread 2>&1 | grep -v "pkg_resources" | grep -v "deprecated" || true
supervisorctl update 2>&1 | grep -v "pkg_resources" | grep -v "deprecated" || true
echo ""

# 7. Prüfe ob Frontend Service jetzt vorhanden ist
echo "[INFO] Prüfe Frontend Service Status..."
if supervisorctl status cyphertrade-frontend 2>&1 | grep -qE "(RUNNING|STOPPED|FATAL|STARTING)"; then
    echo "[SUCCESS] Frontend Service gefunden!"
    supervisorctl status cyphertrade-frontend 2>&1 | grep -v "pkg_resources" | grep -v "deprecated" || true
else
    echo "[ERROR] Frontend Service immer noch nicht gefunden!"
    echo "[INFO] Versuche manuell hinzuzufügen..."
fi
echo ""

# 8. Starte Frontend
echo "[INFO] Starte Frontend..."
supervisorctl start cyphertrade-frontend 2>&1 | grep -v "pkg_resources" | grep -v "deprecated" || {
    echo "[WARNING] Frontend konnte nicht über Supervisor gestartet werden"
    echo "[INFO] Prüfe ob manuell gestartet werden kann..."
}

sleep 5

# 9. Prüfe Status
echo ""
echo "[INFO] Finaler Status:"
supervisorctl status cyphertrade-frontend 2>&1 | grep -v "pkg_resources" | grep -v "deprecated" || {
    echo "[ERROR] Frontend Service nicht gefunden!"
    echo ""
    echo "[INFO] Prüfe Supervisor Logs:"
    tail -20 /var/log/supervisor/supervisord.log 2>/dev/null || echo "Keine Supervisor Logs gefunden"
}

echo ""
echo "=== Fix abgeschlossen ==="
echo ""
echo "Nächste Schritte:"
echo "1. Prüfe Status: sudo supervisorctl status cyphertrade-frontend"
echo "2. Prüfe Logs: tail -f /var/log/supervisor/cyphertrade-frontend-error.log"
echo "3. Falls Frontend nicht startet, starte manuell:"
echo "   cd $FRONTEND_DIR && REACT_APP_BACKEND_URL=http://${CRYPTOKING_IP}:8001 yarn start"

