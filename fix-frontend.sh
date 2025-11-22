#!/bin/bash
# Frontend-Problem Diagnose und Behebung

INSTALL_DIR="/app"
FRONTEND_DIR="${INSTALL_DIR}/frontend"

echo "=== Frontend Diagnose ==="
echo ""

# 1. Prüfe Supervisor Status
echo "[INFO] Prüfe Supervisor Status..."
if command -v supervisorctl &> /dev/null; then
    echo "Supervisor Status:"
    supervisorctl status cyphertrade-frontend 2>&1 || echo "Frontend Service nicht gefunden"
else
    echo "[ERROR] Supervisor nicht installiert!"
fi
echo ""

# 2. Prüfe Frontend-Verzeichnis
echo "[INFO] Prüfe Frontend-Verzeichnis..."
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "[ERROR] Frontend-Verzeichnis nicht gefunden: $FRONTEND_DIR"
    exit 1
else
    echo "[SUCCESS] Frontend-Verzeichnis vorhanden: $FRONTEND_DIR"
fi
echo ""

# 3. Prüfe Node.js und Yarn
echo "[INFO] Prüfe Node.js und Yarn..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "[SUCCESS] Node.js installiert: $NODE_VERSION"
else
    echo "[ERROR] Node.js nicht installiert!"
    exit 1
fi

if command -v yarn &> /dev/null; then
    YARN_VERSION=$(yarn --version)
    echo "[SUCCESS] Yarn installiert: $YARN_VERSION"
    YARN_PATH=$(which yarn)
    echo "Yarn Pfad: $YARN_PATH"
else
    echo "[ERROR] Yarn nicht installiert!"
    echo "[INFO] Installiere Yarn..."
    npm install -g yarn 2>&1 | grep -v "npm WARN" || true
    if command -v yarn &> /dev/null; then
        echo "[SUCCESS] Yarn installiert"
    else
        echo "[ERROR] Yarn konnte nicht installiert werden!"
        exit 1
    fi
fi
echo ""

# 4. Prüfe Frontend Dependencies
echo "[INFO] Prüfe Frontend Dependencies..."
cd "$FRONTEND_DIR" || exit 1

if [ ! -d "node_modules" ]; then
    echo "[WARNING] node_modules nicht gefunden!"
    echo "[INFO] Installiere Dependencies..."
    yarn install --frozen-lockfile 2>&1 | tail -20
else
    echo "[SUCCESS] node_modules vorhanden"
fi
echo ""

# 5. Prüfe .env Datei
echo "[INFO] Prüfe Frontend .env Datei..."
if [ -f "$FRONTEND_DIR/.env" ]; then
    echo "[SUCCESS] .env Datei vorhanden"
    echo "Inhalt:"
    cat "$FRONTEND_DIR/.env"
else
    echo "[WARNING] .env Datei nicht gefunden!"
    echo "[INFO] Erstelle .env Datei..."
    # Versuche CRYPTOKING_IP aus install.sh oder verwende localhost
    if [ -z "$CRYPTOKING_IP" ]; then
        # Versuche IP aus Backend .env zu extrahieren
        if [ -f "${INSTALL_DIR}/backend/.env" ]; then
            # Fallback zu localhost
            CRYPTOKING_IP="localhost"
        fi
    fi
    echo "REACT_APP_BACKEND_URL=http://${CRYPTOKING_IP:-localhost}:8001" > "$FRONTEND_DIR/.env"
    echo "[SUCCESS] .env Datei erstellt"
fi
echo ""

# 6. Prüfe Port 3000
echo "[INFO] Prüfe Port 3000..."
if lsof -i :3000 &> /dev/null || netstat -tuln 2>/dev/null | grep -q ":3000"; then
    echo "[WARNING] Port 3000 bereits belegt!"
    echo "Prozesse auf Port 3000:"
    lsof -i :3000 2>/dev/null || netstat -tuln 2>/dev/null | grep ":3000"
