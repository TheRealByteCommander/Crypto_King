# Project CypherTrade

Ein vollständiges, modulares und sicheres Multi-Agent-System für den automatisierten Handel von Kryptowährungen auf der Binance-Börse, entwickelt mit dem Microsoft Autogen Framework.

## 🚀 Features

### Multi-Agent System (Autogen)
- **NexusChat Agent**: User Interface Agent - Kommunikations-Hub für Benutzerinteraktionen
- **CypherMind Agent**: Decision & Strategy Agent - Analysiert Marktdaten und trifft Handelsentscheidungen
- **CypherTrade Agent**: Trade Execution Agent - Führt Trades auf Binance sicher aus

### Trading Features
- ✅ Moving Average Crossover Strategie (SMA 20/50)
- ✅ Automatische Marktdatenanalyse alle 5 Minuten
- ✅ Binance API Integration (Testnet & Live)
- ✅ Risk Management mit konfigurierbaren Parametern
- ✅ Real-time Performance Tracking

### Dashboard Features
- 📊 Live Performance Charts
- 📈 Trade History mit detaillierten Informationen
- 🤖 Agent Status Monitoring
- 📝 Live Agent Communication Logs
- 💰 Real-time Balance Updates
- 🔄 WebSocket-basierte Live-Updates

### Benachrichtigungen
- ✉️ Email-Benachrichtigungen für Trades
- 📱 Telegram-Bot Integration

## 🏗️ Architektur

```
Project CypherTrade
├── Backend (FastAPI + Python)
│   ├── 3 Autogen AI Agents
│   ├── Binance API Client
│   ├── Trading Strategies
│   ├── WebSocket Server
│   └── MongoDB Persistence
└── Frontend (React)
    ├── Dashboard
    ├── Bot Control Panel
    ├── Performance Charts
    └── Real-time Updates
```

## 📋 Voraussetzungen

### 1. Binance API Keys

**Für Testnet (Empfohlen zum Testen):**
1. Gehen Sie zu: https://testnet.binance.vision/
2. Registrieren Sie sich und erstellen Sie API Keys
3. Notieren Sie sich `API_KEY` und `API_SECRET`

**Für Live Trading (Vorsicht: Echtes Geld!):**
1. Gehen Sie zu: https://www.binance.com/
2. Account erstellen und API Keys generieren
3. Aktivieren Sie "Spot Trading" Berechtigung

### 2. Ollama LLMs (Lokale AI Modelle)

Das System verwendet **Ollama** für lokale LLM-Ausführung:

**Installation:**
```bash
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh

# Modell herunterladen
ollama pull llama3.2

# Server starten
ollama serve
```

**Windows:** Download von https://ollama.com/download

**Empfohlene Modelle:**
- `llama3.2` - Standard, gut ausbalanciert
- `llama3.1` - Größer, besseres Reasoning
- `mistral` - Schnell, präzise
- `gemma2` - Effizient

**Siehe auch:** `/app/OLLAMA_SETUP.md` für Details

## 🔧 Konfiguration

### Binance API Keys

Bearbeiten Sie `/app/backend/.env`:

```env
# Binance API Configuration
BINANCE_API_KEY="your_binance_api_key_here"
BINANCE_API_SECRET="your_binance_api_secret_here"
BINANCE_TESTNET=true
```

### Ollama Konfiguration (bereits gesetzt)

```env
# Ollama ist bereits konfiguriert für:
OLLAMA_BASE_URL="http://localhost:11434/v1"
NEXUSCHAT_MODEL="llama3.2"
CYPHERMIND_MODEL="llama3.2"
CYPHERTRADE_MODEL="llama3.2"
```

### Agent-Prompts anpassen (ohne Code-Update!)

Dateien in `/app/backend/agent_configs/`:
- `nexuschat_config.yaml` - User Interface Agent
- `cyphermind_config.yaml` - Strategy Agent
- `cyphertrade_config.yaml` - Trade Execution Agent

Nach Änderungen: `sudo supervisorctl restart backend`

## 📖 Verwendung

### Bot starten

1. Öffnen Sie das Dashboard
2. Wählen Sie Strategie, Symbol und Betrag
3. Klicken Sie auf "Start Trading Bot"
4. Überwachen Sie Performance, Trades und Agent Logs

### Sicherheitshinweise

⚠️ **WICHTIG**:
- Verwenden Sie Binance Testnet zum Testen
- Starten Sie mit kleinen Beträgen
- Crypto Trading ist riskant - nur investieren, was Sie verlieren können
- Die Entwickler übernehmen keine Haftung

## 📊 Trading Strategie

**Moving Average Crossover**: Fast SMA (20) kreuzt Slow SMA (50)
- **Kaufsignal**: Fast > Slow (von unten)
- **Verkaufssignal**: Fast < Slow (von oben)
- **Analyse**: Alle 5 Minuten

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

### Code Splitting

This section has moved here: [https://facebook.github.io/create-react-app/docs/code-splitting](https://facebook.github.io/create-react-app/docs/code-splitting)

### Analyzing the Bundle Size

This section has moved here: [https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size](https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size)

### Making a Progressive Web App

This section has moved here: [https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app](https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app)

### Advanced Configuration

This section has moved here: [https://facebook.github.io/create-react-app/docs/advanced-configuration](https://facebook.github.io/create-react-app/docs/advanced-configuration)

### Deployment

This section has moved here: [https://facebook.github.io/create-react-app/docs/deployment](https://facebook.github.io/create-react-app/docs/deployment)

### `npm run build` fails to minify

This section has moved here: [https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify](https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify)
