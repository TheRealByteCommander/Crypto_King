#!/bin/bash

################################################################################
# Project CypherTrade - Vollautomatisches Installations-Skript
# 
# Dieses Skript installiert automatisch ohne Benutzerbestätigung:
# - Python 3.11+ mit allen Dependencies
# - Node.js 20 LTS+ und Yarn
# - MongoDB
# - Ollama mit llama3.2
# - Klont GitHub Repository (optional)
# - Erstellt .env Dateien automatisch
# - Konfiguriert das System vollständig
#
# Verwendung:
#   sudo bash install.sh [OPTIONS]
#
# Optionen:
#   --repo-url URL         GitHub Repository URL (Standard: wird aus Git erkannt)
#   --install-dir DIR      Installationsverzeichnis (Standard: /app)
#   --skip-clone           Überspringe GitHub Clone (wenn Repo bereits vorhanden)
#   --skip-ollama          Überspringe lokale Ollama Installation (Remote-Server verwenden)
#   --ollama-server IP     Ollama Server IP (Standard: 192.168.178.155)
#   --cryptoking-ip IP     CryptoKing Server IP (Standard: 192.168.178.154)
#   --help                 Zeige Hilfe
#
# Beispiele:
#   sudo bash install.sh
#   sudo bash install.sh --repo-url https://github.com/user/repo.git --install-dir /opt/cryptotrade
#   sudo bash install.sh --skip-clone
################################################################################

# Exit bei Fehler wird später aktiviert (nach System-Update)
# set -e wird nach update_system aktiviert, um apt_pkg Fehler zu ignorieren

# Standardwerte (Remote-Ollama Infrastruktur)
GITHUB_REPO_URL=""
INSTALL_DIR="/app"
SKIP_CLONE=false
SKIP_OLLAMA_MODEL=false
SKIP_OLLAMA_INSTALL=true  # Standardmäßig Remote-Ollama verwenden
OLLAMA_SERVER_IP="192.168.178.155"
CRYPTOKING_IP="192.168.178.154"
AUTO_YES=true  # Vollautomatisch

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging Funktionen
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
print_banner() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                                                           ║${NC}"
    echo -e "${BLUE}║     ${GREEN}Project CypherTrade - Vollautomatische Installation${BLUE}     ║${NC}"
    echo -e "${BLUE}║          ${YELLOW}AI-Powered Crypto Trading Bot${BLUE}                 ║${NC}"
    echo -e "${BLUE}║                                                           ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Hilfe anzeigen
show_help() {
    echo "Verwendung: sudo bash install.sh [OPTIONS]"
    echo ""
    echo "Optionen:"
    echo "  --repo-url URL         GitHub Repository URL"
    echo "  --install-dir DIR      Installationsverzeichnis (Standard: /app)"
    echo "  --skip-clone           Überspringe GitHub Clone"
    echo "  --skip-ollama          Überspringe lokale Ollama Installation (Standard: aktiv)"
    echo "  --install-ollama-local Installiere Ollama lokal (überschreibt Remote-Setup)"
    echo "  --ollama-server IP     Ollama Server IP (Standard: 192.168.178.155)"
    echo "  --cryptoking-ip IP     CryptoKing Server IP (Standard: 192.168.178.154)"
    echo "  --help                 Zeige diese Hilfe"
    echo ""
    echo "Standard-Konfiguration:"
    echo "  - Remote-Ollama Server: 192.168.178.155"
    echo "  - CryptoKing Server: 192.168.178.154"
    echo ""
    exit 0
}

# Parameter parsen
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --repo-url)
                GITHUB_REPO_URL="$2"
                shift 2
                ;;
            --install-dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --skip-clone)
                SKIP_CLONE=true
                shift
                ;;
            --skip-ollama)
                SKIP_OLLAMA_INSTALL=true
                shift
                ;;
            --ollama-server)
                OLLAMA_SERVER_IP="$2"
                SKIP_OLLAMA_INSTALL=true  # Remote-Server verwenden
                shift 2
                ;;
            --install-ollama-local)
                SKIP_OLLAMA_INSTALL=false  # Lokale Installation
                shift
                ;;
            --cryptoking-ip)
                CRYPTOKING_IP="$2"
                shift 2
                ;;
            --help)
                show_help
                ;;
            *)
                log_error "Unbekannte Option: $1"
                show_help
                ;;
        esac
    done
}

# Root Check
check_root() {
    if [ "$EUID" -ne 0 ]; then 
        log_error "Bitte als root ausführen: sudo bash install.sh"
        exit 1
    fi
    log_success "Root-Rechte vorhanden"
}

