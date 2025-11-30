# Agent Memory & Learning System

Umfassende Dokumentation zum Memory-System von Project CypherTrade, das es Agents ermöglicht aus ihren Fehlern und Erfolgen zu lernen.

## 🧠 Übersicht

Das Memory-System ermöglicht es jedem Agent:
- ✅ Aus vergangenen Trades zu lernen
- ✅ Erfolgreiche Muster zu erkennen
- ✅ Fehler zu vermeiden
- ✅ Performance über Zeit zu verbessern
- ✅ Wissen zwischen Sessions zu behalten

**WICHTIG:** Das Learning-System wird automatisch bei jedem abgeschlossenen Trade aktiviert. Beide Agents (CypherMind & CypherTrade) lernen aus jedem Trade-Outcome.

**NEU:** Das System trackt jetzt auch kontinuierlich Kerzendaten (Pre-Trade, During-Trade, Post-Trade) für besseres Learning und Vorhersagen. Siehe [CANDLE_TRACKING_IMPLEMENTATION.md](CANDLE_TRACKING_IMPLEMENTATION.md) für Details.

## 🏗️ Architektur

### Memory-Typen

**1. Short-Term Memory**
- In-Memory während aktueller Session
- Schneller Zugriff
- Verloren bei Neustart
- Max. 50 Einträge pro Agent

**2. Long-Term Memory**
- Persistent in MongoDB
- Überlebt Neustarts
- Unbegrenzte Speicherung (mit cleanup)
- Durchsuchbar und analysierbar

**3. Trade Learning Memory**
- Spezialisiert für Trade-Outcomes
- Verknüpft Signale mit Ergebnissen
- Confidence-Level Tracking
- Pattern Recognition

### MongoDB Collections

```
memory_nexuschat     # NexusChat Agent Memories
memory_cyphermind    # CypherMind Agent Memories
memory_cyphertrade   # CypherTrade Agent Memories
collective_memory    # Shared memories between agents
```

## 🔧 Implementation

### Memory Storage

Jeder Agent kann Memories speichern:

```python
from memory_manager import MemoryManager

memory_manager = MemoryManager(db)
memory = memory_manager.get_agent_memory("CypherMind")

# Store a memory
await memory.store_memory(
    memory_type="trade_analysis",
    content={
        "symbol": "BTCUSDT",
        "signal": "BUY",
        "confidence": 0.85,
        "indicators": {...}
    },
    metadata={"session_id": "abc123"}
)
```

### Memory Retrieval

```python
# Get recent memories
memories = await memory.retrieve_memories(
    memory_type="trade_analysis",
    limit=20,
    days_back=30
)

# Get lessons learned
lessons = await memory.get_recent_lessons(limit=10)
```

### Learning from Trades

Automatisch nach jedem Trade (inkl. Delay & Slippage Tracking):

```python
await memory.learn_from_trade(
    trade={
        "order_id": "12345",
        "symbol": "BTCUSDT",
        "strategy": "rsi",
        "entry_price": 50000,
        "exit_price": 51000,
        "confidence": 0.75,
        "indicators": {...},
        "decision_price": 50000,  # Preis bei Signal-Generierung
        "execution_price": 50025,  # Tatsächlicher Ausführungspreis
        "execution_delay_seconds": 3.5,  # Delay zwischen Signal und Ausführung
        "price_slippage": 25.0,  # Preis-Differenz
        "price_slippage_percent": 0.05  # Slippage in %
    },
    outcome="success",  # or "failure", "neutral"
    profit_loss=100.0,
    candle_data={  # Optional: Wird automatisch geladen wenn verfügbar
        "pre_trade": {...},      # 200 Kerzen vor Trade
        "during_trade": {...},   # Alle Kerzen während Position
        "post_trade": {...}      # 200 Kerzen nach Verkauf
    }
)
```

**Automatisch erfasste Metriken:**
- `decision_price`: Kurs zum Zeitpunkt der Signal-Generierung
- `execution_price`: Tatsächlicher Ausführungspreis (aus Order-Fills)
- `execution_delay_seconds`: Zeit zwischen Signal und Order-Ausführung
- `price_slippage`: Absolute Preis-Differenz
- `price_slippage_percent`: Slippage in Prozent

**Kerzen-Daten für Learning (NEU):**
- `pre_trade_candles`: 200 Kerzen vor jedem Trade
- `during_trade_candles`: Alle Kerzen während Position offen ist
- `post_trade_candles`: 200 Kerzen nach jedem Verkauf
- Automatische Pattern-Extraktion aus Kerzen-Daten

## 📊 Pattern Recognition

### Symbol + Strategy Insights

```python
insights = await memory.get_pattern_insights(
    symbol="BTCUSDT",
    strategy="rsi"
)
```

**Rückgabe:**
```json
{
  "total_trades": 25,
  "success_rate": 68.0,
  "total_profit_loss": 245.50,
  "avg_profit_per_trade": 9.82,
  "successful_trades": 17,
  "failed_trades": 8,
  "insights": [
    "Successful trades had avg confidence: 0.78"
  ],
  "recommendation": "POSITIVE - Strategy shows good performance"
}
```

