# Quick Fix für apt_pkg Fehler

Wenn Sie den `apt_pkg` Fehler beim apt-get update sehen, führen Sie diese Befehle aus:

## Schnell-Fix

```bash
# 1. Problem beheben
sudo apt-get install -y python3-apt python3-distutils
sudo mv /etc/apt/apt.conf.d/50command-not-found /etc/apt/apt.conf.d/50command-not-found.disabled 2>/dev/null || true

# 2. Hook deaktivieren
sudo mkdir -p /etc/apt/apt.conf.d
echo 'APT::Update::Post-Invoke-Success "";' | sudo tee /etc/apt/apt.conf.d/99-disable-cnf-update-db

# 3. Update erneut ausführen
sudo apt-get update

# 4. Installation fortsetzen
cd /app
sudo bash install.sh --skip-clone \
  --ollama-server 192.168.178.155 \
  --cryptoking-ip 192.168.178.154
```

## Was ist das Problem?

Der Fehler `ModuleNotFoundError: No module named 'apt_pkg'` kommt von einem APT Hook (`cnf-update-db`), der beim `apt-get update` ausgeführt wird. Dieser Hook ist für die "command-not-found" Funktionalität zuständig, aber nicht kritisch für die Installation.

Das aktualisierte Installationsskript behebt dieses Problem automatisch, indem es:
1. Den Hook deaktiviert
2. Die notwendigen Python-Pakete installiert
3. Fehler-Toleranz beim apt-get update einbaut
