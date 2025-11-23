#!/bin/bash
# Vollständiges Update-Skript - Aktualisiert Backend und Frontend

echo "=== CryptoKing Server Update ==="
echo ""

# 1. Zum App-Verzeichnis wechseln
cd /app || { echo "[ERROR] Kann nicht nach /app wechseln!"; exit 1; }

# 2. Git Pull (neueste Änderungen holen)
echo "[INFO] Hole neueste Änderungen von GitHub..."
git pull

if [ $? -ne 0 ]; then
    echo "[ERROR] Git pull fehlgeschlagen! Bitte manuell prüfen."
    exit 1
fi

echo ""
echo "[INFO] Änderungen erfolgreich geholt."
echo ""

# 3. Backend neu starten
echo "[INFO] Starte Backend neu..."
sudo supervisorctl restart cyphertrade-backend

# 4. Kurz warten
sleep 2

# 5. Frontend neu starten
echo "[INFO] Starte Frontend neu..."
sudo supervisorctl restart cyphertrade-frontend

# 6. Status prüfen
echo ""
echo "[INFO] Warte 5 Sekunden auf Start..."
sleep 5

echo ""
echo "[INFO] Service-Status:"
echo ""
echo "=== Backend Status ==="
sudo supervisorctl status cyphertrade-backend

echo ""
echo "=== Frontend Status ==="
sudo supervisorctl status cyphertrade-frontend

echo ""
echo "=== Fertig ==="
echo ""
echo "✅ Update abgeschlossen!"
echo ""
echo "Wenn beide Services 'RUNNING' anzeigen, ist alles in Ordnung."
echo "Falls ein Service 'FATAL' oder 'ERROR' zeigt, prüfe die Logs:"
echo "  - Backend:  tail -50 /var/log/supervisor/cyphertrade-backend.log"
echo "  - Frontend: tail -50 /var/log/supervisor/cyphertrade-frontend.log"
echo ""
echo "Das Frontend sollte sich automatisch aktualisieren."
echo "Falls nicht, bitte die Seite im Browser neu laden (Strg+F5)."

