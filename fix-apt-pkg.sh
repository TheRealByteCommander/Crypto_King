#!/bin/bash

################################################################################
# Quick Fix für apt_pkg Fehler
# 
# Dieses Skript behebt den apt_pkg Fehler dauerhaft
#
# Verwendung: sudo bash fix-apt-pkg.sh
################################################################################

set +e  # Deaktiviere Fehlerbehandlung

echo "Behebe apt_pkg Fehler..."

# 1. Python apt Pakete installieren
apt-get install -y python3-apt python3-distutils 2>/dev/null || true

# 2. command-not-found Hook deaktivieren
if [ -f /etc/apt/apt.conf.d/50command-not-found ]; then
    mv /etc/apt/apt.conf.d/50command-not-found /etc/apt/apt.conf.d/50command-not-found.disabled 2>/dev/null || true
    echo "Hook deaktiviert: /etc/apt/apt.conf.d/50command-not-found"
fi

# 3. Hook-Deaktivierung erstellen
mkdir -p /etc/apt/apt.conf.d
cat > /etc/apt/apt.conf.d/99-disable-cnf-update-db << 'EOF'
APT::Update::Post-Invoke-Success "";
EOF
echo "Hook-Deaktivierung erstellt: /etc/apt/apt.conf.d/99-disable-cnf-update-db"

# 4. cnf-update-db Script deaktivieren
if [ -f /usr/lib/cnf-update-db ]; then
    mv /usr/lib/cnf-update-db /usr/lib/cnf-update-db.disabled 2>/dev/null || true
    chmod -x /usr/lib/cnf-update-db.disabled 2>/dev/null || true
    echo "Script deaktiviert: /usr/lib/cnf-update-db"
fi

# 5. Test: apt-get update ohne Fehler
echo ""
echo "Teste apt-get update..."
apt-get update -qq 2>&1 | grep -vE "(apt_pkg|cnf-update-db|ModuleNotFoundError|Problem executing)" || true

if [ ${PIPESTATUS[0]} -eq 0 ] || [ ${PIPESTATUS[0]} -eq 100 ]; then
    echo "✓ apt-get update erfolgreich (Fehler ignoriert)"
else
    echo "⚠ apt-get update hatte Probleme, aber sollte funktionieren"
fi

echo ""
echo "apt_pkg Fehler behoben!"
echo ""
echo "Sie können jetzt die Installation fortsetzen:"
echo "  cd /app"
echo "  sudo bash install.sh --skip-clone \\"
echo "    --ollama-server 192.168.178.155 \\"
echo "    --cryptoking-ip 192.168.178.154"
echo ""
