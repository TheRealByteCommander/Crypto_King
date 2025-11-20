# Project CypherTrade

**AI-Powered Cryptocurrency Trading Bot mit Microsoft Autogen Framework**

Ein vollständiges Multi-Agent-System für automatisierten Krypto-Handel auf Binance mit drei spezialisierten AI Agents, lokalen LLMs (Ollama) und professionellem Dashboard.

---

## 🚀 Quick Start

```bash
# 1. Installation (Ubuntu 22.04)
sudo bash install.sh

# 2. Binance API Keys konfigurieren
nano /app/backend/.env

# 3. Backend neu starten
sudo supervisorctl restart cyphertrade-backend

# 4. Dashboard öffnen
http://localhost:3000
```

**Siehe:** [QUICK_START.md](QUICK_START.md) für Details

---

## ✨ Features

### 🤖 Multi-Agent System
- **NexusChat** - User Interface Agent
- **CypherMind** - Decision & Strategy Agent  
- **CypherTrade** - Trade Execution Agent

### 💹 Trading Features
- Moving Average Crossover Strategie (SMA 20/50)
- Automatische Marktanalyse alle 5 Minuten
- Binance Integration (Testnet & Live)
- Risk Management
- Real-time Performance Tracking

### 📊 Dashboard
- Live Performance Charts (Recharts)
- Trade History
- Agent Status Monitor
- Live Agent Communication Logs
- WebSocket Real-time Updates
- Cyber-Theme Design

### 🔧 Konfigurierbar
- **Agent-Prompts via YAML** (ohne Code-Update)
- **Ollama LLMs** (lokal, kostenlos)
- **Verschiedene Modelle pro Agent**
- **Strategie-Parameter anpassbar**

---

## 📋 Systemanforderungen

### Minimum:
- Ubuntu 22.04 / 20.04 / 24.04
- 4 GB RAM
- 20 GB Speicher
- 2 CPU Cores

### Empfohlen:
- 8 GB RAM
- 50 GB SSD
- 4+ CPU Cores
- GPU optional (NVIDIA für schnellere LLMs)

---

## 📚 Dokumentation

| Datei | Beschreibung |
|-------|--------------|
| [QUICK_START.md](QUICK_START.md) | ⚡ Schnellstart in 5 Minuten |
| [INSTALLATION.md](INSTALLATION.md) | 📦 Ausführliche Installations-Anleitung |
| [OLLAMA_SETUP.md](OLLAMA_SETUP.md) | 🤖 Ollama & LLM Konfiguration |
| [AGENT_CONFIG_GUIDE.md](AGENT_CONFIG_GUIDE.md) | ⚙️ Agent-Anpassung ohne Code |
| [frontend/README.md](frontend/README.md) | 🎨 Frontend & Features |

---

## 🏗️ Architektur

```
┌─────────────────────────────────────────────────┐
│                   Dashboard                     │
│            (React + WebSocket)                  │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│              FastAPI Backend                    │
│  ┌──────────────────────────────────────────┐  │
│  │        Multi-Agent System (Autogen)      │  │
│  ├──────────────────────────────────────────┤  │
│  │  NexusChat  │ CypherMind │ CypherTrade   │  │
│  │     ↓       │      ↓      │      ↓       │  │
│  │   Ollama    │   Ollama    │   Ollama     │  │
│  │  llama3.2   │  llama3.2   │  llama3.2    │  │
│  └──────────────────────────────────────────┘  │
│              ↓                  ↓               │
│         MongoDB          Binance API            │
└─────────────────────────────────────────────────┘
```

---

## 🔧 Installation

### Automatisch (Empfohlen):

```bash
sudo bash install.sh
```

Installiert automatisch:
- ✅ Python 3.11
- ✅ Node.js 18 & Yarn
- ✅ MongoDB 6.0
- ✅ Ollama & Llama 3.2
- ✅ Alle Dependencies
- ✅ Supervisor Config
- ✅ Services

**Dauer:** 10-20 Minuten

### Manuell:

Siehe [INSTALLATION.md](INSTALLATION.md)

---

## ⚙️ Konfiguration

### 1. Binance API Keys

Edit `/app/backend/.env`:

```env
BINANCE_API_KEY="your_binance_api_key"
BINANCE_API_SECRET="your_binance_secret"
BINANCE_TESTNET=true  # true = Testnet, false = Live
```

**Testnet Keys:** https://testnet.binance.vision/

### 2. Ollama Modelle

```bash
# Standard (bereits installiert)
ollama pull llama3.2

# Alternativen
ollama pull llama3.1    # Größer, besseres Reasoning
ollama pull mistral     # Schnell, präzise
ollama pull gemma2      # Effizient, klein
```

### 3. Agent-Prompts anpassen

Edit YAML-Dateien:
- `/app/backend/agent_configs/nexuschat_config.yaml`
- `/app/backend/agent_configs/cyphermind_config.yaml`
- `/app/backend/agent_configs/cyphertrade_config.yaml`

**Keine Code-Änderungen erforderlich!**

Restart:
```bash
sudo supervisorctl restart cyphertrade-backend
```

Siehe: [AGENT_CONFIG_GUIDE.md](AGENT_CONFIG_GUIDE.md)

---

## 🎯 Verwendung

### 1. Dashboard öffnen

```bash
http://localhost:3000
```

### 2. Bot starten

1. Strategie wählen: `MA Crossover (SMA 20/50)`
2. Symbol: `BTCUSDT`
3. Amount: `100` USDT
4. Klick: **"Start Trading Bot"**

