#!/bin/bash
# Fix Backend CORS und 500-Fehler

INSTALL_DIR="/app"
BACKEND_DIR="${INSTALL_DIR}/backend"
CRYPTOKING_IP="192.168.178.154"

echo "=== Backend CORS & 500-Fehler Fix ==="
echo ""

# 1. Repository aktualisieren
echo "[INFO] Aktualisiere Repository..."
cd "$INSTALL_DIR" || exit 1
git pull 2>&1 | grep -v "Already up to date" || true"
echo ""

# 2. Prüfe Backend .env
echo "[INFO] Prüfe Backend .env..."
if [ ! -f "${BACKEND_DIR}/.env" ]; then
    echo "[ERROR] Backend .env nicht gefunden!"
    exit 1
fi

# 3. Stelle sicher, dass CORS_ORIGINS gesetzt ist
echo "[INFO] Prüfe CORS_ORIGINS Konfiguration..."
if ! grep -q "^CORS_ORIGINS" "${BACKEND_DIR}/.env"; then
    echo "[INFO] CORS_ORIGINS nicht gefunden, füge hinzu..."
    echo "" >> "${BACKEND_DIR}/.env"
    echo "# CORS Configuration" >> "${BACKEND_DIR}/.env"
    echo "CORS_ORIGINS=http://${CRYPTOKING_IP}:3000,http://localhost:3000,http://127.0.0.1:3000" >> "${BACKEND_DIR}/.env"
    echo "[SUCCESS] CORS_ORIGINS hinzugefügt"
else
    # Aktualisiere CORS_ORIGINS falls nötig
    if ! grep -q "${CRYPTOKING_IP}:3000" "${BACKEND_DIR}/.env"; then
        echo "[INFO] Aktualisiere CORS_ORIGINS..."
        sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=http://${CRYPTOKING_IP}:3000,http://localhost:3000,http://127.0.0.1:3000|g" "${BACKEND_DIR}/.env"
        echo "[SUCCESS] CORS_ORIGINS aktualisiert"
    else
        echo "[SUCCESS] CORS_ORIGINS bereits korrekt konfiguriert"
    fi
fi
echo ""

# 4. Zeige CORS_ORIGINS
echo "[INFO] Aktuelle CORS_ORIGINS Konfiguration:"
grep "^CORS_ORIGINS" "${BACKEND_DIR}/.env" || echo "  (nicht gefunden)"
echo ""

# 5. Prüfe Backend Code für CORS-Middleware Position
echo "[INFO] Prüfe Backend Code (CORS-Middleware sollte vor Routen sein)..."
if grep -A 5 "app = FastAPI" "${BACKEND_DIR}/server.py" | grep -q "add_middleware.*CORSMiddleware"; then
    echo "[SUCCESS] CORS-Middleware ist korrekt positioniert (vor Routen)"
else
    echo "[WARNING] CORS-Middleware Position sollte überprüft werden"
fi
echo ""

# 6. Restart Backend
echo "[INFO] Starte Backend neu..."
supervisorctl stop cyphertrade-backend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true
sleep 3

# Prüfe ob noch Prozesse laufen
if pgrep -f "uvicorn.*backend" > /dev/null; then
    echo "[WARNING] Noch laufende Backend-Prozesse gefunden, beende sie..."
    pgrep -f "uvicorn.*backend" | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Prüfe Port 8001
if lsof -i :8001 &> /dev/null; then
    echo "[WARNING] Port 8001 noch belegt, beende Prozess..."
    lsof -ti :8001 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Starte über Supervisor
supervisorctl start cyphertrade-backend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || {
    echo "[ERROR] Backend konnte nicht über Supervisor gestartet werden!"
    echo "[INFO] Starte Backend manuell..."
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    nohup uvicorn server:app --host 0.0.0.0 --port 8001 > /var/log/supervisor/cyphertrade-backend.log 2>&1 &
    BACKEND_PID=$!
    echo "[SUCCESS] Backend manuell gestartet (PID: $BACKEND_PID)"
}

sleep 10

