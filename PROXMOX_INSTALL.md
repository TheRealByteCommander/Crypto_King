# Proxmox Container Installation

Installations-Anleitung für Proxmox Container (CT).

## Voraussetzungen

- Proxmox Container (Ubuntu 22.04 oder neuer)
- Root-Zugriff auf den Container
- Internetverbindung
- GitHub Repository URL

## Installation

### 1. SSH in den Container verbinden

```bash
# Via Proxmox Web-Interface oder SSH
ssh root@<CT_IP_ADDRESS>
```

### 2. Repository klonen und installieren

**Option A: Vollautomatische Installation (Empfohlen)**

```bash
# System aktualisieren
apt-get update && apt-get upgrade -y

# Git installieren (falls nicht vorhanden)
apt-get install -y git

# Repository klonen
cd /tmp
git clone <GITHUB_REPO_URL> /app

# In das Verzeichnis wechseln
cd /app

# Installationsskript ausführbar machen
chmod +x install.sh

# Vollautomatische Installation starten
sudo bash install.sh
```

**Option B: Mit angegebenen Parametern**

```bash
# System aktualisieren
apt-get update && apt-get upgrade -y

# Git installieren
apt-get install -y git

# Repository klonen mit Installationsverzeichnis
cd /tmp
git clone <GITHUB_REPO_URL> /app

# Installation mit Remote-Ollama Server
cd /app
chmod +x install.sh
sudo bash install.sh \
  --install-dir /app \
  --ollama-server 192.168.178.155 \
  --cryptoking-ip 192.168.178.154
```

**Option C: Wenn Repository bereits vorhanden**

```bash
# Wenn Repo bereits geklont ist
cd /app
chmod +x install.sh
sudo bash install.sh --skip-clone \
  --ollama-server 192.168.178.155 \
  --cryptoking-ip 192.168.178.154
```

## Installation mit GitHub Repository

Ersetzen Sie `<GITHUB_REPO_URL>` mit Ihrer Repository-URL:

```bash
# Beispiel: GitHub Repository
git clone https://github.com/IhrUsername/Crypto_King.git /app

# Oder mit SSH (wenn SSH-Keys konfiguriert)
git clone git@github.com:IhrUsername/Crypto_King.git /app
```

## Komplette Installation (Einzeiler)

```bash
apt-get update && apt-get upgrade -y && \
apt-get install -y git && \
cd /tmp && \
git clone <GITHUB_REPO_URL> /app && \
cd /app && \
chmod +x install.sh && \
sudo bash install.sh --ollama-server 192.168.178.155 --cryptoking-ip 192.168.178.154
```

## Nach der Installation

### 1. Binance API Keys konfigurieren

```bash
nano /app/backend/.env
```

Tragen Sie Ihre Binance API Keys ein:
```env
BINANCE_API_KEY="your_api_key_here"
BINANCE_API_SECRET="your_api_secret_here"
BINANCE_TESTNET=true
```

### 2. Services neu starten

```bash
sudo supervisorctl restart cyphertrade-backend
```

### 3. Status überprüfen

```bash
# Alle Services prüfen
sudo supervisorctl status

# Backend API testen
curl http://192.168.178.154:8001/api/health

# Frontend testen
curl http://192.168.178.154:3000
```

### 4. Dashboard öffnen

Öffnen Sie im Browser:
- Frontend: `http://192.168.178.154:3000`
- Backend API: `http://192.168.178.154:8001/api/health`

## Firewall Konfiguration (Proxmox)

Falls Sie eine Firewall verwenden, öffnen Sie die Ports:

```bash
# UFW (Ubuntu Firewall)
ufw allow 8001/tcp  # Backend API
ufw allow 3000/tcp  # Frontend
```

## Troubleshooting

### Repository nicht klonbar

```bash
# Git Konfiguration prüfen
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# SSH Keys für GitHub einrichten (falls nötig)
ssh-keygen -t ed25519 -C "your.email@example.com"
cat ~/.ssh/id_ed25519.pub
# Fügen Sie den öffentlichen Key zu GitHub hinzu
```

### Installation schlägt fehl

```bash
# Logs prüfen
tail -f /var/log/supervisor/cyphertrade-backend-error.log
tail -f /var/log/supervisor/cyphertrade-frontend.log

# MongoDB Status
sudo systemctl status mongod

# Remote-Ollama Server prüfen
curl http://192.168.178.155:11434/api/tags
```

### Services starten nicht

```bash
# Supervisor neu starten
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart all

# Manuell starten (für Tests)
cd /app/backend
source venv/bin/activate
python -m uvicorn server:app --host 0.0.0.0 --port 8001
```

## Systemanforderungen

- **OS**: Ubuntu 22.04 LTS oder neuer
- **RAM**: Mindestens 2 GB (4 GB empfohlen)
- **Disk**: Mindestens 20 GB freier Speicherplatz
- **CPU**: 2 Cores (4+ empfohlen)

## Nützliche Befehle

```bash
# Services verwalten
sudo supervisorctl status
sudo supervisorctl restart all
sudo supervisorctl stop all
sudo supervisorctl start all

# Logs ansehen
tail -f /var/log/supervisor/cyphertrade-backend-error.log
tail -f /var/log/supervisor/cyphertrade-frontend.log

# Installation neu ausführen
cd /app
sudo bash install.sh --skip-clone --ollama-server 192.168.178.155 --cryptoking-ip 192.168.178.154
```

## Wichtige Hinweise

1. **Ollama Server**: Wird NICHT lokal installiert (verwendet Remote-Server)
2. **CryptoKing IP**: 192.168.178.154
3. **Ollama Server IP**: 192.168.178.155
4. **Installationsverzeichnis**: `/app` (Standard)
5. **Vollautomatisch**: Keine Benutzerbestätigungen erforderlich

## GitHub Repository Setup

Wenn Sie das Repository noch nicht auf GitHub haben:

1. **Repository erstellen** auf GitHub
2. **Lokal pushen**:
```bash
cd /pfad/zu/Ihrem/Repo
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/IhrUsername/Crypto_King.git
git push -u origin main
```

3. **Auf Proxmox klonen** (siehe oben)