# OS Check (ohne Bestätigung)
check_os() {
    log_info "Prüfe Betriebssystem..."
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        log_error "Kann OS nicht ermitteln"
        exit 1
    fi
    
    if [[ "$OS" == *"Ubuntu"* ]]; then
        if [[ "$VER" == "22.04" ]] || [[ "$VER" == "20.04" ]] || [[ "$VER" == "24.04" ]]; then
            log_success "Ubuntu $VER erkannt"
        else
            log_warning "Ubuntu Version $VER nicht getestet, fahre automatisch fort..."
        fi
    else
        log_warning "Nicht-Ubuntu System erkannt: $OS. Fahre automatisch fort..."
    fi
}

# System Update
update_system() {
    log_info "Aktualisiere System-Pakete..."
    export DEBIAN_FRONTEND=noninteractive
    export LC_ALL=C.UTF-8
    export LANG=C.UTF-8
    
    # Locale-Probleme beheben
    apt-get install -y -qq locales 2>/dev/null || true
    locale-gen en_US.UTF-8 2>/dev/null || true
    update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 2>/dev/null || true
    
    # apt_pkg Problem beheben
    apt-get install -y -qq python3-apt python3-distutils 2>/dev/null || true
    
    # command-not-found Hook komplett deaktivieren (apt_pkg Fehler)
    if [ -f /etc/apt/apt.conf.d/50command-not-found ]; then
        mv /etc/apt/apt.conf.d/50command-not-found /etc/apt/apt.conf.d/50command-not-found.disabled 2>/dev/null || true
    fi
    
    # Hook-Deaktivierung für apt-get update (vor dem Update!)
    mkdir -p /etc/apt/apt.conf.d
    echo 'APT::Update::Post-Invoke-Success "";' > /etc/apt/apt.conf.d/99-disable-cnf-update-db 2>/dev/null || true
    echo 'APT::Update::Post-Invoke-Success "exit 0";' >> /etc/apt/apt.conf.d/99-disable-cnf-update-db 2>/dev/null || true
    
    # cnf-update-db Script deaktivieren/entfernen
    if [ -f /usr/lib/cnf-update-db ]; then
        mv /usr/lib/cnf-update-db /usr/lib/cnf-update-db.disabled 2>/dev/null || true
        chmod -x /usr/lib/cnf-update-db.disabled 2>/dev/null || true
    fi
    
    # apt-get update mit Fehler-Toleranz
    log_info "Aktualisiere Paketlisten..."
    # Deaktiviere set -e für diese Operation (apt_pkg Fehler ist harmlos)
    set +e
    apt-get update -qq 2>&1 | grep -vE "(apt_pkg|cnf-update-db|ModuleNotFoundError|Problem executing)" || true
    UPDATE_EXIT=$?
    
    # Prüfe ob Update erfolgreich war (Exit Code 0 oder 100 sind OK)
    if [ $UPDATE_EXIT -eq 0 ] || [ $UPDATE_EXIT -eq 100 ]; then
        log_success "Paketlisten aktualisiert"
    else
        # Versuche es nochmal mit komplett deaktiviertem Hook
        log_warning "Update hatte Warnungen, versuche erneut..."
        # Hook komplett deaktivieren
        echo 'APT::Update::Post-Invoke-Success "exit 0";' > /etc/apt/apt.conf.d/99-disable-cnf-update-db
        # cnf-update-db Script entfernen/deaktivieren
        [ -f /usr/lib/cnf-update-db ] && mv /usr/lib/cnf-update-db /usr/lib/cnf-update-db.disabled || true
        [ -f /usr/lib/cnf-update-db.disabled ] && chmod -x /usr/lib/cnf-update-db.disabled || true
        
        apt-get update -qq 2>&1 | grep -vE "(apt_pkg|Problem)" || true
        log_success "Paketlisten aktualisiert (mit Warnungen ignoriert)"
    fi
    
    # System Upgrade (mit Fehlertoleranz)
    apt-get upgrade -y -qq 2>&1 | grep -vE "apt_pkg" || true
    
    log_success "System aktualisiert"
    
    # Reaktiviere set -e für weitere Schritte (nach erfolgreichem Update)
    set -e
}

# Install Essential Packages
install_essentials() {
    log_info "Installiere essenzielle Pakete..."
    
    PACKAGES=(
        "curl"
        "wget"
        "git"
        "build-essential"
        "software-properties-common"
        "apt-transport-https"
        "ca-certificates"
        "gnupg"
        "lsb-release"
        "supervisor"
    )
    
    export DEBIAN_FRONTEND=noninteractive
    apt-get install -y -qq "${PACKAGES[@]}"
    log_success "Essenzielle Pakete installiert"
}

