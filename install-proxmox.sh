#!/bin/bash

################################################################################
# Proxmox Container Installation Script
# 
# Dieses Skript führt eine vollautomatische Installation auf einem
# Proxmox Container (CT) durch.
#
# Verwendung:
#   bash install-proxmox.sh [GITHUB_REPO_URL] [OPTIONS]
#
# Beispiel:
#   bash install-proxmox.sh https://github.com/user/repo.git
#   bash install-proxmox.sh https://github.com/user/repo.git --install-dir /opt/cryptoking
################################################################################

set -e

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Standardwerte
GITHUB_REPO_URL=""
INSTALL_DIR="/app"
OLLAMA_SERVER_IP="192.168.178.155"
CRYPTOKING_IP="192.168.178.154"

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

# Hilfe anzeigen
show_help() {
    echo "Verwendung: bash install-proxmox.sh [GITHUB_REPO_URL] [OPTIONS]"
    echo ""
    echo "Parameter:"
    echo "  GITHUB_REPO_URL         GitHub Repository URL (erforderlich)"
    echo ""
    echo "Optionen:"
    echo "  --install-dir DIR       Installationsverzeichnis (Standard: /app)"
    echo "  --ollama-server IP      Ollama Server IP (Standard: 192.168.178.155)"
    echo "  --cryptoking-ip IP      CryptoKing Server IP (Standard: 192.168.178.154)"
    echo "  --help                  Zeige diese Hilfe"
    echo ""
    echo "Beispiele:"
    echo "  bash install-proxmox.sh https://github.com/user/repo.git"
    echo "  bash install-proxmox.sh https://github.com/user/repo.git --install-dir /opt/cryptoking"
    exit 0
}

# Parameter parsen
if [ $# -eq 0 ] || [ "$1" == "--help" ]; then
    show_help
fi

# Erster Parameter ist die GitHub URL
GITHUB_REPO_URL="$1"
shift

# Weitere Parameter parsen
while [[ $# -gt 0 ]]; do
    case $1 in
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --ollama-server)
            OLLAMA_SERVER_IP="$2"
            shift 2
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

# Prüfen ob GitHub URL angegeben wurde
if [ -z "$GITHUB_REPO_URL" ]; then
    log_error "GitHub Repository URL ist erforderlich!"
    show_help
fi

log_info "Starte Proxmox Container Installation..."
log_info "Repository: $GITHUB_REPO_URL"
log_info "Installationsverzeichnis: $INSTALL_DIR"
log_info "Ollama Server: $OLLAMA_SERVER_IP"
log_info "CryptoKing IP: $CRYPTOKING_IP"
echo ""

# Root Check
if [ "$EUID" -ne 0 ]; then 
    log_error "Bitte als root ausführen: sudo bash install-proxmox.sh"
    exit 1
fi

# System aktualisieren
log_info "Aktualisiere System..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
log_success "System aktualisiert"

# Git installieren
log_info "Installiere Git..."
if command -v git &> /dev/null; then
    log_success "Git bereits installiert"
else
    apt-get install -y -qq git
    log_success "Git installiert"
fi

# Repository klonen
log_info "Klone Repository von $GITHUB_REPO_URL..."
if [ -d "$INSTALL_DIR" ] && [ -d "$INSTALL_DIR/.git" ]; then
    log_warning "Verzeichnis $INSTALL_DIR existiert bereits und ist ein Git-Repo"
    log_info "Überspringe Clone. Verwenden Sie --skip-clone wenn Sie das Repo aktualisieren möchten"
else
    # Entferne existierendes Verzeichnis falls vorhanden
    if [ -d "$INSTALL_DIR" ]; then
        log_warning "Verzeichnis $INSTALL_DIR existiert bereits. Überschreibe..."
        rm -rf "$INSTALL_DIR"
    fi
    
    # Erstelle übergeordnetes Verzeichnis falls nötig
    mkdir -p "$(dirname "$INSTALL_DIR")"
    
    # Klone Repository
    git clone "$GITHUB_REPO_URL" "$INSTALL_DIR" || {
        log_error "Konnte Repository nicht klonen. Bitte URL und Netzwerkverbindung prüfen."
        exit 1
    }
    log_success "Repository erfolgreich geklont"
fi

# Installationsskript ausführbar machen
log_info "Installationsskript vorbereiten..."
cd "$INSTALL_DIR"
chmod +x install.sh
log_success "Installationsskript bereit"

# Hauptinstallation starten
log_info "Starte Hauptinstallation..."
echo ""
bash install.sh \
    --skip-clone \
    --install-dir "$INSTALL_DIR" \
    --ollama-server "$OLLAMA_SERVER_IP" \
    --cryptoking-ip "$CRYPTOKING_IP"

log_success "Proxmox Container Installation abgeschlossen!"
echo ""
log_info "Nächste Schritte:"
echo "  1. Konfigurieren Sie die Binance API Keys:"
echo "     nano $INSTALL_DIR/backend/.env"
echo ""
echo "  2. Services neu starten:"
echo "     sudo supervisorctl restart cyphertrade-backend"
echo ""
echo "  3. Dashboard öffnen:"
echo "     http://$CRYPTOKING_IP:3000"
echo ""
