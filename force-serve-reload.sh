#!/bin/bash
# Force Serve Reload - Tötet alle Serve-Prozesse und startet neu

echo "=== Force Serve Reload ==="
echo ""

cd /app || { echo "[ERROR] Kann nicht nach /app wechseln!"; exit 1; }

# 1. Stoppe Frontend
echo "[INFO] Stoppe Frontend..."
sudo supervisorctl stop cyphertrade-frontend 2>/dev/null || true

# 2. Töte ALLE Serve-Prozesse
echo "[INFO] Töte alle Serve-Prozesse..."
pkill -f "serve.*build" 2>/dev/null || true
pkill -f "serve -s" 2>/dev/null || true
pkill serve 2>/dev/null || true
sleep 3
echo "[SUCCESS] Alle Serve-Prozesse beendet"
echo ""

# 3. Prüfe ob Port 3000 frei ist
echo "[INFO] Prüfe Port 3000..."
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "[WARNING] Port 3000 ist noch belegt!"
    echo "[INFO] Töte Prozesse auf Port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# 4. Prüfe Build
cd frontend
if [ ! -d "build" ] || [ ! -f "build/index.html" ]; then
    echo "[ERROR] Build-Verzeichnis nicht gefunden oder leer!"
    exit 1
fi

MAIN_JS=$(find build/static/js -name "main.*.js" | head -1)
if [ -z "$MAIN_JS" ]; then
    echo "[ERROR] Main JS-Datei nicht gefunden!"
    exit 1
fi

# Prüfe Trading Mode im Build
if ! grep -q "tradingMode\|Trading Mode" "$MAIN_JS" 2>/dev/null; then
    echo "[ERROR] Trading Mode NICHT im Build gefunden!"
    echo "[INFO] Build muss neu erstellt werden"
    exit 1
fi

echo "[SUCCESS] Build ist korrekt (Trading Mode vorhanden)"
echo ""

# 5. Starte Frontend neu
cd /app
echo "[INFO] Starte Frontend neu..."
sudo supervisorctl start cyphertrade-frontend

sleep 5

# 6. Prüfe ob Serve läuft
SERVE_PID=$(ps aux | grep -E "[s]erve.*build" | awk '{print $2}' | head -1)
if [ -n "$SERVE_PID" ]; then
    echo "[SUCCESS] ✓ Serve-Prozess läuft (PID: $SERVE_PID)"
    SERVE_CMD=$(ps -p $SERVE_PID -o cmd= 2>/dev/null)
    echo "[INFO] Serve-Befehl: $SERVE_CMD"
    
    # Teste ob Datei erreichbar ist
    sleep 2
    MAIN_JS_NAME=$(basename "$MAIN_JS")
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:3000/static/js/$MAIN_JS_NAME" 2>/dev/null)
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "[SUCCESS] ✓ Frontend antwortet (HTTP $HTTP_CODE)"
    else
        echo "[WARNING] Frontend antwortet nicht korrekt (HTTP $HTTP_CODE)"
    fi
else
    echo "[ERROR] ✗ Serve-Prozess läuft nicht!"
    echo "[INFO] Prüfe Logs: tail -50 /var/log/supervisor/cyphertrade-frontend.log"
fi

echo ""
echo "=== Fertig ==="
echo ""
echo "Frontend Status:"
sudo supervisorctl status cyphertrade-frontend
echo ""

