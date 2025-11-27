# Update-Anleitung

## Schnell-Update (Empfohlen)

### Linux/Mac:
```bash
bash up.sh
```

### Windows:
```batch
up.bat
```

## Manuelles Update

### Schritt 1: Git Pull
```bash
git pull origin main
```

### Schritt 2: Python Dependencies installieren
```bash
cd backend
pip install -r requirements.txt --upgrade
```

**Wichtig:** Neue Dependencies in diesem Update:
- `feedparser` - Für News-RSS-Feeds
- `beautifulsoup4` - Für HTML-Parsing
- `httpx` - Für asynchrone HTTP-Requests

### Schritt 3: Backend neu starten

**Linux/Mac (Supervisor):**
```bash
sudo supervisorctl restart cyphertrade-backend
```

**Linux/Mac (Systemd):**
```bash
sudo systemctl restart cyphertrade-backend
```

**Docker:**
```bash
docker restart cyphertrade-backend
```

**Manuell:**
- Backend-Prozess beenden (Strg+C oder kill)
- Neu starten: `cd backend && python -m uvicorn server:app --host 0.0.0.0 --port 8001`

### Schritt 4: Frontend (optional)
```bash
cd frontend
npm install  # Nur wenn package.json geändert wurde
```

Frontend aktualisiert sich meist automatisch (Hot Reload).

## Was wurde geändert?

### Neue Features:
- ✅ **Autonomes Trading-System**: CypherMind arbeitet jetzt vollständig autonom
- ✅ **News-System**: News werden automatisch abgerufen und an Agents weitergeleitet
- ✅ **Automatische Coin-Analyse**: CypherMind analysiert regelmäßig optimale Coins
- ✅ **Automatischer Bot-Start**: Bots werden bei guten Opportunities automatisch gestartet

### Neue Dateien:
- `backend/autonomous_manager.py` - Autonomer Manager
- `backend/crypto_news_fetcher.py` - News-Fetcher
- `backend/coin_analyzer.py` - Coin-Analyzer

### Geänderte Dateien:
- `backend/server.py` - Integration des AutonomousManagers
- `backend/agent_configs/cyphermind_config.yaml` - Proaktiver Prompt
- `backend/agent_tools.py` - Neue Tools für autonome Bots
- `backend/agents.py` - News-Weiterleitung
- `backend/bot_manager.py` - Autonomous Bot Support

## Nach dem Update prüfen

1. **Backend-Logs prüfen:**
   ```bash
   tail -f /var/log/supervisor/cyphertrade-backend.log
   ```
   
   Sollte enthalten:
   - "Autonomous Manager started - CypherMind arbeitet jetzt autonom"
   - "News fetch loop started"
   - "Autonomous analysis loop started"

2. **Health-Check:**
   ```bash
   curl http://localhost:8001/health
   ```

3. **Agent-Status prüfen:**
   ```bash
   curl http://localhost:8001/api/agents
   ```

## Troubleshooting

### Fehler: "ModuleNotFoundError: No module named 'feedparser'"
**Lösung:**
```bash
cd backend
pip install feedparser beautifulsoup4 httpx
```

### Fehler: "Autonomous Manager konnte nicht starten"
**Lösung:**
- Prüfe ob Binance-Client verfügbar ist
- Prüfe Backend-Logs auf Fehler
- AutonomousManager startet automatisch, wenn ein Bot läuft

### Backend startet nicht
**Lösung:**
1. Prüfe Logs: `tail -50 /var/log/supervisor/cyphertrade-backend-error.log`
2. Prüfe ob Port 8001 belegt ist: `lsof -i :8001`
3. Prüfe Python-Imports: `python3 -c "import server"`

## Update-Script Details

Das `up.sh` / `up.bat` Script führt automatisch aus:
1. ✅ Git Pull
2. ✅ Python Dependencies installieren
3. ✅ Module-Import prüfen
4. ✅ Backend neu starten (wenn supervisor verfügbar)
5. ✅ Frontend Dependencies (optional)

## Weitere Informationen

- [CRYPTO_NEWS_SYSTEM.md](CRYPTO_NEWS_SYSTEM.md) - News-System Dokumentation
- [AUTONOMOUS_BOTS.md](AUTONOMOUS_BOTS.md) - Autonome Bots Dokumentation
- [AGENT_TOOLS.md](AGENT_TOOLS.md) - Agent Tools Dokumentation