# 7. Prüfe Backend Status
echo ""
echo "[INFO] Prüfe Backend Status..."

# Prüfe ob Backend läuft
if pgrep -f "uvicorn.*backend\|uvicorn.*server" > /dev/null; then
    echo "[SUCCESS] Backend läuft!"
    pgrep -f "uvicorn.*backend\|uvicorn.*server"
else
    echo "[ERROR] Backend läuft NICHT!"
fi

# Prüfe Port 8001
if lsof -i :8001 &> /dev/null; then
    echo "[SUCCESS] Port 8001 ist belegt (Backend läuft)"
else
    echo "[WARNING] Port 8001 ist frei (Backend startet möglicherweise noch)"
fi

# Supervisor Status
supervisorctl status cyphertrade-backend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true

# 8. Teste Backend API
echo ""
echo "[INFO] Teste Backend API..."

sleep 5

# Test CORS mit OPTIONS Request
echo "[INFO] Teste CORS mit OPTIONS Request..."
OPTIONS_RESPONSE=$(curl -s -X OPTIONS \
    -H "Origin: http://${CRYPTOKING_IP}:3000" \
    -H "Access-Control-Request-Method: GET" \
    -H "Access-Control-Request-Headers: Content-Type" \
    -o /dev/null -w "%{http_code}" \
    "http://localhost:8001/api/bot/status" 2>&1)

if [ "$OPTIONS_RESPONSE" == "200" ] || [ "$OPTIONS_RESPONSE" == "204" ] || [ "$OPTIONS_RESPONSE" == "405" ]; then
    echo "[SUCCESS] CORS OPTIONS Request akzeptiert (Status: $OPTIONS_RESPONSE)"
else
    echo "[WARNING] CORS OPTIONS Request Status: $OPTIONS_RESPONSE"
fi

# Test GET Request
echo "[INFO] Teste GET Request..."
GET_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8001/api/bot/status" 2>&1)

if [ "$GET_RESPONSE" == "200" ]; then
    echo "[SUCCESS] GET Request erfolgreich (Status: 200)"
elif [ "$GET_RESPONSE" == "500" ]; then
    echo "[WARNING] GET Request gibt 500-Fehler (möglicherweise Binance API Problem)"
    echo "[INFO] Prüfe Backend Logs für Details..."
    if [ -f "/var/log/supervisor/cyphertrade-backend.log" ]; then
        echo "[INFO] Letzte Backend-Logs (Fehler):"
        tail -20 /var/log/supervisor/cyphertrade-backend.log | grep -i "error\|exception\|traceback" | tail -5 || echo "  (keine Fehler gefunden)"
    fi
else
    echo "[WARNING] GET Request Status: $GET_RESPONSE"
fi

# Test Health Endpoint
echo "[INFO] Teste Health Endpoint..."
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8001/api/health" 2>&1)

if [ "$HEALTH_RESPONSE" == "200" ]; then
    echo "[SUCCESS] Health Endpoint erfolgreich (Status: 200)"
else
    echo "[WARNING] Health Endpoint Status: $HEALTH_RESPONSE"
fi

echo ""
echo "=== Zusammenfassung ==="
echo ""
echo "Backend sollte jetzt auf http://${CRYPTOKING_IP}:8001 laufen"
echo "Frontend sollte auf http://${CRYPTOKING_IP}:3000 laufen"
echo ""
echo "CORS ist konfiguriert für:"
echo "  - http://${CRYPTOKING_IP}:3000"
echo "  - http://localhost:3000"
echo "  - http://127.0.0.1:3000"
echo ""
echo "Bitte prüfen Sie im Browser:"
echo "1. Hard Refresh (Ctrl + Shift + R)"
echo "2. Console (F12) - sollte keine CORS-Fehler mehr zeigen"
echo "3. Network Tab - Responses sollten CORS-Header enthalten"
echo ""
echo "Falls weiterhin 500-Fehler auftreten:"
echo "1. Prüfe Binance API Keys in ${BACKEND_DIR}/.env"
echo "2. Prüfe Backend Logs: tail -f /var/log/supervisor/cyphertrade-backend.log"
echo ""

