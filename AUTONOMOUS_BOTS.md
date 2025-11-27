# Autonome Bot-Verwaltung durch CypherMind

## Übersicht

CypherMind kann jetzt **autonome Trading-Bots** starten und verwalten, um optimale Profit-Chancen zu nutzen. Das System kombiniert Echtzeitkurse, technische Indikatoren und News-Analysen, um die besten Coins und Strategien zu identifizieren.

## Funktionen

### 1. Coin-Analyse (`analyze_optimal_coins`)

CypherMind kann mehrere Coins analysieren und die besten Trading-Opportunities identifizieren.

**Analyse-Komponenten:**
- **Echtzeitkurse**: Aktuelle Marktpreise
- **Technische Indikatoren**: Alle 5 Strategien werden getestet (MA Crossover, RSI, MACD, Bollinger Bands, Combined)
- **News-Analyse**: Relevante News werden berücksichtigt
- **Volatilität**: 24h-Volatilität wird berechnet
- **Trend-Analyse**: Langfristige Trend-Richtung wird erkannt

**Score-Berechnung:**
- Beste Strategie: 40%
- Trend: 20%
- Volatilität: 20%
- News: 20%

**Parameter:**
- `max_coins`: Max. Anzahl Coins zu analysieren (default: 10, max: 20)
- `min_score`: Mindest-Score (0.0-1.0, default: 0.2)
- `exclude_symbols`: Symbole die ausgeschlossen werden sollen

**Beispiel:**
```python
analyze_optimal_coins(
    max_coins=10,
    min_score=0.3,
    exclude_symbols=["BTCUSDT"]  # Bereits gehandelt
)
```

**Antwort:**
```json
{
  "success": true,
  "count": 5,
  "coins": [
    {
      "symbol": "ETHUSDT",
      "current_price": 2456.78,
      "score": 0.65,
      "profit_potential": "HIGH",
      "best_strategy": "combined",
      "best_strategy_confidence": 0.82,
      "trend": "UP",
      "volatility_24h": 3.2,
      "news_score": 0.3,
      "news_count": 2
    }
  ]
}
```

### 2. Autonomer Bot-Start (`start_autonomous_bot`)

CypherMind kann max. **2 autonome Bots** starten.

**Budget-Berechnung:**
1. **Durchschnittsbudget** der laufenden Bots wird berechnet
2. **Verfügbares Kapital** wird geprüft (USDT Balance)
3. **Max. 40%** des verfügbaren Kapitals
4. Budget = `min(Durchschnittsbudget, 40% verfügbares Kapital)`
5. Minimum: 10 USDT

**Parameter:**
- `symbol`: Trading-Symbol (z.B. "ETHUSDT")
- `strategy`: Strategie (ma_crossover, rsi, macd, bollinger_bands, combined)
- `timeframe`: Timeframe (default: "5m")
- `trading_mode`: SPOT, MARGIN, FUTURES (default: "SPOT")

**Beispiel:**
```python
start_autonomous_bot(
    symbol="ETHUSDT",
    strategy="combined",
    timeframe="15m",
    trading_mode="SPOT"
)
```

**Antwort:**
```json
{
  "success": true,
  "bot_id": "abc123...",
  "symbol": "ETHUSDT",
  "strategy": "combined",
  "budget": 150.50,
  "message": "Autonomous bot started successfully with budget 150.50 USDT (avg: 200.00, max 40%: 150.50)"
}
```

### 3. Bot-Status (`get_autonomous_bots_status`)

CypherMind kann den Status aller seiner autonomen Bots abrufen.

**Antwort:**
```json
{
  "success": true,
  "count": 2,
  "bots": [
    {
      "bot_id": "abc123...",
      "is_running": true,
      "status": {
        "bot_id": "abc123...",
        "is_running": true,
        "config": {...},
        "position": {...},
        "unrealized_pnl": 5.23,
        "unrealized_pnl_percent": 3.45
      }
    }
  ]
}
```

## Workflow

### Typischer Ablauf:

1. **Coin-Analyse durchführen**
   ```
   CypherMind: analyze_optimal_coins(max_coins=10, min_score=0.3)
   ```

2. **Beste Coins identifizieren**
   - Coins mit Score > 0.3
   - Beste Strategie pro Coin
   - Profit-Potenzial bewerten

3. **Autonome Bots starten**
   ```
   CypherMind: start_autonomous_bot(
       symbol="ETHUSDT",
       strategy="combined"  # Beste Strategie aus Analyse
   )
   ```

4. **Bots überwachen**
   ```
   CypherMind: get_autonomous_bots_status()
   ```

5. **Lernen aus Trades**
   - Jeder Bot lernt automatisch aus seinen Trades
   - Memory System speichert Erfolge/Fehler
   - CypherMind kann aus den Ergebnissen lernen

## Budget-Logik

### Beispiel-Berechnung:

**Szenario:**
- 3 laufende Bots mit Budgets: 100 USDT, 150 USDT, 200 USDT
- Verfügbares Kapital: 1000 USDT

