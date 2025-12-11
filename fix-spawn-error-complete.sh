#!/bin/bash
# Umfassendes Fix-Script für Supervisor Spawn Errors
# Behebt häufige Ursachen für spawn errors beim Dienst-Neustart

set -e

echo "=========================================="
echo "Supervisor Spawn Error Fix"
echo "=========================================="
echo ""

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verzeichnisse
INSTALL_DIR="/app"
BACKEND_DIR="$INSTALL_DIR/backend"
FRONTEND_DIR="$INSTALL_DIR/frontend"

# Prüfe ob wir im richtigen Verzeichnis sind
if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${YELLOW}[WARN] /app/backend nicht gefunden, versuche aktuelles Verzeichnis...${NC}"
    INSTALL_DIR="$(pwd)"
    BACKEND_DIR="$INSTALL_DIR/backend"
    FRONTEND_DIR="$INSTALL_DIR/frontend"
fi

echo "[INFO] Install-Verzeichnis: $INSTALL_DIR"
echo "[INFO] Backend-Verzeichnis: $BACKEND_DIR"
echo "[INFO] Frontend-Verzeichnis: $FRONTEND_DIR"
echo ""

# ==========================================
# 1. Prüfe Supervisor Logs
# ==========================================
echo -e "${YELLOW}Step 1: Prüfe Supervisor Error Logs${NC}"
echo ""

# Backend Error Logs
if [ -f "/var/log/supervisor/cyphertrade-backend-error.log" ]; then
    echo "[INFO] Backend Error Logs (letzte 30 Zeilen):"
    tail -30 /var/log/supervisor/cyphertrade-backend-error.log | grep -vE "(pkg_resources|deprecated|UserWarning)" || true
    echo ""
else
    echo "[WARN] Backend Error Log nicht gefunden"
fi

# Frontend Error Logs
if [ -f "/var/log/supervisor/cyphertrade-frontend-error.log" ]; then
    echo "[INFO] Frontend Error Logs (letzte 30 Zeilen):"
    tail -30 /var/log/supervisor/cyphertrade-frontend-error.log | grep -vE "(pkg_resources|deprecated|UserWarning)" || true
    echo ""
else
    echo "[WARN] Frontend Error Log nicht gefunden"
fi

# ==========================================
# 2. Prüfe Backend
# ==========================================
echo -e "${YELLOW}Step 2: Prüfe Backend${NC}"
echo ""

if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}[ERROR] Backend-Verzeichnis nicht gefunden: $BACKEND_DIR${NC}"
    exit 1
fi

cd "$BACKEND_DIR" || exit 1

# Prüfe venv
if [ ! -d "venv" ]; then
    echo -e "${RED}[ERROR] Virtual Environment nicht gefunden: $BACKEND_DIR/venv${NC}"
    echo "[INFO] Erstelle venv..."
    python3 -m venv venv
fi

# Aktiviere venv
source venv/bin/activate

# Prüfe Python
PYTHON_PATH="$(which python)"
echo "[INFO] Python-Pfad: $PYTHON_PATH"
python --version || {
    echo -e "${RED}[ERROR] Python nicht verfügbar${NC}"
    exit 1
}

# Prüfe kritische Module
echo "[INFO] Prüfe kritische Python-Module..."
python -c "import uvicorn; print('✓ uvicorn OK')" || {
    echo -e "${RED}[ERROR] uvicorn nicht installiert${NC}"
    echo "[INFO] Installiere uvicorn..."
    pip install uvicorn[standard] --quiet
}

python -c "import fastapi; print('✓ fastapi OK')" || {
    echo -e "${RED}[ERROR] fastapi nicht installiert${NC}"
    echo "[INFO] Installiere fastapi..."
    pip install fastapi --quiet
}

# Prüfe server.py Import
echo "[INFO] Prüfe server.py Import..."
python -c "import server; print('✓ server.py OK')" || {
    echo -e "${RED}[ERROR] server.py kann nicht importiert werden${NC}"
    echo "[INFO] Prüfe Syntax..."
    python -m py_compile server.py || {
        echo -e "${RED}[ERROR] Syntax-Fehler in server.py gefunden!${NC}"
        exit 1
    }
    exit 1
}