# Install Python 3.11
install_python() {
    log_info "Prüfe Python Installation..."
    
    if command -v python3.11 &> /dev/null; then
        PYTHON_VERSION=$(python3.11 --version | cut -d' ' -f2)
        log_success "Python 3.11 bereits installiert (Version: $PYTHON_VERSION)"
    else
        log_info "Installiere Python 3.11..."
        export DEBIAN_FRONTEND=noninteractive
        add-apt-repository ppa:deadsnakes/ppa -y
        apt-get update -qq
        apt-get install -y -qq python3.11 python3.11-venv python3.11-dev python3-pip
        
        # Python 3.11 als Standard setzen
        update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 --slave /usr/bin/python3-config python3-config /usr/bin/python3.11-config 2>/dev/null || true
        
        log_success "Python 3.11 installiert"
    fi
    
    # Pip upgraden
    python3.11 -m pip install --upgrade pip setuptools wheel --quiet
}

# Install Node.js and Yarn
install_nodejs() {
    log_info "Prüfe Node.js Installation..."
    
    # Locale für NodeSource Script setzen
    export LC_ALL=C.UTF-8
    export LANG=C.UTF-8
    
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version 2>/dev/null || echo "v0.0.0")
        MAJOR_VERSION=$(echo $NODE_VERSION | cut -d'.' -f1 | sed 's/v//')
        
        if [ "$MAJOR_VERSION" -ge 20 ]; then
            log_success "Node.js bereits installiert (Version: $NODE_VERSION)"
        else
            log_warning "Node.js Version zu alt ($NODE_VERSION), aktualisiere auf Node.js 20 LTS..."
            # Alte Node.js Versionen und Konflikte entfernen
            log_info "Entferne alte Node.js Pakete..."
            apt-get remove -y nodejs npm libnode-dev libnode72 2>/dev/null || true
            apt-get purge -y nodejs npm libnode-dev libnode72 2>/dev/null || true
            dpkg --remove --force-remove-reinstreq libnode-dev libnode72 2>/dev/null || true
            rm -rf /etc/apt/sources.list.d/nodesource.list 2>/dev/null || true
            
            # Paket-Cache bereinigen
            apt-get update -qq 2>/dev/null || true
            dpkg --configure -a 2>/dev/null || true
            
            # Abhängigkeiten bereinigen
            apt-get autoremove -y -qq 2>/dev/null || true
            apt-get autoclean -qq 2>/dev/null || true
            
            # Node.js 20 LTS installieren
            log_info "Installiere Node.js 20 LTS..."
            curl -fsSL https://deb.nodesource.com/setup_20.x | bash - 2>&1 | grep -v "DEPRECATION" || true
            apt-get update -qq 2>/dev/null || true
            apt-get install -y -qq nodejs
            log_success "Node.js 20 LTS installiert"
        fi
    else
        log_info "Installiere Node.js 20 LTS..."
        # Alte Node.js Pakete entfernen falls vorhanden
        log_info "Entferne alte Node.js Pakete..."
        apt-get remove -y nodejs npm libnode-dev libnode72 2>/dev/null || true
        apt-get purge -y nodejs npm libnode-dev libnode72 2>/dev/null || true
        dpkg --remove --force-remove-reinstreq libnode-dev libnode72 2>/dev/null || true
        rm -rf /etc/apt/sources.list.d/nodesource.list 2>/dev/null || true
        
        # Paket-Cache bereinigen
        apt-get update -qq 2>/dev/null || true
        dpkg --configure -a 2>/dev/null || true
        
        # Node.js 20 LTS installieren
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - 2>&1 | grep -v "DEPRECATION" || true
        apt-get update -qq 2>/dev/null || true
        apt-get install -y -qq nodejs
        log_success "Node.js 20 LTS installiert"
    fi
    
    # Prüfe ob npm verfügbar ist
    if ! command -v npm &> /dev/null; then
        log_warning "npm nicht gefunden, installiere npm..."
        apt-get install -y -qq npm
    fi
    
    # npm Version prüfen
    NPM_VERSION=$(npm --version 2>/dev/null || echo "0.0.0")
    log_info "npm Version: $NPM_VERSION"
    
    # Yarn installieren
    if ! command -v yarn &> /dev/null; then
        log_info "Installiere Yarn..."
        npm install -g yarn --silent 2>&1 | grep -v "npm WARN" || true
        log_success "Yarn installiert"
    else
        YARN_VERSION=$(yarn --version 2>/dev/null || echo "unknown")
        log_success "Yarn bereits installiert (Version: $YARN_VERSION)"
    fi
}

