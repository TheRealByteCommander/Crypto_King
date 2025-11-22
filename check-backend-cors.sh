#!/bin/bash
# Prüfe Backend CORS-Konfiguration und Status

echo "=== Backend CORS & Status Check ==="
echo ""

# 1. Prüfe Backend Status
echo "[INFO] Prüfe Backend Status..."
sudo supervisorctl status cyphertrade-backend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)"
echo ""

# 2. Prüfe ob Backend läuft
if pgrep -f "uvicorn.*server\|uvicorn.*backend" > /dev/null 2>&1; then
    echo "[SUCCESS] Backend Prozess läuft!"
    pgrep -f "uvicorn.*server\|uvicorn.*backend"
else
    echo "[ERROR] Backend Prozess läuft NICHT!"
fi
echo ""

# 3. Prüfe Port 8001
if lsof -i :8001 > /dev/null 2>&1; then
    echo "[SUCCESS] Port 8001 ist belegt"
    lsof -i :8001 | head -3
else
    echo "[ERROR] Port 8001 ist NICHT belegt!"
fi
echo ""

# 4. Prüfe CORS_ORIGINS in .env
echo "[INFO] CORS_ORIGINS Konfiguration:"
if [ -f "/app/backend/.env" ]; then
    grep "^CORS_ORIGINS" /app/backend/.env || echo "  (nicht gefunden)"
else
    echo "  (.env Datei nicht gefunden)"
fi
echo ""

# 5. Prüfe Backend Logs
echo "[INFO] Letzte Backend Logs (Startup & CORS):"
if [ -f "/var/log/supervisor/cyphertrade-backend.log" ]; then
    tail -50 /var/log/supervisor/cyphertrade-backend.log | grep -E "(CORS|started|ERROR|Exception)" | tail -10 || echo "  (keine relevanten Logs gefunden)"
else
    echo "  (Log-Datei nicht gefunden)"
fi
echo ""

# 6. Teste CORS-Header
echo "[INFO] Teste CORS-Header..."
sleep 2

CORS_RESPONSE=$(curl -s -I -H "Origin: http://192.168.178.154:3000" \
    http://localhost:8001/api/bot/status 2>&1)

if echo "$CORS_RESPONSE" | grep -qi "access-control-allow-origin"; then
    echo "[SUCCESS] CORS-Header vorhanden:"
    echo "$CORS_RESPONSE" | grep -i "access-control" | head -5
else
    echo "[ERROR] CORS-Header NICHT vorhanden!"
    echo "Response Headers:"
    echo "$CORS_RESPONSE" | head -10
fi
echo ""

# 7. Teste API Response
echo "[INFO] Teste API Response..."
API_RESPONSE=$(curl -s -H "Origin: http://192.168.178.154:3000" \
    http://localhost:8001/api/bot/status 2>&1)

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Origin: http://192.168.178.154:3000" \
    http://localhost:8001/api/bot/status 2>&1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "[SUCCESS] API gibt 200 zurück"
    echo "Response (erste 200 Zeichen):"
    echo "$API_RESPONSE" | head -c 200
    echo "..."
elif [ "$HTTP_CODE" = "500" ]; then
    echo "[WARNING] API gibt 500 zurück (aber CORS-Header sollten trotzdem gesendet werden)"
    echo "Response:"
    echo "$API_RESPONSE" | head -20
else
    echo "[WARNING] API gibt HTTP $HTTP_CODE zurück"
    echo "Response:"
    echo "$API_RESPONSE" | head -10
fi
echo ""

# 8. Teste OPTIONS Request (Preflight)
echo "[INFO] Teste OPTIONS Request (CORS Preflight)..."
OPTIONS_RESPONSE=$(curl -s -X OPTIONS \
    -H "Origin: http://192.168.178.154:3000" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: Content-Type" \
    -o /dev/null -w "%{http_code}" \
    http://localhost:8001/api/bot/start 2>&1)

if [ "$OPTIONS_RESPONSE" = "200" ] || [ "$OPTIONS_RESPONSE" = "204" ] || [ "$OPTIONS_RESPONSE" = "405" ]; then
    echo "[SUCCESS] OPTIONS Request akzeptiert (Status: $OPTIONS_RESPONSE)"
else
    echo "[WARNING] OPTIONS Request Status: $OPTIONS_RESPONSE"
fi
echo ""

echo "=== Zusammenfassung ==="
echo ""
echo "Wenn CORS-Header vorhanden sind, sollte das Frontend jetzt funktionieren."
echo "Bitte im Browser:"
echo "1. Hard Refresh (Ctrl + Shift + R)"
echo "2. Console (F12) prüfen - sollte keine CORS-Fehler mehr zeigen"
echo "3. Network Tab - Responses sollten CORS-Header enthalten"
echo ""

