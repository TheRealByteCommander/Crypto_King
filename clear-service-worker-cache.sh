#!/bin/bash
# Service Worker Cache löschen - Frontend mit Cache-Busting neu bauen

echo "=== Service Worker Cache löschen ==="
echo ""

cd /app/frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

# 1. Stoppe Frontend
echo "[INFO] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true
sleep 2

# 2. Lösche Service Worker Dateien im Build
echo "[INFO] Lösche Service Worker Dateien..."
rm -f build/service-worker.js
rm -f build/workbox-*.js
rm -f build/precache-manifest.*.js
echo "[SUCCESS] Service Worker Dateien gelöscht"

# 3. Lösche Build komplett
echo "[INFO] Lösche Build komplett..."
rm -rf build
echo "[SUCCESS] Build gelöscht"

# 4. Ändere Build-Hash (Cache-Busting)
echo "[INFO] Erstelle neuen Build mit Cache-Busting..."
NODE_ENV=production GENERATE_SOURCEMAP=false yarn build

if [ $? -ne 0 ]; then
    echo "[ERROR] Build fehlgeschlagen!"
    exit 1
fi

# 5. Füge Cache-Busting Header zu index.html hinzu
echo "[INFO] Füge Cache-Busting Header hinzu..."
sed -i 's|<head>|<head>\n  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">\n  <meta http-equiv="Pragma" content="no-cache">\n  <meta http-equiv="Expires" content="0">|' build/index.html

# 6. Starte Frontend
cd /app
echo "[INFO] Starte Frontend..."
sudo supervisorctl start cyphertrade-frontend

sleep 3

echo ""
echo "=== Fertig ==="
echo ""
echo "Service Worker Cache wurde gelöscht."
echo ""
echo "Im Browser:"
echo "1. F12 → Application Tab → Service Workers"
echo "2. Klicke auf 'Unregister' bei allen Service Workers"
echo "3. F12 → Application Tab → Clear Storage"
echo "4. 'Clear site data' klicken"
echo "5. Browser komplett schließen"
echo "6. Browser neu öffnen"
echo "7. Strg + Shift + R (Hard Reload)"
echo ""

