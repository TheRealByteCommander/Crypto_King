# Kerzen-Tracking-System - Analyse & Implementierungsvorschlag

## 🔍 Aktueller Stand

### Was CypherMind aktuell HAT:
- ✅ `get_market_data()` Tool - kann bis zu 1000 historische Kerzen abrufen
- ✅ Zugriff auf Binance API für Kursdaten
- ✅ Memory-System für Trade-Learning
- ✅ Bot-Loop, der alle 5 Minuten Kursdaten für Analysen abruft

### Was CypherMind NICHT hat:
- ❌ Kontinuierliches Tracking der letzten 200 Kerzen für laufende Bots
- ❌ Speicherung von Kerzendaten in der Datenbank
- ❌ Post-Trade-Tracking (200 Kerzen nach Verkauf)
- ❌ Systematische Verfolgung für bessere Vorhersagen

## 💡 Vorschlag: Kerzen-Tracking-System

### Feature 1: Pre-Trade-Tracking (200 Kerzen)
**Zweck:** Sammle die letzten 200 Kerzen vor jedem Trade-Entscheidungspunkt

**Implementierung:**
- Im Bot-Loop: Bei jeder Analyse die letzten 200 Kerzen sammeln
- In MongoDB speichern: `bot_candles` Collection
- Struktur:
  ```json
  {
    "bot_id": "uuid",
    "symbol": "BTCUSDT",
    "timeframe": "5m",
    "candles": [...],  // Array mit 200 Kerzen
    "updated_at": "timestamp",
    "trade_phase": "pre_trade"  // oder "post_trade"
  }
  ```

### Feature 2: Post-Trade-Tracking (200 Kerzen nach Verkauf)
**Zweck:** Verfolge weitere 200 Kerzen nach Verkauf, um zu lernen, ob die Entscheidung richtig war

**Implementierung:**
- Nach SELL-Signal: Starte Post-Trade-Tracking
- Sammle 200 neue Kerzen (entsprechend dem Timeframe)
- Speichere mit Verknüpfung zum Trade
- Analysiere später: "Was wäre passiert, wenn wir länger gehalten hätten?"

### Feature 3: Learning-Integration
**Zweck:** Nutze die gesammelten Kerzendaten für besseres Learning

**Implementierung:**
- Erweitere Memory-System um Kerzen-Daten
- Analysiere Muster in Pre-Trade-Kerzen erfolgreicher Trades
- Lerne aus Post-Trade-Kerzen: Timing-Optimierung

## 🏗️ Technische Umsetzung

### 1. Neue MongoDB Collection: `bot_candles`
```python
{
  "bot_id": str,
  "symbol": str,
  "timeframe": str,
  "phase": "pre_trade" | "post_trade",
  "trade_id": Optional[str],  # Verknüpfung zum Trade (bei post_trade)
  "candles": List[Dict],  # Array von Kerzen-Daten
  "start_timestamp": datetime,
  "end_timestamp": datetime,
  "count": int  # Anzahl Kerzen (sollte 200 sein)
}
```

### 2. CandleTracker Klasse
```python
class CandleTracker:
    def __init__(self, db, binance_client):
        self.db = db
        self.binance_client = binance_client
        
    async def track_pre_trade_candles(self, bot_id, symbol, timeframe, limit=200):
        """Sammle und speichere die letzten 200 Kerzen vor Trade"""
        
    async def start_post_trade_tracking(self, bot_id, symbol, timeframe, trade_id):
        """Starte Post-Trade-Tracking nach Verkauf"""
        
    async def update_post_trade_tracking(self, bot_id, trade_id):
        """Aktualisiere Post-Trade-Kerzen (bis 200 erreicht)"""
```

### 3. Integration in Bot-Manager
- Im Bot-Loop: Rufe CandleTracker auf
- Nach SELL: Starte Post-Trade-Tracking
- Speichere Kerzen-Daten in MongoDB

### 4. CypherMind Tools erweitern
- Neues Tool: `get_bot_candles(bot_id, phase="pre_trade")`
- Ermöglicht CypherMind Zugriff auf gesammelte Kerzendaten

## 📊 Vorteile

1. **Bessere Vorhersagen:**
   - CypherMind kann Muster in Pre-Trade-Kerzen erkennen
   - Verknüpfung von Kerzen-Mustern mit Trade-Erfolg

2. **Lernen aus Timing:**
   - Post-Trade-Kerzen zeigen: "War der Verkauf optimal?"
   - Lerne optimale Exit-Timing-Strategien

3. **Datenbasis für ML:**
   - 200 Kerzen vor/nach jedem Trade = wertvolle Trainingsdaten
   - Pattern Recognition verbessern

4. **Retrospektive Analysen:**
   - Später analysieren: "Was wäre passiert bei längerem Halten?"
   - Optimierung der Take-Profit-Strategien

## 🎯 Implementierungsschritte

1. ✅ Analyse (diese Datei)
2. ⬜ Erstelle CandleTracker Klasse
3. ⬜ MongoDB Schema erweitern
4. ⬜ Integration in Bot-Manager
5. ⬜ CypherMind Tools erweitern
6. ⬜ Memory-System Integration
7. ⬜ Tests & Dokumentation

## 💾 Speicher-Bedarf

**Pro Bot:**
- Pre-Trade: 200 Kerzen × ~200 Bytes = 40 KB
- Post-Trade: 200 Kerzen × ~200 Bytes = 40 KB
- **Total pro Bot: ~80 KB**

**Bei 6 autonomen Bots:**
- ~480 KB für aktive Tracking-Daten
- Plus historische Daten (können nach Analyse archiviert werden)

**Empfehlung:** Alte Tracking-Daten nach 30 Tagen archivieren/löschen

## 🚀 Nächste Schritte

Soll ich mit der Implementierung beginnen? Ich würde vorschlagen:

1. **CandleTracker Klasse** erstellen
2. **MongoDB Schema** definieren
3. **Bot-Integration** implementieren
4. **CypherMind Tools** erweitern

Dies würde CypherMind die gewünschten Ressourcen geben! 🎯

