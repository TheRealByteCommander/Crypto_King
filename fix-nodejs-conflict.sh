#!/bin/bash
# Quick-Fix für libnode-dev Konflikt bei Node.js Installation

echo "=== Behebe libnode-dev Konflikt ==="

# Entferne konfliktierende Pakete
echo "[INFO] Entferne alte Node.js Pakete..."
apt-get remove -y nodejs npm libnode-dev libnode72 2>/dev/null || true
apt-get purge -y nodejs npm libnode-dev libnode72 2>/dev/null || true

# Force remove falls nötig
dpkg --remove --force-remove-reinstreq libnode-dev libnode72 2>/dev/null || true

# Paket-Cache bereinigen
echo "[INFO] Bereinige Paket-Cache..."
apt-get update -qq 2>&1 | grep -vE "(apt_pkg|Problem)" || true
dpkg --configure -a 2>/dev/null || true

# Autoremove
apt-get autoremove -y -qq 2>/dev/null || true
apt-get autoclean -qq 2>/dev/null || true

echo "[SUCCESS] libnode-dev Konflikt behoben!"
echo "[INFO] Sie können jetzt die Installation fortsetzen:"
echo "  cd /app && git pull && sudo bash install.sh --skip-clone --ollama-server 192.168.178.155 --cryptoking-ip 192.168.178.154"

