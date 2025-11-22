#!/bin/bash
# Prüfe Backend-Fehler und Logs

echo "=== Backend Fehler-Analyse ==="
echo ""

# 1. Prüfe Backend Status
echo "[INFO] Backend Status:"
sudo supervisorctl status cyphertrade-backend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)"
echo ""

# 2. Prüfe Backend Logs (letzte 50 Zeilen)
echo "[INFO] Backend Logs (letzte 50 Zeilen):"
if [ -f "/var/log/supervisor/cyphertrade-backend.log" ]; then
    tail -50 /var/log/supervisor/cyphertrade-backend.log
else
    echo "  Log-Datei nicht gefunden"
fi
echo ""

# 3. Prüfe Backend Error Logs
echo "[INFO] Backend Error Logs:"
if [ -f "/var/log/supervisor/cyphertrade-backend-error.log" ]; then
    tail -50 /var/log/supervisor/cyphertrade-backend-error.log
else
    echo "  Error-Log-Datei nicht gefunden"
fi
echo ""

# 4. Teste API Endpunkte
echo "[INFO] Teste API Endpunkte..."

# Test /api/bot/status
echo "[INFO] Teste GET /api/bot/status..."
STATUS_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -H "Origin: http://192.168.178.154:3000" \
    http://localhost:8001/api/bot/status 2>&1)

STATUS_HTTP_CODE=$(echo "$STATUS_RESPONSE" | grep "HTTP_CODE:" | cut -d':' -f2)
STATUS_BODY=$(echo "$STATUS_RESPONSE" | grep -v "HTTP_CODE:")

echo "  HTTP Status: $STATUS_HTTP_CODE"
if [ "$STATUS_HTTP_CODE" = "200" ]; then
    echo "[SUCCESS] /api/bot/status gibt 200 zurück"
    echo "  Response: $STATUS_BODY" | head -c 200
    echo "..."
elif [ "$STATUS_HTTP_CODE" = "500" ]; then
    echo "[ERROR] /api/bot/status gibt 500 zurück"
    echo "  Error Response:"
    echo "$STATUS_BODY" | head -20
else
    echo "[WARNING] /api/bot/status gibt $STATUS_HTTP_CODE zurück"
fi
echo ""

# Test /api/bot/start (POST)
echo "[INFO] Teste POST /api/bot/start..."
START_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -H "Origin: http://192.168.178.154:3000" \
    -d '{"strategy":"ma_crossover","symbol":"BTCUSDT","amount":100}' \
    http://localhost:8001/api/bot/start 2>&1)

START_HTTP_CODE=$(echo "$START_RESPONSE" | grep "HTTP_CODE:" | cut -d':' -f2)
START_BODY=$(echo "$START_RESPONSE" | grep -v "HTTP_CODE:")

echo "  HTTP Status: $START_HTTP_CODE"
if [ "$START_HTTP_CODE" = "200" ]; then
    echo "[SUCCESS] /api/bot/start gibt 200 zurück"
    echo "  Response: $START_BODY" | head -c 200
    echo "..."
elif [ "$START_HTTP_CODE" = "500" ]; then
    echo "[ERROR] /api/bot/start gibt 500 zurück"
    echo "  Error Response:"
    echo "$START_BODY" | head -20
else
    echo "[WARNING] /api/bot/start gibt $START_HTTP_CODE zurück"
fi
echo ""

# 5. Prüfe Python/Python3.11 Installation
echo "[INFO] Prüfe Python Installation:"
if command -v python3.11 > /dev/null 2>&1; then
    PYTHON_VERSION=$(python3.11 --version 2>&1)
    echo "[SUCCESS] $PYTHON_VERSION installiert"
else
    echo "[ERROR] Python 3.11 nicht gefunden!"
fi
echo ""

# 6. Prüfe Backend venv
echo "[INFO] Prüfe Backend Virtual Environment:"
if [ -d "/app/backend/venv" ]; then
    echo "[SUCCESS] venv vorhanden: /app/backend/venv"
    if [ -f "/app/backend/venv/bin/python" ]; then
        VENV_PYTHON=$(/app/backend/venv/bin/python --version 2>&1)
        echo "[SUCCESS] venv Python: $VENV_PYTHON"
    else
        echo "[ERROR] venv/bin/python nicht gefunden!"
    fi
else
    echo "[ERROR] venv nicht gefunden: /app/backend/venv"
fi
echo ""

# 7. Prüfe Backend Dependencies
echo "[INFO] Prüfe Backend Dependencies:"
if [ -f "/app/backend/requirements.txt" ]; then
    echo "[SUCCESS] requirements.txt vorhanden"
    echo "  Anzahl Dependencies: $(wc -l < /app/backend/requirements.txt)"
else
    echo "[ERROR] requirements.txt nicht gefunden!"
fi
echo ""

# 8. Teste ob Backend-Prozess läuft
echo "[INFO] Prüfe Backend-Prozess:"
if pgrep -f "uvicorn.*server\|uvicorn.*backend" > /dev/null 2>&1; then
    BACKEND_PID=$(pgrep -f "uvicorn.*server\|uvicorn.*backend" | head -1)
    echo "[SUCCESS] Backend-Prozess läuft (PID: $BACKEND_PID)"
    echo "  Command:"
    ps -p $BACKEND_PID -o cmd= 2>/dev/null | head -1
else
    echo "[ERROR] Backend-Prozess läuft NICHT!"
fi
echo ""

echo "=== Zusammenfassung ==="
echo ""
echo "Bitte prüfen Sie:"
echo "1. Backend Logs für Fehler-Details"
echo "2. Python 3.11 und venv sind korrekt installiert"
echo "3. Backend Dependencies sind installiert"
echo ""
echo "Um die Fehler zu sehen, führen Sie aus:"
echo "  tail -f /var/log/supervisor/cyphertrade-backend.log"
echo "  tail -f /var/log/supervisor/cyphertrade-backend-error.log"
echo ""

