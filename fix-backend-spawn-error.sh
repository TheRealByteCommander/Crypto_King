#!/bin/bash
# Behebt Backend Spawn Error

set -e

echo "=== Backend Spawn Error beheben ==="
echo ""

BACKEND_DIR="/app/backend"

# 1. Prüfe Fehler-Logs
echo "[INFO] Prüfe Backend Error Logs (letzte 50 Zeilen):"
tail -50 /var/log/supervisor/cyphertrade-backend-error.log 2>/dev/null || echo "[WARNING] Error-Log-Datei nicht gefunden"
echo ""

echo "[INFO] Prüfe Backend Logs (letzte 50 Zeilen):"
tail -50 /var/log/supervisor/cyphertrade-backend.log 2>/dev/null || echo "[WARNING] Log-Datei nicht gefunden"
echo ""

# 2. Prüfe ob Backend-Verzeichnis existiert
if [ ! -d "$BACKEND_DIR" ]; then
    echo "[ERROR] Backend-Verzeichnis nicht gefunden: $BACKEND_DIR"
    exit 1
fi

cd "$BACKEND_DIR" || exit 1

# 3. Prüfe ob venv existiert
if [ ! -d "venv" ]; then
    echo "[ERROR] Virtual Environment nicht gefunden: $BACKEND_DIR/venv"
    exit 1
fi

# 4. Prüfe ob Python-Module installiert sind
echo "[INFO] Prüfe Python-Installation..."
source venv/bin/activate
python --version
python -c "import uvicorn; print('uvicorn OK')" || {
    echo "[ERROR] uvicorn nicht installiert"
    exit 1
}
python -c "import server; print('server module OK')" || {
    echo "[ERROR] server.py nicht gefunden oder Fehler beim Import"
    exit 1
}

# 5. Prüfe ob Port 8001 belegt ist
echo "[INFO] Prüfe Port 8001..."
if lsof -i :8001 > /dev/null 2>&1; then
    echo "[WARNING] Port 8001 ist bereits belegt:"
    lsof -i :8001
    echo "[INFO] Beende Prozesse auf Port 8001..."
    lsof -ti :8001 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# 6. Teste ob server.py direkt startet
echo "[INFO] Teste direkten Start von server.py..."
timeout 5 python -m uvicorn server:app --host 0.0.0.0 --port 8001 || {
    echo "[ERROR] Server startet nicht direkt"
    echo "[INFO] Prüfe Syntax-Fehler..."
    python -m py_compile server.py || {
        echo "[ERROR] Syntax-Fehler in server.py gefunden!"
        exit 1
    }
}

# 7. Aktualisiere Supervisor Config
echo "[INFO] Aktualisiere Supervisor Config..."
PYTHON_PATH="$BACKEND_DIR/venv/bin/python"
if [ ! -f "$PYTHON_PATH" ]; then
    echo "[ERROR] Python nicht gefunden: $PYTHON_PATH"
    exit 1
fi

sudo tee /etc/supervisor/conf.d/cyphertrade-backend.conf > /dev/null << EOF
[program:cyphertrade-backend]
directory=$BACKEND_DIR
command=$PYTHON_PATH -m uvicorn server:app --host 0.0.0.0 --port 8001
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/cyphertrade-backend.log
stderr_logfile=/var/log/supervisor/cyphertrade-backend-error.log
environment=PATH="$BACKEND_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
stopwaitsecs=10
killasgroup=true
priority=999
EOF

echo "[SUCCESS] Supervisor Config aktualisiert"

# 8. Supervisor neu laden
echo "[INFO] Lade Supervisor neu..."
sudo supervisorctl reread 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true
sudo supervisorctl update 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true

# 9. Stoppe Backend (falls noch läuft)
echo "[INFO] Stoppe Backend (falls noch läuft)..."
sudo supervisorctl stop cyphertrade-backend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true
sleep 2

# 10. Starte Backend
echo "[INFO] Starte Backend..."
sudo supervisorctl start cyphertrade-backend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || {
    echo "[ERROR] Backend startet nicht über Supervisor"
    echo "[INFO] Versuche manuellen Start..."
    cd "$BACKEND_DIR"
    source venv/bin/activate
    nohup python -m uvicorn server:app --host 0.0.0.0 --port 8001 > /var/log/supervisor/cyphertrade-backend.log 2>&1 &
    BACKEND_PID=$!
    echo "[SUCCESS] Backend manuell gestartet (PID: $BACKEND_PID)"
}

# 11. Warte kurz und prüfe Status
sleep 3
echo ""
echo "[INFO] Prüfe Backend Status..."
sudo supervisorctl status cyphertrade-backend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true

# 12. Prüfe ob Port 8001 belegt ist
if lsof -i :8001 > /dev/null 2>&1; then
    echo "[SUCCESS] Port 8001 ist belegt - Backend läuft!"
    lsof -i :8001 | head -3
else
    echo "[WARNING] Port 8001 ist NICHT belegt - Backend läuft möglicherweise nicht"
fi

echo ""
echo "=== Zusammenfassung ==="
echo ""
echo "Falls Backend immer noch nicht startet, prüfe:"
echo "  tail -50 /var/log/supervisor/cyphertrade-backend-error.log"
echo "  tail -50 /var/log/supervisor/cyphertrade-backend.log"
echo ""
echo "Manuelle Prüfung:"
echo "  cd /app/backend"
echo "  source venv/bin/activate"
echo "  python -m uvicorn server:app --host 0.0.0.0 --port 8001"
echo ""

