#!/bin/bash
# CT-Server Update Script - Aktualisiert Backend und Frontend auf dem CryptoKing Server

echo "=== CryptoKing Server Update ==="
echo ""

cd /app || { echo "[ERROR] Kann nicht nach /app wechseln!"; exit 1; }

# 1. Git Pull - Hole neueste Änderungen
echo "[INFO] Hole neueste Änderungen von GitHub..."
git stash 2>/dev/null || true  # Stashe lokale Änderungen falls vorhanden
git pull origin main

if [ $? -ne 0 ]; then
    echo "[ERROR] Git pull fehlgeschlagen!"
    exit 1
fi

echo "[SUCCESS] Neueste Änderungen geladen"
echo ""

# 2. Backend Update
echo "[INFO] Aktualisiere Backend..."
cd backend || { echo "[ERROR] Backend-Verzeichnis nicht gefunden!"; exit 1; }

# Prüfe ob venv existiert und aktiviere es
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "[INFO] Virtual Environment aktiviert"
fi

# Installiere/Update Dependencies falls requirements.txt geändert wurde
if [ -f "requirements.txt" ]; then
    echo "[INFO] Installiere/Update Python Dependencies..."
    pip install -q -r requirements.txt --upgrade 2>/dev/null || pip install -r requirements.txt --upgrade
fi

cd /app
echo "[SUCCESS] Backend aktualisiert"
echo ""

# 3. Frontend Update
echo "[INFO] Aktualisiere Frontend..."
cd frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

# Installiere/Update Dependencies falls package.json geändert wurde
if [ -f "package.json" ]; then
    echo "[INFO] Installiere/Update Node Dependencies..."
    yarn install --silent 2>/dev/null || yarn install
fi

cd /app
echo "[SUCCESS] Frontend aktualisiert"
echo ""

# 4. Backend neu starten
echo "[INFO] Starte Backend neu..."
sudo supervisorctl restart cyphertrade-backend

# Warte kurz
sleep 2

# Prüfe Backend Status
BACKEND_STATUS=$(sudo supervisorctl status cyphertrade-backend | grep -o "RUNNING\|STOPPED\|FATAL\|ERROR")
if [ "$BACKEND_STATUS" = "RUNNING" ]; then
    echo "[SUCCESS] Backend läuft"
else
    echo "[WARNING] Backend Status: $BACKEND_STATUS"
    echo "[INFO] Prüfe Logs: tail -50 /var/log/supervisor/cyphertrade-backend-error.log"
fi
echo ""

# 5. Frontend neu starten
echo "[INFO] Starte Frontend neu..."
sudo supervisorctl restart cyphertrade-frontend

# Warte kurz
sleep 2

# Prüfe Frontend Status
FRONTEND_STATUS=$(sudo supervisorctl status cyphertrade-frontend | grep -o "RUNNING\|STOPPED\|FATAL\|ERROR")
if [ "$FRONTEND_STATUS" = "RUNNING" ]; then
    echo "[SUCCESS] Frontend läuft"
else
    echo "[WARNING] Frontend Status: $FRONTEND_STATUS"
    echo "[INFO] Prüfe Logs: tail -50 /var/log/supervisor/cyphertrade-frontend-error.log"
fi
echo ""

# 6. Zusammenfassung
echo "=== Update abgeschlossen ==="
echo ""
echo "Backend Status: $BACKEND_STATUS"
echo "Frontend Status: $FRONTEND_STATUS"
echo ""
echo "Logs prüfen:"
echo "  Backend:  tail -f /var/log/supervisor/cyphertrade-backend.log"
echo "  Frontend: tail -f /var/log/supervisor/cyphertrade-frontend.log"
echo ""
echo "Bei Problemen:"
echo "  Backend Logs:  tail -50 /var/log/supervisor/cyphertrade-backend-error.log"
echo "  Frontend Logs: tail -50 /var/log/supervisor/cyphertrade-frontend-error.log"
echo ""

