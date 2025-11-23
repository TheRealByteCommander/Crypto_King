# 📋 CryptoKing Server Update - Anleitung

## 🚀 Schnell-Update (Empfohlen)

```bash
cd /app
git pull
chmod +x update-ct-server.sh
sudo bash update-ct-server.sh
```

Das Script macht automatisch:
- ✅ Git Pull (lädt neueste Änderungen)
- ✅ Backend Dependencies aktualisieren
- ✅ Frontend Dependencies aktualisieren
- ✅ Backend neu starten
- ✅ Frontend neu starten
- ✅ Status-Prüfung

## 📝 Manuelles Update

Falls das automatische Script nicht funktioniert:

### 1. Backend Update

```bash
cd /app
git pull
cd backend
source venv/bin/activate  # Falls venv vorhanden
pip install -r requirements.txt --upgrade
cd ..
sudo supervisorctl restart cyphertrade-backend
```

### 2. Frontend Update

```bash
cd /app/frontend
yarn install  # Nur wenn package.json geändert wurde
cd ..
sudo supervisorctl restart cyphertrade-frontend
```

### 3. Status prüfen

```bash
# Backend Status
sudo supervisorctl status cyphertrade-backend

# Frontend Status
sudo supervisorctl status cyphertrade-frontend

# Logs anzeigen
tail -f /var/log/supervisor/cyphertrade-backend.log
tail -f /var/log/supervisor/cyphertrade-frontend.log
```

## 🔍 Logs bei Problemen

```bash
# Backend Fehler-Logs
tail -50 /var/log/supervisor/cyphertrade-backend-error.log

# Frontend Fehler-Logs
tail -50 /var/log/supervisor/cyphertrade-frontend-error.log
```

## ✅ Was wurde aktualisiert?

### Margin- und Futures-Trading
- ✅ Trading-Mode: SPOT, MARGIN, FUTURES
- ✅ Short-Positionen werden jetzt unterstützt
- ✅ Position-Tracking für LONG und SHORT
- ✅ P/L-Berechnung für beide Richtungen

### Frontend
- ✅ Trading-Mode-Auswahl im BotControl
- ✅ Position-Status-Anzeige erweitert

## 🎯 Nach dem Update

1. **Browser Cache leeren**: Strg+F5 im Browser
2. **Bot starten**: Im Dashboard einen Bot mit neuem Trading-Mode starten
3. **Testen**: Short-Position mit MARGIN oder FUTURES testen

## ⚠️ Wichtig

- **Trading-Mode**: Standard ist SPOT (Long Only)
- **Short-Trading**: Nur mit MARGIN oder FUTURES möglich
- **Backend muss neu gestartet werden** für die neuen Features

