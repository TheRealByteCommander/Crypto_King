#!/bin/bash
# Frontend Update Check - Prüft ob Frontend aktualisiert wurde

echo "=== Frontend Update Check ==="
echo ""

cd /app || { echo "[ERROR] Kann nicht nach /app wechseln!"; exit 1; }

# 1. Prüfe Git Status
echo "[INFO] Prüfe Git Status..."
LATEST_COMMIT=$(git log -1 --oneline)
echo "Neuester Commit: $LATEST_COMMIT"
echo ""

# 2. Prüfe ob Trading Mode im Frontend Code ist
echo "[INFO] Prüfe Frontend Code auf Trading Mode..."
cd frontend/src/components || { echo "[ERROR] Frontend components nicht gefunden!"; exit 1; }

if grep -q "tradingMode\|Trading Mode" BotControl.js 2>/dev/null; then
    echo "[SUCCESS] Trading Mode Code gefunden im Frontend"
    grep -n "tradingMode\|Trading Mode" BotControl.js | head -5
else
    echo "[ERROR] Trading Mode Code NICHT gefunden im Frontend!"
    echo "[INFO] Frontend muss aktualisiert werden"
fi
echo ""

# 3. Prüfe Frontend Build Status
echo "[INFO] Prüfe Frontend Build Status..."
cd /app/frontend

if [ -d "build" ]; then
    BUILD_DATE=$(stat -c %y build/index.html 2>/dev/null || stat -f %Sm build/index.html 2>/dev/null || echo "Unbekannt")
    echo "[INFO] Production Build vorhanden"
    echo "Build-Datum: $BUILD_DATE"
    
    # Prüfe ob Trading Mode im Build ist
    if grep -q "tradingMode\|Trading Mode" build/static/js/*.js 2>/dev/null; then
        echo "[SUCCESS] Trading Mode im Production Build gefunden"
    else
        echo "[WARNING] Trading Mode NICHT im Production Build gefunden"
        echo "[INFO] Production Build muss neu erstellt werden"
    fi
else
    echo "[INFO] Kein Production Build vorhanden - läuft im Development Modus"
fi
echo ""

# 4. Prüfe Supervisor Status
echo "[INFO] Prüfe Frontend Status..."
FRONTEND_STATUS=$(sudo supervisorctl status cyphertrade-frontend 2>/dev/null | grep -o "RUNNING\|STOPPED\|FATAL\|ERROR" || echo "UNBEKANNT")
echo "Frontend Status: $FRONTEND_STATUS"
echo ""

# 5. Prüfe Frontend Logs
echo "[INFO] Letzte Frontend Log-Zeilen:"
tail -10 /var/log/supervisor/cyphertrade-frontend.log 2>/dev/null || echo "[WARNING] Log-Datei nicht gefunden"
echo ""

# 6. Zusammenfassung
echo "=== Zusammenfassung ==="
echo ""
if grep -q "tradingMode" /app/frontend/src/components/BotControl.js 2>/dev/null; then
    echo "✅ Trading Mode Code im Frontend vorhanden"
else
    echo "❌ Trading Mode Code im Frontend FEHLT"
    echo "   → Git Pull ausführen: cd /app && git pull"
fi

if [ -d "/app/frontend/build" ]; then
    echo "✅ Production Build vorhanden"
    echo "   → Falls Trading Mode fehlt: sudo bash /app/setup-production-build.sh"
else
    echo "ℹ️  Frontend läuft im Development Modus"
    echo "   → Für Production: sudo bash /app/setup-production-build.sh"
fi

echo ""
echo "=== Nächste Schritte ==="
echo ""
echo "1. Frontend Code aktualisieren:"
echo "   cd /app && git pull"
echo ""
echo "2. Production Build erstellen:"
echo "   sudo bash /app/setup-production-build.sh"
echo ""
echo "3. Browser-Cache leeren:"
echo "   Strg + Shift + R im Browser"

