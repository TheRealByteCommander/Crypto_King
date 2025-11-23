#!/bin/bash
# Backend-Only Update - Schnelles Update nur für Backend

echo "=== Backend Update ==="
echo ""

cd /app || { echo "[ERROR] Kann nicht nach /app wechseln!"; exit 1; }

# 1. Git Pull
echo "[INFO] Hole neueste Änderungen von GitHub..."
git pull

if [ $? -ne 0 ]; then
    echo "[ERROR] Git pull fehlgeschlagen! Bitte manuell prüfen."
    exit 1
fi

# 2. Zeige letzten Commit
echo ""
echo "[INFO] Neuester Commit:"
git log -1 --oneline

# 3. Backend neu starten
echo ""
echo "[INFO] Starte Backend neu..."
sudo supervisorctl restart cyphertrade-backend

# 4. Warte und prüfe Status
echo ""
echo "[INFO] Warte 3 Sekunden auf Start..."
sleep 3

echo ""
echo "[INFO] Backend Status:"
sudo supervisorctl status cyphertrade-backend

echo ""
echo "=== Fertig ==="
echo "Backend sollte jetzt mit den neuesten Änderungen laufen."

