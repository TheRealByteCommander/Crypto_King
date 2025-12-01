# Trading Strategien - Project CypherTrade

Umfassender Guide zu allen verfügbaren Trading-Strategien.

## 📊 Verfügbare Strategien

Project CypherTrade unterstützt **6 Trading-Strategien**:

1. **Moving Average Crossover** - Trend-Folge Strategie
2. **RSI** - Momentum-basierte Strategie
3. **MACD** - Trend und Momentum Kombination
4. **Bollinger Bands** - Volatilitäts-basierte Strategie
5. **Combined** - Multi-Indikator Strategie
6. **Grid Trading** - Range Trading Strategie

---

## 1. Moving Average Crossover (MA Crossover)

### Beschreibung
Klassische Trend-Folge-Strategie basierend auf zwei Simple Moving Averages (SMA).

### Indikatoren
- **Fast SMA**: 20 Perioden (kurzfristiger Trend)
- **Slow SMA**: 50 Perioden (langfristiger Trend)

### Signale

**BUY Signal:**
- Fast SMA kreuzt Slow SMA von unten nach oben
- Indikation: Aufwärtstrend beginnt

**SELL Signal:**
- Fast SMA kreuzt Slow SMA von oben nach unten
- Indikation: Abwärtstrend beginnt

**HOLD:**
- Keine Kreuzung
- SMAs parallel oder zu nah beieinander

### Confidence Level
- Basis: 0.6
- Erhöht sich mit Distanz zwischen SMAs
- Maximum: 0.9

### Best Practices
- ✅ Gut für: Starke Trends, längerfristige Trades
- ❌ Schlecht für: Seitwärtsmärkte, volatile Märkte
- 💡 Tipp: Kombiniere mit RSI zur Bestätigung

### Konfiguration

In `/app/backend/agent_configs/cyphermind_config.yaml`:

```yaml
strategy_params:
  ma_crossover:
    fast_period: 20        # Schneller SMA
    slow_period: 50        # Langsamer SMA
    confidence_threshold: 0.6
```

### Beispiel-Trade

```
Zeitpunkt: 10:00
Fast SMA: $48,500
Slow SMA: $48,000
Previous Fast SMA: $47,950
Previous Slow SMA: $48,050

→ Fast SMA crossed above Slow SMA
→ Signal: BUY
→ Confidence: 0.75
→ Reason: "Bullish crossover detected"
```

---

## 2. RSI (Relative Strength Index)

### Beschreibung
Momentum-Oszillator der überkaufte und überverkaufte Bedingungen identifiziert.

### Indikatoren
- **RSI Period**: 14 Perioden
- **Oversold Level**: 30
- **Overbought Level**: 70

### Signale

**BUY Signal:**
- RSI kreuzt über Oversold-Level (30) → Confidence 0.7
- RSI < 25 (extrem überverkauft) → Confidence 0.85

**SELL Signal:**
- RSI kreuzt unter Overbought-Level (70) → Confidence 0.7
- RSI > 75 (extrem überkauft) → Confidence 0.85

**HOLD:**
- RSI zwischen 30 und 70 (neutrale Zone)

### Confidence Level
- Normal Crossing: 0.7
- Extreme Levels (<25 oder >75): 0.85

### Best Practices
- ✅ Gut für: Seitwärtsmärkte, Mean-Reversion
- ❌ Schlecht für: Starke Trends (kann lange überkauft/überverkauft bleiben)
- 💡 Tipp: Verwende 30/70 für normale Märkte, 20/80 für volatile Märkte

### Konfiguration

```yaml
strategy_params:
  rsi:
    period: 14              # RSI Berechnung Periode
    oversold: 30            # Oversold Schwelle
    overbought: 70          # Overbought Schwelle
    confidence_threshold: 0.7
```

### Beispiel-Trade

```
Zeitpunkt: 10:05
RSI: 28
Previous RSI: 32
Oversold: 30

→ RSI crossed below oversold level
→ Signal: BUY
→ Confidence: 0.70
→ Reason: "RSI indicates oversold condition"
```

---

