#!/bin/bash
# Prüfe welche Dateien tatsächlich vom Server ausgeliefert werden

echo "=== Prüfe ausgelieferte Dateien ==="
echo ""

cd /app/frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

# 1. Prüfe Build-Verzeichnis
echo "[INFO] Prüfe Build-Verzeichnis..."
if [ ! -d "build" ]; then
    echo "[ERROR] Build-Verzeichnis nicht gefunden!"
    exit 1
fi

echo "[SUCCESS] Build-Verzeichnis existiert"
BUILD_SIZE=$(du -sh build | cut -f1)
echo "[INFO] Build-Größe: $BUILD_SIZE"
echo ""

# 2. Finde main.js im Build
MAIN_JS=$(find build/static/js -name "main.*.js" | head -1)
if [ -z "$MAIN_JS" ]; then
    echo "[ERROR] Main JS-Datei nicht gefunden!"
    exit 1
fi

echo "[INFO] Main JS-Datei: $MAIN_JS"
JS_SIZE=$(ls -lh "$MAIN_JS" | awk '{print $5}')
echo "[INFO] JS-Dateigröße: $JS_SIZE"
echo ""

# 3. Prüfe Trading Mode im Build
echo "[INFO] Prüfe Trading Mode im Build..."
if grep -q "tradingMode\|Trading Mode" "$MAIN_JS" 2>/dev/null; then
    echo "[SUCCESS] ✓ Trading Mode im Build gefunden"
    
    # Prüfe Grid-Layout
    if grep -q "md:grid-cols-3" "$MAIN_JS" 2>/dev/null; then
        echo "[SUCCESS] ✓ Neues Grid-Layout (3+2) im Build gefunden"
    else
        echo "[WARNING] ⚠ Altes Grid-Layout noch im Build"
    fi
else
    echo "[ERROR] ✗ Trading Mode NICHT im Build gefunden!"
fi
echo ""

# 4. Prüfe welcher Port verwendet wird
echo "[INFO] Prüfe Frontend-Port..."
FRONTEND_PORT=$(sudo netstat -tlnp 2>/dev/null | grep -E "3000|serve" | head -1 | awk '{print $4}' | cut -d: -f2)
if [ -z "$FRONTEND_PORT" ]; then
    echo "[WARNING] Port nicht gefunden, versuche Supervisor Config..."
    FRONTEND_PORT="3000"
fi

echo "[INFO] Frontend läuft auf Port: $FRONTEND_PORT"
echo ""

# 5. Prüfe welche Datei tatsächlich ausgeliefert wird
echo "[INFO] Teste HTTP-Request..."
MAIN_JS_NAME=$(basename "$MAIN_JS")
MAIN_JS_PATH="/static/js/$MAIN_JS_NAME"

echo "[INFO] Versuche Datei zu laden: http://localhost:$FRONTEND_PORT$MAIN_JS_PATH"
echo ""

# Versuche Datei zu laden
HTTP_RESPONSE=$(curl -s -o /tmp/test_main.js -w "%{http_code}" "http://localhost:$FRONTEND_PORT$MAIN_JS_PATH" 2>/dev/null)

if [ "$HTTP_RESPONSE" = "200" ]; then
    echo "[SUCCESS] ✓ Datei erfolgreich geladen (HTTP $HTTP_RESPONSE)"
    SERVED_SIZE=$(ls -lh /tmp/test_main.js | awk '{print $5}')
    echo "[INFO] Geladene Dateigröße: $SERVED_SIZE"
    
    # Vergleiche Dateien
    if cmp -s "$MAIN_JS" /tmp/test_main.js 2>/dev/null; then
        echo "[SUCCESS] ✓ Servierte Datei ist identisch mit Build-Datei"
    else
        echo "[ERROR] ✗ Servierte Datei unterscheidet sich von Build-Datei!"
        echo "[INFO] Prüfe Trading Mode in servierter Datei..."
        if grep -q "tradingMode\|Trading Mode" /tmp/test_main.js 2>/dev/null; then
            echo "[SUCCESS] ✓ Trading Mode in servierter Datei gefunden"
        else
            echo "[ERROR] ✗ Trading Mode NICHT in servierter Datei!"
            echo "[INFO] Serviere Datei könnte alt sein oder gecached werden"
        fi
    fi
    
    # Prüfe Grid-Layout in servierter Datei
    if grep -q "md:grid-cols-3" /tmp/test_main.js 2>/dev/null; then
        echo "[SUCCESS] ✓ Neues Grid-Layout in servierter Datei gefunden"
    elif grep -q "md:grid-cols-4" /tmp/test_main.js 2>/dev/null; then
        echo "[ERROR] ✗ ALTES Grid-Layout (4 Spalten) in servierter Datei!"
        echo "[INFO] Das erklärt warum Trading Mode nicht sichtbar ist!"
    fi
else
    echo "[ERROR] ✗ Datei konnte nicht geladen werden (HTTP $HTTP_RESPONSE)"
    echo "[INFO] Prüfe ob Frontend läuft..."
    sudo supervisorctl status cyphertrade-frontend
fi

echo ""

# 6. Prüfe Serve-Prozess
echo "[INFO] Prüfe Serve-Prozess..."
SERVE_PID=$(ps aux | grep -E "[s]erve.*build" | awk '{print $2}' | head -1)
if [ -n "$SERVE_PID" ]; then
    echo "[INFO] Serve-Prozess gefunden (PID: $SERVE_PID)"
    SERVE_CMD=$(ps -p $SERVE_PID -o cmd= 2>/dev/null)
    echo "[INFO] Serve-Befehl: $SERVE_CMD"
    
    # Prüfe ob serve das richtige Verzeichnis serviert
    if echo "$SERVE_CMD" | grep -q "/app/frontend/build"; then
        echo "[SUCCESS] ✓ Serve serviert das richtige Verzeichnis"
    else
        echo "[ERROR] ✗ Serve serviert möglicherweise das falsche Verzeichnis!"
    fi
else
    echo "[WARNING] Serve-Prozess nicht gefunden"
fi

echo ""

# 7. Prüfe Supervisor Config
echo "[INFO] Prüfe Supervisor Config..."
SUPERVISOR_CONFIG="/etc/supervisor/conf.d/cyphertrade-frontend.conf"
if [ -f "$SUPERVISOR_CONFIG" ]; then
    echo "[INFO] Supervisor Config:"
    cat "$SUPERVISOR_CONFIG" | grep -E "^command|^directory" || cat "$SUPERVISOR_CONFIG"
    echo ""
fi

# Cleanup
rm -f /tmp/test_main.js

echo "=== Zusammenfassung ==="
echo ""
echo "Falls servierte Datei alt ist:"
echo "1. Frontend neu starten: sudo supervisorctl restart cyphertrade-frontend"
echo "2. Serve-Prozess killen und neu starten"
echo "3. Prüfe ob serve das richtige Verzeichnis serviert"
echo ""

