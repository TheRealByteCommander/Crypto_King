#!/bin/bash
# Force Complete Rebuild - Löscht ALLES und baut komplett neu

echo "=== Force Complete Rebuild ==="
echo ""
echo "⚠️  WARNUNG: Dies löscht den kompletten Build und Cache!"
echo ""

cd /app/frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

# 1. Stoppe Frontend
echo "[INFO] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true
sleep 2

# 2. Lösche Build komplett
echo "[INFO] Lösche Build..."
rm -rf build
echo "[SUCCESS] Build gelöscht"

# 3. Lösche node_modules/.cache
echo "[INFO] Lösche Build-Cache..."
rm -rf node_modules/.cache
rm -rf .cache
echo "[SUCCESS] Cache gelöscht"

# 4. Lösche yarn cache (optional, aber sicher)
echo "[INFO] Lösche Yarn Cache..."
yarn cache clean 2>/dev/null || true
echo "[SUCCESS] Yarn Cache geleert"

# 5. Prüfe Code-Version
echo ""
echo "[INFO] Prüfe Code-Version..."
if grep -q "grid-cols-1 md:grid-cols-3" src/components/BotControl.js 2>/dev/null; then
    echo "[SUCCESS] ✓ Neuer Code gefunden (3+2 Layout)"
else
    echo "[ERROR] ✗ Alter Code noch vorhanden!"
    echo "[INFO] Prüfe BotControl.js manuell..."
    exit 1
fi

if grep -q "Trading Mode.*SPOT/MARGIN/FUTURES" src/components/BotControl.js 2>/dev/null; then
    echo "[SUCCESS] ✓ Trading Mode Label gefunden"
else
    echo "[ERROR] ✗ Trading Mode Label nicht gefunden!"
    exit 1
fi

# 6. Neuer Build
echo ""
echo "[INFO] Erstelle neuen Production Build..."
echo "[INFO] Dies kann 2-3 Minuten dauern..."
NODE_ENV=production yarn build

if [ $? -ne 0 ]; then
    echo "[ERROR] Build fehlgeschlagen!"
    exit 1
fi

# 7. Prüfe ob Trading Mode im Build ist
echo ""
echo "[INFO] Prüfe Trading Mode im Build..."
MAIN_JS=$(find build/static/js -name "main.*.js" | head -1)
if [ -z "$MAIN_JS" ]; then
    echo "[ERROR] Haupt-JS-Datei nicht gefunden!"
    exit 1
fi

if grep -q "tradingMode\|Trading Mode" "$MAIN_JS" 2>/dev/null; then
    echo "[SUCCESS] ✓ Trading Mode im Build gefunden"
else
    echo "[ERROR] ✗ Trading Mode NICHT im Build gefunden!"
    echo "[INFO] Build-Datei: $MAIN_JS"
    exit 1
fi

# Prüfe Grid-Layout im Build
if grep -q "grid-cols-1.*md:grid-cols-3\|grid-cols-1.*md:grid-cols-2" "$MAIN_JS" 2>/dev/null; then
    echo "[SUCCESS] ✓ Neues Grid-Layout im Build gefunden"
else
    echo "[WARNING] ⚠ Grid-Layout könnte noch alt sein"
fi

# 8. Starte Frontend
cd /app
echo ""
echo "[INFO] Starte Frontend..."
sudo supervisorctl start cyphertrade-frontend

sleep 3

echo ""
echo "=== Fertig ==="
echo ""
echo "Frontend Status:"
sudo supervisorctl status cyphertrade-frontend
echo ""
echo "=== WICHTIG ==="
echo ""
echo "1. Browser komplett schließen"
echo "2. Browser neu öffnen"
echo "3. Strg + Shift + R (Hard Reload)"
echo "4. Prüfe ob Grid jetzt 2 Zeilen hat (3 Spalten + 2 Spalten)"
echo ""

