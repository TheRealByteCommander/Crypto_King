#!/bin/bash
# Debuggt Frontend-Start-Problem

set -e

echo "=== Frontend Debug ==="
echo ""

# 1. Prüfe vollständige Logs
echo "[INFO] Frontend Error Logs (letzte 100 Zeilen):"
if [ -f "/var/log/supervisor/cyphertrade-frontend-error.log" ]; then
    tail -100 /var/log/supervisor/cyphertrade-frontend-error.log
else
    echo "  Error-Log-Datei nicht gefunden"
fi
echo ""

echo "[INFO] Frontend Logs (letzte 100 Zeilen):"
if [ -f "/var/log/supervisor/cyphertrade-frontend.log" ]; then
    tail -100 /var/log/supervisor/cyphertrade-frontend.log
else
    echo "  Log-Datei nicht gefunden"
fi
echo ""

# 2. Prüfe Frontend Verzeichnis
echo "[INFO] Prüfe Frontend Verzeichnis:"
cd /app/frontend || { echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"; exit 1; }

# 3. Prüfe .env Datei
echo "[INFO] Prüfe .env Datei:"
if [ -f ".env" ]; then
    echo "[SUCCESS] .env vorhanden:"
    cat .env
else
    echo "[ERROR] .env nicht gefunden!"
fi
echo ""

# 4. Prüfe node_modules
echo "[INFO] Prüfe node_modules:"
if [ -d "node_modules" ]; then
    echo "[SUCCESS] node_modules vorhanden"
    echo "  Anzahl Module: $(find node_modules -maxdepth 1 -type d | wc -l)"
else
    echo "[ERROR] node_modules nicht vorhanden!"
    echo "[INFO] Installiere Dependencies..."
    yarn install --frozen-lockfile || yarn install
fi
echo ""

# 5. Prüfe package.json
echo "[INFO] Prüfe package.json:"
if [ -f "package.json" ]; then
    echo "[SUCCESS] package.json vorhanden"
else
    echo "[ERROR] package.json nicht gefunden!"
    exit 1
fi
echo ""

# 6. Teste yarn direkt
echo "[INFO] Teste yarn direkt:"
if ! command -v yarn > /dev/null 2>&1; then
    echo "[ERROR] Yarn nicht gefunden!"
    exit 1
fi
YARN_VERSION=$(yarn --version 2>&1)
echo "[SUCCESS] Yarn Version: $YARN_VERSION"
echo ""

# 7. Teste node direkt
echo "[INFO] Teste node direkt:"
if ! command -v node > /dev/null 2>&1; then
    echo "[ERROR] Node nicht gefunden!"
    exit 1
fi
NODE_VERSION=$(node --version 2>&1)
echo "[SUCCESS] Node Version: $NODE_VERSION"
echo ""

# 8. Führe yarn start manuell aus (mit vollem Output)
echo "[INFO] Führe yarn start manuell aus (10 Sekunden timeout):"
echo "[INFO] Um die vollständige Ausgabe zu sehen..."
echo ""

# Setze Environment-Variablen
export REACT_APP_BACKEND_URL="http://192.168.178.154:8001"
export NODE_ENV="development"
export GENERATE_SOURCEMAP="false"
export DISABLE_HOT_RELOAD="true"
export FAST_REFRESH="false"
export WDS_SOCKET_HOST=""

# Führe yarn start aus und fange die Ausgabe
timeout 10 yarn start 2>&1 || {
    EXIT_CODE=$?
    echo ""
    echo "[INFO] yarn start beendet mit Exit-Code: $EXIT_CODE"
    echo "[INFO] Das ist normal nach dem Timeout, aber prüfe die Fehlermeldungen oben"
}

echo ""
echo "=== Zusammenfassung ==="
echo ""
echo "Wenn 'yarn start' oben einen Fehler zeigt, ist das die Ursache."
echo "Wenn nicht, prüfe bitte die Logs manuell:"
echo "  tail -100 /var/log/supervisor/cyphertrade-frontend-error.log"
echo "  tail -100 /var/log/supervisor/cyphertrade-frontend.log"
echo ""

