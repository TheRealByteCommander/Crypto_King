# Project CypherTrade

Ein vollständiges, modulares und sicheres Multi-Agent-System für den automatisierten Handel von Kryptowährungen auf der Binance-Börse, entwickelt mit dem Microsoft Autogen Framework.

## 🚀 Features

### Multi-Agent System (Autogen)
- **NexusChat Agent**: User Interface Agent - Kommunikations-Hub für Benutzerinteraktionen
- **CypherMind Agent**: Decision & Strategy Agent - Analysiert Marktdaten und trifft Handelsentscheidungen
- **CypherTrade Agent**: Trade Execution Agent - Führt Trades auf Binance sicher aus

### Trading Features
- ✅ **5 Trading-Strategien**: MA Crossover, RSI, MACD, Bollinger Bands, Combined
- ✅ **Flexible Timeframes**: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
- ✅ **Trading Modes**: SPOT, MARGIN, FUTURES (Short Trading unterstützt)
- ✅ Automatische Marktdatenanalyse (konfigurierbares Intervall)
- ✅ Binance API Integration (Testnet & Live)
- ✅ Risk Management mit konfigurierbaren Parametern
- ✅ Real-time Performance Tracking
- ✅ Portfolio Management mit Multi-Asset Support

### Dashboard Features
- 📊 Live Performance Charts (Recharts)
- 📈 Trade History mit detaillierten Informationen
- 💼 Portfolio Overview (Multi-Asset Tracking mit P&L)
- 🤖 Agent Status Monitoring
- 📝 Live Agent Communication Logs
- 🧠 AI Learning Insights (Memory System)
- 📊 Volatile Assets Discovery
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

## 📊 Trading Strategien

Project CypherTrade unterstützt **5 Trading-Strategien**:

1. **Moving Average Crossover** - Fast SMA (20) kreuzt Slow SMA (50)
   - **Kaufsignal**: Fast > Slow (von unten)
   - **Verkaufssignal**: Fast < Slow (von oben)

2. **RSI** - Relative Strength Index (Momentum)
   - **Kaufsignal**: RSI < 30 (Oversold)
   - **Verkaufssignal**: RSI > 70 (Overbought)

3. **MACD** - Moving Average Convergence Divergence
   - Trend + Momentum Kombination

4. **Bollinger Bands** - Volatilitäts-basiert
   - Mean-Reversion Strategie

5. **Combined** - Multi-Indikator (MA + RSI + MACD)
   - Konsens aus 3 Strategien (empfohlen für Anfänger)

**Verfügbare Timeframes**: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M

**Detaillierte Dokumentation**: Siehe `/app/TRADING_STRATEGIES.md`

## 🔧 Weitere Features

### Memory & Learning System
- Agents lernen aus vergangenen Trades
- Pattern Recognition für bessere Entscheidungen
- Collective Insights von allen Agents
- Siehe: `/app/MEMORY_SYSTEM.md`

### Agent Tools
- Funktionale Tools für alle Agents
- Market Data Access für CypherMind
- Trade Execution Tools für CypherTrade
- Information Tools für NexusChat
- Siehe: `/app/AGENT_TOOLS.md`

### MCP Server
- Model Context Protocol Integration
- Tool-basierte API für externe Agents
- Siehe: `/app/MCP_SERVER.md`

### Trading Modes
- **SPOT**: Standard Spot Trading
- **MARGIN**: Margin Trading mit Leverage
- **FUTURES**: Futures Trading mit Short Support
- Siehe: `/app/TRADING-MODE-ANLEITUNG.md`

---

## 📚 Weitere Dokumentation

- **Haupt-README**: `/app/README.md`
- **Installation**: `/app/INSTALLATION.md`
- **Quick Start**: `/app/QUICK_START.md`
- **Trading Strategien**: `/app/TRADING_STRATEGIES.md`
- **Trading Modes**: `/app/TRADING-MODE-ANLEITUNG.md`
- **Ollama Setup**: `/app/OLLAMA_SETUP.md`
- **Agent Config**: `/app/AGENT_CONFIG_GUIDE.md`
- **Memory System**: `/app/MEMORY_SYSTEM.md`
- **Agent Tools**: `/app/AGENT_TOOLS.md`
- **MCP Server**: `/app/MCP_SERVER.md`
