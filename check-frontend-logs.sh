#!/bin/bash
# Prüft Frontend Error Logs

echo "=== Frontend Error Logs ==="
echo ""

# Prüfe Error Logs
echo "[INFO] Frontend Error Logs (letzte 50 Zeilen):"
if [ -f "/var/log/supervisor/cyphertrade-frontend-error.log" ]; then
    tail -50 /var/log/supervisor/cyphertrade-frontend-error.log
else
    echo "  Error-Log-Datei nicht gefunden"
    echo "  Erstelle Log-Verzeichnis falls nötig..."
    sudo mkdir -p /var/log/supervisor
    sudo touch /var/log/supervisor/cyphertrade-frontend-error.log
    sudo touch /var/log/supervisor/cyphertrade-frontend.log
fi
echo ""

# Prüfe normale Logs
echo "[INFO] Frontend Logs (letzte 50 Zeilen):"
if [ -f "/var/log/supervisor/cyphertrade-frontend.log" ]; then
    tail -50 /var/log/supervisor/cyphertrade-frontend.log
else
    echo "  Log-Datei nicht gefunden"
fi
echo ""

# Prüfe Supervisor Config
echo "[INFO] Supervisor Config:"
cat /etc/supervisor/conf.d/cyphertrade-frontend.conf
echo ""

# Teste yarn start manuell
echo "[INFO] Teste yarn start manuell (5 Sekunden)..."
cd /app/frontend || exit 1
timeout 5 yarn start 2>&1 | head -20 || echo "  yarn start läuft (normal nach timeout)"
echo ""

