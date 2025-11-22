# Quick Fix für Node.js Installation

Wenn die Node.js Installation Probleme hat, führen Sie dieses Skript aus:

## Schnell-Reparatur

```bash
# Im Proxmox Container (als root)
cd /app
chmod +x fix-nodejs.sh
sudo bash fix-nodejs.sh
```

## Manuelle Reparatur (wenn Skript nicht funktioniert)

```bash
# 1. Alte Installation entfernen
apt-get remove -y nodejs npm
rm -rf /etc/apt/sources.list.d/nodesource.list

# 2. System aktualisieren
apt-get update

# 3. Node.js 20 LTS installieren
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# 4. npm prüfen und installieren falls nötig
npm --version || apt-get install -y npm

# 5. Yarn installieren
npm install -g yarn
```

## Installation fortsetzen

Nach der Reparatur können Sie die Installation fortsetzen:

```bash
cd /app
sudo bash install.sh --skip-clone \
  --ollama-server 192.168.178.155 \
  --cryptoking-ip 192.168.178.154
```

Oder starten Sie nur die fehlenden Teile:

```bash
# Nur Frontend Dependencies installieren
cd /app/frontend
yarn install
```
