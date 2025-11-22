#!/bin/bash

################################################################################
# Quick Fix: Node.js und npm reparieren
# 
# Dieses Skript behebt Node.js Installation Probleme:
# - Entfernt alte Node.js Versionen
# - Installiert Node.js 20 LTS
# - Installiert npm falls fehlend
# - Installiert Yarn
#
# Verwendung: sudo bash fix-nodejs.sh
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Root Check
if [ "$EUID" -ne 0 ]; then 
    log_error "Bitte als root ausführen: sudo bash fix-nodejs.sh"
    exit 1
fi

log_info "Starte Node.js Reparatur..."

# Locale setzen
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Alte Node.js Version entfernen
log_info "Entferne alte Node.js Installationen..."
apt-get remove -y nodejs npm 2>/dev/null || true
apt-get purge -y nodejs npm 2>/dev/null || true
rm -rf /etc/apt/sources.list.d/nodesource.list 2>/dev/null || true
apt-get autoremove -y -qq

# Alte npm Installationen entfernen
rm -rf /usr/local/lib/node_modules 2>/dev/null || true
rm -rf /usr/local/bin/npm 2>/dev/null || true
rm -rf /usr/local/bin/node 2>/dev/null || true

# System aktualisieren
log_info "Aktualisiere Paketlisten..."
apt-get update -qq

# Node.js 20 LTS installieren
log_info "Installiere Node.js 20 LTS..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash - 2>&1 | grep -v "DEPRECATION" || true

# Node.js installieren
log_info "Installiere Node.js..."
apt-get install -y -qq nodejs

# Prüfe Installation
NODE_VERSION=$(node --version 2>/dev/null || echo "nicht installiert")
NPM_VERSION=$(npm --version 2>/dev/null || echo "nicht installiert")

if [ "$NODE_VERSION" != "nicht installiert" ]; then
    log_success "Node.js installiert: $NODE_VERSION"
else
    log_error "Node.js Installation fehlgeschlagen!"
    exit 1
fi

if [ "$NPM_VERSION" != "nicht installiert" ]; then
    log_success "npm installiert: $NPM_VERSION"
else
    log_warning "npm nicht gefunden, installiere separat..."
    apt-get install -y -qq npm
    NPM_VERSION=$(npm --version 2>/dev/null || echo "nicht installiert")
    if [ "$NPM_VERSION" != "nicht installiert" ]; then
        log_success "npm installiert: $NPM_VERSION"
    else
        log_error "npm Installation fehlgeschlagen!"
        exit 1
    fi
fi

# Yarn installieren
log_info "Installiere Yarn..."
if ! command -v yarn &> /dev/null; then
    npm install -g yarn --silent 2>&1 | grep -v "npm WARN" || true
    YARN_VERSION=$(yarn --version 2>/dev/null || echo "unknown")
    if [ "$YARN_VERSION" != "unknown" ]; then
        log_success "Yarn installiert: $YARN_VERSION"
    else
        log_warning "Yarn Installation hat Probleme. Versuche manuell..."
        npm install -g yarn
    fi
else
    YARN_VERSION=$(yarn --version 2>/dev/null || echo "unknown")
    log_success "Yarn bereits installiert: $YARN_VERSION"
fi

echo ""
log_success "Node.js Reparatur abgeschlossen!"
echo ""
log_info "Installierte Versionen:"
echo "  Node.js: $NODE_VERSION"
echo "  npm: $NPM_VERSION"
echo "  Yarn: $YARN_VERSION"
echo ""
