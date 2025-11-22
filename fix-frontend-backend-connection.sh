#!/bin/bash
# Diagnose und Fix für Frontend-Backend Verbindungsprobleme

INSTALL_DIR="/app"
FRONTEND_DIR="${INSTALL_DIR}/frontend"
BACKEND_DIR="${INSTALL_DIR}/backend"

# Versuche CRYPTOKING_IP zu bestimmen
if [ -f "${BACKEND_DIR}/.env" ]; then
    CRYPTOKING_IP=$(grep -E "^REACT_APP_BACKEND_URL=" ${FRONTEND_DIR}/.env 2>/dev/null | cut -d'/' -f3 | cut -d':' -f1 || echo "192.168.178.154")
else
    CRYPTOKING_IP="192.168.178.154"
fi

echo "=== Frontend-Backend Verbindungsdiagnose ==="
echo ""

# 1. Prüfe Frontend .env Datei
echo "[INFO] Prüfe Frontend .env Datei..."
if [ -f "${FRONTEND_DIR}/.env" ]; then
    echo "[SUCCESS] .env Datei vorhanden"
    echo "Inhalt:"
    cat "${FRONTEND_DIR}/.env"
    BACKEND_URL=$(grep "^REACT_APP_BACKEND_URL=" "${FRONTEND_DIR}/.env" | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "")
    if [ -z "$BACKEND_URL" ]; then
        echo "[ERROR] REACT_APP_BACKEND_URL nicht gefunden!"
    else
        echo ""
        echo "[INFO] Backend URL: $BACKEND_URL"
        BACKEND_IP=$(echo "$BACKEND_URL" | cut -d'/' -f3 | cut -d':' -f1)
        BACKEND_PORT=$(echo "$BACKEND_URL" | cut -d'/' -f3 | cut -d':' -f2 | cut -d'/' -f1)
        echo "[INFO] Backend IP: $BACKEND_IP"
        echo "[INFO] Backend Port: $BACKEND_PORT"
    fi
else
    echo "[ERROR] Frontend .env Datei nicht gefunden!"
    echo "[INFO] Erstelle .env Datei..."
    echo "REACT_APP_BACKEND_URL=http://${CRYPTOKING_IP}:8001" > "${FRONTEND_DIR}/.env"
    echo "[SUCCESS] .env Datei erstellt"
fi
echo ""

# 2. Prüfe Backend Verfügbarkeit
echo "[INFO] Prüfe Backend Verfügbarkeit..."
BACKEND_IP=${BACKEND_IP:-$CRYPTOKING_IP}
BACKEND_PORT=${BACKEND_PORT:-8001}

# Teste localhost
if curl -s --connect-timeout 3 "http://localhost:${BACKEND_PORT}/api/health" > /dev/null 2>&1; then
    echo "[SUCCESS] Backend erreichbar auf localhost:${BACKEND_PORT}"
else
    echo "[WARNING] Backend nicht auf localhost:${BACKEND_PORT} erreichbar"
fi

# Teste mit IP
if curl -s --connect-timeout 3 "http://${BACKEND_IP}:${BACKEND_PORT}/api/health" > /dev/null 2>&1; then
    echo "[SUCCESS] Backend erreichbar auf ${BACKEND_IP}:${BACKEND_PORT}"
    BACKEND_REACHABLE=true
else
    echo "[ERROR] Backend NICHT erreichbar auf ${BACKEND_IP}:${BACKEND_PORT}"
    BACKEND_REACHABLE=false
fi
echo ""

# 3. Prüfe Backend Status
echo "[INFO] Prüfe Backend Status..."
if supervisorctl status cyphertrade-backend 2>/dev/null | grep -q "RUNNING"; then
    echo "[SUCCESS] Backend Service läuft"
    BACKEND_RUNNING=true
else
    echo "[ERROR] Backend Service läuft NICHT!"
    echo "Status:"
    supervisorctl status cyphertrade-backend 2>&1 || echo "Service nicht gefunden"
    BACKEND_RUNNING=false
fi
echo ""

# 4. Prüfe Backend Health Endpoint
echo "[INFO] Teste Backend Health Endpoint..."
HEALTH_RESPONSE=$(curl -s --connect-timeout 5 "http://${BACKEND_IP}:${BACKEND_PORT}/api/health" 2>&1)
if echo "$HEALTH_RESPONSE" | grep -q "\"status\""; then
    echo "[SUCCESS] Health Endpoint antwortet:"
    echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
else
    echo "[ERROR] Health Endpoint antwortet nicht korrekt:"
    echo "$HEALTH_RESPONSE"
fi
echo ""

# 5. Prüfe CORS Konfiguration
echo "[INFO] Prüfe CORS Konfiguration..."
if [ -f "${BACKEND_DIR}/server.py" ]; then
    if grep -q "CORSMiddleware" "${BACKEND_DIR}/server.py"; then
        echo "[SUCCESS] CORS Middleware gefunden"
        CORS_ORIGINS=$(grep -E "allow_origins|origins" "${BACKEND_DIR}/server.py" | head -1 || echo "*")
        echo "[INFO] CORS Origins: $CORS_ORIGINS"
    else
        echo "[WARNING] CORS Middleware nicht gefunden!"
    fi
fi
echo ""