### Recommendations

Basierend auf historischer Performance:

| Success Rate | Avg P&L | Recommendation |
|--------------|---------|----------------|
| > 60% | > 0 | POSITIVE |
| > 50% | > 0 | NEUTRAL |
| < 40% | Any | NEGATIVE |
| < 50% | < 0 | NEGATIVE |

## 🎯 Learning Process

### 1. Trade Execution

```
User starts bot → CypherMind analyzes → Signal generated → 
CypherTrade executes → Trade stored with metadata
```

### 2. Trade Completion

```
SELL signal → Calculate P&L → Determine outcome →
Learn from trade → Store in memory → Extract lessons
```

### 3. Lesson Extraction

**Automatisch generierte Lessons:**

- ✅ "Strategy 'rsi' worked well with confidence 0.85"
- ✅ "High profit trade - similar conditions may be favorable"
- ❌ "Strategy 'ma_crossover' failed with confidence 0.55"
- ❌ "Low confidence signals are risky - require higher threshold"
- ⏱️ "High execution delay (12.5s) - market may have moved significantly"
- ⏱️ "Fast execution (1.8s) - good timing"
- 💰 "Positive slippage (+0.15%) - execution price better than expected"
- 💰 "Negative slippage (-0.32%) - execution price worse than expected, consider faster execution"
- 💰 "Minimal slippage (0.02%) - good execution quality"

**Kerzen-Pattern Lessons (NEU):**
- 📊 "Strong upward trend before entry (+3.2%) led to success"
- 📊 "Price reached 5.8% profit during position but exited at 2.1% - could optimize take-profit strategy"
- 📊 "Position held for 45 candles - consider earlier exit for losing positions"
- 📊 "Price was profitable (+4.2%) during position but closed at loss (-1.5%) - should have taken profit earlier"
- 📊 "Price continued rising after exit (+6.5%) - could have held longer for more profit"

### 4. Pattern Application

Bei nächster Analyse:
```
CypherMind checks historical performance →
Sees 70% success rate with RSI on BTCUSDT →
Adjusts confidence accordingly →
Makes informed decision
```

## 🔍 Memory Injection in Agents

### Automatische Integration

Beim Bot-Start wird jedem Agent sein Memory-Summary injiziert:

```
=== Memory Summary for CypherMind ===

Recent Lessons Learned:
1. Strategy 'rsi' worked well with confidence 0.85
2. High profit trade - similar conditions may be favorable
3. BTCUSDT shows strong performance with combined strategy

Recent Trade Outcomes:
- rsi: success (P&L: $125.50)
- ma_crossover: failure (P&L: $-45.20)
- combined: success (P&L: $87.30)

=== End Memory Summary ===
```

### Agent-Prompts mit Memory

Agents nutzen Memory für bessere Entscheidungen:

**CypherMind Beispiel:**
```
Agent sieht: "RSI signal for BTCUSDT"
Agent prüft Memory: "70% success rate in past"
Agent denkt: "This looks promising based on history"
Agent entscheidet: "Execute with higher confidence"
```

## 📈 Dashboard Integration

### AI Learning Tab

Neuer Tab im Dashboard zeigt:

1. **Agent Memory Stats**
   - Total Memories pro Agent
   - Recent Lessons Count

2. **Recent Lessons Learned**
   - Liste aller extrahierten Lessons
   - Filterable pro Agent

3. **Learning Status**
   - Active Learning Mode
   - Real-time Updates

### API Endpoints

```javascript
// Get agent memory
GET /api/memory/{agent_name}?limit=20

// Get lessons
GET /api/memory/{agent_name}/lessons?limit=10

// Get collective insights
GET /api/memory/insights/collective

// Get pattern insights
GET /api/memory/pattern/{symbol}/{strategy}
```

## 🔄 Memory Lifecycle

### Storage Flow

```
1. Event occurs (trade, analysis, etc.)
2. Agent stores in short-term memory
3. Simultaneously saved to MongoDB
4. Tagged with timestamp, type, metadata
5. Available for retrieval
```

### Cleanup Process

```python
# Automatically clear old memories (90 days)
await memory.clear_old_memories(days_to_keep=90)
```

**Default Retention:**
- Trade Learning: 90 days
- Analysis Memories: 60 days
- Logs: 30 days

## 📊 Memory Statistics

### Per Agent

```bash
curl http://localhost:8001/api/memory/CypherMind
```

**Response:**
```json
{
  "agent": "CypherMind",
  "memories": [...],
  "count": 150
}
```

### Collective

```bash
curl http://localhost:8001/api/memory/insights/collective
```

**Response:**
```json
{
  "NexusChat": {
    "total_memories": 50,
    "recent_lessons": ["Lesson 1", "Lesson 2"]
  },
  "CypherMind": {
    "total_memories": 150,
    "recent_lessons": ["Lesson 1", "Lesson 2"]
  },
  "CypherTrade": {
    "total_memories": 75,
    "recent_lessons": ["Lesson 1"]
  }
}
```

## 🧪 Testing Memory System

### Manual Test