# Prüfe Port 8001
echo "[INFO] Prüfe Port 8001..."
if lsof -i :8001 > /dev/null 2>&1; then
    echo -e "${YELLOW}[WARN] Port 8001 ist belegt${NC}"
    echo "[INFO] Beende Prozesse auf Port 8001..."
    lsof -ti :8001 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# ==========================================
# 3. Prüfe Frontend
# ==========================================
echo ""
echo -e "${YELLOW}Step 3: Prüfe Frontend${NC}"
echo ""

if [ -d "$FRONTEND_DIR" ]; then
    cd "$FRONTEND_DIR" || exit 1
    
    # Prüfe node_modules
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}[WARN] node_modules nicht gefunden${NC}"
    else
        echo "[INFO] node_modules vorhanden"
    fi
    
    # Prüfe yarn/npm
    if command -v yarn >/dev/null 2>&1; then
        YARN_PATH="$(which yarn)"
        echo "[INFO] yarn gefunden: $YARN_PATH"
    elif command -v npm >/dev/null 2>&1; then
        NPM_PATH="$(which npm)"
        echo "[INFO] npm gefunden: $NPM_PATH"
    else
        echo -e "${RED}[ERROR] Weder yarn noch npm gefunden${NC}"
    fi
    
    # Prüfe Port 3000
    echo "[INFO] Prüfe Port 3000..."
    if lsof -i :3000 > /dev/null 2>&1; then
        echo -e "${YELLOW}[WARN] Port 3000 ist belegt${NC}"
        echo "[INFO] Beende Prozesse auf Port 3000..."
        lsof -ti :3000 | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
else
    echo -e "${YELLOW}[WARN] Frontend-Verzeichnis nicht gefunden${NC}"
fi

# ==========================================
# 4. Aktualisiere Supervisor Configs
# ==========================================
echo ""
echo -e "${YELLOW}Step 4: Aktualisiere Supervisor Configs${NC}"
echo ""

cd "$INSTALL_DIR" || exit 1

# Backend Config
echo "[INFO] Aktualisiere Backend Supervisor Config..."
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
startsecs=5
startretries=3
EOF

echo -e "${GREEN}[OK] Backend Config aktualisiert${NC}"

# Frontend Config (falls Frontend vorhanden)
if [ -d "$FRONTEND_DIR" ] && command -v yarn >/dev/null 2>&1; then
    echo "[INFO] Aktualisiere Frontend Supervisor Config..."
    
    # Prüfe ob build/ Verzeichnis existiert (Production)
    if [ -d "$FRONTEND_DIR/build" ]; then
        # Production: serve verwenden
        if command -v serve >/dev/null 2>&1; then
            FRONTEND_CMD="serve -s build -l 3000"
        else
            echo "[WARN] serve nicht gefunden, installiere..."
            npm install -g serve 2>/dev/null || true
            FRONTEND_CMD="serve -s build -l 3000"
        fi
    else
        # Development: yarn start
        FRONTEND_CMD="yarn start"
    fi
    
    sudo tee /etc/supervisor/conf.d/cyphertrade-frontend.conf > /dev/null << EOF
[program:cyphertrade-frontend]
directory=$FRONTEND_DIR
command=$FRONTEND_CMD
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/cyphertrade-frontend.log
stderr_logfile=/var/log/supervisor/cyphertrade-frontend-error.log
environment=PATH="/usr/local/bin:/usr/bin:/bin",REACT_APP_BACKEND_URL="http://192.168.178.155:8001"
stopwaitsecs=10
killasgroup=true
priority=998
startsecs=10
startretries=3
EOF
    
    echo -e "${GREEN}[OK] Frontend Config aktualisiert${NC}"
fi

