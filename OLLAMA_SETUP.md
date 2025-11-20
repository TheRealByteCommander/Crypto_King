# Ollama LLM Setup für Project CypherTrade

Dieses Projekt ist für die Verwendung mit **Ollama** (lokale LLMs) konfiguriert.

## 🚀 Ollama Installation

### Linux / macOS

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Windows

Download von: https://ollama.com/download

## 📦 Modelle herunterladen

### Empfohlene Modelle für Trading:

**Llama 3.2 (Standard, empfohlen):**
```bash
ollama pull llama3.2
```

**Alternative Modelle:**

```bash
# Llama 3.1 - Größeres Modell, bessere Reasoning
ollama pull llama3.1

# Mistral - Gut für strukturierte Ausgaben
ollama pull mistral

# Gemma 2 - Schnell und effizient
ollama pull gemma2

# DeepSeek Coder - Spezialisiert auf Code/Daten
ollama pull deepseek-coder
```

## ⚙️ Konfiguration

### 1. Ollama Server starten

```bash
ollama serve
```

Der Server läuft auf: `http://localhost:11434`

### 2. Backend .env anpassen

Die `/app/backend/.env` ist bereits für Ollama konfiguriert:

```env
# Ollama Base URL
OLLAMA_BASE_URL="http://localhost:11434/v1"
OLLAMA_API_KEY="ollama"

# NexusChat Agent
NEXUSCHAT_LLM_PROVIDER="ollama"
NEXUSCHAT_MODEL="llama3.2"
NEXUSCHAT_BASE_URL="http://localhost:11434/v1"

# CypherMind Agent
CYPHERMIND_LLM_PROVIDER="ollama"
CYPHERMIND_MODEL="llama3.2"
CYPHERMIND_BASE_URL="http://localhost:11434/v1"

# CypherTrade Agent
CYPHERTRADE_LLM_PROVIDER="ollama"
CYPHERTRADE_MODEL="llama3.2"
CYPHERTRADE_BASE_URL="http://localhost:11434/v1"
```

### 3. Verschiedene Modelle pro Agent verwenden

Sie können für jeden Agent ein unterschiedliches Modell verwenden:

```env
NEXUSCHAT_MODEL="llama3.2"      # Schnell für UI
CYPHERMIND_MODEL="llama3.1"     # Größer für bessere Analyse
CYPHERTRADE_MODEL="mistral"     # Präzise für Ausführung
```

## 🧪 Ollama testen

### Test 1: Ollama Server prüfen

```bash
curl http://localhost:11434/api/tags
```

Sollte die installierten Modelle auflisten.

### Test 2: Modell testen

```bash
ollama run llama3.2
```

Interaktiver Chat öffnet sich. Testen Sie das Modell.

### Test 3: API-Kompatibilität testen

```bash
curl http://localhost:11434/v1/models
```

Sollte OpenAI-kompatible API Response zurückgeben.

## 📊 Agent-Konfiguration anpassen

Die Agent-Prompts können ohne Code-Update angepasst werden:

**Dateien:** `/app/backend/agent_configs/*.yaml`

### Beispiel: Modell für CypherMind ändern

1. Öffne `/app/backend/.env`
2. Ändere: `CYPHERMIND_MODEL="llama3.1"`
3. Restart: `sudo supervisorctl restart backend`

### Beispiel: Prompt für CypherMind anpassen

1. Öffne `/app/backend/agent_configs/cyphermind_config.yaml`
2. Bearbeite das `system_message` Feld
3. Restart: `sudo supervisorctl restart backend`

## 🔧 Performance-Optimierung

### GPU-Beschleunigung (NVIDIA)

Ollama nutzt automatisch verfügbare GPUs. Prüfen mit:

```bash
ollama ps
```

### Mehrere Modelle parallel

Ollama lädt Modelle dynamisch. Sie können mehrere Modelle gleichzeitig verwenden:

```env
NEXUSCHAT_MODEL="llama3.2"
CYPHERMIND_MODEL="llama3.1"
CYPHERTRADE_MODEL="mistral"
```

### RAM-Management

Ollama entlädt ungenutzte Modelle automatisch nach 5 Minuten.

Manuell entladen:
```bash
ollama stop llama3.2
```

## 🚨 Troubleshooting

### Problem: Ollama Server nicht erreichbar

**Lösung:**
```bash
# Server starten
ollama serve

# Port prüfen
netstat -tlnp | grep 11434
```

### Problem: Modell nicht gefunden

**Lösung:**
```bash
# Verfügbare Modelle auflisten
ollama list

# Modell herunterladen
ollama pull llama3.2
```

### Problem: Langsame Responses

**Lösungen:**
1. Kleineres Modell verwenden (z.B. `gemma2` statt `llama3.1`)
2. `temperature` in YAML-Config reduzieren
3. GPU aktivieren (falls verfügbar)

### Problem: Agent-Initialisierung schlägt fehl

**Prüfen:**
```bash
# Backend Logs
tail -f /var/log/supervisor/backend.err.log

# Ollama Logs
journalctl -u ollama -f
```

## 📈 Modell-Empfehlungen pro Agent

### NexusChat (User Interface)
- **Empfohlen:** `llama3.2` oder `gemma2`
- **Warum:** Schnell, freundlich, gute Sprachqualität
- **Temperature:** 0.7

### CypherMind (Decision & Strategy)
- **Empfohlen:** `llama3.1` oder `mistral`
- **Warum:** Besseres Reasoning, strukturierte Ausgaben
- **Temperature:** 0.5 (niedrig für Konsistenz)

### CypherTrade (Trade Execution)
- **Empfohlen:** `mistral` oder `deepseek-coder`
- **Warum:** Präzise, zuverlässig, gute JSON-Ausgaben
- **Temperature:** 0.3 (sehr niedrig für Determinismus)

## 🔄 Von OpenAI zu Ollama wechseln

Falls Sie von OpenAI wechseln möchten:

1. **Ollama installieren und Modell pullen**
2. **`.env` anpassen:**
   ```env
   # Alt (OpenAI)
   NEXUSCHAT_API_KEY="sk-..."
   NEXUSCHAT_MODEL="gpt-4"
   
   # Neu (Ollama)
   NEXUSCHAT_BASE_URL="http://localhost:11434/v1"
   NEXUSCHAT_MODEL="llama3.2"
   ```
3. **Backend neu starten**
4. **Testen**

## 💡 Vorteile von Ollama

- ✅ **Kostenlos** - Keine API-Kosten
- ✅ **Privat** - Daten bleiben lokal
- ✅ **Schnell** - Keine Netzwerk-Latenz
- ✅ **Offline** - Funktioniert ohne Internet
- ✅ **Flexibel** - Viele Modelle zur Auswahl

## ⚠️ Limitierungen

- ❌ Benötigt lokale Rechenleistung (CPU/GPU)
- ❌ Modelle können 4-8 GB RAM nutzen
- ❌ Qualität kann je nach Modell variieren
- ❌ Kleinere Modelle weniger "intelligent" als GPT-4

## 🔗 Ressourcen

- **Ollama Website:** https://ollama.com
- **Modell-Bibliothek:** https://ollama.com/library
- **GitHub:** https://github.com/ollama/ollama
- **Discord:** https://discord.gg/ollama

## 📝 Nächste Schritte

1. ✅ Ollama installiert
2. ✅ Modell heruntergeladen
3. ✅ Backend konfiguriert
4. ✅ Backend neu gestartet
5. ✅ Dashboard öffnen und Bot testen!

---

**Tipp:** Starten Sie mit `llama3.2` für alle Agents und optimieren Sie später je nach Bedarf!
