#!/bin/bash
# Backend neu starten nach Code-Update

echo "=== Backend Neustart ==="
echo ""

cd /app || { echo "[ERROR] /app Verzeichnis nicht gefunden!"; exit 1; }

# 1. Hole neueste Änderungen
echo "[1/3] Hole neueste Änderungen..."
git pull

# 2. Stoppe Backend
echo ""
echo "[2/3] Stoppe Backend..."
sudo supervisorctl stop cyphertrade-backend

# 3. Starte Backend
echo ""
echo "[3/3] Starte Backend neu..."
sudo supervisorctl start cyphertrade-backend

# 4. Prüfe Status
echo ""
echo "=== Backend Status ==="
sleep 2
sudo supervisorctl status cyphertrade-backend

echo ""
echo "=== Wichtig ==="
echo "Laufende Bots müssen manuell neu gestartet werden, damit sie die neue Logik verwenden!"
echo "1. Im Frontend: Bot stoppen"
echo "2. Im Frontend: Bot mit gleichen Einstellungen neu starten"
echo ""
echo "Oder alle laufenden Bots stoppen und neu starten, wenn du sicherstellen willst, dass alle die neue Logik verwenden."

