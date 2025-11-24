#!/bin/bash
# Prüfe Backend-Fehler

echo "=== Backend Fehlerdiagnose ==="
echo ""

cd /app || { echo "[ERROR] /app Verzeichnis nicht gefunden!"; exit 1; }

# 1. Prüfe Supervisor Logs
echo "[1/3] Prüfe Supervisor Error Log..."
echo "--- Letzte 50 Zeilen des Error Logs ---"
sudo tail -50 /var/log/supervisor/cyphertrade-backend-error.log 2>/dev/null || echo "Kein Error Log gefunden"
echo ""

# 2. Prüfe Backend Output Log
echo "[2/3] Prüfe Backend Output Log..."
echo "--- Letzte 50 Zeilen des Output Logs ---"
sudo tail -50 /var/log/supervisor/cyphertrade-backend.log 2>/dev/null || echo "Kein Output Log gefunden"
echo ""

# 3. Versuche Backend manuell zu starten
echo "[3/3] Versuche Backend manuell zu starten (für Fehlermeldung)..."
echo "--- Python Syntax Check ---"
cd /app/backend
python3 -m py_compile bot_manager.py binance_client.py 2>&1 || echo "Syntax-Fehler gefunden!"

echo ""
echo "=== Versuche Backend direkt zu starten ==="
cd /app/backend
timeout 5 python3 -c "from bot_manager import TradingBot; print('Import erfolgreich!')" 2>&1 || echo "Import-Fehler!"

