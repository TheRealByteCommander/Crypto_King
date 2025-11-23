#!/bin/bash
# Schneller Frontend-Fix - Behebt spawn errors

echo "=== Frontend Quick Fix ==="
echo ""

cd /app || { echo "[ERROR] Kann nicht nach /app wechseln!"; exit 1; }

# 1. Stoppe Frontend
echo "[INFO] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true

# 2. Töte alle Prozesse auf Port 3000
echo "[INFO] Prüfe Port 3000..."
if lsof -i :3000 > /dev/null 2>&1; then
    echo "[INFO] Beende Prozesse auf Port 3000..."
    sudo lsof -ti :3000 | xargs sudo kill -9 2>/dev/null || true
    sleep 2
fi

# 3. Prüfe Frontend-Verzeichnis
cd frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

# 4. Starte Frontend manuell um Fehler zu sehen
echo "[INFO] Versuche Frontend zu starten (10 Sekunden Test)..."
timeout 10 yarn start 2>&1 | head -30 || echo "[INFO] Timeout erreicht"

echo ""
echo "[INFO] Starte Frontend über Supervisor..."
cd /app
sudo supervisorctl start cyphertrade-frontend

sleep 3

echo ""
echo "[INFO] Frontend Status:"
sudo supervisorctl status cyphertrade-frontend

echo ""
echo "=== Fertig ==="
echo "Falls Frontend noch nicht läuft, prüfe die Logs:"
echo "  tail -50 /var/log/supervisor/cyphertrade-frontend-error.log"