# 6. Prüfe ob Frontend läuft
echo "[INFO] Prüfe Frontend Status..."
if supervisorctl status cyphertrade-frontend 2>/dev/null | grep -q "RUNNING"; then
    echo "[SUCCESS] Frontend Service läuft"
    FRONTEND_RUNNING=true
else
    echo "[WARNING] Frontend Service läuft NICHT oder nicht gefunden"
    FRONTEND_RUNNING=false
fi
echo ""

# 7. Teste Backend API Endpunkt (bot/start)
echo "[INFO] Teste Backend API Endpunkt..."
BOT_START_TEST=$(curl -s -X POST "http://${BACKEND_IP}:${BACKEND_PORT}/api/bot/status" 2>&1)
if echo "$BOT_START_TEST" | grep -qE "(\"is_running\"|\"status\"|error)" || echo "$BOT_START_TEST" | grep -q "Not Found"; then
    echo "[SUCCESS] API Endpunkt antwortet"
    echo "Response:"
    echo "$BOT_START_TEST" | head -5
else
    echo "[WARNING] API Endpunkt antwortet möglicherweise nicht korrekt:"
    echo "$BOT_START_TEST" | head -5
fi
echo ""

# 8. Zeige Netzwerk-Konfiguration
echo "[INFO] Netzwerk-Konfiguration:"
echo "Hostname: $(hostname)"
echo "IP-Adressen:"
hostname -I 2>/dev/null || ip addr show | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}' | cut -d'/' -f1
echo ""

# 9. Zusammenfassung und Lösungsvorschläge
echo "=== Zusammenfassung ==="
echo ""

if [ "$BACKEND_RUNNING" = false ]; then
    echo "[ERROR] Backend läuft nicht!"
    echo "[LÖSUNG] Backend starten:"
    echo "  sudo supervisorctl start cyphertrade-backend"
    echo "  sudo supervisorctl status cyphertrade-backend"
fi

if [ "$BACKEND_REACHABLE" = false ]; then
    echo "[ERROR] Backend ist nicht erreichbar auf ${BACKEND_IP}:${BACKEND_PORT}"
    echo "[LÖSUNG] Prüfen Sie:"
    echo "  1. Backend läuft: sudo supervisorctl status cyphertrade-backend"
    echo "  2. Port 8001 ist offen: sudo netstat -tuln | grep 8001"
    echo "  3. Firewall: sudo ufw status (falls aktiv)"
    echo "  4. Backend Logs: tail -f /var/log/supervisor/cyphertrade-backend-error.log"
fi

if [ "$FRONTEND_RUNNING" = false ]; then
    echo "[WARNING] Frontend läuft nicht"
    echo "[LÖSUNG] Frontend starten:"
    echo "  sudo supervisorctl start cyphertrade-frontend"
fi

# 10. Prüfe Frontend .env Datei Korrektheit
echo ""
echo "[INFO] Prüfe Frontend .env Datei Korrektheit..."
if [ -f "${FRONTEND_DIR}/.env" ]; then
    CURRENT_URL=$(grep "^REACT_APP_BACKEND_URL=" "${FRONTEND_DIR}/.env" | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "")
    EXPECTED_URL="http://${CRYPTOKING_IP}:8001"
    
    if [ "$CURRENT_URL" = "$EXPECTED_URL" ] || echo "$CURRENT_URL" | grep -q "${CRYPTOKING_IP}:8001"; then
        echo "[SUCCESS] Frontend .env enthält korrekte Backend URL"
    else
        echo "[WARNING] Frontend .env Backend URL könnte falsch sein:"
        echo "  Aktuell: $CURRENT_URL"
        echo "  Erwartet: $EXPECTED_URL"
        echo ""
        echo "[FIX] Korrigiere Frontend .env..."
        echo "REACT_APP_BACKEND_URL=http://${CRYPTOKING_IP}:8001" > "${FRONTEND_DIR}/.env"
        echo "[SUCCESS] Frontend .env aktualisiert"
        echo "[INFO] Frontend NEU starten, damit .env geladen wird:"
        echo "  sudo supervisorctl restart cyphertrade-frontend"
    fi
fi
echo ""

# 11. Finale Empfehlungen
echo "=== Nächste Schritte ==="
echo ""
echo "1. Frontend .env prüfen und ggf. korrigieren:"
echo "   cat ${FRONTEND_DIR}/.env"
echo "   Sollte enthalten: REACT_APP_BACKEND_URL=http://${CRYPTOKING_IP}:8001"
echo ""
echo "2. Frontend NEU starten (wichtig! .env wird beim Start geladen):"
echo "   sudo supervisorctl restart cyphertrade-frontend"
echo ""
echo "3. Backend Status prüfen:"
echo "   curl http://${CRYPTOKING_IP}:8001/api/health"
echo ""
echo "4. Browser Console prüfen (F12):"
echo "   - Öffnen Sie: http://${CRYPTOKING_IP}:3000"
echo "   - Drücken Sie F12 (Developer Tools)"
echo "   - Gehen Sie zu 'Console' Tab"
echo "   - Klicken Sie auf 'Start Trading Bot'"
echo "   - Prüfen Sie die Fehlermeldungen"
echo ""
echo "5. Network Tab prüfen:"
echo "   - Gehen Sie zu 'Network' Tab"
echo "   - Klicken Sie auf 'Start Trading Bot'"
echo "   - Suchen Sie nach dem POST Request zu /api/bot/start"
echo "   - Prüfen Sie Status Code und Response"
echo ""