else
    echo "[SUCCESS] Port 3000 frei"
fi
echo ""

# 7. Prüfe Frontend Logs
echo "[INFO] Prüfe Frontend Logs (letzte 20 Zeilen)..."
if [ -f "/var/log/supervisor/cyphertrade-frontend.log" ]; then
    echo "--- stdout log ---"
    tail -20 /var/log/supervisor/cyphertrade-frontend.log
fi
if [ -f "/var/log/supervisor/cyphertrade-frontend-error.log" ]; then
    echo "--- error log ---"
    tail -20 /var/log/supervisor/cyphertrade-frontend-error.log
fi
echo ""

# 8. Prüfe Supervisor Konfiguration
echo "[INFO] Prüfe Supervisor Konfiguration..."
if [ -f "/etc/supervisor/conf.d/cyphertrade-frontend.conf" ]; then
    echo "[SUCCESS] Supervisor Config vorhanden:"
    cat /etc/supervisor/conf.d/cyphertrade-frontend.conf
else
    echo "[ERROR] Supervisor Config nicht gefunden!"
    echo "[INFO] Erstelle Supervisor Config..."
    cat > /etc/supervisor/conf.d/cyphertrade-frontend.conf << EOF
[program:cyphertrade-frontend]
directory=$FRONTEND_DIR
command=$(which yarn) start
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/cyphertrade-frontend.log
stderr_logfile=/var/log/supervisor/cyphertrade-frontend-error.log
environment=PATH="/usr/local/bin:/usr/bin:/bin",REACT_APP_BACKEND_URL="http://${CRYPTOKING_IP:-localhost}:8001"
EOF
    echo "[SUCCESS] Supervisor Config erstellt"
    supervisorctl reread
    supervisorctl update
fi
echo ""

# 9. Versuche Frontend zu starten
echo "=== Frontend starten ==="
echo "[INFO] Stoppe Frontend Service (falls laufend)..."
supervisorctl stop cyphertrade-frontend 2>/dev/null || true

echo "[INFO] Starte Frontend Service..."
supervisorctl start cyphertrade-frontend 2>/dev/null || {
    echo "[ERROR] Frontend konnte nicht über Supervisor gestartet werden!"
    echo "[INFO] Versuche manuell zu starten..."
    cd "$FRONTEND_DIR"
    export REACT_APP_BACKEND_URL="http://${CRYPTOKING_IP:-localhost}:8001"
    nohup yarn start > /var/log/supervisor/cyphertrade-frontend.log 2>&1 &
    echo "[INFO] Frontend manuell gestartet (PID: $!)"
}

sleep 5

# 10. Prüfe Status
echo ""
echo "=== Status Prüfung ==="
if supervisorctl status cyphertrade-frontend 2>/dev/null | grep -q "RUNNING"; then
    echo "[SUCCESS] Frontend läuft!"
elif pgrep -f "yarn start" > /dev/null || pgrep -f "react-scripts start" > /dev/null; then
    echo "[SUCCESS] Frontend läuft (manuell gestartet)!"
else
    echo "[ERROR] Frontend läuft nicht!"
    echo ""
    echo "[INFO] Prüfen Sie die Logs:"
    echo "  tail -f /var/log/supervisor/cyphertrade-frontend-error.log"
    echo ""
    echo "[INFO] Oder starten Sie manuell:"
    echo "  cd $FRONTEND_DIR"
    echo "  yarn start"
fi

echo ""
echo "=== Zusammenfassung ==="
echo "Frontend sollte auf erreichbar sein:"
echo "  - http://localhost:3000"
echo "  - http://${CRYPTOKING_IP:-$(hostname -I | awk '{print $1}')}:3000"
echo ""
echo "Status prüfen:"
echo "  sudo supervisorctl status cyphertrade-frontend"
echo ""
echo "Logs ansehen:"
echo "  tail -f /var/log/supervisor/cyphertrade-frontend-error.log"

