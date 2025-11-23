#!/bin/bash
# Frontend Spawn Error Fix - Prüft und behebt häufige Probleme

echo "=== Frontend Spawn Error Debug & Fix ==="
echo ""

cd /app || { echo "[ERROR] Kann nicht nach /app wechseln!"; exit 1; }

# 1. Frontend Logs prüfen
echo "[INFO] Frontend Error Logs (letzte 50 Zeilen):"
tail -50 /var/log/supervisor/cyphertrade-frontend-error.log 2>/dev/null || echo "[WARNING] Error-Log-Datei nicht gefunden"

echo ""
echo "[INFO] Frontend Logs (letzte 50 Zeilen):"
tail -50 /var/log/supervisor/cyphertrade-frontend.log 2>/dev/null || echo "[WARNING] Log-Datei nicht gefunden"

echo ""

# 2. Prüfe ob Port 3000 belegt ist
echo "[INFO] Prüfe Port 3000..."
if lsof -i :3000 > /dev/null 2>&1; then
    echo "[WARNING] Port 3000 ist belegt!"
    echo "[INFO] Prozesse auf Port 3000:"
    lsof -i :3000
    echo ""
    echo "[INFO] Beende Prozesse auf Port 3000..."
    sudo lsof -ti :3000 | xargs sudo kill -9 2>/dev/null
    sleep 2
fi

# 3. Prüfe Frontend-Verzeichnis
echo ""
echo "[INFO] Prüfe Frontend Verzeichnis:"
if [ ! -d "frontend" ]; then
    echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"
    exit 1
fi

cd frontend || { echo "[ERROR] Kann nicht nach frontend wechseln!"; exit 1; }

# 4. Prüfe .env Datei
echo "[INFO] Prüfe .env Datei:"
if [ -f ".env" ]; then
    echo "[SUCCESS] .env vorhanden:"
    cat .env
else
    echo "[WARNING] .env nicht gefunden"
fi

# 5. Prüfe node_modules
echo ""
echo "[INFO] Prüfe node_modules:"
if [ -d "node_modules" ]; then
    echo "[SUCCESS] node_modules vorhanden"
    module_count=$(find node_modules -maxdepth 1 -type d | wc -l)
    echo "Anzahl Module: $module_count"
else
    echo "[WARNING] node_modules nicht gefunden"
fi

# 6. Prüfe package.json
echo ""
echo "[INFO] Prüfe package.json:"
if [ -f "package.json" ]; then
    echo "[SUCCESS] package.json vorhanden"
else
    echo "[ERROR] package.json nicht gefunden!"
    exit 1
fi

# 7. Teste yarn direkt
echo ""
echo "[INFO] Teste yarn direkt:"
which yarn || echo "[WARNING] yarn nicht gefunden"

# 8. Versuche manuell zu starten (mit Timeout)
echo ""
echo "[INFO] Versuche Frontend manuell zu starten (10 Sekunden Test)..."
timeout 10 yarn start 2>&1 | head -30 || echo "[INFO] Timeout erreicht oder Fehler aufgetreten"

# 9. Prüfe Supervisor Config
echo ""
echo "[INFO] Prüfe Supervisor Config für Frontend:"
sudo supervisorctl status cyphertrade-frontend

echo ""
echo "=== Zusammenfassung ==="
echo "Wenn oben ein Fehler angezeigt wurde, ist das die Ursache."
echo ""
echo "Nächste Schritte:"
echo "1. Prüfe die Fehlermeldungen oben"
echo "2. Falls Port 3000 belegt war, wurde er freigegeben"
echo "3. Versuche Frontend manuell zu starten:"
echo "   cd /app/frontend && yarn start"
echo "4. Falls Probleme bestehen, prüfe die Logs:"
echo "   tail -100 /var/log/supervisor/cyphertrade-frontend-error.log"
