# Frontend-Backend Verbindungsproblem beheben

## Problem
Das Frontend versucht auf `localhost:8001` zuzugreifen statt auf `192.168.178.154:8001`.

Alle Fehler zeigen:
```
localhost:8001/api/strategies:1   Failed to load resource: net::ERR_CONNECTION_REFUSED
localhost:8001/api/bot/status:1   Failed to load resource: net::ERR_CONNECTION_REFUSED
WebSocket connection to 'ws://localhost:8001/api/ws' failed:
```

## Lösung

### 1. Frontend .env Datei prüfen und korrigieren

```bash
# Prüfe Frontend .env
cat /app/frontend/.env

# Sollte enthalten:
# REACT_APP_BACKEND_URL=http://192.168.178.154:8001

# Falls falsch oder fehlt:
cd /app/frontend
echo "REACT_APP_BACKEND_URL=http://192.168.178.154:8001" > .env

# Prüfe ob korrekt:
cat .env
```

### 2. Frontend NEU starten (WICHTIG!)

React lädt die `.env` Datei beim **Start**. Nach Änderungen muss das Frontend neu gestartet werden:

```bash
# Stoppe Frontend
sudo supervisorctl stop cyphertrade-frontend

# Warte kurz
sleep 2

# Starte Frontend neu
sudo supervisorctl start cyphertrade-frontend

# Prüfe Status
sudo supervisorctl status cyphertrade-frontend
```

### 3. Browser Cache leeren

Da React die Umgebungsvariablen zur Build-Zeit einbindet, sollten Sie:

1. **Hard Refresh im Browser:**
   - Chrome/Edge: `Ctrl + Shift + R` (Windows) oder `Cmd + Shift + R` (Mac)
   - Firefox: `Ctrl + F5` (Windows) oder `Cmd + Shift + R` (Mac)

2. **Browser komplett neu starten**

3. **Cache leeren:**
   - `F12` → Network Tab → "Disable cache" aktivieren
   - Oder: Settings → Clear browsing data → Cached images and files

### 4. Vollständiger Neustart (wenn nichts hilft)

```bash
# 1. Frontend .env korrigieren
cd /app/frontend
echo "REACT_APP_BACKEND_URL=http://192.168.178.154:8001" > .env
cat .env

# 2. Frontend komplett neu starten
sudo supervisorctl stop cyphertrade-frontend
sleep 3
sudo supervisorctl start cyphertrade-frontend

# 3. Prüfe ob Frontend läuft
sudo supervisorctl status cyphertrade-frontend

# 4. Prüfe Logs
tail -f /var/log/supervisor/cyphertrade-frontend.log

# 5. Warte bis Frontend vollständig gestartet ist (kann 1-2 Minuten dauern)
sleep 30

# 6. Teste Backend-Verbindung vom Server
curl http://192.168.178.154:8001/api/health
```

### 5. Browser Console prüfen

Nach dem Neustart im Browser:

1. Öffnen Sie: `http://192.168.178.154:3000`
2. Drücken Sie `F12` (Developer Tools)
3. Gehen Sie zu "Console" Tab
4. Suchen Sie nach Anfragen - sie sollten jetzt auf `192.168.178.154:8001` zeigen, NICHT auf `localhost:8001`

## Alternative: Automatisches Fix-Skript

```bash
cd /app
git pull
chmod +x fix-frontend-backend-connection.sh
sudo bash fix-frontend-backend-connection.sh
```

## Wichtige Hinweise

1. **React lädt .env beim Start** - nach Änderungen immer Frontend neu starten!
2. **Hard Refresh im Browser** - der Browser kann alte JavaScript-Dateien im Cache haben
3. **Prüfe Browser Console** - die Fehlermeldungen zeigen genau, welche URL verwendet wird

## Nach dem Fix sollte funktionieren

- API Calls gehen an `http://192.168.178.154:8001/api/*`
- WebSocket verbindet zu `ws://192.168.178.154:8001/api/ws`
- Keine `ERR_CONNECTION_REFUSED` Fehler mehr
- Dashboard lädt Daten vom Backend