## 3. MACD (Moving Average Convergence Divergence)

### Beschreibung
Trend-Following Momentum-Indikator der Beziehung zwischen zwei EMAs zeigt.

### Indikatoren
- **Fast EMA**: 12 Perioden
- **Slow EMA**: 26 Perioden
- **Signal Line**: 9 Perioden EMA des MACD

### Signale

**BUY Signal:**
- MACD Line kreuzt Signal Line von unten nach oben
- Indikation: Bullischer Momentum-Shift

**SELL Signal:**
- MACD Line kreuzt Signal Line von oben nach unten
- Indikation: Bearisher Momentum-Shift

**HOLD:**
- Keine Kreuzung
- MACD und Signal parallel

### Confidence Level
- Kreuzung: 0.75
- Erhöht sich bei starkem Histogram

### Best Practices
- ✅ Gut für: Trend-Identifikation, Momentum-Shifts
- ❌ Schlecht für: Choppy Markets
- 💡 Tipp: Achte auf Histogram-Divergenzen

### Konfiguration

```yaml
strategy_params:
  macd:
    fast_period: 12         # Fast EMA
    slow_period: 26         # Slow EMA
    signal_period: 9        # Signal Line
    confidence_threshold: 0.7
```

### Beispiel-Trade

```
Zeitpunkt: 10:10
MACD: 125
Signal: 120
Previous MACD: 118
Previous Signal: 122

→ MACD crossed above Signal Line
→ Signal: BUY
→ Confidence: 0.75
→ Reason: "Bullish MACD crossover"
```

---

## 4. Bollinger Bands

### Beschreibung
Volatilitäts-Indikator der Preis-Kanäle basierend auf Standardabweichung zeigt.

### Indikatoren
- **Middle Band**: 20-Period SMA
- **Upper Band**: SMA + (2 × Std Dev)
- **Lower Band**: SMA - (2 × Std Dev)

### Signale

**BUY Signal:**
- Preis bounced off Lower Band → Confidence 0.7
- Preis < Lower Band × 0.98 (weit unter Band) → Confidence 0.8

**SELL Signal:**
- Preis bounced off Upper Band → Confidence 0.7
- Preis > Upper Band × 1.02 (weit über Band) → Confidence 0.8

**HOLD:**
- Preis innerhalb der Bänder

### Confidence Level
- Band Touch/Bounce: 0.7
- Außerhalb der Bands: 0.8

### Best Practices
- ✅ Gut für: Volatilitäts-Trading, Mean-Reversion
- ❌ Schlecht für: Starke Breakouts
- 💡 Tipp: Kombination mit RSI für bessere Signale

### Konfiguration

```yaml
strategy_params:
  bollinger_bands:
    period: 20              # SMA Period
    std_dev: 2              # Standard Deviations
    confidence_threshold: 0.7
```

### Beispiel-Trade

```
Zeitpunkt: 10:15
Price: $47,850
Lower Band: $48,000
Previous Price: $47,950

→ Price bounced off lower Bollinger Band
→ Signal: BUY
→ Confidence: 0.70
→ Reason: "Mean reversion from lower band"
```

---

## 5. Combined Strategy (Multi-Indikator)

### Beschreibung
Kombiniert MA Crossover, RSI und MACD für robustere Signale durch Konsens.

### Komponenten
- Moving Average Crossover
- RSI Strategy
- MACD Strategy

### Signale

**BUY Signal:**
- Mindestens 2 von 3 Strategien zeigen BUY
- Confidence steigt mit Anzahl übereinstimmender Signale

**SELL Signal:**
- Mindestens 2 von 3 Strategien zeigen SELL
- Confidence steigt mit Anzahl übereinstimmender Signale

**HOLD:**
- Weniger als 2 Übereinstimmungen
- Gemischte Signale

### Confidence Level
```
2/3 Strategien: 0.6 + 0.2 = 0.80
3/3 Strategien: 0.6 + 0.3 = 0.90
```

