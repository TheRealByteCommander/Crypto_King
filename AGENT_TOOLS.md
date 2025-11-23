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

