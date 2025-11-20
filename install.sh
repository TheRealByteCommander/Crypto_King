#!/bin/bash

################################################################################
# Project CypherTrade - Automatisches Installations-Skript für Ubuntu 22.04
# 
# Dieses Skript installiert:
# - Python 3.11+ mit allen Dependencies
# - Node.js 18+ und Yarn
# - MongoDB
# - Ollama mit llama3.2
# - Alle Projekt-Dependencies
# - Konfiguriert das System
#
# Verwendung: sudo bash install.sh
################################################################################

set -e  # Exit bei Fehler

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
    echo -e "${BLUE}║          ${GREEN}Project CypherTrade Installer${BLUE}                  ║${NC}"
    echo -e "${BLUE}║          ${YELLOW}AI-Powered Crypto Trading Bot${BLUE}                 ║${NC}"
    echo -e "${BLUE}║                                                           ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Root Check
check_root() {
    if [ "$EUID" -ne 0 ]; then 
        log_error "Bitte als root ausführen: sudo bash install.sh"
        exit 1
    fi
    log_success "Root-Rechte vorhanden"
}

# OS Check
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
            log_warning "Ubuntu Version $VER nicht getestet, fahre fort..."
        fi
    else
        log_warning "Nicht-Ubuntu System erkannt: $OS. Installation könnte fehlschlagen."
        read -p "Trotzdem fortfahren? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# System Update
update_system() {
    log_info "Aktualisiere System-Pakete..."
    apt-get update -qq
    apt-get upgrade -y -qq
    log_success "System aktualisiert"
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
        add-apt-repository ppa:deadsnakes/ppa -y
        apt-get update -qq
        apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip
        
        # Python 3.11 als Standard setzen
        update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
        
        log_success "Python 3.11 installiert"
    fi
    
    # Pip upgraden
    python3.11 -m pip install --upgrade pip setuptools wheel
}

# Install Node.js and Yarn
install_nodejs() {
    log_info "Prüfe Node.js Installation..."
    
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        MAJOR_VERSION=$(echo $NODE_VERSION | cut -d'.' -f1 | sed 's/v//')
        
        if [ "$MAJOR_VERSION" -ge 18 ]; then
            log_success "Node.js bereits installiert (Version: $NODE_VERSION)"
        else
            log_warning "Node.js Version zu alt ($NODE_VERSION), aktualisiere..."
            curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
            apt-get install -y nodejs
        fi
    else
        log_info "Installiere Node.js 18..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
        apt-get install -y nodejs
        log_success "Node.js installiert"
    fi
    
    # Yarn installieren
    if ! command -v yarn &> /dev/null; then
        log_info "Installiere Yarn..."
        npm install -g yarn
        log_success "Yarn installiert"
    else
        log_success "Yarn bereits installiert"
    fi
}

# Install MongoDB
install_mongodb() {
    log_info "Prüfe MongoDB Installation..."
    
    if systemctl is-active --quiet mongod; then
        log_success "MongoDB läuft bereits"
        return
    fi
    
    if command -v mongod &> /dev/null; then
        log_info "MongoDB installiert, starte Service..."
        systemctl start mongod
        systemctl enable mongod
        log_success "MongoDB Service gestartet"
        return
    fi
    
    log_info "Installiere MongoDB..."
    
    # MongoDB GPG Key
    curl -fsSL https://www.mongodb.org/static/pgp/server-6.0.asc | \
        gpg -o /usr/share/keyrings/mongodb-server-6.0.gpg --dearmor
    
    # MongoDB Repository
    echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-6.0.gpg ] \
        https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | \
        tee /etc/apt/sources.list.d/mongodb-org-6.0.list
    
    apt-get update -qq
    apt-get install -y mongodb-org
    
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

# Install Ollama
install_ollama() {
    log_info "Prüfe Ollama Installation..."
    
    if command -v ollama &> /dev/null; then
        log_success "Ollama bereits installiert"
    else
        log_info "Installiere Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
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
    
    # Llama3.2 herunterladen
    log_info "Lade Llama 3.2 Modell herunter (dies kann einige Minuten dauern)..."
    
    if ollama list | grep -q "llama3.2"; then
        log_success "Llama 3.2 bereits heruntergeladen"
    else
        ollama pull llama3.2
        log_success "Llama 3.2 erfolgreich heruntergeladen"
    fi
}

# Setup Project Directory
setup_project_directory() {
    log_info "Prüfe Projekt-Verzeichnis..."
    
    PROJECT_DIR="/app"
    
    if [ ! -d "$PROJECT_DIR" ]; then
        log_error "Projekt-Verzeichnis $PROJECT_DIR nicht gefunden!"
        log_info "Bitte führen Sie das Skript aus dem Projekt-Verzeichnis aus"
        exit 1
    fi
    
    cd $PROJECT_DIR
    log_success "Projekt-Verzeichnis: $PROJECT_DIR"
}