### Best Practices
- ✅ Gut für: Reduzierte False Signals, höhere Sicherheit
- ❌ Schlecht für: Weniger Trades, langsamere Reaktion
- 💡 Tipp: Beste Strategie für Anfänger

### Konfiguration

```yaml
strategy_params:
  combined:
    min_signals: 2          # Minimum übereinstimmende Signale
    confidence_threshold: 0.75
```

### Beispiel-Trade

```
Zeitpunkt: 10:20

MA Crossover: BUY (Fast > Slow crossover)
RSI: BUY (RSI < 30)
MACD: HOLD (No crossover)

→ 2/3 Strategies suggest BUY
→ Signal: BUY
→ Confidence: 0.80
→ Reason: "Multi-indicator consensus"
```

---

## 6. Grid Trading Strategy

### Beschreibung
Range-Trading-Strategie die von Preis-Oszillationen in einem definierten Bereich profitiert. Erstellt ein Raster von Preis-Levels oberhalb und unterhalb des aktuellen Preises.

### Indikatoren
- **Grid Levels**: Anzahl der Levels oberhalb und unterhalb (Standard: 5)
- **Grid Spacing**: Abstand zwischen Levels in Prozent (Standard: 1.0%)

### Signale

**BUY Signal:**
- Preis erreicht oder fällt unter ein unteres Grid-Level → Confidence 0.6-0.9
- Preis fällt signifikant (>0.5× Grid-Spacing) → Confidence 0.7-0.85

**SELL Signal:**
- Preis erreicht oder steigt über ein oberes Grid-Level → Confidence 0.6-0.9
- Preis steigt signifikant (>0.5× Grid-Spacing) → Confidence 0.7-0.85

**HOLD:**
- Preis innerhalb des Grid-Bereichs
- Keine signifikante Bewegung

### Confidence Level
- Grid-Level erreicht: 0.6-0.9 (abhängig von Nähe zum Level)
- Signifikante Bewegung: 0.7-0.85 (abhängig von Bewegungsgröße)

### Best Practices
- ✅ Gut für: Range-Bound Märkte, Seitwärtsbewegungen
- ❌ Schlecht für: Starke Trends, Breakouts
- 💡 Tipp: Anpassung der Grid-Spacing an Volatilität (höhere Volatilität = größere Spacing)

### Konfiguration

```yaml
strategy_params:
  grid:
    grid_levels: 5              # Anzahl Levels oberhalb/unterhalb
    grid_spacing_percent: 1.0    # Abstand zwischen Levels in %
    confidence_threshold: 0.6
```

### Beispiel-Trade

```
Zeitpunkt: 10:25
Current Price: $48,000
Grid Spacing: 1.0% = $480
Lower Grid Level: $47,520
Previous Price: $47,600

→ Price reached lower grid level at $47,520
→ Signal: BUY
→ Confidence: 0.75
→ Reason: "Price reached lower grid level (Grid spacing: 1.0%)"
```

---

## 📊 Strategie-Vergleich

| Strategie | Typ | Trade-Frequenz | Risiko | Best For |
|-----------|-----|----------------|--------|----------|
| MA Crossover | Trend | Niedrig | Mittel | Trends |
| RSI | Momentum | Mittel | Mittel | Seitwärts |
| MACD | Trend+Momentum | Mittel | Mittel | Trends |
| Bollinger Bands | Volatilität | Hoch | Mittel-Hoch | Volatil |
| Combined | Multi | Niedrig | Niedrig | Alle |
| Grid Trading | Range | Hoch | Mittel | Range-Bound |

---

## 🎯 Strategie-Auswahl Guide

### Für Anfänger
**Empfehlung: Combined Strategy**
- Reduzierte False Signals
- Höhere Confidence
- Lernen durch Multi-Indikator-Analyse

### Für Trending Markets
**Empfehlung: MA Crossover oder MACD**
- Fangen starke Trends ein
- Klare Signale
- Weniger Noise

### Für Volatile Markets
**Empfehlung: RSI oder Bollinger Bands**
- Profitieren von Volatilität
- Mean-Reversion
- Häufigere Trades

