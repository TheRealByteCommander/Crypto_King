# Agent-Konfiguration ohne Code-Update

Die drei AI Agents können vollständig über YAML-Dateien konfiguriert werden, ohne den Code zu ändern.

## 📁 Konfigurations-Dateien

```
/app/backend/agent_configs/
├── nexuschat_config.yaml    # User Interface Agent
├── cyphermind_config.yaml   # Decision & Strategy Agent  
├── cyphertrade_config.yaml  # Trade Execution Agent
└── README.md                # Detaillierte Dokumentation
```

## 🎯 Schnellstart: Agent-Prompt ändern

### Beispiel: CypherMind konservativer machen

**Datei:** `/app/backend/agent_configs/cyphermind_config.yaml`

```yaml
system_message: |
  Du bist CypherMind, ein SEHR vorsichtiger strategischer Analyst.
  
  Deine Aufgaben:
  - Analysiere Marktdaten extrem gründlich
  - Handel NUR bei eindeutigen Signalen
  - Bei JEGLICHEM Zweifel: HOLD
  - Bevorzuge kleine, sichere Gewinne
  
  Zusätzliche Sicherheitsregel:
  - Minimum 3 bestätigende Indikatoren für Trade
  - Maximale Position: 50% der verfügbaren Mittel

temperature: 0.3  # Niedriger = konservativer
```

**Anwenden:**
```bash
sudo supervisorctl restart backend
```

## 🔧 Konfigurierbare Parameter

### 1. System Message (Agent-Persönlichkeit)

Das Kernstück - definiert das Verhalten des Agents:

```yaml
system_message: |
  Ihr Agent-Prompt hier...
  Mehrere Zeilen möglich
  - Bullet Points
  - Strukturierte Anweisungen
```

**Best Practices:**
- Klare, präzise Sprache
- Spezifische Aufgaben definieren
- Entscheidungsprinzipien formulieren
- Beispiele geben

### 2. LLM Temperature

Steuert die "Kreativität" des Modells:

```yaml
temperature: 0.7
```

- **0.0-0.3**: Deterministisch, konsistent (gut für CypherTrade)
- **0.4-0.7**: Ausbalanciert (gut für CypherMind)
- **0.8-1.0**: Kreativ, variabel (gut für NexusChat)

### 3. Max Tokens

Maximale Länge der Response:

```yaml
max_tokens: 2000
```

- **1000-2000**: Standard
- **3000+**: Für lange Analysen

### 4. Timeout

Maximale Wartezeit auf LLM Response:

```yaml
timeout: 120  # Sekunden
```

### 5. Strategieparameter (CypherMind)

```yaml
strategy_params:
  ma_crossover:
    fast_period: 20         # Schneller SMA
    slow_period: 50         # Langsamer SMA
    confidence_threshold: 0.7
```

### 6. Sicherheitslimits (CypherTrade)

```yaml
safety_limits:
  max_order_value_usdt: 1000
  min_order_value_usdt: 10
  require_confirmation_above_usdt: 500
```

## 📝 Beispiel-Konfigurationen

### Aggressive Trading (CypherMind)

```yaml
system_message: |
  Du bist CypherMind, ein aggressiver Trader.
  
  - Nutze alle Trading-Opportunities
  - Höhere Risiko-Toleranz
  - Schnelle Entscheidungen
  
temperature: 0.6  # Etwas höher für Flexibilität

strategy_params:
  ma_crossover:
    fast_period: 10   # Kürzere Perioden = mehr Signale
    slow_period: 30
```

### Konservative Trading (CypherMind)

```yaml
system_message: |
  Du bist CypherMind, ein konservativer Analyst.
  
  - Nur eindeutige Signale
  - Lange Beobachtung
  - Sicherheit vor Profit
  
temperature: 0.3  # Niedrig für Konsistenz

strategy_params:
  ma_crossover:
    fast_period: 30   # Längere Perioden = weniger Signale
    slow_period: 100
```

### Deutsch sprechender Agent (NexusChat)

```yaml
system_message: |
  Du bist Nexus, der deutsche Kommunikations-Hub.
  
  - Antworte IMMER auf Deutsch
  - Verwende höfliche, professionelle Sprache
  - Erkläre technische Begriffe
  - Nutze Trading-Fachbegriffe korrekt
```

### Englisch sprechender Agent (NexusChat)

```yaml
system_message: |
  You are Nexus, the English communication hub.
  
  - Always respond in English
  - Use professional trading terminology
  - Be clear and concise
```

## 🔄 Workflow: Konfiguration ändern

### Schritt 1: Backup erstellen

```bash
cp /app/backend/agent_configs/cyphermind_config.yaml \
   /app/backend/agent_configs/cyphermind_config.yaml.backup
```

### Schritt 2: Datei bearbeiten

