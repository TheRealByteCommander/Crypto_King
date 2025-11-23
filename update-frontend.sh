#!/bin/bash
# Frontend-Update Script - Holt neueste Änderungen und startet Frontend neu

echo "=== Frontend Update ==="
echo ""

# 1. Zum App-Verzeichnis wechseln
cd /app || { echo "[ERROR] Kann nicht nach /app wechseln!"; exit 1; }

# 2. Git Pull (neueste Änderungen holen)
echo "[INFO] Hole neueste Änderungen von GitHub..."
git pull

# 3. Frontend neu starten
echo "[INFO] Starte Frontend neu..."
sudo supervisorctl restart cyphertrade-frontend

# 4. Status prüfen
echo ""
echo "[INFO] Frontend Status:"
sleep 3
sudo supervisorctl status cyphertrade-frontend

echo ""
echo "=== Fertig ==="
echo "Das Frontend sollte sich automatisch aktualisieren."
echo "Falls nicht, bitte die Seite im Browser neu laden (Strg+F5)."

