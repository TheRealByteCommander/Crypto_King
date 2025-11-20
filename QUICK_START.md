# Quick Start Guide - Project CypherTrade

Schnellstart in 5 Minuten! ⚡

## 🚀 Installation (Ubuntu 22.04)

### Eine Zeile Installation:

```bash
sudo bash install.sh
```

Das war's! Das Skript installiert automatisch:
- Python 3.11
- Node.js & Yarn  
- MongoDB
- Ollama & Llama 3.2
- Alle Dependencies

**Dauer:** 10-20 Minuten

## ⚙️ Konfiguration

Nach der Installation:

```bash
nano /app/backend/.env
```

**Binance API Keys eintragen:**

```env
BINANCE_API_KEY="your_api_key_here"
BINANCE_API_SECRET="your_api_secret_here"
BINANCE_TESTNET=true
```

**Speichern & Neu starten:**

```bash
sudo supervisorctl restart cyphertrade-backend
```

## 🎯 Verwendung

1. **Dashboard öffnen:** `http://localhost:3000`

2. **Bot konfigurieren:**
   - Strategie: `MA Crossover (SMA 20/50)`
   - Symbol: `BTCUSDT`
   - Amount: `10` (USDT)

3. **Bot starten:** Klick auf "Start Trading Bot"

4. **Monitoring:**
   - Performance Tab → Charts
   - Trade History → Alle Trades
   - Agent Logs → AI-Kommunikation

## 🔍 Status überprüfen

```bash
# Alle Services
sudo supervisorctl status

# Logs
tail -f /var/log/supervisor/cyphertrade-backend-error.log
```

## 🛠️ Nützliche Befehle

```bash
# Services neu starten
sudo supervisorctl restart all

# Backend neu starten
sudo supervisorctl restart cyphertrade-backend

# Frontend neu starten
sudo supervisorctl restart cyphertrade-frontend

# Ollama testen
ollama run llama3.2

# MongoDB Status
sudo systemctl status mongod
```

## 📚 Dokumentation

- **Installation:** `/app/INSTALLATION.md`
- **Ollama Setup:** `/app/OLLAMA_SETUP.md`
- **Agent Config:** `/app/AGENT_CONFIG_GUIDE.md`
- **README:** `/app/frontend/README.md`

## ⚠️ Wichtig

- ✅ Verwenden Sie **Binance Testnet** zum Testen!
- ✅ Starten Sie mit **kleinen Beträgen** (10 USDT)
- ✅ Beobachten Sie die **Agent Logs**
- ❌ **Nicht** mit echtem Geld ohne Tests starten!

## 🚨 Probleme?

**Backend startet nicht:**
```bash
tail -f /var/log/supervisor/cyphertrade-backend-error.log
```

**Ollama nicht erreichbar:**
```bash
ollama serve
```

**MongoDB läuft nicht:**
```bash
sudo systemctl restart mongod
```

**API Keys funktionieren nicht:**
- Überprüfen Sie die Keys in `/app/backend/.env`
- Testnet-Keys auf https://testnet.binance.vision/

## 🎓 Tutorial

### 1. Testnet Setup

1. Gehe zu: https://testnet.binance.vision/
2. Registriere dich (kostenlos)
3. API Key erstellen
4. Keys in `/app/backend/.env` eintragen

### 2. Ersten Trade

1. Bot starten mit 10 USDT
2. Warten auf Analyse (5 Minuten Intervall)
3. Bei Signal → Trade wird ausgeführt
4. In "Trade History" Tab → Trade sehen

### 3. Agent-Logs verstehen

```
NexusChat: "Benutzer hat Bot gestartet"
CypherMind: "Analysiere BTCUSDT..."
CypherMind: "Fast SMA: 48,500 | Slow SMA: 48,000"
CypherMind: "Signal: BUY - Fast crossed above Slow"
CypherTrade: "Executing BUY 0.0002 BTC..."
CypherTrade: "Order executed: ID 12345"
```

## 📈 Performance Monitoring

- **Profit/Loss Card:** Gesamt P&L
- **Performance Chart:** Visueller Verlauf
- **Trade Count:** Anzahl Trades
- **Agent Status:** Welche LLMs laufen

## 🔧 Erweiterte Konfiguration

### Agent-Prompts anpassen:

```bash
nano /app/backend/agent_configs/cyphermind_config.yaml
```

### Anderes Ollama Modell verwenden:

```bash
# Modell herunterladen
ollama pull mistral

# In .env eintragen
nano /app/backend/.env
# CYPHERMIND_MODEL="mistral"

# Neu starten
sudo supervisorctl restart cyphertrade-backend
```

## 💡 Tipps

1. **Testnet zuerst:** Immer mit Testnet beginnen
2. **Kleine Beträge:** Testen Sie mit 10-50 USDT
3. **Logs beobachten:** Verstehen Sie das Agent-Verhalten
4. **Strategie verstehen:** MA Crossover = SMA20 kreuzt SMA50
5. **Geduld:** Trades passieren nur bei klaren Signalen

## 🎉 Ready!

Sie sind bereit für AI-gestütztes Crypto Trading!

**Viel Erfolg! 🚀**

---

**Support:** Siehe `/app/INSTALLATION.md` für detaillierte Troubleshooting-Hilfe