# ==========================================
# 5. Supervisor neu laden
# ==========================================
echo ""
echo -e "${YELLOW}Step 5: Supervisor neu laden${NC}"
echo ""

sudo supervisorctl reread 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true
sudo supervisorctl update 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true

# ==========================================
# 6. Stoppe Services (falls laufen)
# ==========================================
echo ""
echo -e "${YELLOW}Step 6: Stoppe Services${NC}"
echo ""

sudo supervisorctl stop cyphertrade-backend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true
sudo supervisorctl stop cyphertrade-frontend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true

sleep 3

# ==========================================
# 7. Starte Services
# ==========================================
echo ""
echo -e "${YELLOW}Step 7: Starte Services${NC}"
echo ""

# Backend starten
echo "[INFO] Starte Backend..."
sudo supervisorctl start cyphertrade-backend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || {
    echo -e "${RED}[ERROR] Backend konnte nicht über Supervisor gestartet werden${NC}"
    echo "[INFO] Versuche manuellen Start..."
    cd "$BACKEND_DIR"
    source venv/bin/activate
    nohup python -m uvicorn server:app --host 0.0.0.0 --port 8001 > /var/log/supervisor/cyphertrade-backend.log 2>&1 &
    BACKEND_PID=$!
    echo -e "${GREEN}[OK] Backend manuell gestartet (PID: $BACKEND_PID)${NC}"
}

sleep 3

# Frontend starten (falls vorhanden)
if [ -d "$FRONTEND_DIR" ]; then
    echo "[INFO] Starte Frontend..."
    sudo supervisorctl start cyphertrade-frontend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || {
        echo -e "${YELLOW}[WARN] Frontend konnte nicht über Supervisor gestartet werden${NC}"
    }
fi

# ==========================================
# 8. Prüfe Status
# ==========================================
echo ""
echo -e "${YELLOW}Step 8: Prüfe Service-Status${NC}"
echo ""

sleep 2

echo "=== Backend Status ==="
sudo supervisorctl status cyphertrade-backend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true

echo ""
echo "=== Frontend Status ==="
sudo supervisorctl status cyphertrade-frontend 2>&1 | grep -vE "(pkg_resources|deprecated|UserWarning)" || true

echo ""
echo "=== Port-Check ==="
if lsof -i :8001 > /dev/null 2>&1; then
    echo -e "${GREEN}[OK] Port 8001 ist belegt - Backend läuft${NC}"
else
    echo -e "${RED}[ERROR] Port 8001 ist NICHT belegt - Backend läuft möglicherweise nicht${NC}"
fi

if lsof -i :3000 > /dev/null 2>&1; then
    echo -e "${GREEN}[OK] Port 3000 ist belegt - Frontend läuft${NC}"
else
    echo -e "${YELLOW}[WARN] Port 3000 ist NICHT belegt${NC}"
fi

# ==========================================
# Zusammenfassung
# ==========================================
echo ""
echo "=========================================="
echo -e "${GREEN}Fix abgeschlossen!${NC}"
echo "=========================================="
echo ""
echo "Falls Probleme weiterhin bestehen:"
echo "  1. Prüfe Error Logs:"
echo "     tail -50 /var/log/supervisor/cyphertrade-backend-error.log"
echo "     tail -50 /var/log/supervisor/cyphertrade-frontend-error.log"
echo ""
echo "  2. Prüfe Status Logs:"
echo "     tail -50 /var/log/supervisor/cyphertrade-backend.log"
echo "     tail -50 /var/log/supervisor/cyphertrade-frontend.log"
echo ""
echo "  3. Manuelle Prüfung Backend:"
echo "     cd $BACKEND_DIR"
echo "     source venv/bin/activate"
echo "     python -m uvicorn server:app --host 0.0.0.0 --port 8001"
echo ""
echo "  4. Prüfe Supervisor Config:"
echo "     cat /etc/supervisor/conf.d/cyphertrade-backend.conf"
echo "     cat /etc/supervisor/conf.d/cyphertrade-frontend.conf"
echo ""