# Install Backend Dependencies
install_backend_deps() {
    log_info "Installiere Backend-Dependencies..."
    
    cd /app/backend
    
    # Virtual Environment erstellen falls nicht vorhanden
    if [ ! -d "venv" ]; then
        log_info "Erstelle Python Virtual Environment..."
        python3.11 -m venv venv
    fi
    
    # Aktiviere venv und installiere Dependencies
    source venv/bin/activate
    
    log_info "Installiere Python-Pakete..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    deactivate
    
    log_success "Backend-Dependencies installiert"
}

# Install Frontend Dependencies
install_frontend_deps() {
    log_info "Installiere Frontend-Dependencies..."
    
    cd /app/frontend
    
    # Node modules installieren
    if [ ! -d "node_modules" ]; then
        log_info "Installiere Node-Pakete (kann einige Minuten dauern)..."
        yarn install --silent
    else
        log_info "Node modules bereits vorhanden, überspringe..."
    fi
    
    log_success "Frontend-Dependencies installiert"
}

# Configure Environment
configure_env() {
    log_info "Konfiguriere Umgebungsvariablen..."
    
    # Backend .env prüfen
    if [ ! -f "/app/backend/.env" ]; then
        log_error "Backend .env Datei nicht gefunden!"
        exit 1
    fi
    
    # Frontend .env prüfen
    if [ ! -f "/app/frontend/.env" ]; then
        log_error "Frontend .env Datei nicht gefunden!"
        exit 1
    fi
    
    log_warning "Bitte konfigurieren Sie die folgenden Dateien:"
    echo ""
    echo "  1. /app/backend/.env"
    echo "     - BINANCE_API_KEY"
    echo "     - BINANCE_API_SECRET"
    echo ""
    
    read -p "Möchten Sie jetzt die API Keys eingeben? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Binance API Key: " BINANCE_KEY
        read -p "Binance API Secret: " BINANCE_SECRET
        
        # Update .env
        sed -i "s/BINANCE_API_KEY=\".*\"/BINANCE_API_KEY=\"$BINANCE_KEY\"/" /app/backend/.env
        sed -i "s/BINANCE_API_SECRET=\".*\"/BINANCE_API_SECRET=\"$BINANCE_SECRET\"/" /app/backend/.env
        
        log_success "API Keys konfiguriert"
    else
        log_warning "Bitte konfigurieren Sie die API Keys manuell in /app/backend/.env"
    fi
}

# Setup Supervisor
setup_supervisor() {
    log_info "Konfiguriere Supervisor..."
    
    # Supervisor Config für Backend
    cat > /etc/supervisor/conf.d/cyphertrade-backend.conf << 'EOF'
[program:cyphertrade-backend]
directory=/app/backend
command=/app/backend/venv/bin/python -m uvicorn server:app --host 0.0.0.0 --port 8001
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/cyphertrade-backend.log
stderr_logfile=/var/log/supervisor/cyphertrade-backend-error.log
environment=PATH="/app/backend/venv/bin"
EOF
    
    # Supervisor Config für Frontend
    cat > /etc/supervisor/conf.d/cyphertrade-frontend.conf << 'EOF'
[program:cyphertrade-frontend]
directory=/app/frontend
command=/usr/bin/yarn start
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/cyphertrade-frontend.log
stderr_logfile=/var/log/supervisor/cyphertrade-frontend-error.log
environment=PATH="/usr/local/bin:/usr/bin:/bin"
EOF
    
    # Supervisor neu laden
    supervisorctl reread
    supervisorctl update
    
    log_success "Supervisor konfiguriert"
}

