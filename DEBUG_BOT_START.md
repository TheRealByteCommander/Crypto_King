# Debugging: Warum werden keine autonomen Bots gestartet?

## Mögliche Gründe und Lösungen

### 1. ❌ Autonomous Manager nicht gestartet oder Binance Client fehlt

**Symptome:**
- Logs zeigen: "Binance client not available, skipping autonomous analysis"
- Keine Logs von "Autonomous analysis loop started"

**Prüfung:**
```bash
# Backend-Logs prüfen
tail -f /var/log/supervisor/cyphertrade-backend.log | grep -i "autonomous\|binance"
```

**Lösung:**
- Mindestens einen Bot manuell starten (damit Binance Client initialisiert wird)
- Oder: Autonomous Manager wartet auf ersten Bot-Start

**Code-Stelle:**
- `backend/autonomous_manager.py:165` - Prüft ob `binance_client` verfügbar ist

---

### 2. ❌ Coin Analyzer findet keine Coins mit Score >= 0.4

**Symptome:**
- CypherMind führt `analyze_optimal_coins` aus, aber findet keine Coins
- Alle Coins haben Score < 0.4

**Mögliche Ursachen:**
- **Zu hohe Schwelle (0.4)**: Markt ist flach, keine starken Signale
- **Strategien geben nur HOLD/SELL**: Keine BUY-Signale gefunden
- **Nur Top 50 Coins werden analysiert**: Bessere Coins werden übersehen
- **Trend ist negativ**: Alle Coins im Abwärtstrend

**Prüfung:**
```python
# Manuell testen:
from coin_analyzer import CoinAnalyzer
from binance_client import BinanceClientWrapper

client = BinanceClientWrapper()
analyzer = CoinAnalyzer(client)
results = await analyzer.find_optimal_coins(min_score=0.2, max_coins=20)
print(f"Found {len(results)} coins with score >= 0.2")
for r in results[:10]:
    print(f"{r['symbol']}: Score={r['score']:.3f}, Strategy={r.get('best_strategy')}")
```

**Lösung:**
- **Schwelle temporär senken**: `min_score=0.2` statt 0.4 testen
- **Mehr Coins analysieren**: `max_coins=50` statt 20
- **Coin Analyzer verbessern**: Mehr Coins prüfen (nicht nur Top 50)

**Code-Stelle:**
- `backend/coin_analyzer.py:275` - Analysiert nur Top 50 Coins
- `backend/coin_analyzer.py:283` - Filtert nach `min_score >= 0.4`

---

### 3. ❌ CypherMind wird nicht aktiviert oder antwortet nicht

**Symptome:**
- Keine Logs von "CypherMind activated for autonomous analysis"
- CypherMind führt keine Tools aus

**Mögliche Ursachen:**
- **LLM antwortet nicht**: Ollama nicht erreichbar oder Timeout
- **Agent-Kommunikation funktioniert nicht**: `user_proxy.send()` schlägt fehl
- **CypherMind ignoriert Nachricht**: LLM interpretiert Anweisung falsch

**Prüfung:**
```bash
# Prüfe ob Ollama läuft
curl http://localhost:11434/api/tags

# Prüfe Backend-Logs
tail -f /var/log/supervisor/cyphertrade-backend.log | grep -i "cyphermind\|activated"
```

**Lösung:**
- Ollama-Service prüfen und neu starten
- LLM-Config prüfen (`backend/config.py`)
- Agent-Logs in MongoDB prüfen

**Code-Stelle:**
- `backend/autonomous_manager.py:237` - `user_proxy.send()` mit `request_reply=True`

---

### 4. ❌ Budget-Probleme

**Symptome:**
- Bot-Start schlägt fehl mit "Insufficient balance"
- Berechnetes Budget ist zu niedrig (< 10 USDT)

**Prüfung:**
```python
# Prüfe verfügbares Kapital
from binance_client import BinanceClientWrapper
client = BinanceClientWrapper()
balance = client.get_account_balance("USDT", "SPOT")
print(f"Available USDT: {balance}")
```

**Lösung:**
- Mindestens 25 USDT auf dem Account haben (für 1 Bot mit 10 USDT + Reserve)
- Für 6 Bots: Mindestens 60-100 USDT empfohlen

**Code-Stelle:**
- `backend/agent_tools.py:979` - Budget-Berechnung: `min(avg_budget, 40% of capital)`
- `backend/agent_tools.py:984` - Minimum: 10 USDT

---

### 5. ❌ Binance API Probleme

**Symptome:**
- "Error getting market data"
- "Binance API error"
- Timeouts bei API-Calls

**Prüfung:**
```bash
# Prüfe API-Verbindung
curl https://api.binance.com/api/v3/ping
```

**Lösung:**
- API-Key und Secret prüfen
- Internet-Verbindung prüfen
- Binance API Status prüfen

---

### 6. ❌ Strategien geben keine BUY-Signale

**Symptome:**
- Alle Strategien geben HOLD oder SELL
- Confidence ist zu niedrig (< 0.6)

**Mögliche Ursachen:**
- **Markt ist bearish**: Alle Indikatoren zeigen Abwärtstrend
- **RSI zu hoch**: Überkauft (> 70)
- **MACD negativ**: Keine Aufwärtsbewegung
- **Bollinger Bands**: Preis zu hoch

**Prüfung:**
```python
# Teste Strategien manuell
from strategies import get_strategy
from binance_client import BinanceClientWrapper

client = BinanceClientWrapper()
df = client.get_market_data("BTCUSDT", "5m", 100)

strategy = get_strategy("rsi")
result = strategy.analyze(df)
print(f"Signal: {result['signal']}, Confidence: {result['confidence']}")
```