### 3. Monitoring

- **Performance Tab:** P&L Charts
- **Trade History:** Alle Trades mit Details
- **Agent Logs:** Live AI-Kommunikation

### 4. Bot stoppen

Klick: **"Stop Trading Bot"**

---

## 📊 Trading Strategien

### 5 Verfügbare Strategien

1. **Moving Average Crossover** - Trend-Folge (SMA 20/50)
2. **RSI** - Relative Strength Index (Momentum)
3. **MACD** - Moving Average Convergence Divergence
4. **Bollinger Bands** - Volatilitäts-basiert
5. **Combined** - Multi-Indikator (MA + RSI + MACD)

### Strategie-Auswahl

Wählen Sie im Dashboard aus dem Dropdown-Menü:

- **MA Crossover**: Gut für Trends
- **RSI**: Gut für Seitwärtsmärkte (Oversold/Overbought)
- **MACD**: Trend + Momentum Kombination
- **Bollinger Bands**: Volatilitäts-Trading
- **Combined**: Konsens aus 3 Indikatoren (empfohlen für Anfänger)

**Analyse-Intervall**: Alle 5 Minuten

**Detaillierte Strategie-Dokumentation**: [TRADING_STRATEGIES.md](TRADING_STRATEGIES.md)

**Anpassbar in:** `/app/backend/agent_configs/cyphermind_config.yaml`

```yaml
strategy_params:
  ma_crossover:
    fast_period: 20
    slow_period: 50
```

---

## 🔍 Service Management

### Status überprüfen

```bash
sudo supervisorctl status
```

### Services neu starten

```bash
# Alle Services
sudo supervisorctl restart all

# Einzeln
sudo supervisorctl restart cyphertrade-backend
sudo supervisorctl restart cyphertrade-frontend
```

### Logs ansehen

```bash
# Backend
tail -f /var/log/supervisor/cyphertrade-backend-error.log

# Frontend
tail -f /var/log/supervisor/cyphertrade-frontend.log

# MongoDB
sudo journalctl -u mongod -f

# Ollama
journalctl -u ollama -f
```

---

## 🚨 Troubleshooting

### Backend startet nicht

```bash
# Logs prüfen
tail -f /var/log/supervisor/cyphertrade-backend-error.log

# Dependencies installieren
cd /app/backend
source venv/bin/activate
pip install -r requirements.txt
```

### Ollama nicht erreichbar

```bash
# Service prüfen
sudo systemctl status ollama

# Manuell starten
ollama serve

# Modelle prüfen
ollama list
```

### MongoDB Probleme

```bash
# Status
sudo systemctl status mongod

# Neu starten
sudo systemctl restart mongod

# Port prüfen
sudo lsof -i :27017
```

**Detaillierte Hilfe:** [INSTALLATION.md](INSTALLATION.md)

---

## 🔐 Sicherheit

### ⚠️ Wichtige Hinweise

1. **Testnet verwenden:** Testen Sie IMMER zuerst mit Binance Testnet
2. **Kleine Beträge:** Starten Sie mit 10-50 USDT
3. **API Keys schützen:** Niemals committen oder teilen
4. **Firewall:** Schließen Sie Ports 3000 & 8001 wenn kein Remote-Zugriff nötig
5. **Monitoring:** Beobachten Sie die Logs regelmäßig

### Crypto Trading Risiken

- ❌ Cryptocurrency Trading ist **hochriskant**
- ❌ Nie mehr investieren als Sie verlieren können
- ❌ Bot-Trading garantiert **keine** Gewinne
- ❌ Entwickler übernehmen **keine Haftung**
- ❌ Nur für Bildungszwecke

---

## 🛠️ Entwicklung

### Backend Development

```bash
cd /app/backend
source venv/bin/activate
python -m uvicorn server:app --reload --port 8001
```

### Frontend Development

```bash
cd /app/frontend
yarn start
```

### Neue Strategie hinzufügen

Edit: `/app/backend/strategies.py`

```python
class MyStrategy(TradingStrategy):
    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        # Ihre Strategie hier
        return {"signal": "BUY", "reason": "..."}
```

---

## 📈 Roadmap

- [ ] RSI Strategie
- [ ] MACD Strategie
- [ ] Bollinger Bands
- [ ] Backtesting Framework
- [ ] Multi-Symbol Trading
- [ ] Advanced Risk Management
- [ ] Machine Learning Integration
- [ ] Mobile App

---

## 🤝 Contributing

Contributions welcome! Bitte erstellen Sie Issues oder Pull Requests.

---

## 📄 Lizenz

Dieses Projekt wurde für **Bildungszwecke** entwickelt.

---

## 🙏 Credits

- **Microsoft Autogen** - Multi-Agent Framework
- **Ollama** - Lokale LLMs
- **Binance** - Crypto Exchange API
- **FastAPI** - Backend Framework
- **React** - Frontend Framework

---

## 📞 Support

Bei Fragen oder Problemen:

1. Überprüfen Sie die Dokumentation
2. Lesen Sie [INSTALLATION.md](INSTALLATION.md) Troubleshooting
3. Prüfen Sie die Logs
4. Erstellen Sie ein GitHub Issue

---

**Made with ❤️ using Microsoft Autogen, Ollama & FastAPI**

**⚠️ Use at your own risk. Trading cryptocurrencies involves substantial risk of loss.**

---

## Getting Started with Create React App
