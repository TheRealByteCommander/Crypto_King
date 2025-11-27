# Agent Tools System

## Übersicht

Alle Agents haben jetzt Zugriff auf echte Tools/Funktionen, um ihre Aufgaben zu erfüllen:

## CypherMind - Market Data Tools

CypherMind hat Zugriff auf folgende Tools für Echtzeit-Marktdaten:

1. **get_current_price(symbol)** - Echtzeit-Kurs für ein Symbol abrufen
   - Beispiel: `get_current_price("BTCUSDT")` → `{"price": 45678.90}`
   - WICHTIG: CypherMind MUSS diese Funktion verwenden, um echte Kurse zu bekommen!

2. **get_market_data(symbol, interval, limit)** - Historische Kline-Daten für technische Analyse
   - Beispiel: `get_market_data("BTCUSDT", "5m", 100)`
   - Gibt OHLCV-Daten zurück für Indikator-Berechnung

3. **get_bot_status()** - Aktuellen Bot-Status abrufen
   - Zeigt: Bot läuft, Strategie, Symbol, Betrag

4. **get_recent_analyses(limit)** - Letzte Marktanalysen abrufen
   - Für Kontext und Trend-Erkennung

5. **get_tradable_symbols(search)** - Alle handelbaren Symbole abrufen
   - Beispiel: `get_tradable_symbols(search="DOGE")`

6. **validate_symbol(symbol)** - Prüfen ob Symbol handelbar ist
   - Beispiel: `validate_symbol("BTCUSDT")`

7. **analyze_optimal_coins(max_coins, min_score, exclude_symbols)** - Analysiert Coins für optimale Trading-Opportunities
   - Kombiniert Echtzeitkurse, technische Indikatoren, News, Volatilität, Trends
   - Gibt Score (0.0-1.0) und beste Strategie pro Coin zurück
   - Beispiel: `analyze_optimal_coins(max_coins=10, min_score=0.3)`
   - Siehe: [AUTONOMOUS_BOTS.md](AUTONOMOUS_BOTS.md) für Details

8. **start_autonomous_bot(symbol, strategy, timeframe, trading_mode)** - Startet autonomen Bot
   - Max. 2 autonome Bots pro CypherMind
   - Budget wird automatisch berechnet: Durchschnittsbudget der laufenden Bots, aber max. 40% des verfügbaren Kapitals
   - Beispiel: `start_autonomous_bot(symbol="ETHUSDT", strategy="combined")`
   - Siehe: [AUTONOMOUS_BOTS.md](AUTONOMOUS_BOTS.md) für Details

9. **get_autonomous_bots_status()** - Status aller autonomen Bots abrufen
   - Zeigt Performance und Learning-Progress
   - Beispiel: `get_autonomous_bots_status()`

## CypherTrade - Trade Execution Tools

CypherTrade hat Zugriff auf folgende Tools für sichere Trade-Ausführung:

1. **get_current_price(symbol)** - Kurs vor Order-Platzierung prüfen

2. **get_account_balance(asset)** - Verfügbare Balance prüfen
   - Beispiel: `get_account_balance("USDT")` → `{"balance": 10000.0}`

3. **execute_order(symbol, side, quantity, order_type)** - Order ausführen
   - Beispiel: `execute_order("BTCUSDT", "BUY", 0.01, "MARKET")`
   - WICHTIG: Nur von CypherMind autorisierte Orders!

4. **get_order_status(symbol, order_id)** - Order-Status prüfen

## NexusChat - Information Tools

NexusChat hat Zugriff auf folgende Tools für Benutzer-Information:

1. **get_bot_status()** - Bot-Status für Benutzer anzeigen

2. **get_current_price(symbol)** - Echte Kurse für Benutzer abrufen

3. **get_trade_history(limit)** - Letzte Trades anzeigen

4. **get_recent_analyses(limit)** - Marktanalysen für Benutzer erklären

5. **get_crypto_news(limit, symbols, query)** - Aktuelle Krypto-News von vertrauenswürdigen Quellen
   - Beispiel: `get_crypto_news(limit=10, symbols=["BTC", "ETH"])`
   - Quellen: CoinDesk, CoinTelegraph, CryptoSlate, Decrypt, The Block
   - Automatische Spam/Fake-News-Filterung
   - Rate Limiting: max. 10 Requests/Minute pro Quelle
   - Siehe: [CRYPTO_NEWS_SYSTEM.md](CRYPTO_NEWS_SYSTEM.md) für Details

6. **share_news_with_agents(articles, target_agents, priority)** - Wichtige News an andere Agents weiterleiten
   - Beispiel: `share_news_with_agents(articles=[...], target_agents=["both"], priority="high")`
   - Teilt News mit CypherMind (für Trading-Entscheidungen) und/oder CypherTrade (für Risikomanagement)
   - Nur wirklich relevante News weiterleiten (Regulation, Major Events, Security-Breaches, etc.)
   - Siehe: [CRYPTO_NEWS_SYSTEM.md](CRYPTO_NEWS_SYSTEM.md) für Details

## Wichtig für CypherMind

CypherMind MUSS die Funktion `get_current_price()` verwenden, um echte Echtzeit-Kurse zu bekommen!

**Vor jeder Analyse:**
```python
# CypherMind sollte immer zuerst den aktuellen Kurs abrufen:
current_price = get_current_price("BTCUSDT")
# Dann kann es mit echten Daten analysieren
```

**Beispiel für CypherMind Workflow:**
1. `get_current_price("BTCUSDT")` → Echtzeit-Kurs
2. `get_market_data("BTCUSDT", "5m", 100)` → Historische Daten
3. Berechne Indikatoren (RSI, MACD, etc.)
4. Treffe Handelsentscheidung basierend auf echten Daten
5. Sende Befehl an CypherTrade

## Tool-Registrierung

Tools werden automatisch bei Agent-Initialisierung registriert:
- Tools sind im `llm_config["functions"]` enthalten
- UserProxy hat `function_map` für Tool-Ausführung
- Tools sind asynchron und werden korrekt verarbeitet

## Fehlerbehandlung

Alle Tools geben strukturierte Antworten zurück:
- `{"success": True, "result": {...}}` bei Erfolg
- `{"success": False, "error": "..."}` bei Fehler

## Test

Um zu testen, ob Tools funktionieren:
1. Starte den Bot
2. Frage NexusChat: "Was ist der aktuelle BTC-Preis?"
3. NexusChat sollte `get_current_price("BTCUSDT")` aufrufen
4. Die Antwort sollte den echten Kurs enthalten