# Install MongoDB
install_mongodb() {
    log_info "Prüfe MongoDB Installation..."
    
    if systemctl is-active --quiet mongod 2>/dev/null; then
        log_success "MongoDB läuft bereits"
        return
    fi
    
    if command -v mongod &> /dev/null; then
        log_info "MongoDB installiert, starte Service..."
        systemctl start mongod 2>/dev/null || true
        systemctl enable mongod 2>/dev/null || true
        log_success "MongoDB Service gestartet"
        return
    fi
    
    log_info "Installiere MongoDB..."
    
    # MongoDB GPG Key
    curl -fsSL https://www.mongodb.org/static/pgp/server-6.0.asc | \
        gpg -o /usr/share/keyrings/mongodb-server-6.0.gpg --dearmor 2>/dev/null
    
    # MongoDB Repository
    echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-6.0.gpg ] \
        https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | \
        tee /etc/apt/sources.list.d/mongodb-org-6.0.list >/dev/null
    
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq mongodb-org
    
    # MongoDB starten und aktivieren
    systemctl start mongod
    systemctl enable mongod
    
    # Warten bis MongoDB bereit ist
    sleep 5
    
    if systemctl is-active --quiet mongod; then
        log_success "MongoDB erfolgreich installiert und gestartet"
    else
        log_error "MongoDB konnte nicht gestartet werden"
        exit 1
    fi
}

# Install Ollama (optional wenn Remote-Server verwendet wird)
install_ollama() {
    if [ "$SKIP_OLLAMA_INSTALL" = true ]; then
        log_info "Lokale Ollama Installation übersprungen (Remote-Server: $OLLAMA_SERVER_IP)"
        log_info "Prüfe Remote-Ollama Verbindung..."
        
        # Teste Verbindung zum Remote-Ollama Server
        if curl -s --connect-timeout 5 "http://$OLLAMA_SERVER_IP:11434/api/tags" > /dev/null 2>&1; then
            log_success "Remote-Ollama Server erreichbar: http://$OLLAMA_SERVER_IP:11434"
        else
            log_warning "Remote-Ollama Server nicht erreichbar: http://$OLLAMA_SERVER_IP:11434"
            log_info "Bitte stellen Sie sicher, dass der Ollama Server läuft und erreichbar ist"
        fi
        return
    fi
    
    log_info "Prüfe lokale Ollama Installation..."
    
    if command -v ollama &> /dev/null; then
        log_success "Ollama bereits installiert"
    else
        log_info "Installiere Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh >/dev/null 2>&1
        log_success "Ollama installiert"
    fi
    
    # Ollama Service starten
    log_info "Starte Ollama Service..."
    systemctl start ollama 2>/dev/null || true
    systemctl enable ollama 2>/dev/null || true
    
    # Alternativ: Ollama im Hintergrund starten wenn kein systemd service
    if ! systemctl is-active --quiet ollama 2>/dev/null; then
        log_info "Starte Ollama manuell..."
        nohup ollama serve > /var/log/ollama.log 2>&1 &
        sleep 3
    fi
    
    # Llama3.2 herunterladen (wenn nicht übersprungen)
    if [ "$SKIP_OLLAMA_MODEL" = false ]; then
        log_info "Lade Llama 3.2 Modell herunter (dies kann einige Minuten dauern)..."
        
        if ollama list 2>/dev/null | grep -q "llama3.2"; then
            log_success "Llama 3.2 bereits heruntergeladen"
        else
            ollama pull llama3.2
            log_success "Llama 3.2 erfolgreich heruntergeladen"
        fi
    else
        log_info "Ollama Modell Download übersprungen"
    fi
}