**Lösung:**
- **Schwelle senken**: Temporär `min_score=0.2` testen
- **Andere Strategien prüfen**: Vielleicht funktioniert "combined" besser
- **Warten auf bessere Marktbedingungen**

**Code-Stelle:**
- `backend/coin_analyzer.py:93` - BUY-Signale geben positiven Score
- `backend/coin_analyzer.py:179` - Gesamt-Score kombiniert mehrere Faktoren

---

### 7. ❌ Coin Analyzer analysiert zu wenige Coins

**Problem:**
- Nur Top 50 Coins werden analysiert (nach Alphabet sortiert)
- Bessere Coins könnten übersehen werden

**Code-Stelle:**
- `backend/coin_analyzer.py:275` - `symbols_to_analyze = usdt_symbols[:50]`

**Lösung:**
- Mehr Coins analysieren (z.B. Top 100 oder alle)
- Nach Volumen statt Alphabet sortieren

---

### 8. ❌ Fehlende Dependencies

**Symptome:**
- "coin_analyzer not available"
- "crypto_news_fetcher not available"
- Import-Fehler

**Prüfung:**
```bash
# Prüfe Python-Module
python3 -c "from coin_analyzer import CoinAnalyzer; print('OK')"
python3 -c "from crypto_news_fetcher import get_news_fetcher; print('OK')"
```

**Lösung:**
```bash
pip install feedparser beautifulsoup4 httpx
```

---

### 9. ❌ Agent Tools nicht verfügbar

**Symptome:**
- CypherMind kann Tools nicht aufrufen
- "Tool not available" Fehler

**Prüfung:**
- Agent-Logs in MongoDB prüfen
- Backend-Logs auf Tool-Fehler prüfen

**Lösung:**
- Agent Tools initialisieren prüfen
- Binance Client in Agent Tools verfügbar machen

---

### 10. ❌ Max Bots bereits erreicht

**Symptome:**
- "Max autonomous bots (6) already running"
- Keine neuen Bots werden gestartet

**Prüfung:**
```python
# Prüfe laufende Bots
all_bots = bot_manager.get_all_bots()
autonomous = [b for b in all_bots.values() 
              if b.is_running and b.current_config.get("autonomous")]
print(f"Autonomous bots: {len(autonomous)}")
```

**Lösung:**
- Warten bis ein Bot gestoppt wird (nach 24h bei schlechter Performance)
- Oder: Manuell einen Bot stoppen

---

## Debugging-Checkliste

### Schritt 1: Prüfe ob Autonomous Manager läuft
```bash
tail -f /var/log/supervisor/cyphertrade-backend.log | grep -i "autonomous"
```
**Erwartet:** "AutonomousManager started", "Autonomous analysis loop started"

### Schritt 2: Prüfe ob CypherMind aktiviert wird
```bash
tail -f /var/log/supervisor/cyphertrade-backend.log | grep -i "cyphermind.*activated"
```
**Erwartet:** "CypherMind activated for autonomous analysis"

### Schritt 3: Prüfe ob Coin-Analyse durchgeführt wird
```bash
tail -f /var/log/supervisor/cyphertrade-backend.log | grep -i "analyze_optimal_coins\|coin.*analysis"
```
**Erwartet:** "Analyzing X coins for optimal trading opportunities"

### Schritt 4: Prüfe Agent-Logs in MongoDB
```python
# In Python Shell oder Script
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def check_logs():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.cyphertrade
    logs = await db.agent_logs.find({
        "agent_name": "CypherMind"
    }).sort("timestamp", -1).limit(20).to_list(20)
    
    for log in logs:
        print(f"{log['timestamp']}: {log['message'][:200]}")

asyncio.run(check_logs())
```

### Schritt 5: Teste Coin Analyzer manuell
```python
from coin_analyzer import CoinAnalyzer
from binance_client import BinanceClientWrapper
import asyncio

async def test():
    client = BinanceClientWrapper()
    analyzer = CoinAnalyzer(client)
    
    # Test mit niedrigerer Schwelle
    results = await analyzer.find_optimal_coins(min_score=0.2, max_coins=10)
    print(f"Found {len(results)} coins")
    for r in results:
        print(f"{r['symbol']}: {r['score']:.3f}")

asyncio.run(test())
```

### Schritt 6: Prüfe Budget-Berechnung
```python
from binance_client import BinanceClientWrapper

client = BinanceClientWrapper()
balance = client.get_account_balance("USDT", "SPOT")
print(f"Available: {balance} USDT")
print(f"40%: {balance * 0.4} USDT")
print(f"Min required: 10 USDT")
```

---

## Empfohlene Verbesserungen

### 1. Coin Analyzer: Mehr Coins analysieren
- Aktuell: Nur Top 50 (alphabetisch)
- Verbesserung: Top 100 nach 24h-Volumen sortieren

### 2. Score-Schwelle anpassbar machen
- Aktuell: Fest 0.4
- Verbesserung: Dynamisch basierend auf Marktbedingungen

### 3. Besseres Logging
- Detaillierte Logs für jeden Schritt
- Warum wurde kein Bot gestartet?

### 4. Fallback-Mechanismus
- Wenn keine Coins mit Score >= 0.4: Temporär auf 0.2 senken
- Oder: Beste verfügbare Coins nehmen (auch wenn < 0.4)

---

## Häufigste Probleme (Top 3)

1. **Keine Coins mit Score >= 0.4** (70% der Fälle)
   - Lösung: Schwelle temporär senken oder mehr Coins analysieren

2. **Binance Client nicht verfügbar** (20% der Fälle)
   - Lösung: Mindestens einen Bot manuell starten

3. **CypherMind antwortet nicht** (10% der Fälle)
   - Lösung: Ollama prüfen, LLM-Config prüfen

