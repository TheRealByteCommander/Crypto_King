#!/bin/bash
# Test Script - Prüft ob Trading Mode wirklich im Build ist

echo "=== Trading Mode Build Test ==="
echo ""

cd /app/frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

# 1. Prüfe ob Build existiert
if [ ! -d "build" ]; then
    echo "[ERROR] Build-Verzeichnis nicht gefunden!"
    exit 1
fi

echo "[INFO] Prüfe Production Build..."
echo ""

# 2. Prüfe index.html
echo "[INFO] Prüfe index.html..."
if grep -q "Trading Mode\|tradingMode" build/index.html 2>/dev/null; then
    echo "[SUCCESS] Trading Mode in index.html gefunden"
else
    echo "[INFO] Trading Mode nicht in index.html (normal, da React app)"
fi
echo ""

# 3. Prüfe JavaScript Bundle
echo "[INFO] Prüfe JavaScript Bundles..."
JS_FILES=$(find build/static/js -name "*.js" 2>/dev/null)
if [ -z "$JS_FILES" ]; then
    echo "[ERROR] Keine JavaScript-Dateien gefunden!"
    exit 1
fi

FOUND_IN_BUILD=false
for js_file in $JS_FILES; do
    if grep -q "tradingMode\|Trading Mode\|trading-mode" "$js_file" 2>/dev/null; then
        echo "[SUCCESS] Trading Mode in $js_file gefunden"
        FOUND_IN_BUILD=true
        
        # Zeige Kontext
        echo "[INFO] Kontext:"
        grep -n "tradingMode\|Trading Mode\|trading-mode" "$js_file" 2>/dev/null | head -3
        echo ""
        break
    fi
done

if [ "$FOUND_IN_BUILD" = false ]; then
    echo "[ERROR] Trading Mode NICHT in JavaScript-Bundles gefunden!"
    echo "[INFO] Möglicherweise wurde die Komponente nicht richtig gebaut"
    echo ""
    echo "Größte JS-Datei:"
    ls -lh build/static/js/*.js | sort -k5 -rh | head -1
    exit 1
fi

# 4. Prüfe CSS (falls vorhanden)
echo "[INFO] Prüfe CSS..."
CSS_FILES=$(find build/static/css -name "*.css" 2>/dev/null)
if [ -n "$CSS_FILES" ]; then
    for css_file in $CSS_FILES; do
        if grep -q "tradingMode\|trading-mode" "$css_file" 2>/dev/null; then
            echo "[INFO] Trading Mode in CSS gefunden: $css_file"
        fi
    done
fi
echo ""

# 5. Prüfe Source Maps (falls vorhanden)
echo "[INFO] Prüfe Source Maps..."
MAP_FILES=$(find build/static/js -name "*.map" 2>/dev/null)
if [ -n "$MAP_FILES" ]; then
    for map_file in $MAP_FILES; do
        if grep -q "tradingMode\|Trading Mode\|BotControl" "$map_file" 2>/dev/null; then
            echo "[INFO] BotControl in Source Map gefunden: $map_file"
        fi
    done
fi
echo ""

echo "=== Zusammenfassung ==="
echo ""
if [ "$FOUND_IN_BUILD" = true ]; then
    echo "✅ Trading Mode ist im Build vorhanden"
    echo ""
    echo "Wenn Trading Mode trotzdem nicht sichtbar ist:"
    echo "1. Browser-Konsole öffnen (F12)"
    echo "2. Nach JavaScript-Fehlern suchen"
    echo "3. Network-Tab prüfen, ob alle Dateien geladen werden"
    echo "4. debug-trading-mode.js im Browser ausführen"
else
    echo "❌ Trading Mode ist NICHT im Build"
    echo "[INFO] Build muss neu erstellt werden"
fi
echo ""