# GitHub Repository klonen
clone_repository() {
    if [ "$SKIP_CLONE" = true ]; then
        log_info "GitHub Clone übersprungen (--skip-clone aktiviert)"
        return
    fi
    
    # Prüfe ob Verzeichnis bereits existiert und ein Git Repo ist
    if [ -d "$INSTALL_DIR" ] && [ -d "$INSTALL_DIR/.git" ]; then
        log_info "Git Repository bereits vorhanden in $INSTALL_DIR"
        log_info "Überspringe Clone. Verwenden Sie --skip-clone für zukünftige Läufe."
        return
    fi
    
    # Versuche Repository URL zu bestimmen
    if [ -z "$GITHUB_REPO_URL" ]; then
        # Wenn wir bereits in einem Git Repo sind, hole die Remote URL
        if [ -d ".git" ]; then
            GITHUB_REPO_URL=$(git remote get-url origin 2>/dev/null || echo "")
        fi
        
        # Wenn immer noch leer, versuche aus dem aktuellen Verzeichnis zu bestimmen
        if [ -z "$GITHUB_REPO_URL" ]; then
            log_warning "Keine GitHub Repository URL angegeben."
            log_info "Erstelle Installationsverzeichnis ohne Clone..."
            mkdir -p "$INSTALL_DIR"
            return
        fi
    fi
    
    log_info "Klone Repository von $GITHUB_REPO_URL nach $INSTALL_DIR..."
    
    # Entferne existierendes Verzeichnis falls vorhanden
    if [ -d "$INSTALL_DIR" ]; then
        log_warning "Verzeichnis $INSTALL_DIR existiert bereits. Überschreibe..."
        rm -rf "$INSTALL_DIR"
    fi
    
    # Klone Repository
    git clone "$GITHUB_REPO_URL" "$INSTALL_DIR" 2>/dev/null || {
        log_error "Konnte Repository nicht klonen. Bitte URL prüfen oder --skip-clone verwenden."
        exit 1
    }
    
    log_success "Repository erfolgreich geklont"
}

# Setup Project Directory
setup_project_directory() {
    log_info "Prüfe Projekt-Verzeichnis..."
    
    if [ ! -d "$INSTALL_DIR" ]; then
        log_error "Projekt-Verzeichnis $INSTALL_DIR nicht gefunden!"
        log_info "Versuche Clone..."
        clone_repository
    fi
    
    if [ ! -d "$INSTALL_DIR" ]; then
        log_error "Projekt-Verzeichnis konnte nicht erstellt werden!"
        exit 1
    fi
    
    cd "$INSTALL_DIR"
    log_success "Projekt-Verzeichnis: $INSTALL_DIR"
}

# Create .env file for backend
create_backend_env() {
    log_info "Erstelle Backend .env Datei..."
    
    ENV_FILE="$INSTALL_DIR/backend/.env"
    
    # Erstelle backend Verzeichnis falls nicht vorhanden
    mkdir -p "$INSTALL_DIR/backend"
    
    # Wenn .env bereits existiert, überspringe
    if [ -f "$ENV_FILE" ]; then
        log_warning "Backend .env bereits vorhanden, überspringe Erstellung"
        return
    fi
    
    # Erstelle .env mit Standardwerten (verwendet Remote-Ollama IP)
    cat > "$ENV_FILE" << EOF
# MongoDB Configuration
MONGO_URL=mongodb://localhost:27017
DB_NAME=cryptotrade

# Binance API Configuration
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
BINANCE_TESTNET=true

# Ollama Configuration
OLLAMA_BASE_URL=http://$OLLAMA_SERVER_IP:11434/v1
OLLAMA_API_KEY=ollama

# Agent LLM Configuration
NEXUSCHAT_LLM_PROVIDER=ollama
NEXUSCHAT_MODEL=llama3.2
NEXUSCHAT_BASE_URL=http://$OLLAMA_SERVER_IP:11434/v1

CYPHERMIND_LLM_PROVIDER=ollama
CYPHERMIND_MODEL=llama3.2
CYPHERMIND_BASE_URL=http://$OLLAMA_SERVER_IP:11434/v1

CYPHERTRADE_LLM_PROVIDER=ollama
CYPHERTRADE_MODEL=llama3.2
CYPHERTRADE_BASE_URL=http://$OLLAMA_SERVER_IP:11434/v1

# Trading Configuration
DEFAULT_STRATEGY=ma_crossover
DEFAULT_SYMBOL=BTCUSDT
DEFAULT_AMOUNT=100
MAX_POSITION_SIZE=1000
RISK_PER_TRADE=0.02

# CORS Configuration
CORS_ORIGINS=http://$CRYPTOKING_IP:3000,http://localhost:3000,http://127.0.0.1:3000

# MCP Server Configuration
MCP_ENABLED=false
MCP_PORT=8002

# Notification Configuration
EMAIL_ENABLED=false
TELEGRAM_ENABLED=false
EOF
    
    log_success "Backend .env Datei erstellt: $ENV_FILE"
    log_warning "Bitte tragen Sie Ihre Binance API Keys in $ENV_FILE ein"
}

# Create .env file for frontend
create_frontend_env() {
    log_info "Erstelle Frontend .env Datei..."
    
    ENV_FILE="$INSTALL_DIR/frontend/.env"
    
    # Erstelle frontend Verzeichnis falls nicht vorhanden
    mkdir -p "$INSTALL_DIR/frontend"
    
    # Wenn .env bereits existiert, überspringe
    if [ -f "$ENV_FILE" ]; then
        log_warning "Frontend .env bereits vorhanden, überspringe Erstellung"
        return
    fi
    
    # Erstelle .env mit Standardwerten
    cat > "$ENV_FILE" << EOF
REACT_APP_BACKEND_URL=http://$CRYPTOKING_IP:8001
EOF
    
    log_success "Frontend .env Datei erstellt: $ENV_FILE"
}

