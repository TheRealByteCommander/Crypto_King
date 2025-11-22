#!/bin/bash
# Prüfe Frontend-Fehler

echo "=== Frontend Fehler-Analyse ==="
echo ""

# 1. Prüfe Frontend Status
echo "[INFO] Frontend Status:"
sudo supervisorctl status cyphertrade-frontend
echo ""

# 2. Prüfe Frontend Logs
echo "[INFO] Frontend Logs (letzte 50 Zeilen):"
if [ -f "/var/log/supervisor/cyphertrade-frontend.log" ]; then
    tail -50 /var/log/supervisor/cyphertrade-frontend.log
else
    echo "  Log-Datei nicht gefunden"
fi
echo ""

# 3. Prüfe Frontend Error Logs
echo "[INFO] Frontend Error Logs:"
if [ -f "/var/log/supervisor/cyphertrade-frontend-error.log" ]; then
    tail -50 /var/log/supervisor/cyphertrade-frontend-error.log
else
    echo "  Error-Log-Datei nicht gefunden"
fi
echo ""

# 4. Prüfe Supervisor Config
echo "[INFO] Supervisor Config für Frontend:"
if [ -f "/etc/supervisor/conf.d/cyphertrade-frontend.conf" ]; then
    cat /etc/supervisor/conf.d/cyphertrade-frontend.conf
else
    echo "  Config-Datei nicht gefunden!"
fi
echo ""

# 5. Prüfe ob Yarn verfügbar ist
echo "[INFO] Prüfe Yarn Installation:"
if command -v yarn > /dev/null 2>&1; then
    YARN_VERSION=$(yarn --version 2>&1)
    echo "[SUCCESS] Yarn installiert (Version: $YARN_VERSION)"
else
    echo "[ERROR] Yarn nicht gefunden!"
fi
echo ""

# 6. Prüfe ob Node.js verfügbar ist
echo "[INFO] Prüfe Node.js Installation:"
if command -v node > /dev/null 2>&1; then
    NODE_VERSION=$(node --version 2>&1)
    echo "[SUCCESS] Node.js installiert (Version: $NODE_VERSION)"
else
    echo "[ERROR] Node.js nicht gefunden!"
fi
echo ""

# 7. Prüfe Frontend Verzeichnis
echo "[INFO] Prüfe Frontend Verzeichnis:"
if [ -d "/app/frontend" ]; then
    echo "[SUCCESS] Frontend-Verzeichnis vorhanden: /app/frontend"
    if [ -f "/app/frontend/package.json" ]; then
        echo "[SUCCESS] package.json vorhanden"
    else
        echo "[ERROR] package.json nicht gefunden!"
    fi
    if [ -f "/app/frontend/.env" ]; then
        echo "[SUCCESS] .env vorhanden"
        echo "  REACT_APP_BACKEND_URL:"
        grep REACT_APP_BACKEND_URL /app/frontend/.env || echo "    Nicht gesetzt!"
    else
        echo "[WARNING] .env nicht gefunden!"
    fi
else
    echo "[ERROR] Frontend-Verzeichnis nicht gefunden!"
fi
echo ""

# 8. Teste Frontend-Build manuell
echo "[INFO] Teste Frontend-Installation:"
cd /app/frontend 2>/dev/null || { echo "[ERROR] Kann nicht nach /app/frontend wechseln!"; exit 1; }

if command -v yarn > /dev/null 2>&1; then
    echo "[INFO] Prüfe Dependencies..."
    if [ -d "node_modules" ]; then
        echo "[SUCCESS] node_modules vorhanden"
    else
        echo "[WARNING] node_modules nicht vorhanden - Dependencies müssen installiert werden"
    fi
fi
echo ""

echo "=== Zusammenfassung ==="
echo ""
echo "Bitte prüfen Sie:"
echo "1. Supervisor-Logs für detaillierte Fehlermeldungen"
echo "2. Frontend-Verzeichnis und Dependencies"
echo "3. .env-Datei mit REACT_APP_BACKEND_URL"
echo ""
echo "Um die vollständigen Logs zu sehen:"
echo "  tail -100 /var/log/supervisor/cyphertrade-frontend.log"
echo "  tail -100 /var/log/supervisor/cyphertrade-frontend-error.log"
echo ""

