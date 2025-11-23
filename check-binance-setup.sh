#!/bin/bash
# Prüft Binance Setup und gibt Anweisungen

echo "=== Binance Setup Check ==="
echo ""

cd /app/backend || { echo "[ERROR] Backend-Verzeichnis nicht gefunden!"; exit 1; }

# 1. Prüfe .env
echo "[INFO] Prüfe .env Datei..."
if [ ! -f ".env" ]; then
    echo "[ERROR] .env Datei nicht gefunden!"
    exit 1
fi

# Zeige API Key Info (ohne vollständigen Key zu zeigen)
BINANCE_API_KEY=$(grep -E "^BINANCE_API_KEY=" .env 2>/dev/null | cut -d'=' -f2- | sed 's/^["'\'']*//;s/["'\'']*$//')
BINANCE_TESTNET=$(grep -E "^BINANCE_TESTNET=" .env 2>/dev/null | cut -d'=' -f2- | sed 's/^["'\'']*//;s/["'\'']*$//' | tr '[:upper:]' '[:lower:]')

if [ -z "$BINANCE_API_KEY" ]; then
    echo "[ERROR] BINANCE_API_KEY nicht in .env gefunden!"
    echo ""
    echo "Bitte füge hinzu:"
    echo "  BINANCE_API_KEY=dein_key"
    echo "  BINANCE_API_SECRET=dein_secret"
    exit 1
fi

# Zeige nur ersten und letzten Teil des Keys (Sicherheit)
KEY_PREVIEW="${BINANCE_API_KEY:0:8}...${BINANCE_API_KEY: -4}"
echo "[INFO] API Key gefunden: $KEY_PREVIEW"
echo "[INFO] Testnet Mode: ${BINANCE_TESTNET:-true}"
echo ""

# 2. Wichtige Info für Binance Testnet
echo "=== WICHTIG: Binance Testnet Limitations ==="
echo ""
echo "⚠️  Binance Testnet unterstützt NUR Spot Trading!"
echo ""
echo "Das bedeutet:"
echo "  ✅ SPOT Mode: Funktioniert"
echo "  ❌ MARGIN Mode: FUNKTIONIERT NICHT auf Testnet"
echo "  ❌ FUTURES Mode: FUNKTIONIERT NICHT auf Testnet"
echo ""
echo "Für MARGIN/FUTURES Trading benötigst du:"
echo "  1. Einen Binance MAINNET Account"
echo "  2. Einen MAINNET API Key mit erweiterten Permissions"
echo "  3. BINANCE_TESTNET=false in .env"
echo ""

# 3. Prüfe welche Bots laufen
echo "=== Aktuell laufende Bots ==="
echo ""
echo "Prüfe welche Trading Modes verwendet werden..."
echo ""
echo "Tipp: Prüfe im Dashboard welche Bots laufen und welche Trading Mode sie verwenden"
echo ""

# 4. API Key Update Anleitung
echo "=== API Key zur .env hinzufügen ==="
echo ""
echo "1. Kopiere den API Key von Binance Testnet:"
echo "   - Gehe zur API Management Seite"
echo "   - Klicke auf deinen API Key"
echo "   - Kopiere 'API Key' und 'Secret Key'"
echo ""
echo "2. Füge zur .env Datei hinzu:"
echo ""
echo "   cd /app/backend"
echo "   nano .env"
echo ""
echo "   Füge hinzu/aktualisiere:"
echo "   BINANCE_API_KEY=dein_api_key_hier"
echo "   BINANCE_API_SECRET=dein_secret_key_hier"
echo "   BINANCE_TESTNET=true"
echo ""
echo "3. Backend neu starten:"
echo "   sudo supervisorctl restart cyphertrade-backend"
echo ""
echo "4. Prüfe ob es funktioniert:"
echo "   tail -20 /var/log/supervisor/cyphertrade-backend.log"
echo ""