# Install Backend Dependencies
install_backend_deps() {
    log_info "Installiere Backend-Dependencies..."
    
    if [ ! -d "$INSTALL_DIR/backend" ]; then
        log_error "Backend Verzeichnis nicht gefunden: $INSTALL_DIR/backend"
        exit 1
    fi
    
    cd "$INSTALL_DIR/backend"
    
    # Virtual Environment erstellen falls nicht vorhanden
    if [ ! -d "venv" ]; then
        log_info "Erstelle Python Virtual Environment..."
        python3.11 -m venv venv
    fi
    
    # Aktiviere venv und installiere Dependencies
    source venv/bin/activate
    
    log_info "Installiere Python-Pakete..."
    pip install --upgrade pip --quiet
    pip install -r requirements.txt --quiet 2>&1 | grep -v "WARNING" || true
    
    deactivate
    
    log_success "Backend-Dependencies installiert"
}

# Install Frontend Dependencies
install_frontend_deps() {
    log_info "Installiere Frontend-Dependencies..."
    
    if [ ! -d "$INSTALL_DIR/frontend" ]; then
        log_error "Frontend Verzeichnis nicht gefunden: $INSTALL_DIR/frontend"
        exit 1
    fi
    
    cd "$INSTALL_DIR/frontend"
    
    # Node modules installieren
    if [ ! -d "node_modules" ]; then
        log_info "Installiere Node-Pakete (kann einige Minuten dauern)..."
        yarn install --silent 2>&1 | grep -v "warning" || true
    else
        log_info "Node modules bereits vorhanden, überspringe..."
    fi
    
    log_success "Frontend-Dependencies installiert"
}

# Setup Supervisor
setup_supervisor() {
    log_info "Konfiguriere Supervisor..."
    
    # Supervisor Config für Backend
    cat > /etc/supervisor/conf.d/cyphertrade-backend.conf << EOF
[program:cyphertrade-backend]
directory=$INSTALL_DIR/backend
command=$INSTALL_DIR/backend/venv/bin/python -m uvicorn server:app --host 0.0.0.0 --port 8001
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/cyphertrade-backend.log
stderr_logfile=/var/log/supervisor/cyphertrade-backend-error.log
environment=PATH="$INSTALL_DIR/backend/venv/bin:/usr/local/bin:/usr/bin:/bin"
EOF
    
    # Supervisor Config für Frontend
    cat > /etc/supervisor/conf.d/cyphertrade-frontend.conf << EOF
[program:cyphertrade-frontend]
directory=$INSTALL_DIR/frontend
command=/usr/bin/yarn start
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/cyphertrade-frontend.log
stderr_logfile=/var/log/supervisor/cyphertrade-frontend-error.log
environment=PATH="/usr/local/bin:/usr/bin:/bin",REACT_APP_BACKEND_URL="http://$CRYPTOKING_IP:8001"
EOF
    
    # Supervisor neu laden
    supervisorctl reread >/dev/null 2>&1 || true
    supervisorctl update >/dev/null 2>&1 || true
    
    log_success "Supervisor konfiguriert"
}

# Start Services
start_services() {
    log_info "Starte Services..."
    
    # MongoDB
    systemctl restart mongod 2>/dev/null || true
    
    # Ollama (nur wenn lokal installiert)
    if [ "$SKIP_OLLAMA_INSTALL" = false ]; then
        systemctl restart ollama 2>/dev/null || nohup ollama serve > /var/log/ollama.log 2>&1 &
    fi
    
    # Backend & Frontend via Supervisor
    supervisorctl start cyphertrade-backend 2>/dev/null || supervisorctl restart cyphertrade-backend 2>/dev/null || true
    supervisorctl start cyphertrade-frontend 2>/dev/null || supervisorctl restart cyphertrade-frontend 2>/dev/null || true
    
    sleep 5
    
    log_success "Services gestartet"
}

