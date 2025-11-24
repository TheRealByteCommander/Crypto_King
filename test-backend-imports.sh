#!/bin/bash
# Teste Backend-Imports

echo "=== Backend Import Test ==="
echo ""

cd /app/backend || { echo "[ERROR] /app/backend Verzeichnis nicht gefunden!"; exit 1; }

echo "[1/2] Teste Python-Syntax..."
python3 -m py_compile bot_manager.py binance_client.py server.py 2>&1
if [ $? -eq 0 ]; then
    echo "[SUCCESS] ✓ Syntax OK"
else
    echo "[ERROR] Syntax-Fehler gefunden!"
    exit 1
fi

echo ""
echo "[2/2] Teste Imports..."
python3 << 'EOF'
import sys
sys.path.insert(0, '/app/backend')

try:
    print("Importiere binance_client...")
    from binance_client import BinanceClientWrapper
    print("  ✓ binance_client importiert")
    
    print("Importiere bot_manager...")
    from bot_manager import TradingBot, BotManager
    print("  ✓ bot_manager importiert")
    
    print("Importiere server...")
    from server import app
    print("  ✓ server importiert")
    
    print("\n[SUCCESS] Alle Imports erfolgreich!")
    
except Exception as e:
    print(f"\n[ERROR] Import-Fehler: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo "\n[SUCCESS] Alle Tests erfolgreich!"
else
    echo "\n[ERROR] Import-Test fehlgeschlagen!"
fi

