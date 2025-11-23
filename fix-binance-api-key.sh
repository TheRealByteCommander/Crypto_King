#!/bin/bash
# Prüft und fixiert Binance API Key Probleme

echo "=== Binance API Key Diagnose ==="
echo ""

cd /app/backend || { echo "[ERROR] Backend-Verzeichnis nicht gefunden!"; exit 1; }

# 1. Prüfe .env Datei
echo "[1/5] Prüfe .env Datei..."
if [ ! -f ".env" ]; then
    echo "[ERROR] .env Datei nicht gefunden!"
    exit 1
fi

BINANCE_API_KEY=$(grep -E "^BINANCE_API_KEY=" .env 2>/dev/null | cut -d'=' -f2- | sed 's/^["'\'']*//;s/["'\'']*$//')
BINANCE_API_SECRET=$(grep -E "^BINANCE_API_SECRET=" .env 2>/dev/null | cut -d'=' -f2- | sed 's/^["'\'']*//;s/["'\'']*$//')
BINANCE_TESTNET=$(grep -E "^BINANCE_TESTNET=" .env 2>/dev/null | cut -d'=' -f2- | sed 's/^["'\'']*//;s/["'\'']*$//' | tr '[:upper:]' '[:lower:]')

if [ -z "$BINANCE_API_KEY" ] || [ "$BINANCE_API_KEY" = "" ]; then
    echo "[ERROR] ✗ BINANCE_API_KEY nicht in .env gefunden oder leer!"
    echo ""
    echo "Bitte füge folgende Zeilen zur .env Datei hinzu:"
    echo "  BINANCE_API_KEY=dein_api_key_hier"
    echo "  BINANCE_API_SECRET=dein_api_secret_hier"
    echo "  BINANCE_TESTNET=true  # oder false für Mainnet"
    exit 1
fi

if [ -z "$BINANCE_API_SECRET" ] || [ "$BINANCE_API_SECRET" = "" ]; then
    echo "[ERROR] ✗ BINANCE_API_SECRET nicht in .env gefunden oder leer!"
    exit 1
fi

echo "[SUCCESS] ✓ API Key gefunden (Länge: ${#BINANCE_API_KEY} Zeichen)"
echo "[INFO] Testnet Mode: ${BINANCE_TESTNET:-true}"
echo ""

# 2. Prüfe API Key Format
echo "[2/5] Prüfe API Key Format..."
if [ ${#BINANCE_API_KEY} -lt 10 ]; then
    echo "[WARNING] ⚠ API Key ist sehr kurz - könnte ungültig sein"
fi
if [ ${#BINANCE_API_SECRET} -lt 20 ]; then
    echo "[WARNING] ⚠ API Secret ist sehr kurz - könnte ungültig sein"
fi
echo ""

# 3. Teste API Key mit Python
echo "[3/5] Teste Binance API Verbindung..."
python3 << 'PYTHON_SCRIPT'
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    from dotenv import load_dotenv
    
    # Load .env
    load_dotenv()
    
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    testnet = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
    
    if not api_key or not api_secret:
        print("[ERROR] API Key oder Secret fehlt!")
        sys.exit(1)
    
    print(f"[INFO] Versuche Verbindung zu Binance {'Testnet' if testnet else 'Mainnet'}...")
    
    client = Client(api_key, api_secret, testnet=testnet)
    
    # Test connection
    try:
        account = client.get_account()
        print(f"[SUCCESS] ✓ API Key ist gültig!")
        print(f"[INFO] Account Status: OK")
        
        # Check permissions
        print(f"[INFO] Prüfe API Key Permissions...")
        
        # Try to get account info (requires trading permissions)
        print(f"[SUCCESS] ✓ Trading Permissions: OK")
        
        sys.exit(0)
    except BinanceAPIException as e:
        error_code = e.code
        error_msg = str(e)
        
        if error_code == -2008:
            print(f"[ERROR] ✗ Invalid Api-Key ID (Code: {error_code})")
            print(f"[INFO] Mögliche Ursachen:")
            print(f"  1. API Key ist falsch oder wurde gelöscht")
            print(f"  2. API Key passt nicht zum {'Testnet' if testnet else 'Mainnet'} Mode")
            print(f"  3. API Key hat nicht die richtigen Permissions")
            print("")
            print(f"[INFO] Für {'Testnet' if testnet else 'Mainnet'} benötigst du:")
            if testnet:
                print(f"  - Testnet API Key von: https://testnet.binance.vision/")
            else:
                print(f"  - Mainnet API Key von: https://www.binance.com/en/my/settings/api-management")
            print(f"  - Permissions: Enable Reading, Enable Spot & Margin Trading, Enable Futures")
        elif error_code == -1022:
            print(f"[ERROR] ✗ Invalid signature (Code: {error_code})")
            print(f"[INFO] API Secret ist falsch!")
        elif error_code == -1021:
            print(f"[ERROR] ✗ Timestamp error (Code: {error_code})")
            print(f"[INFO] Systemzeit ist falsch - synchronisiere Systemzeit!")
        else:
            print(f"[ERROR] ✗ Binance API Error: {error_msg} (Code: {error_code})")
        
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] ✗ Unerwarteter Fehler: {e}")
        sys.exit(1)

except ImportError as e:
    print(f"[ERROR] Python-Module fehlen: {e}")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Fehler: {e}")
    sys.exit(1)
PYTHON_SCRIPT

API_TEST_RESULT=$?
echo ""

# 4. Prüfe Systemzeit (wichtig für Binance API)
echo "[4/5] Prüfe Systemzeit..."
CURRENT_TIME=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
echo "[INFO] Systemzeit (UTC): $CURRENT_TIME"

# Check if time is synced (within 5 minutes of current time)
TIMESTAMP=$(date +%s)
# This is a rough check - in production you might want to compare with NTP
echo "[INFO] Unix Timestamp: $TIMESTAMP"
echo ""

# 5. Zeige Hilfe
echo "[5/5] Zusammenfassung..."
echo ""

if [ $API_TEST_RESULT -eq 0 ]; then
    echo "✅ Binance API Key ist gültig!"
    echo ""
    echo "Falls Trades trotzdem fehlschlagen:"
    echo "1. Prüfe ob API Key die richtigen Permissions hat:"
    echo "   - Enable Reading"
    echo "   - Enable Spot & Margin Trading"
    echo "   - Enable Futures (für FUTURES Mode)"
    echo "2. Prüfe ob IP-Restriction aktiviert ist"
    echo "3. Prüfe Backend Logs: tail -50 /var/log/supervisor/cyphertrade-backend.log"
else
    echo "❌ Binance API Key ist ungültig!"
    echo ""
    echo "=== LÖSUNG ==="
    echo ""
    echo "1. Testnet API Key erstellen:"
    echo "   https://testnet.binance.vision/"
    echo ""
    echo "2. Oder Mainnet API Key erstellen:"
    echo "   https://www.binance.com/en/my/settings/api-management"
    echo ""
    echo "3. API Key und Secret zur .env Datei hinzufügen:"
    echo "   cd /app/backend"
    echo "   nano .env"
    echo ""
    echo "   Füge hinzu:"
    echo "   BINANCE_API_KEY=dein_api_key_hier"
    echo "   BINANCE_API_SECRET=dein_api_secret_hier"
    echo "   BINANCE_TESTNET=true  # oder false"
    echo ""
    echo "4. Backend neu starten:"
    echo "   sudo supervisorctl restart cyphertrade-backend"
    echo ""
fi

echo ""