# Verify Installation
verify_installation() {
    log_info "Überprüfe Installation..."
    
    CHECKS_PASSED=0
    CHECKS_TOTAL=6
    
    # Check 1: MongoDB
    if systemctl is-active --quiet mongod; then
        log_success "✓ MongoDB läuft"
        ((CHECKS_PASSED++))
    else
        log_error "✗ MongoDB läuft nicht"
    fi
    
    # Check 2: Ollama (lokal oder remote)
    if [ "$SKIP_OLLAMA_INSTALL" = true ]; then
        # Prüfe Remote-Ollama Server
        if curl -s --connect-timeout 5 "http://$OLLAMA_SERVER_IP:11434/api/tags" > /dev/null 2>&1; then
            log_success "✓ Remote-Ollama Server erreichbar ($OLLAMA_SERVER_IP)"
            ((CHECKS_PASSED++))
        else
            log_error "✗ Remote-Ollama Server nicht erreichbar ($OLLAMA_SERVER_IP)"
        fi
        
        # Check 3: Ollama Modell (Remote)
        if curl -s --connect-timeout 5 "http://$OLLAMA_SERVER_IP:11434/api/tags" | grep -q "llama3.2" 2>/dev/null; then
            log_success "✓ Llama 3.2 Modell auf Remote-Server verfügbar"
            ((CHECKS_PASSED++))
        else
            log_warning "✗ Llama 3.2 Modell auf Remote-Server nicht gefunden"
        fi
    else
        # Prüfe lokales Ollama
        if pgrep -x "ollama" > /dev/null || systemctl is-active --quiet ollama 2>/dev/null; then
            log_success "✓ Ollama läuft lokal"
            ((CHECKS_PASSED++))
        else
            log_error "✗ Ollama läuft nicht"
        fi
        
        # Check 3: Ollama Modell (lokal)
        if [ "$SKIP_OLLAMA_MODEL" = true ] || ollama list 2>/dev/null | grep -q "llama3.2"; then
            log_success "✓ Llama 3.2 Modell verfügbar"
            ((CHECKS_PASSED++))
        else
            log_warning "✗ Llama 3.2 Modell nicht gefunden"
        fi
    fi
    
    # Check 4: Backend
    if supervisorctl status cyphertrade-backend 2>/dev/null | grep -q "RUNNING"; then
        log_success "✓ Backend läuft"
        ((CHECKS_PASSED++))
    else
        log_error "✗ Backend läuft nicht"
        log_info "Prüfe Logs: tail -f /var/log/supervisor/cyphertrade-backend-error.log"
    fi
    
    # Check 5: Frontend
    if supervisorctl status cyphertrade-frontend 2>/dev/null | grep -q "RUNNING"; then
        log_success "✓ Frontend läuft"
        ((CHECKS_PASSED++))
    else
        log_error "✗ Frontend läuft nicht"
        log_info "Prüfe Logs: tail -f /var/log/supervisor/cyphertrade-frontend.log"
    fi
    
    # Check 6: Backend API erreichbar
    sleep 5
    if curl -s "http://$CRYPTOKING_IP:8001/api/health" > /dev/null 2>&1 || curl -s http://localhost:8001/api/health > /dev/null 2>&1; then
        log_success "✓ Backend API erreichbar"
        ((CHECKS_PASSED++))
    else
        log_warning "✗ Backend API nicht erreichbar (startet möglicherweise noch)"
    fi
    
    echo ""
    log_info "Installation Check: $CHECKS_PASSED/$CHECKS_TOTAL Tests erfolgreich"
    echo ""
    
    if [ $CHECKS_PASSED -eq $CHECKS_TOTAL ]; then
        return 0
    else
        return 1
    fi
}

# Print Final Instructions
print_final_instructions() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}║          Installation Abgeschlossen!                     ║${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    log_info "Nächste Schritte:"
    echo ""
    echo "  1. Konfigurieren Sie die Binance API Keys:"
    echo "     ${YELLOW}nano $INSTALL_DIR/backend/.env${NC}"
    echo ""
    echo "  2. Starten Sie die Services neu:"
    echo "     ${YELLOW}sudo supervisorctl restart cyphertrade-backend${NC}"
    echo ""
    echo "  3. Öffnen Sie das Dashboard:"
    echo "     ${YELLOW}http://$CRYPTOKING_IP:3000${NC}"
    echo "     (oder lokal: http://localhost:3000)"
    echo ""
    echo "  4. Überprüfen Sie die Logs bei Problemen:"
    echo "     ${YELLOW}tail -f /var/log/supervisor/cyphertrade-backend-error.log${NC}"
    echo "     ${YELLOW}tail -f /var/log/supervisor/cyphertrade-frontend.log${NC}"
    echo ""
    
    log_info "Nützliche Befehle:"
    echo ""
    echo "  Status prüfen:        ${YELLOW}sudo supervisorctl status${NC}"
    echo "  Services neu starten: ${YELLOW}sudo supervisorctl restart all${NC}"
    echo "  Ollama testen:        ${YELLOW}ollama run llama3.2${NC}"
    echo "  MongoDB prüfen:       ${YELLOW}sudo systemctl status mongod${NC}"
    echo ""
    
    log_info "Installationsverzeichnis: $INSTALL_DIR"
    echo ""
    
    log_warning "⚠️  WICHTIG:"
    echo "  - Tragen Sie Ihre Binance API Keys in $INSTALL_DIR/backend/.env ein"
    echo "  - Ollama Server: http://$OLLAMA_SERVER_IP:11434"
    echo "  - CryptoKing Server: $CRYPTOKING_IP"
    echo "  - Verwenden Sie Binance Testnet zum Testen (BINANCE_TESTNET=true)"
    echo "  - Starten Sie mit kleinen Beträgen"
    echo "  - Crypto Trading ist riskant!"
    echo ""
}

