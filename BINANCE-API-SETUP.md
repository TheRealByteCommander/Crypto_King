# 🔑 Binance API Key Setup

## Fehler: "Invalid Api-Key ID" (Code -2008)

Dieser Fehler bedeutet, dass der Binance API Key ungültig oder falsch konfiguriert ist.

## Lösung

### Schritt 1: API Key Diagnose

Führe auf dem CT-Server aus:

```bash
cd /app
git pull
chmod +x fix-binance-api-key.sh
sudo bash fix-binance-api-key.sh
```

### Schritt 2: API Key erstellen

#### Für Testnet (empfohlen zum Testen):

1. Gehe zu: https://testnet.binance.vision/
2. Erstelle einen Account
3. Gehe zu: API Management
4. Erstelle einen neuen API Key
5. **WICHTIG:** Aktiviere folgende Permissions:
   - ✅ Enable Reading
   - ✅ Enable Spot & Margin Trading
   - ✅ Enable Futures (für FUTURES Mode)

#### Für Mainnet (echtes Trading):

1. Gehe zu: https://www.binance.com/en/my/settings/api-management
2. Erstelle einen neuen API Key
3. **WICHTIG:** Aktiviere folgende Permissions:
   - ✅ Enable Reading
   - ✅ Enable Spot & Margin Trading
   - ✅ Enable Futures (für FUTURES Mode)
   - ⚠️ **IP-Restriction** (empfohlen): Füge deine Server-IP hinzu

### Schritt 3: API Key zur .env hinzufügen

```bash
cd /app/backend
nano .env
```

Füge/aktualisiere folgende Zeilen:

```env
BINANCE_API_KEY=dein_api_key_hier
BINANCE_API_SECRET=dein_api_secret_hier
BINANCE_TESTNET=true  # true für Testnet, false für Mainnet
```

### Schritt 4: Backend neu starten

```bash
sudo supervisorctl restart cyphertrade-backend
```

### Schritt 5: Erneut testen

```bash
sudo bash fix-binance-api-key.sh
```

## Wichtige Hinweise

### Testnet vs Mainnet

- **Testnet:** `BINANCE_TESTNET=true` - Nur Test-Geld, keine echten Trades
- **Mainnet:** `BINANCE_TESTNET=false` - ECHTES Geld, ECHTE Trades!

### API Key Permissions

Für automatisches Trading in SPOT, MARGIN und FUTURES benötigst du:

1. **Enable Reading** - Zum Abrufen von Marktdaten
2. **Enable Spot & Margin Trading** - Für SPOT und MARGIN Mode
3. **Enable Futures** - Für FUTURES Mode

### IP-Restriction

Wenn IP-Restriction aktiviert ist, muss die Server-IP in Binance eingetragen sein.

Prüfe Server-IP:
```bash
curl -s ifconfig.me
```

## Troubleshooting

### Fehler Code -2008 (Invalid Api-Key ID)
- API Key ist falsch oder leer
- API Key wurde gelöscht
- API Key passt nicht zum Testnet/Mainnet Mode

### Fehler Code -1022 (Invalid signature)
- API Secret ist falsch

### Fehler Code -1021 (Timestamp error)
- Systemzeit ist falsch
- Lösung: `sudo ntpdate -s time.nist.gov` oder `sudo timedatectl set-ntp true`

