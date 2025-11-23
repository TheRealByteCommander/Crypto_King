#!/bin/bash
# Schneller Frontend Rebuild - Nur Build neu erstellen ohne alles andere

echo "=== Frontend Rebuild ==="
echo ""

cd /app/frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

# Stoppe Frontend
echo "[INFO] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true
sleep 2

# Lösche Build
echo "[INFO] Lösche alten Build..."
rm -rf build
echo "[SUCCESS] Alter Build gelöscht"
echo ""

# Neuer Build
echo "[INFO] Erstelle neuen Production Build..."
NODE_ENV=production yarn build

if [ $? -ne 0 ]; then
    echo "[ERROR] Build fehlgeschlagen!"
    exit 1
fi

echo "[SUCCESS] Build erstellt"
echo ""

# Starte Frontend
cd /app
echo "[INFO] Starte Frontend..."
sudo supervisorctl start cyphertrade-frontend

sleep 3

echo ""
echo "=== Fertig ==="
echo ""
echo "Frontend Status:"
sudo supervisorctl status cyphertrade-frontend
echo ""
echo "WICHTIG: Browser-Cache leeren (Strg + Shift + R)"