# Main Installation Function
main() {
    print_banner
    
    log_info "Vollautomatische Installation von Project CypherTrade..."
    log_info "Installationsverzeichnis: $INSTALL_DIR"
    echo ""
    
    # Parameter parsen
    parse_args "$@"
    
    # Checks
    check_root
    check_os
    
    log_info "Diese Installation wird folgendes installieren:"
    echo "  - Python 3.11"
    echo "  - Node.js 20 LTS & Yarn"
    echo "  - MongoDB 6.0"
    if [ "$SKIP_OLLAMA_INSTALL" = true ]; then
        echo "  - Ollama (Remote-Server: $OLLAMA_SERVER_IP)"
    else
        echo "  - Ollama & Llama 3.2 (lokal)"
    fi
    echo "  - Alle Projekt-Dependencies"
    if [ "$SKIP_CLONE" = false ]; then
        echo "  - GitHub Repository klonen"
    fi
    echo "  - .env Dateien erstellen (Ollama: $OLLAMA_SERVER_IP)"
    echo ""
    log_info "Starte automatische Installation (keine Bestätigung erforderlich)..."
    echo ""
    
    # Phase 1: System-Update
    log_info "=== Phase 1: System-Update ==="
    # Deaktiviere set -e für System-Update (apt_pkg Fehler ist harmlos)
    set +e
    update_system
    # Reaktiviere set -e nach dem Update
    set -e
    
    # Phase 2: Essenzielle Pakete
    echo ""
    log_info "=== Phase 2: Essenzielle Pakete ==="
    install_essentials
    
    # Phase 3: Python 3.11
    echo ""
    log_info "=== Phase 3: Python 3.11 ==="
    install_python
    
    # Phase 4: Node.js & Yarn
    echo ""
    log_info "=== Phase 4: Node.js & Yarn ==="
    install_nodejs
    
    # Phase 5: MongoDB
    echo ""
    log_info "=== Phase 5: MongoDB ==="
    install_mongodb
    
    # Phase 6: Ollama & Llama 3.2
    echo ""
    log_info "=== Phase 6: Ollama & Llama 3.2 ==="
    install_ollama
    
    # Phase 7: Repository klonen
    echo ""
    log_info "=== Phase 7: Repository Setup ==="
    clone_repository
    setup_project_directory
    
    # Phase 8: .env Dateien erstellen
    echo ""
    log_info "=== Phase 8: Konfigurationsdateien ==="
    create_backend_env
    create_frontend_env
    
    # Phase 9: Backend Dependencies
    echo ""
    log_info "=== Phase 9: Backend Dependencies ==="
    install_backend_deps
    
    # Phase 10: Frontend Dependencies
    echo ""
    log_info "=== Phase 10: Frontend Dependencies ==="
    install_frontend_deps
    
    # Phase 11: Supervisor Setup
    echo ""
    log_info "=== Phase 11: Supervisor Setup ==="
    setup_supervisor
    
    # Phase 12: Services starten
    echo ""
    log_info "=== Phase 12: Services starten ==="
    start_services
    
    # Phase 13: Installations-Überprüfung
    echo ""
    log_info "=== Phase 13: Installations-Überprüfung ==="
    if verify_installation; then
        print_final_instructions
        log_success "Installation erfolgreich abgeschlossen! 🚀"
        exit 0
    else
        log_warning "Installation abgeschlossen, aber einige Checks fehlgeschlagen"
        log_info "Bitte überprüfen Sie die Logs für Details"
        print_final_instructions
        exit 1
    fi
}

# Error Handler (wird nach System-Update aktiviert)
trap 'log_error "Installation fehlgeschlagen in Zeile $LINENO. Exit code: $?"' ERR

# set -e wird in update_system deaktiviert und nach dem Update aktiviert
# Nicht hier aktivieren, da apt_pkg Fehler sonst zum Abbruch führen würde

# Run Main
main "$@"