# Start Services
start_services() {
    log_info "Starte Services..."
    
    # MongoDB
    systemctl restart mongod
    
    # Ollama
    systemctl restart ollama 2>/dev/null || nohup ollama serve > /var/log/ollama.log 2>&1 &
    
    # Backend & Frontend via Supervisor
    supervisorctl restart cyphertrade-backend
    supervisorctl restart cyphertrade-frontend
    
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
    
    # Check 2: Ollama
    if pgrep -x "ollama" > /dev/null || systemctl is-active --quiet ollama; then
        log_success "✓ Ollama läuft"
        ((CHECKS_PASSED++))
    else
        log_error "✗ Ollama läuft nicht"
    fi
    
    # Check 3: Ollama Modell
    if ollama list 2>/dev/null | grep -q "llama3.2"; then
        log_success "✓ Llama 3.2 Modell verfügbar"
        ((CHECKS_PASSED++))
    else
        log_error "✗ Llama 3.2 Modell nicht gefunden"
    fi
    
    # Check 4: Backend
    if supervisorctl status cyphertrade-backend | grep -q "RUNNING"; then
        log_success "✓ Backend läuft"
        ((CHECKS_PASSED++))
    else
        log_error "✗ Backend läuft nicht"
        log_info "Prüfe Logs: tail -f /var/log/supervisor/cyphertrade-backend-error.log"
    fi
    
    # Check 5: Frontend
    if supervisorctl status cyphertrade-frontend | grep -q "RUNNING"; then
        log_success "✓ Frontend läuft"
        ((CHECKS_PASSED++))
    else
        log_error "✗ Frontend läuft nicht"
        log_info "Prüfe Logs: tail -f /var/log/supervisor/cyphertrade-frontend-error.log"
    fi
    
    # Check 6: Backend API erreichbar
    sleep 5
    if curl -s http://localhost:8001/api/health > /dev/null 2>&1; then
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
    echo "     ${YELLOW}nano /app/backend/.env${NC}"
    echo ""
    echo "  2. Starten Sie die Services neu:"
    echo "     ${YELLOW}sudo supervisorctl restart cyphertrade-backend${NC}"
    echo ""
    echo "  3. Öffnen Sie das Dashboard:"
    echo "     ${YELLOW}http://localhost:3000${NC}"
    echo ""
    echo "  4. Überprüfen Sie die Logs bei Problemen:"
    echo "     ${YELLOW}tail -f /var/log/supervisor/cyphertrade-backend-error.log${NC}"
    echo "     ${YELLOW}tail -f /var/log/supervisor/cyphertrade-frontend.log${NC}"
    echo ""
    
    log_info "Nützliche Befehle:"
    echo ""
    echo "  Status prüfen:     ${YELLOW}sudo supervisorctl status${NC}"
    echo "  Services neu starten: ${YELLOW}sudo supervisorctl restart all${NC}"
    echo "  Ollama testen:     ${YELLOW}ollama run llama3.2${NC}"
    echo "  MongoDB prüfen:    ${YELLOW}sudo systemctl status mongod${NC}"
    echo ""
    
    log_info "Dokumentation:"
    echo ""
    echo "  - README:           /app/frontend/README.md"
    echo "  - Ollama Setup:     /app/OLLAMA_SETUP.md"
    echo "  - Agent Config:     /app/AGENT_CONFIG_GUIDE.md"
    echo ""
    
    log_warning "⚠️  WICHTIG:"
    echo "  - Verwenden Sie Binance Testnet zum Testen (BINANCE_TESTNET=true)"
    echo "  - Starten Sie mit kleinen Beträgen"
    echo "  - Crypto Trading ist riskant!"
    echo ""
}

# Main Installation Function
main() {
    print_banner
    
    log_info "Starte Installation von Project CypherTrade..."
    echo ""
    
    check_root
    check_os
    
    log_info "Diese Installation wird folgendes installieren:"
    echo "  - Python 3.11"
    echo "  - Node.js 18 & Yarn"
    echo "  - MongoDB 6.0"
    echo "  - Ollama & Llama 3.2"
    echo "  - Alle Projekt-Dependencies"
    echo ""
    
    read -p "Fortfahren? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Installation abgebrochen"
        exit 0
    fi
    
    echo ""
    log_info "=== Phase 1: System-Update ==="
    update_system
    
    echo ""
    log_info "=== Phase 2: Essenzielle Pakete ==="
    install_essentials
    
    echo ""
    log_info "=== Phase 3: Python 3.11 ==="
    install_python
    
    echo ""
    log_info "=== Phase 4: Node.js & Yarn ==="
    install_nodejs
    
    echo ""
    log_info "=== Phase 5: MongoDB ==="
    install_mongodb
    
    echo ""
    log_info "=== Phase 6: Ollama & Llama 3.2 ==="
    install_ollama
    
    echo ""
    log_info "=== Phase 7: Projekt-Setup ==="
    setup_project_directory
    
    echo ""
    log_info "=== Phase 8: Backend Dependencies ==="
    install_backend_deps
    
    echo ""
    log_info "=== Phase 9: Frontend Dependencies ==="
    install_frontend_deps
    
    echo ""
    log_info "=== Phase 10: Konfiguration ==="
    configure_env
    
    echo ""
    log_info "=== Phase 11: Supervisor Setup ==="
    setup_supervisor
    
    echo ""
    log_info "=== Phase 12: Services starten ==="
    start_services
    
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

# Error Handler
trap 'log_error "Installation fehlgeschlagen in Zeile $LINENO. Exit code: $?"' ERR

# Run Main
main "$@"
