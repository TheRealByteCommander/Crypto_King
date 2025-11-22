# Binance Testnet API Keys einrichten

## 🚀 Schnell-Anleitung

### 1. Binance Testnet Account erstellen

1. **Öffnen Sie die Binance Testnet Website:**
   ```
   https://testnet.binance.vision/
   ```

2. **Erstellen Sie einen Account:**
   - Klicken Sie auf "Sign In with GitHub"
   - Oder melden Sie sich mit Ihrem GitHub-Account an
   - Falls Sie keinen GitHub-Account haben, erstellen Sie einen unter: https://github.com

### 2. API Keys generieren

1. **Nach dem Login:**
   - Klicken Sie auf Ihr Profil (rechts oben)
   - Wählen Sie "API Key Management" oder "API Management"

2. **Neue API Keys erstellen:**
   - Klicken Sie auf "Generate API Key"
   - Vergeben Sie einen Namen (z.B. "CryptoKing Testnet")
   - Bestätigen Sie die Erstellung

3. **API Keys kopieren:**
   - **API Key:** Eine Zeichenkette wie `abc123xyz789...`
   - **Secret Key:** Eine weitere Zeichenkette (wird nur einmal angezeigt!)
   - ⚠️ **WICHTIG:** Kopieren Sie den Secret Key sofort, er wird nur einmal angezeigt!

### 3. API Keys in .env Datei eintragen

1. **Öffnen Sie die Backend .env Datei:**
   ```bash
   nano /app/backend/.env
   # Oder:
   vi /app/backend/.env
   ```

2. **Tragen Sie die Keys ein:**
   ```env
   BINANCE_API_KEY=ihr_api_key_hier
   BINANCE_API_SECRET=ihr_secret_key_hier
   BINANCE_TESTNET=true
   ```

   **WICHTIG:**
   - ❌ **KEINE** Anführungszeichen um die Keys
   - ❌ **KEINE** Leerzeichen vor/nach dem `=`
   - ✅ Direkt nach dem `=` beginnen

   **Richtig:**
   ```env
   BINANCE_API_KEY=abc123xyz789
   BINANCE_API_SECRET=secret123xyz789
   BINANCE_TESTNET=true
   ```

   **Falsch:**
   ```env
   BINANCE_API_KEY="abc123xyz789"  # ❌ Keine Anführungszeichen!
   BINANCE_API_KEY = abc123xyz789  # ❌ Keine Leerzeichen!
   BINANCE_API_KEY=abc123xyz789    # ✅ Richtig
   ```

3. **Speichern Sie die Datei:**
   - `nano`: `Ctrl + X`, dann `Y`, dann `Enter`
   - `vi`: `Esc`, dann `:wq`, dann `Enter`

### 4. Backend neu starten

```bash
# Backend neu starten (lädt neue .env Werte)
sudo supervisorctl restart cyphertrade-backend

# Status prüfen
sudo supervisorctl status cyphertrade-backend

# Health Check (sollte Binance als valid zeigen)
curl http://localhost:8001/api/health | python3 -m json.tool
```

### 5. Binance Verbindung testen

```bash
# API Health Check
curl http://localhost:8001/api/health | python3 -m json.tool

# Sollte zeigen:
# {
#   "status": "healthy" oder "degraded",
#   "services": {
#     "binance": {
#       "valid": true,
#       "error": null
#     }
#   }
# }
```

## 📋 Beispiel .env Datei

