#!/bin/bash
# Prüfe ob Frontend im Production-Mode läuft

echo "=== Frontend Mode Check ==="
echo ""

# Prüfe Supervisor Config
echo "[INFO] Prüfe Supervisor Config..."
SUPERVISOR_CONFIG="/etc/supervisor/conf.d/cyphertrade-frontend.conf"
if [ -f "$SUPERVISOR_CONFIG" ]; then
    echo "[INFO] Supervisor Config gefunden:"
    cat "$SUPERVISOR_CONFIG" | grep -E "^command|^directory" || cat "$SUPERVISOR_CONFIG"
    echo ""
    
    # Prüfe ob serve verwendet wird
    if grep -q "serve" "$SUPERVISOR_CONFIG"; then
        echo "[SUCCESS] ✓ Frontend läuft mit 'serve' (Production Mode)"
    else
        echo "[WARNING] ⚠ Frontend läuft NICHT mit 'serve' - könnte Development Mode sein!"
    fi
else
    echo "[ERROR] Supervisor Config nicht gefunden: $SUPERVISOR_CONFIG"
fi

echo ""

# Prüfe laufende Prozesse
echo "[INFO] Prüfe laufende Frontend-Prozesse..."
ps aux | grep -E "yarn|node|serve|react" | grep -v grep | head -5
echo ""

# Prüfe ob Build existiert
echo "[INFO] Prüfe Build-Verzeichnis..."
if [ -d "/app/frontend/build" ]; then
    echo "[SUCCESS] Build-Verzeichnis existiert"
    BUILD_SIZE=$(du -sh /app/frontend/build 2>/dev/null | cut -f1)
    echo "[INFO] Build-Größe: $BUILD_SIZE"
    
    MAIN_JS=$(find /app/frontend/build/static/js -name "main.*.js" 2>/dev/null | head -1)
    if [ -n "$MAIN_JS" ]; then
        echo "[INFO] Main JS: $MAIN_JS"
        
        # Prüfe Trading Mode im Build
        if grep -q "tradingMode\|Trading Mode" "$MAIN_JS" 2>/dev/null; then
            echo "[SUCCESS] ✓ Trading Mode im Build gefunden"
        else
            echo "[ERROR] ✗ Trading Mode NICHT im Build gefunden!"
        fi
        
        # Prüfe Grid-Layout
        if grep -q "md:grid-cols-3\|md:grid-cols-2" "$MAIN_JS" 2>/dev/null; then
            echo "[SUCCESS] ✓ Neues Grid-Layout (3+2) im Build gefunden"
        elif grep -q "md:grid-cols-4" "$MAIN_JS" 2>/dev/null; then
            echo "[WARNING] ⚠ Altes Grid-Layout (4 Spalten) noch im Build!"
        fi
    else
        echo "[ERROR] Main JS Datei nicht gefunden!"
    fi
else
    echo "[ERROR] Build-Verzeichnis existiert nicht!"
fi

echo ""
echo "=== Zusammenfassung ==="
echo ""
echo "Wenn 'serve' nicht verwendet wird, läuft Frontend im Development Mode."
echo "In diesem Fall wird der Build nicht verwendet, sondern 'yarn start'."
echo ""

