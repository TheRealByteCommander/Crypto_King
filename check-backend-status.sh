#!/bin/bash
# Prüft den Backend-Status und zeigt alle verfügbaren Informationen

BACKEND_URL="http://localhost:8001"

echo "=== Backend Status-Check ==="
echo "Backend URL: ${BACKEND_URL}"
echo ""

# 1. Health Check
echo "[INFO] Health Check..."
curl -s "${BACKEND_URL}/api/health" | python3 -m json.tool 2>/dev/null || curl -s "${BACKEND_URL}/api/health"
echo ""
echo ""

# 2. Agents Status
echo "[INFO] Agents Konfiguration..."
curl -s "${BACKEND_URL}/api/agents" | python3 -m json.tool 2>/dev/null || curl -s "${BACKEND_URL}/api/agents"
echo ""
echo ""

# 3. Bot Status
echo "[INFO] Bot Status..."
curl -s "${BACKEND_URL}/api/bot/status" | python3 -m json.tool 2>/dev/null || curl -s "${BACKEND_URL}/api/bot/status"
echo ""
echo ""

# 4. Verfügbare Strategien
echo "[INFO] Verfügbare Strategien..."
curl -s "${BACKEND_URL}/api/strategies" | python3 -m json.tool 2>/dev/null || curl -s "${BACKEND_URL}/api/strategies"
echo ""
echo ""

echo "=== Zusammenfassung ==="
echo "Wenn Binance API-Key Fehler angezeigt wird:"
echo "  1. Prüfen Sie die .env Datei: /app/backend/.env"
echo "  2. Stellen Sie sicher, dass BINANCE_API_KEY und BINANCE_API_SECRET korrekt sind"
echo "  3. Starten Sie das Backend neu: sudo supervisorctl restart cyphertrade-backend"
echo ""
echo "Alle verfügbaren Endpunkte:"
echo "  - GET  ${BACKEND_URL}/api/health        - System Health Check"
echo "  - GET  ${BACKEND_URL}/api/agents        - Agents Konfiguration"
echo "  - GET  ${BACKEND_URL}/api/bot/status    - Bot Status"
echo "  - GET  ${BACKEND_URL}/api/strategies    - Verfügbare Strategien"
echo "  - GET  ${BACKEND_URL}/api/trades        - Trade History"
echo "  - GET  ${BACKEND_URL}/api/logs          - Agent Logs"
echo "  - POST ${BACKEND_URL}/api/bot/start     - Bot starten"
echo "  - POST ${BACKEND_URL}/api/bot/stop      - Bot stoppen"

