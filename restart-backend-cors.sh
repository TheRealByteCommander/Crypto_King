#!/bin/bash
# Forcierter Backend Neustart mit CORS-Fix

INSTALL_DIR="/app"
BACKEND_DIR="${INSTALL_DIR}/backend"
CRYPTOKING_IP="192.168.178.154"

echo "=== Forcierter Backend Neustart mit CORS-Fix ==="
echo ""

# 1. Stoppe Backend komplett
echo "[INFO] Stoppe Backend..."
supervisorctl stop cyphertrade-backend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true

# Töte alle uvicorn Prozesse
pkill -9 -f "uvicorn.*backend\|uvicorn.*server" 2>/dev/null || true
sleep 2

# Töte Prozesse auf Port 8001
if lsof -ti :8001 > /dev/null 2>&1; then
    echo "[INFO] Töte Prozesse auf Port 8001..."
    lsof -ti :8001 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# 2. Prüfe und setze CORS_ORIGINS in .env
echo "[INFO] Prüfe Backend .env..."
if [ ! -f "${BACKEND_DIR}/.env" ]; then
    echo "[ERROR] Backend .env nicht gefunden!"
    exit 1
fi

# Setze CORS_ORIGINS (überschreibe falls vorhanden)
echo "[INFO] Setze CORS_ORIGINS..."
if grep -q "^CORS_ORIGINS" "${BACKEND_DIR}/.env" 2>/dev/null; then
    # Ersetze existierende Zeile
    sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=http://${CRYPTOKING_IP}:3000,http://localhost:3000,http://127.0.0.1:3000|g" "${BACKEND_DIR}/.env"
else
    # Füge hinzu
    echo "" >> "${BACKEND_DIR}/.env"
    echo "# CORS Configuration" >> "${BACKEND_DIR}/.env"
    echo "CORS_ORIGINS=http://${CRYPTOKING_IP}:3000,http://localhost:3000,http://127.0.0.1:3000" >> "${BACKEND_DIR}/.env"
fi

echo "[SUCCESS] CORS_ORIGINS konfiguriert:"
grep "^CORS_ORIGINS" "${BACKEND_DIR}/.env"
echo ""

# 3. Prüfe ob server.py die CORS-Middleware vor den Routen hat
echo "[INFO] Prüfe Backend Code..."
if grep -A 10 "app = FastAPI" "${BACKEND_DIR}/server.py" 2>/dev/null | grep -q "add_middleware.*CORSMiddleware"; then
    echo "[SUCCESS] CORS-Middleware ist vor den Routen (korrekt)"
else
    echo "[ERROR] CORS-Middleware ist NICHT vor den Routen!"
    echo "[INFO] Aktualisiere Repository..."
    cd "$INSTALL_DIR"
    git pull
fi
echo ""

# 4. Starte Backend über Supervisor
echo "[INFO] Starte Backend über Supervisor..."
cd "$BACKEND_DIR" || exit 1

# Aktiviere venv falls vorhanden
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Stelle sicher, dass Supervisor Config korrekt ist
cat > /etc/supervisor/conf.d/cyphertrade-backend.conf << EOF
[program:cyphertrade-backend]
directory=${BACKEND_DIR}
command=${BACKEND_DIR}/venv/bin/python -m uvicorn server:app --host 0.0.0.0 --port 8001
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/cyphertrade-backend.log
stderr_logfile=/var/log/supervisor/cyphertrade-backend-error.log
environment=PATH="${BACKEND_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin"
EOF

# Supervisor neu laden
supervisorctl reread 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true
supervisorctl update 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true

# Starte Backend
supervisorctl start cyphertrade-backend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || {
    echo "[WARNING] Supervisor Start fehlgeschlagen, starte manuell..."
    
    cd "$BACKEND_DIR"
    source venv/bin/activate 2>/dev/null || true
    nohup python -m uvicorn server:app --host 0.0.0.0 --port 8001 > /var/log/supervisor/cyphertrade-backend.log 2>&1 &
    BACKEND_PID=$!
    echo "[SUCCESS] Backend manuell gestartet (PID: $BACKEND_PID)"
}

sleep 10

# 5. Prüfe Status
echo ""
echo "[INFO] Prüfe Backend Status..."

# Prüfe Prozess
if pgrep -f "uvicorn.*server\|uvicorn.*backend" > /dev/null 2>&1; then
    echo "[SUCCESS] Backend Prozess läuft!"
    pgrep -f "uvicorn.*server\|uvicorn.*backend"
else
    echo "[ERROR] Backend Prozess läuft NICHT!"
fi

# Prüfe Port
if lsof -i :8001 > /dev/null 2>&1; then
    echo "[SUCCESS] Port 8001 ist belegt"
    lsof -i :8001 | head -3
else
    echo "[ERROR] Port 8001 ist NICHT belegt!"
fi

# Supervisor Status
echo "[INFO] Supervisor Status:"
supervisorctl status cyphertrade-backend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true

# 6. Teste CORS direkt
echo ""
echo "[INFO] Teste CORS-Header..."
sleep 3

# Teste ob CORS-Header vorhanden sind
CORS_TEST=$(curl -s -I -H "Origin: http://${CRYPTOKING_IP}:3000" \
    "http://localhost:8001/api/bot/status" 2>&1 | grep -i "access-control-allow-origin" || echo "NOT_FOUND")

if echo "$CORS_TEST" | grep -qi "access-control"; then
    echo "[SUCCESS] CORS-Header vorhanden:"
    echo "$CORS_TEST"
else
    echo "[ERROR] CORS-Header NICHT vorhanden!"
    echo "[INFO] Prüfe Backend Logs..."
    if [ -f "/var/log/supervisor/cyphertrade-backend.log" ]; then
        echo "[INFO] Letzte Backend-Logs:"
        tail -30 /var/log/supervisor/cyphertrade-backend.log | tail -10
    fi
fi

# 7. Zeige Backend Logs (letzte 20 Zeilen)
echo ""
echo "[INFO] Backend Logs (letzte 20 Zeilen):"
if [ -f "/var/log/supervisor/cyphertrade-backend.log" ]; then
    tail -20 /var/log/supervisor/cyphertrade-backend.log
else
    echo "  (Log-Datei nicht gefunden)"
fi

echo ""
echo "=== Fertig ==="
echo ""
echo "Bitte prüfen Sie:"
echo "1. Backend läuft auf Port 8001"
echo "2. CORS-Header sind vorhanden"
echo "3. Im Browser: Hard Refresh (Ctrl + Shift + R)"
echo "4. Console sollte keine CORS-Fehler mehr zeigen"
echo ""

