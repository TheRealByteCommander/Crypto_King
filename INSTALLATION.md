# Installation Guide - Project CypherTrade

Vollständige Installations-Anleitung für Ubuntu 22.04 / 20.04 / 24.04

## 🚀 Automatische Installation (Empfohlen)

### Voraussetzungen

- **Ubuntu 22.04 LTS** (oder 20.04 / 24.04)
- **Root-Zugriff** (sudo)
- **Mindestens 4 GB RAM**
- **Mindestens 20 GB freier Speicherplatz**
- **Internetverbindung**

### Schritt 1: Repository klonen oder entpacken

Wenn Sie das Projekt noch nicht haben:

```bash
# Option A: Via Git
git clone <repository-url> /app
cd /app

# Option B: Bereits vorhanden
cd /app
```

### Schritt 2: Installations-Skript ausführen

```bash
sudo bash install.sh
```

Das Skript wird automatisch:
- ✅ System aktualisieren
- ✅ Python 3.11 installieren
- ✅ Node.js 18 & Yarn installieren
- ✅ MongoDB 6.0 installieren und konfigurieren
- ✅ Ollama & Llama 3.2 installieren
- ✅ Alle Backend-Dependencies installieren
- ✅ Alle Frontend-Dependencies installieren
- ✅ Supervisor konfigurieren
- ✅ Services starten

**Installationsdauer:** Ca. 10-20 Minuten (abhängig von Internetgeschwindigkeit)

### Schritt 3: Binance API Keys konfigurieren

Nach der Installation:

```bash
nano /app/backend/.env
```

Tragen Sie Ihre Binance API Keys ein:

```env
BINANCE_API_KEY="your_api_key_here"
BINANCE_API_SECRET="your_api_secret_here"
BINANCE_TESTNET=true  # true für Testnet, false für Live
```

**Speichern:** `Ctrl+O`, `Enter`, `Ctrl+X`

### Schritt 4: Services neu starten

```bash
sudo supervisorctl restart cyphertrade-backend
```

### Schritt 5: Dashboard öffnen

```bash
# Lokal
http://localhost:3000

# Remote (ersetzen Sie IP)
http://YOUR_SERVER_IP:3000
```

## 🛠️ Manuelle Installation

Falls das automatische Skript nicht funktioniert:

### 1. System-Update

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### 2. Python 3.11 installieren

```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
python3.11 -m pip install --upgrade pip
```

### 3. Node.js & Yarn installieren

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash -
sudo apt-get install -y nodejs
sudo npm install -g yarn
```

### 4. MongoDB installieren

```bash
# GPG Key
curl -fsSL https://www.mongodb.org/static/pgp/server-6.0.asc | \
    sudo gpg -o /usr/share/keyrings/mongodb-server-6.0.gpg --dearmor

# Repository
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-6.0.gpg ] \
    https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | \
    sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list

# Installation
sudo apt-get update
sudo apt-get install -y mongodb-org

# Starten
sudo systemctl start mongod
sudo systemctl enable mongod
```

### 5. Ollama installieren

```bash
curl -fsSL https://ollama.com/install.sh | sh

# Modell herunterladen
ollama pull llama3.2

# Service starten
sudo systemctl start ollama
sudo systemctl enable ollama
```

### 6. Backend-Dependencies

```bash
cd /app/backend

# Virtual Environment
python3.11 -m venv venv
source venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

deactivate
```

### 7. Frontend-Dependencies

```bash
cd /app/frontend
yarn install
```

### 8. Supervisor konfigurieren

```bash
sudo apt-get install -y supervisor

# Backend Config
sudo nano /etc/supervisor/conf.d/cyphertrade-backend.conf
```

Inhalt:
```ini
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
```

```bash
# Frontend Config
sudo nano /etc/supervisor/conf.d/cyphertrade-frontend.conf
```

Inhalt:
```ini
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
```

```bash
# Supervisor neu laden
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
```

## 🔍 Verifikation

### Services überprüfen

```bash
# Alle Services
sudo supervisorctl status

# Einzelne Services
sudo systemctl status mongod
sudo systemctl status ollama
```

### Backend API testen

```bash
curl http://localhost:8001/api/health
```

Erwartete Ausgabe:
```json
{
  "status": "healthy",
  "timestamp": "...",
  "bot_running": false,
  "agents": {...}
}
```

### Ollama testen

```bash
ollama list
# Sollte llama3.2 auflisten

ollama run llama3.2
# Startet interaktiven Chat
```

### Logs überprüfen

```bash
# Backend Logs
tail -f /var/log/supervisor/cyphertrade-backend-error.log

# Frontend Logs
tail -f /var/log/supervisor/cyphertrade-frontend.log

# MongoDB Logs
sudo tail -f /var/log/mongodb/mongod.log

