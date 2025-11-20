# Agent Configuration Files

Diese YAML-Dateien enthalten die System-Prompts und Konfigurationen für die drei Autogen AI Agents.

## Dateien

- `nexuschat_config.yaml` - NexusChat Agent (User Interface)
- `cyphermind_config.yaml` - CypherMind Agent (Decision & Strategy)
- `cyphertrade_config.yaml` - CypherTrade Agent (Trade Execution)

## Anpassungen ohne Code-Update

Sie können die folgenden Aspekte anpassen, ohne den Code zu ändern:

### 1. System Messages (Prompts)

Ändern Sie das Feld `system_message` um das Verhalten des Agents anzupassen:

```yaml
system_message: |
  Ihr neuer Agent-Prompt hier...
  Mehrere Zeilen möglich.
```

### 2. LLM Parameters

```yaml
temperature: 0.7     # 0.0-1.0 (höher = kreativer)
max_tokens: 2000     # Maximale Response-Länge
timeout: 120         # Timeout in Sekunden
```

### 3. Agent Verhalten

```yaml
verbose: true                    # Detailliertes Logging
autoreply_max_consecutive: 10    # Max. Auto-Replies
```

### 4. Spezifische Parameter

**CypherMind - Strategie-Parameter:**
```yaml
strategy_params:
  ma_crossover:
    fast_period: 20              # Schneller SMA Zeitraum
    slow_period: 50              # Langsamer SMA Zeitraum
    confidence_threshold: 0.7    # Mindest-Konfidenz für Trade
```

**CypherTrade - Sicherheits-Limits:**
```yaml
safety_limits:
  max_order_value_usdt: 1000           # Maximaler Order-Wert
  min_order_value_usdt: 10             # Minimaler Order-Wert
  require_confirmation_above_usdt: 500 # Bestätigung ab diesem Wert
```

## Änderungen aktivieren

Nach Änderungen an den YAML-Dateien:

```bash
sudo supervisorctl restart backend
```

## Best Practices

1. **Backup erstellen** vor Änderungen
2. **Kleine Änderungen** testen
3. **System Prompts** klar und präzise formulieren
4. **Temperature** niedrig halten für konsistentes Verhalten (0.3-0.7)
5. **Safety Limits** bei CypherTrade nicht zu hoch setzen

## Beispiel: Agent-Persönlichkeit ändern

Wenn Sie CypherMind konservativer machen möchten:

```yaml
system_message: |
  Du bist CypherMind, ein SEHR vorsichtiger strategischer Analyst.
  
  Zusätzliche Regel:
  - Handel NUR wenn alle Indikatoren eindeutig sind
  - Bei kleinsten Zweifeln: HOLD
  - Bevorzuge kleinere, sichere Gewinne
  
temperature: 0.3  # Noch niedriger für mehr Konsistenz
```

## Warnung

⚠️ Änderungen an Agent-Prompts können das Trading-Verhalten erheblich beeinflussen.
Testen Sie Änderungen immer erst mit Binance Testnet!