```python
# 1. Start bot with strategy
# 2. Execute trades
# 3. Check memory

curl http://localhost:8001/api/memory/CypherMind/lessons

# Should show learned lessons
```

### Verify Learning

```bash
# After 5+ trades, check pattern insights
curl "http://localhost:8001/api/memory/pattern/BTCUSDT/rsi"

# Should show success rate and recommendation
```

## 💡 Best Practices

### For Users

1. **Let it Learn**
   - Minimum 10 trades für meaningful patterns
   - Mehr Trades = Besseres Learning

2. **Review Lessons**
   - Check "AI Learning" Tab regelmäßig
   - Verstehe was die Agents lernen

3. **Monitor Performance**
   - Pattern Insights zeigen was funktioniert
   - Adjust strategies basierend auf Learnings

4. **Clean Old Data**
   - System cleaned automatisch nach 90 Tagen
   - Manuell möglich via API

### For Developers

1. **Memory-Aware Decisions**
   - Prüfe immer pattern insights vor Trades
   - Nutze success rate für confidence adjustment

2. **Structured Storage**
   - Verwende klare memory_types
   - Konsistente metadata structures

3. **Efficient Retrieval**
   - Limit queries zu reasonable amounts
   - Cache short-term für Performance

## 🔐 Privacy & Data

### Stored Data

**Gespeichert:**
- Trade decisions & outcomes
- Indicator values
- Confidence levels
- P&L results
- Timestamps

**NICHT gespeichert:**
- API Keys
- Private keys
- Personal information
- Account balances (außer für analysis)

### Data Retention

**Default:**
- 90 Tage für Trade Learning
- Automatisches Cleanup
- Manuell adjustable

**Löschen:**
```python
# Clear all memories for an agent
await memory.collection.delete_many({"agent": "CypherMind"})

# Clear old memories
await memory.clear_old_memories(days_to_keep=30)
```

## 📖 Example Use Cases

### Use Case 1: Confidence Adjustment

**Scenario:** RSI strategy has 80% success rate

**Learning:**
```python
insights = await memory.get_pattern_insights("BTCUSDT", "rsi")
# Returns: success_rate = 80%

# Agent adjusts confidence
if insights["success_rate"] > 70:
    confidence += 0.1  # Boost confidence
```

### Use Case 2: Strategy Selection

**Scenario:** Multiple strategies available

**Learning:**
```python
# Check performance of each strategy
for strategy in ["rsi", "macd", "ma_crossover"]:
    insights = await memory.get_pattern_insights("BTCUSDT", strategy)
    
# Select best performing strategy
best_strategy = max(strategies, key=lambda s: s["success_rate"])
```

### Use Case 3: Risk Management

**Scenario:** Detect failing patterns

**Learning:**
```python
insights = await memory.get_pattern_insights("BTCUSDT", "macd")

if insights["success_rate"] < 40:
    # Stop using this strategy for this symbol
    logger.warning("Strategy underperforming - skipping trade")
    return "HOLD"
```

## 🚀 Advanced Features

### Custom Memory Types

Eigene Memory-Typen definieren:

```python
await memory.store_memory(
    memory_type="market_condition",
    content={
        "volatility": "high",
        "trend": "bullish",
        "volume": "above_average"
    }
)
```

### Memory Search

```python
# Find specific memories
memories = await memory.collection.find({
    "type": "trade_learning",
    "content.outcome": "success",
    "content.profit_loss": {"$gt": 100}
}).to_list(10)
```

### Collective Learning

Shared insights across agents:

```python
await memory_manager.store_collective_memory(
    memory_type="market_event",
    content={
        "event": "Bitcoin halving",
        "impact": "high",
        "observed_pattern": "increased volatility"
    }
)
```

## 🔮 Future Enhancements

Geplante Features:

- [ ] Machine Learning Models für Pattern Prediction
- [ ] Sentiment Analysis Integration
- [ ] Multi-Symbol Pattern Recognition
- [ ] Collaborative Learning zwischen Instances
- [ ] Memory Export/Import
- [ ] Advanced Visualization
- [ ] Real-time Learning Alerts

## 📝 Configuration

### Memory Settings

In `/app/backend/.env`:

```env
# Memory Configuration (Optional)
MEMORY_RETENTION_DAYS=90
MEMORY_MAX_SHORT_TERM=50
MEMORY_ENABLE_COLLECTIVE=true
```

### Per-Agent Tuning

In agent configs:

```yaml
# In cyphermind_config.yaml
memory_settings:
  enable_learning: true
  confidence_adjustment: true
  min_trades_for_pattern: 10
```

---

## 🎓 Summary

Das Memory-System transformiert die Agents von statischen Executors zu lernenden, adaptiven Tradern die:

- ✅ **Lernen** aus jedem Trade
- ✅ **Erinnern** an Erfolge und Fehler
- ✅ **Anpassen** ihre Strategien
- ✅ **Verbessern** über Zeit
- ✅ **Teilen** Wissen untereinander

**Das Ergebnis:** Intelligentere Trading-Entscheidungen basierend auf realer Erfahrung!

---

**Made with 🧠 - AI that Actually Learns!**
