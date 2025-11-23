# 🔄 Frontend Update Anleitung

## Automatisches Update (empfohlen)

Nach jedem Frontend-Update mit Build-Änderungen:

```bash
cd /app
git pull
chmod +x force-serve-reload.sh
sudo bash force-serve-reload.sh
```

Dieses Script:
- Stoppt das Frontend
- Beendet alle Serve-Prozesse
- Gibt Port 3000 frei
- Verifiziert den Build
- Startet Frontend neu

## Manuelles Update

1. **Git Pull**
   ```bash
   cd /app
   git pull
   ```

2. **Frontend neu bauen (falls Code-Änderungen)**
   ```bash
   cd /app/frontend
   rm -rf build
   NODE_ENV=production yarn build
   ```

3. **Serve neu starten**
   ```bash
   sudo supervisorctl restart cyphertrade-frontend
   ```

## Troubleshooting

### Trading Mode nicht sichtbar?

1. **Prüfe ob Build korrekt ist:**
   ```bash
   cd /app
   sudo bash check-served-files.sh
   ```

2. **Force Reload:**
   ```bash
   cd /app
   sudo bash force-serve-reload.sh
   ```

3. **Browser-Cache leeren:**
   - Strg + Shift + R (Hard Reload)
   - Oder: F12 → Application → Clear Storage

### Port 3000 belegt?

```bash
lsof -ti:3000 | xargs kill -9
sudo supervisorctl restart cyphertrade-frontend
```