```bash
nano /app/backend/agent_configs/cyphermind_config.yaml
```

Oder über VS Code / Editor Ihrer Wahl.

### Schritt 3: Validierung (Optional)

```bash
# YAML Syntax prüfen
python3 -c "import yaml; yaml.safe_load(open('/app/backend/agent_configs/cyphermind_config.yaml'))"
```

### Schritt 4: Backend neu starten

```bash
sudo supervisorctl restart backend
```

### Schritt 5: Logs prüfen

```bash
tail -f /var/log/supervisor/backend.err.log
```

Sollte zeigen:
```
Loaded config for cyphermind from cyphermind_config.yaml
✓ CypherMind initialized
```

### Schritt 6: Testen

1. Dashboard öffnen
2. Bot starten mit kleinem Betrag
3. Agent Logs beobachten
4. Verhalten validieren

## 🧪 Testing-Tipps

### Test 1: Prompt-Änderung testen

1. Ändere `system_message` zu etwas Offensichtlichem:
   ```yaml
   system_message: |
     Du bist ein TEST Agent. 
     Antworte immer mit "TEST RESPONSE" am Anfang.
   ```

2. Backend restart
3. Bot starten und Logs checken
4. Wenn "TEST RESPONSE" erscheint → Config funktioniert!

### Test 2: Temperature testen

1. Setze `temperature: 0.0`
2. Starte Bot mehrmals mit gleichen Parametern
3. Responses sollten identisch sein

### Test 3: Strategie-Parameter testen

```yaml
strategy_params:
  ma_crossover:
    fast_period: 5   # Sehr kurz
    slow_period: 10  # Sehr kurz
```

Sollte zu vielen (möglicherweise falschen) Signalen führen.

## 🚨 Troubleshooting

### Problem: Änderungen werden nicht übernommen

**Lösungen:**
```bash
# 1. Backend wirklich neu gestartet?
sudo supervisorctl status backend

# 2. Config-Datei korrekt?
cat /app/backend/agent_configs/cyphermind_config.yaml

# 3. YAML Syntax ok?
python3 -c "import yaml; print(yaml.safe_load(open('/app/backend/agent_configs/cyphermind_config.yaml')))"

# 4. Berechtigungen ok?
ls -la /app/backend/agent_configs/

# 5. Cache löschen
sudo supervisorctl stop backend
sleep 2
sudo supervisorctl start backend
```

### Problem: Agent-Verhalten unerwartet

**Debug:**
```bash
# Agent Logs ansehen
tail -f /var/log/supervisor/backend.err.log | grep -A 5 "Agent"

# Welche Config wird geladen?
tail -f /var/log/supervisor/backend.err.log | grep "Loaded config"
```

### Problem: YAML Syntax Error

**Häufige Fehler:**
```yaml
# ❌ FALSCH - Einrückung inkonsistent
system_message: |
  Zeile 1
 Zeile 2  # Falsche Einrückung!

# ✅ RICHTIG
system_message: |
  Zeile 1
  Zeile 2
```

## 📊 Monitoring der Änderungen

### Vor/Nach Vergleich

```bash
# Backup ansehen
cat /app/backend/agent_configs/cyphermind_config.yaml.backup

# Aktuell ansehen
cat /app/backend/agent_configs/cyphermind_config.yaml

# Diff
diff /app/backend/agent_configs/cyphermind_config.yaml.backup \
     /app/backend/agent_configs/cyphermind_config.yaml
```

### Änderungs-Historie

```bash
# Git nutzen (falls initialisiert)
cd /app/backend/agent_configs
git log --oneline cyphermind_config.yaml
```

## 💡 Best Practices

### 1. Inkrementelle Änderungen

Ändern Sie immer nur einen Parameter und testen Sie!

### 2. Dokumentation

Kommentieren Sie Ihre Änderungen:

```yaml
# Geändert am 2024-11-20: Temperature reduziert für konsistenteres Verhalten
temperature: 0.5  # War vorher 0.7
```

### 3. Versionierung

```bash
# Versionen mit Datum
cp cyphermind_config.yaml cyphermind_config_20241120.yaml
```

### 4. Testing mit Testnet

Testen Sie IMMER mit Binance Testnet:

```env
BINANCE_TESTNET=true
```

### 5. Kleine Beträge

Auch mit Testnet - kleine Beträge verwenden:

```
Amount: 10 USDT (nicht 1000!)
```

## 🔗 Weiterführende Ressourcen

- `/app/backend/agent_configs/README.md` - Detaillierte Config-Doku
- `/app/OLLAMA_SETUP.md` - Ollama & Modell-Setup
- `https://ollama.com/library` - Verfügbare Modelle

---

**Tipp:** Beginnen Sie mit kleinen Prompt-Änderungen und testen Sie ausgiebig, bevor Sie größere Anpassungen vornehmen!