### Für Seitwärtsmärkte
**Empfehlung: RSI oder Grid Trading**
- RSI: Oversold/Overbought funktioniert gut
- Grid Trading: Profitiert von Preis-Oszillationen
- Häufige Trades
- Range-Trading

---

## ⚙️ Strategie wechseln

### Via Dashboard

1. Bot stoppen (falls laufend)
2. Strategie aus Dropdown wählen
3. Bot neu starten

### Via .env Datei

```bash
nano /app/backend/.env
```

Ändern:
```env
DEFAULT_STRATEGY="rsi"  # oder macd, bollinger_bands, combined
```

Restart:
```bash
sudo supervisorctl restart cyphertrade-backend
```

### Strategie-Parameter anpassen

Edit `/app/backend/agent_configs/cyphermind_config.yaml`:

```yaml
strategy_params:
  rsi:
    period: 10              # Kürzere Periode = mehr Signale
    oversold: 25            # Aggressiver
    overbought: 75          # Aggressiver
```

---

## 📈 Backtesting-Tipps

### Testnet zuerst!
```env
BINANCE_TESTNET=true
```

### Kleine Beträge
```
Amount: 10-50 USDT
```

### Verschiedene Märkte testen
- **Trending:** BTCUSDT, ETHUSDT
- **Volatile:** DOGEUSDT, SHIBUSDT
- **Stable:** USDCUSDT (für Tests)

### Logs analysieren

```bash
tail -f /var/log/supervisor/cyphertrade-backend-error.log | grep "Strategy"
```

---

## 🚨 Wichtige Hinweise

### False Signals
**Alle Strategien** können False Signals generieren:
- MA Crossover: Whipsaws in Seitwärtsmärkten
- RSI: Bleibt lange in extremen Bereichen
- MACD: Verzögerung bei schnellen Moves
- Bollinger Bands: Breakouts statt Bounces
- Combined: Langsamer, verpasst schnelle Moves

### Risk Management
- **Stop Loss**: Implementiere eigene Stop-Loss-Logik
- **Position Sizing**: Nie mehr als 2-5% des Kapitals
- **Max Trades**: Limitiere tägliche Trades
- **Drawdown Limit**: Stoppe bei X% Verlust

### Marktbedingungen
**Keine Strategie funktioniert immer:**
- Passe Strategie an Marktbedingungen an
- Überwache Performance regelmäßig
- Sei bereit zu wechseln

---

## 🔧 Eigene Strategie hinzufügen

### 1. Strategie-Klasse erstellen

Edit `/app/backend/strategies.py`:

```python
class MyCustomStrategy(TradingStrategy):
    def __init__(self):
        super().__init__("my_custom")
    
    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        # Ihre Logik hier
        signal = "BUY"  # oder SELL, HOLD
        confidence = 0.75
        
        return {
            "signal": signal,
            "reason": "Your reason",
            "confidence": confidence,
            "indicators": {...},
            "timestamp": str(df.iloc[-1]['timestamp'])
        }
```

### 2. Zu Factory hinzufügen

```python
def get_strategy(strategy_name: str) -> TradingStrategy:
    strategies = {
        "ma_crossover": MovingAverageCrossover(),
        "rsi": RSIStrategy(),
        "my_custom": MyCustomStrategy(),  # Ihre Strategie
    }
    return strategies[strategy_name]
```

### 3. Config hinzufügen

In `cyphermind_config.yaml`:

```yaml
strategy_params:
  my_custom:
    param1: value1
    param2: value2
```

### 4. Backend restart

```bash
sudo supervisorctl restart cyphertrade-backend
```

---

## 📚 Weitere Ressourcen

- **TradingView**: Chart-Analyse mit Indikatoren
- **Investopedia**: Strategie-Erklärungen
- **Binance Academy**: Krypto-Trading-Basics

---

**⚠️ Trading-Warnung:**

Alle Strategien sind für **Bildungszwecke**. Crypto Trading ist hochriskant. Keine Strategie garantiert Gewinne. Testen Sie immer zuerst mit Testnet und kleinen Beträgen!

---

**Viel Erfolg beim Trading! 📈**
