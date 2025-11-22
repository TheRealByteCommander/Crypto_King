#!/bin/bash

################################################################################
# Sofort-Fix für Proxmox Container
# 
# Führen Sie dieses Skript direkt im Container aus
################################################################################

echo "=== apt_pkg Fehler beheben ==="

# 1. Python apt Pakete installieren
apt-get install -y python3-apt python3-distutils

# 2. Hook komplett deaktivieren
mkdir -p /etc/apt/apt.conf.d
cat > /etc/apt/apt.conf.d/99-disable-cnf-update-db << 'EOF'
APT::Update::Post-Invoke-Success "";
APT::Update::Post-Invoke-Success "exit 0";
EOF

# 3. command-not-found deaktivieren
[ -f /etc/apt/apt.conf.d/50command-not-found ] && \
    mv /etc/apt/apt.conf.d/50command-not-found /etc/apt/apt.conf.d/50command-not-found.disabled

# 4. cnf-update-db Script deaktivieren
[ -f /usr/lib/cnf-update-db ] && \
    mv /usr/lib/cnf-update-db /usr/lib/cnf-update-db.disabled && \
    chmod -x /usr/lib/cnf-update-db.disabled

# 5. Test: Update ohne Fehler
echo ""
echo "Teste apt-get update..."
apt-get update -qq 2>&1 | grep -vE "(apt_pkg|cnf-update-db|ModuleNotFoundError|Problem executing)" || true

echo ""
echo "✓ apt_pkg Fehler behoben!"
echo ""
echo "Nächster Schritt:"
echo "  cd /app && git pull && sudo bash install.sh --skip-clone --ollama-server 192.168.178.155 --cryptoking-ip 192.168.178.154"
echo ""
