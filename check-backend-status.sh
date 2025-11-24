#!/bin/bash
# Prüfe Backend-Status und Logs

echo "=== Backend Status Check ==="
echo ""

# 1. Supervisor Status
echo "[1/4] Supervisor Status..."
sudo supervisorctl status cyphertrade-backend
echo ""

# 2. Prozess prüfen
echo "[2/4] Prozess Status..."
ps aux | grep -E "uvicorn|python.*server" | grep -v grep || echo "Kein Prozess gefunden"
echo ""

# 3. Logs prüfen
echo "[3/4] Letzte Backend Log-Zeilen (Output)..."
sudo tail -30 /var/log/supervisor/cyphertrade-backend.log 2>/dev/null || echo "Kein Output Log gefunden"
echo ""

# 4. Error Logs prüfen
echo "[4/4] Letzte Error Log-Zeilen..."
sudo tail -30 /var/log/supervisor/cyphertrade-backend-error.log 2>/dev/null || echo "Kein Error Log gefunden"
echo ""

# 5. API Test
echo "[5/5] Teste API Endpoint..."
curl -s http://localhost:8000/api/health 2>/dev/null && echo "" || echo "API nicht erreichbar"
curl -s http://localhost:8000/api/bots/status 2>/dev/null | head -c 200 && echo "" || echo "API nicht erreichbar"
