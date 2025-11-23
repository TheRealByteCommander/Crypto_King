# 📍 Trading Mode einstellen - Anleitung

## Wo findest du die Trading Mode Auswahl?

Die **Trading Mode** Auswahl befindet sich im **"Start New Bot"** Formular:

```
┌─────────────────────────────────────────────┐
│ Start New Bot                               │
├─────────────────────────────────────────────┤
│ Strategy: [RSI...]                          │
│ Symbol: [BTCUSDT]                           │
│ Timeframe: [5 Minuten]                      │
│ Trading Mode: [SPOT (Long Only)]  ⬅️ HIER! │
│ Amount (USDT): [100]                        │
│                                             │
│ [Start New Bot]                             │
└─────────────────────────────────────────────┘
```

## Optionen:

1. **SPOT (Long Only)**
   - Standard-Modus
   - Nur Long-Positionen möglich
   - Kein Short-Trading

2. **MARGIN (Long + Short)**
   - Long- und Short-Positionen möglich
   - Erlaubt Short-Trading
   - Nutzt Margin-Konto

3. **FUTURES (Long + Short)**
   - Long- und Short-Positionen möglich
   - Erlaubt Short-Trading
   - Nutzt Futures-Konto
   - Leverage möglich

## Wenn die Auswahl nicht sichtbar ist:

### Option 1: Server aktualisieren

```bash
cd /app
git pull
chmod +x update-ct-server.sh
sudo bash update-ct-server.sh
```

### Option 2: Browser-Cache leeren

1. Drücke **Strg + Shift + R** (Hard Reload)
2. Oder: **Strg + F5**
3. Oder: Browser-Cache manuell leeren

### Option 3: Frontend neu bauen (Production Build)

```bash
cd /app
sudo bash setup-production-build.sh
```

## Verwendung:

1. **Trading Mode** auswählen (SPOT/MARGIN/FUTURES)
2. Alle anderen Einstellungen wie gewohnt ausfüllen
3. **"Start New Bot"** klicken
4. Der Bot wird mit dem gewählten Trading Mode gestartet

## Hinweise:

- **SPOT**: Für normale Long-Only Strategien
- **MARGIN/FUTURES**: Für Short-Trading notwendig
- **Short-Positionen**: Werden automatisch eröffnet, wenn SELL-Signal kommt und keine Position vorhanden ist