```env
# MongoDB Configuration
MONGO_URL=mongodb://localhost:27017
DB_NAME=cryptotrade

# Binance API Configuration (TESTNET)
BINANCE_API_KEY=abc123xyz789abcdefghijklmnopqrstuvwxyz
BINANCE_API_SECRET=secret123xyz789abcdefghijklmnopqrstuvwxyz123456789
BINANCE_TESTNET=true

# Ollama Configuration
OLLAMA_BASE_URL=http://192.168.178.155:11434/v1
OLLAMA_API_KEY=ollama

# Agent LLM Configuration
NEXUSCHAT_LLM_PROVIDER=ollama
NEXUSCHAT_MODEL=ajindal/llama3.1-storm:8b
NEXUSCHAT_BASE_URL=http://192.168.178.155:11434/v1

CYPHERMIND_LLM_PROVIDER=ollama
CYPHERMIND_MODEL=0xroyce/plutus:latest
CYPHERMIND_BASE_URL=http://192.168.178.155:11434/v1

CYPHERTRADE_LLM_PROVIDER=ollama
CYPHERTRADE_MODEL=Qwen2.5:7b-instruct
CYPHERTRADE_BASE_URL=http://192.168.178.155:11434/v1

# Trading Configuration
DEFAULT_STRATEGY=ma_crossover
DEFAULT_SYMBOL=BTCUSDT
DEFAULT_AMOUNT=100
MAX_POSITION_SIZE=1000
RISK_PER_TRADE=0.02

# CORS Configuration
CORS_ORIGINS=*

# MCP Server Configuration
MCP_ENABLED=false
MCP_PORT=8002

# Notification Configuration
EMAIL_ENABLED=false
TELEGRAM_ENABLED=false
```

## 🔒 Sicherheitshinweise

### Testnet vs. Mainnet

- ✅ **Testnet (BINANCE_TESTNET=true):** Für Tests, kein echtes Geld
- ⚠️ **Mainnet (BINANCE_TESTNET=false):** ECHTES Geld, nur für Produktion!

### Best Practices

1. **Niemals Testnet Keys für Mainnet verwenden**
2. **Secret Key sicher aufbewahren** (nur einmal sichtbar!)
3. **API Keys nur mit nötigen Berechtigungen** (keine Withdrawal-Rechte für Tests)
4. **.env Datei nicht committen** (sollte in .gitignore sein)

### Berechtigungen

Für Trading Tests brauchen Sie normalerweise:
- ✅ **Enable Reading** (Lesen von Marktdaten)
- ✅ **Enable Spot & Margin Trading** (Spot Trading)
- ❌ **Enable Withdrawals** (NICHT aktivieren für Tests!)

## 🚨 Troubleshooting

### Problem: "API-key format invalid"

**Lösung:**
```bash
# Prüfe .env Datei
cat /app/backend/.env | grep BINANCE

# Sollte so aussehen:
# BINANCE_API_KEY=abc123xyz789
# BINANCE_API_SECRET=secret123xyz789
# BINANCE_TESTNET=true

# Keine Anführungszeichen, keine Leerzeichen!
```

### Problem: "Invalid API-key, IP, or permissions"

**Lösung:**
1. Prüfen Sie ob die API Keys korrekt kopiert wurden (keine Leerzeichen)
2. Prüfen Sie ob `BINANCE_TESTNET=true` gesetzt ist
3. Prüfen Sie die Berechtigungen im Binance Testnet Account

### Problem: "Signature for this request is not valid"

**Lösung:**
1. Prüfen Sie ob der Secret Key korrekt ist
2. Stellen Sie sicher, dass keine Leerzeichen im Secret Key sind
3. Backend neu starten

### Problem: Backend zeigt Binance als "invalid"

**Logs prüfen:**
```bash
# Backend Logs
tail -f /var/log/supervisor/cyphertrade-backend-error.log

# Health Check
curl http://localhost:8001/api/health | python3 -m json.tool
```

## 📚 Weitere Ressourcen

- **Binance Testnet:** https://testnet.binance.vision/
- **Binance API Dokumentation:** https://binance-docs.github.io/apidocs/
- **Testnet API Dokumentation:** https://testnet.binance.vision/

## ✅ Checkliste

- [ ] Binance Testnet Account erstellt
- [ ] API Keys generiert und kopiert
- [ ] Keys in `/app/backend/.env` eingetragen (ohne Anführungszeichen!)
- [ ] `BINANCE_TESTNET=true` gesetzt
- [ ] Backend neu gestartet
- [ ] Health Check zeigt Binance als `valid: true`

