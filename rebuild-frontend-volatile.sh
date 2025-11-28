#!/bin/bash

# Frontend Rebuild für Volatile Assets 24h Fix

echo "═══════════════════════════════════════════════════════════"
echo "Frontend Rebuild: Volatile Assets 24h Fix"
echo "═══════════════════════════════════════════════════════════"

cd /app/frontend || exit 1

echo "[1/5] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend

echo "[2/5] Lösche alten Build..."
rm -rf build

echo "[3/5] Installiere/Update Dependencies..."
yarn install

echo "[4/5] Erstelle neuen Production Build..."
echo "→ Dies kann 2-3 Minuten dauern..."
yarn run build

if [ ! -d "build" ]; then
    echo "❌ Build fehlgeschlagen!"
    exit 1
fi

echo "[5/5] Starte Frontend neu..."
sudo supervisorctl start cyphertrade-frontend

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ Frontend Rebuild abgeschlossen!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Frontend Status:"
sudo supervisorctl status cyphertrade-frontend

echo ""
echo "⚠️ WICHTIG: Browser-Cache leeren!"
echo "1. Browser komplett schließen"
echo "2. Browser neu öffnen"
echo "3. Strg + Shift + R (Hard Reload)"
echo "   ODER: F12 → Application Tab → Clear Storage → 'Clear site data'"
echo ""
echo "Erwartetes Ergebnis:"
echo "- 'Volatilste Assets (24 Stunden)' sollte angezeigt werden"
echo ""

