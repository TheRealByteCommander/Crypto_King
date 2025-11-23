#!/bin/bash
# Verify Build Content - Prüft genau was im Build ist

echo "=== Build Content Verification ==="
echo ""

cd /app/frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

if [ ! -d "build" ]; then
    echo "[ERROR] Build-Verzeichnis nicht gefunden!"
    exit 1
fi

echo "[INFO] Prüfe Build-Inhalt..."
echo ""

# 1. Finde die Haupt-JS-Datei
MAIN_JS=$(find build/static/js -name "main.*.js" | head -1)
if [ -z "$MAIN_JS" ]; then
    echo "[ERROR] Haupt-JS-Datei nicht gefunden!"
    exit 1
fi

echo "[INFO] Haupt-JS-Datei: $MAIN_JS"
echo ""

# 2. Prüfe ob Trading Mode drin ist
echo "[INFO] Suche nach Trading Mode im Build..."
if grep -q "tradingMode" "$MAIN_JS" 2>/dev/null; then
    echo "[SUCCESS] 'tradingMode' gefunden"
    
    # Zeige Kontext
    echo ""
    echo "[INFO] Kontext (erste 5 Treffer):"
    grep -n "tradingMode" "$MAIN_JS" 2>/dev/null | head -5
else
    echo "[ERROR] 'tradingMode' NICHT im Build gefunden!"
fi
echo ""

# 3. Prüfe ob Trading Mode Label drin ist
if grep -q "Trading Mode\|trading-mode" "$MAIN_JS" 2>/dev/null; then
    echo "[SUCCESS] 'Trading Mode' Text gefunden"
    echo "[INFO] Kontext:"
    grep -n "Trading Mode\|trading-mode" "$MAIN_JS" 2>/dev/null | head -3
else
    echo "[WARNING] 'Trading Mode' Text nicht gefunden (kann bei Minification normal sein)"
fi
echo ""

# 4. Prüfe ob SPOT/MARGIN/FUTURES drin ist
if grep -q "SPOT.*Long Only\|MARGIN.*Short\|FUTURES.*Short" "$MAIN_JS" 2>/dev/null; then
    echo "[SUCCESS] Trading Mode Optionen gefunden"
else
    echo "[WARNING] Trading Mode Optionen nicht gefunden"
    if grep -q "SPOT\|MARGIN\|FUTURES" "$MAIN_JS" 2>/dev/null; then
        echo "[INFO] Aber einzelne Werte gefunden:"
        grep -o "SPOT\|MARGIN\|FUTURES" "$MAIN_JS" 2>/dev/null | sort -u
    fi
fi
echo ""

# 5. Prüfe ob BotControl Komponente drin ist
if grep -q "BotControl\|bot-control" "$MAIN_JS" 2>/dev/null; then
    echo "[SUCCESS] BotControl Komponente gefunden"
else
    echo "[WARNING] BotControl nicht explizit gefunden (kann bei Minification normal sein)"
fi
echo ""

# 6. Dateigröße
echo "[INFO] Build-Dateigröße:"
ls -lh "$MAIN_JS"
echo ""

# 7. Prüfe ob alle 5 Felder erkannt werden können
echo "[INFO] Prüfe auf Field-Labels..."
LABELS=("Strategy" "Symbol" "Timeframe" "Trading Mode" "Amount")
for label in "${LABELS[@]}"; do
    if grep -q "$label" "$MAIN_JS" 2>/dev/null; then
        echo "[SUCCESS] '$label' gefunden"
    else
        echo "[WARNING] '$label' nicht gefunden"
    fi
done
echo ""

echo "=== Zusammenfassung ==="
echo ""
echo "Falls Trading Mode nicht sichtbar ist, aber im Build vorhanden ist:"
echo "1. Browser-Konsole prüfen (F12 → Console)"
echo "2. Network-Tab prüfen (F12 → Network)"
echo "3. Prüfe ob main.*.js geladen wird"
echo "4. Prüfe ob JavaScript-Fehler vorhanden sind"
echo ""

