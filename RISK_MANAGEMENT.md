# Risikomanagement - Stop-Loss & Take-Profit

## 🛡️ Übersicht

Project CypherTrade implementiert automatisches Risikomanagement mit Stop-Loss und Take-Profit Regeln, um Verluste zu begrenzen und Gewinne zu sichern.

## 📊 Implementierte Regeln

### Stop-Loss: -5%
- **Trigger**: Position wird automatisch geschlossen bei **-5% Verlust** oder mehr
- **Zweck**: Begrenzt Verluste und schützt das Kapital
- **Funktioniert für**: LONG und SHORT Positionen
- **Überwachung**: Automatisch in jedem Bot-Loop (alle 5 Minuten)

### Take-Profit: ≥2% (MINDESTANFORDERUNG)
- **Trigger**: Position wird automatisch geschlossen bei **≥2% Gewinn**
- **KRITISCH**: Verkäufe unter 2% Gewinn werden automatisch blockiert!
- **Zweck**: Sichert Gewinne und verhindert zu frühe Verkäufe
- **Funktioniert für**: LONG und SHORT Positionen
- **Überwachung**: Automatisch in jedem Bot-Loop (alle 5 Minuten)
- **Trailing Stop**: Bei LONG-Positionen wird Take-Profit ausgelöst, wenn Preis 3% vom Höchststand fällt (aber nur wenn ≥2% Gewinn)

## 🔧 Funktionsweise

### Automatische Überwachung

Der Bot prüft in jedem Loop (alle 5 Minuten):

1. **Position vorhanden?** → Prüfe P&L
2. **P&L berechnen** → Aktueller Preis vs. Entry-Preis
3. **Stop-Loss prüfen** → Wenn ≤ -5% → Position schließen
4. **Take-Profit prüfen** → Wenn ≥2% → Position schließen (Trailing Stop bei LONG)
5. **SELL-Befehle validieren** → Blockiere automatisch alle Verkäufe unter 2% Gewinn

### Position-Schließung

Bei Stop-Loss oder Take-Profit:
- ✅ Position wird sofort geschlossen (MARKET Order)
- ✅ Trade wird in Datenbank gespeichert mit `exit_reason`
- ✅ Learning-System wird aufgerufen (Agents lernen aus Trade)
- ✅ Position-Status wird zurückgesetzt

## 📝 Trade-Dokumentation

Geschlossene Positionen werden mit folgenden Informationen gespeichert:

```json
{
  "exit_reason": "STOP_LOSS" | "TAKE_PROFIT",
  "pnl": -100.50,
  "pnl_percent": -2.15,
  "position_entry_price": 50000.0,
  "entry_price": 49000.0,
  "strategy": "ma_crossover",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 🎯 Beispiele

### Beispiel 1: Stop-Loss

```
Position: LONG
Entry Price: 50,000 USDT
Current Price: 47,500 USDT
P&L: -5.0%

→ STOP LOSS triggered (≥5% Verlust)
→ Position geschlossen
→ Trade gespeichert mit exit_reason: "STOP_LOSS"
```

### Beispiel 2: Take-Profit

```
Position: LONG
Entry Price: 50,000 USDT
Current Price: 51,500 USDT
P&L: +3.0%

→ TAKE PROFIT triggered (≥2% Gewinn)
→ Position geschlossen
→ Trade gespeichert mit exit_reason: "TAKE_PROFIT"
```

### Beispiel 3: Verkauf unter 2% wird blockiert

```
Position: LONG
Entry Price: 50,000 USDT
Current Price: 50,800 USDT
P&L: +1.6%

→ SELL-Befehl von Agent empfangen
→ System prüft: Gewinn 1.6% < Minimum 2%
→ SELL-Befehl BLOCKIERT
→ Position bleibt offen bis ≥2% Gewinn erreicht
```

### Beispiel 3: SHORT Position

```
Position: SHORT
Entry Price: 50,000 USDT
Current Price: 48,500 USDT
P&L: +3.0% (für SHORT: Profit wenn Preis fällt)

→ TAKE PROFIT triggered
→ BUY Order zum Schließen der SHORT Position
→ Trade gespeichert mit exit_reason: "TAKE_PROFIT"
```

## ⚙️ Konfiguration

Die Regeln sind in `backend/constants.py` definiert:

```python
STOP_LOSS_PERCENT = -5.0  # Stop loss at -5%
TAKE_PROFIT_MIN_PERCENT = 2.0  # Minimum take profit at +2% (MANDATORY - Verkäufe unter 2% werden blockiert)
TAKE_PROFIT_TRAILING_PERCENT = 3.0  # Trailing stop: sell when price falls 3% from highest price
```

**Anpassung:** Edit `backend/constants.py` und Backend neu starten.

## 🔍 Monitoring

### Logs

Stop-Loss/Take-Profit Aktivitäten werden geloggt:

```bash
# Backend Logs
tail -f /var/log/supervisor/cyphertrade-backend-error.log | grep -i "stop\|profit"
```

### Dashboard

Im Dashboard können Sie sehen:
- **Trade History**: Trades mit `exit_reason` Filter
- **Performance Charts**: P&L mit Stop-Loss/Take-Profit Markierungen
- **Agent Logs**: Meldungen über Stop-Loss/Take-Profit Trigger

### API

```bash
# Alle Trades mit Stop-Loss
curl "http://localhost:8001/api/trades?exit_reason=STOP_LOSS"

# Alle Trades mit Take-Profit
curl "http://localhost:8001/api/trades?exit_reason=TAKE_PROFIT"
```

## 🧠 Learning Integration

Stop-Loss und Take-Profit Trades werden automatisch für das Learning-System gespeichert:

- **CypherMind** lernt aus Entscheidungen
- **CypherTrade** lernt aus Ausführungen
- **Pattern Recognition** erkennt erfolgreiche/fehlgeschlagene Trades
- **Memory System** speichert Lessons

Siehe: [MEMORY_SYSTEM.md](MEMORY_SYSTEM.md)

## ⚠️ Wichtige Hinweise

1. **Überwachungs-Intervall**: Stop-Loss/Take-Profit wird alle 5 Minuten geprüft (Bot-Loop Intervall)
2. **Keine Echtzeit-Überwachung**: Bei sehr schnellen Preisbewegungen kann es zu geringfügigen Abweichungen kommen
3. **Market Orders**: Positionen werden mit MARKET Orders geschlossen (sofortige Ausführung)
4. **Gebühren**: Binance-Gebühren (0.2% gesamt) werden bei P&L-Berechnung berücksichtigt
5. **Testnet**: Funktioniert auf Testnet und Live-Accounts

## 📊 Best Practices

1. **Kleine Beträge testen**: Testen Sie Stop-Loss/Take-Profit mit kleinen Beträgen
2. **Monitoring**: Beobachten Sie die Logs nach Bot-Start
3. **Trade History prüfen**: Überprüfen Sie, ob Trades korrekt dokumentiert sind
4. **Learning beobachten**: Prüfen Sie Memory-System nach mehreren Trades

## 🔄 Deaktivierung

Um Stop-Loss/Take-Profit zu deaktivieren (NICHT empfohlen):

Edit `backend/bot_manager.py`:
- Kommentiere Zeile 357-358 aus: `await self._check_stop_loss_and_take_profit(...)`

**WARNUNG**: Deaktivierung entfernt wichtigen Risikoschutz!

---

**Made with 🛡️ - Automatic Risk Management for Safer Trading**