**Berechnung:**
1. Durchschnittsbudget = (100 + 150 + 200) / 3 = **150 USDT**
2. Max. 40% Kapital = 1000 * 0.4 = **400 USDT**
3. Budget = min(150, 400) = **150 USDT**

**Wenn verfügbares Kapital niedrig:**
- Verfügbares Kapital: 200 USDT
- Max. 40% = 200 * 0.4 = **80 USDT**
- Budget = min(150, 80) = **80 USDT**

## Learning & Memory

Jeder autonome Bot lernt automatisch:

- **Erfolgreiche Trades**: Welche Strategien/Coins funktionieren?
- **Fehlgeschlagene Trades**: Was sollte vermieden werden?
- **Execution Delay & Slippage**: Wie kann Ausführung verbessert werden?
- **News-Korrelation**: Welche News führten zu erfolgreichen Trades?

CypherMind kann aus den Ergebnissen aller autonomen Bots lernen:
- Welche Coins sind profitabel?
- Welche Strategien funktionieren am besten?
- Welche Kombinationen (Coin + Strategie) sind optimal?

## Limits & Sicherheit

- **Max. 2 autonome Bots** pro CypherMind
- **Max. 40% des verfügbaren Kapitals** pro Bot
- **Automatisches Risikomanagement**: Stop-Loss (-2%), Take-Profit (2-5%)
- **Memory System**: Alle Trades werden für Learning gespeichert

## Best Practices

1. **Coin-Analyse vor Bot-Start**
   - Immer `analyze_optimal_coins` vor `start_autonomous_bot` verwenden
   - Nur Coins mit Score > 0.3 starten
   - Beste Strategie aus Analyse verwenden

2. **Diversifikation**
   - Verschiedene Coins handeln (nicht nur BTC/ETH)
   - Verschiedene Strategien testen
   - Verschiedene Timeframes nutzen

3. **Überwachung**
   - Regelmäßig `get_autonomous_bots_status` aufrufen
   - Performance beobachten
   - Bei schlechter Performance: Bot stoppen und lernen

4. **News berücksichtigen**
   - Wichtige News können Score beeinflussen
   - Regulatorische Änderungen beachten
   - Major Events können große Bewegungen verursachen

## Beispiel-Workflow

```
1. CypherMind: "Ich analysiere die besten Coins für Trading..."
   → analyze_optimal_coins(max_coins=10, min_score=0.3)

2. Ergebnis: ETHUSDT (Score: 0.65, Strategy: combined), SOLUSDT (Score: 0.52, Strategy: rsi)

3. CypherMind: "Ich starte autonome Bots für die besten Coins..."
   → start_autonomous_bot(symbol="ETHUSDT", strategy="combined")
   → start_autonomous_bot(symbol="SOLUSDT", strategy="rsi")

4. CypherMind: "Ich überwache meine autonomen Bots..."
   → get_autonomous_bots_status()

5. Nach einiger Zeit: Bots lernen aus Trades, CypherMind analysiert Ergebnisse
```

## Technische Details

### Coin-Analyse-Algorithmus

1. **Echtzeitkurs abrufen**
2. **Marktdaten für mehrere Timeframes** (5m, 15m, 1h, 4h)
3. **Alle Strategien testen** auf verschiedenen Timeframes
4. **Beste Strategie identifizieren** (höchster Score)
5. **Volatilität berechnen** (24h)
6. **Trend analysieren** (SMA-Vergleich)
7. **News abrufen** und bewerten
8. **Gesamt-Score berechnen** (gewichteter Durchschnitt)
9. **Profit-Potenzial einschätzen** (HIGH/MEDIUM/LOW)

### Budget-Berechnung

```python
# 1. Durchschnittsbudget
running_bots = [b for b in all_bots if b.is_running]
avg_budget = sum(b.amount for b in running_bots) / len(running_bots)

# 2. Verfügbares Kapital
available_capital = binance_client.get_account_balance("USDT", trading_mode)

# 3. Max. 40% des Kapitals
max_budget_from_capital = available_capital * 0.4

# 4. Finales Budget
calculated_budget = min(avg_budget, max_budget_from_capital)

# 5. Minimum sicherstellen
if calculated_budget < 10.0:
    calculated_budget = 10.0
```

## Fehlerbehandlung

- **Max. Bots erreicht**: Fehler wenn bereits 2 Bots laufen
- **Unzureichendes Kapital**: Budget wird auf Minimum (10 USDT) gesetzt
- **Symbol nicht handelbar**: Fehler wird zurückgegeben
- **Binance API Fehler**: Wird geloggt und zurückgegeben

## Monitoring

Alle autonomen Bots werden in der Datenbank markiert:
- `started_by: "CypherMind"`
- `autonomous: true`
- `calculated_budget`: Berechnetes Budget
- `avg_budget_of_running`: Durchschnittsbudget zum Startzeitpunkt
- `available_capital_at_start`: Verfügbares Kapital zum Startzeitpunkt

Diese Informationen können für spätere Analysen verwendet werden.