# Ollama Logs
journalctl -u ollama -f
```

## 🚨 Troubleshooting

### Problem: Python 3.11 nicht gefunden

**Lösung:**
```bash
sudo apt-get install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev
```

### Problem: MongoDB startet nicht

**Logs prüfen:**
```bash
sudo journalctl -u mongod -n 50
```

**Häufige Ursache:** Port 27017 bereits belegt
```bash
sudo lsof -i :27017
# Falls ein anderer Prozess läuft, beenden
```

**Service neu starten:**
```bash
sudo systemctl restart mongod
```

### Problem: Ollama Modell Download schlägt fehl

**Speicherplatz prüfen:**
```bash
df -h
# Llama 3.2 benötigt ~2 GB
```

**Manuell herunterladen:**
```bash
ollama pull llama3.2
```

**Alternative Modelle (kleiner):**
```bash
ollama pull gemma2  # ~1.6 GB
```

### Problem: Backend startet nicht

**Logs ansehen:**
```bash
tail -f /var/log/supervisor/cyphertrade-backend-error.log
```

**Häufige Fehler:**

1. **Import Error**: Dependencies fehlen
   ```bash
   cd /app/backend
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Port 8001 belegt**:
   ```bash
   sudo lsof -i :8001
   # Process beenden
   ```

3. **MongoDB nicht erreichbar**:
   ```bash
   sudo systemctl status mongod
   ```

### Problem: Frontend startet nicht

**Port 3000 prüfen:**
```bash
sudo lsof -i :3000
```

**Node modules neu installieren:**
```bash
cd /app/frontend
rm -rf node_modules
yarn install
```

**Yarn Cache leeren:**
```bash
yarn cache clean
```

### Problem: Ollama nicht erreichbar

**Service prüfen:**
```bash
sudo systemctl status ollama
```

**Manuell starten:**
```bash
ollama serve
```

**Port prüfen:**
```bash
curl http://localhost:11434/api/tags
```

## 🔧 Nachträgliche Konfiguration

### Verschiedene Ollama Modelle verwenden

Edit `/app/backend/.env`:

```env
NEXUSCHAT_MODEL="llama3.2"
CYPHERMIND_MODEL="llama3.1"  # Größeres Modell für Strategie
CYPHERTRADE_MODEL="mistral"  # Präzises Modell für Execution
```

Modelle herunterladen:
```bash
ollama pull llama3.1
ollama pull mistral
```

Restart:
```bash
sudo supervisorctl restart cyphertrade-backend
```

### Agent-Prompts anpassen

Edit YAML-Dateien:
```bash
nano /app/backend/agent_configs/cyphermind_config.yaml
```

Restart:
```bash
sudo supervisorctl restart cyphertrade-backend
```

Siehe: `/app/AGENT_CONFIG_GUIDE.md`

## 📊 Ressourcen-Anforderungen

### Minimum:
- **CPU:** 2 Cores
- **RAM:** 4 GB
- **Disk:** 20 GB
- **Internet:** DSL 6000+

### Empfohlen:
- **CPU:** 4+ Cores
- **RAM:** 8 GB
- **Disk:** 50 GB SSD
- **Internet:** 16 Mbit/s+

### Mit GPU (Optional):
- **GPU:** NVIDIA mit 8+ GB VRAM
- **CUDA:** 11.x oder 12.x
- **Ollama nutzt GPU automatisch**

## 🔐 Sicherheit

### Firewall konfigurieren

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 3000/tcp  # Frontend (nur wenn Remote-Zugriff gewünscht)
sudo ufw allow 8001/tcp  # Backend API (nur wenn Remote-Zugriff gewünscht)
sudo ufw enable
```

**Wichtig:** Setzen Sie Frontend/Backend nur frei, wenn Sie Remote-Zugriff benötigen!

### .env Datei schützen

```bash
chmod 600 /app/backend/.env
chmod 600 /app/frontend/.env
```

### MongoDB Authentifizierung aktivieren (Produktion)

Siehe: https://www.mongodb.com/docs/manual/tutorial/enable-authentication/

## 🔄 Updates

### System-Updates

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### Python-Dependencies updaten

```bash
cd /app/backend
source venv/bin/activate
pip install --upgrade -r requirements.txt
deactivate
sudo supervisorctl restart cyphertrade-backend
```

### Ollama Modelle updaten

```bash
ollama pull llama3.2
```

## 📞 Support

Bei Problemen:

1. **Logs überprüfen** (siehe oben)
2. **Dokumentation lesen:**
   - `/app/frontend/README.md`
   - `/app/OLLAMA_SETUP.md`
   - `/app/AGENT_CONFIG_GUIDE.md`
3. **Installation wiederholen:**
   ```bash
   sudo bash install.sh
   ```

## 🎯 Nächste Schritte nach Installation

1. ✅ Binance Testnet Account erstellen
2. ✅ API Keys generieren und in .env eintragen
3. ✅ Dashboard öffnen
4. ✅ Bot mit kleinem Betrag (10 USDT) testen
5. ✅ Agent Logs beobachten
6. ✅ Performance überwachen

**Viel Erfolg mit Project CypherTrade! 🚀**
