# Diagnose-Skript: Automatische Bot-Erstellung

## Verwendung

```bash
cd /app/backend
python3 check_autonomous_bot_prerequisites.py
```

**WICHTIG:** Verwende `python3` (nicht `pyrhon3` oder `python`)

## Was wird geprüft?

Das Skript prüft alle Voraussetzungen für die automatische Bot-Erstellung:

1. ✅ MongoDB Verbindung
2. ✅ Binance Client (API Keys, Verbindung)
3. ✅ Agent Manager (CypherMind, UserProxy)
4. ✅ Bot Manager
5. ✅ Agent Tools (analyze_optimal_coins, start_autonomous_bot)
6. ✅ Coin Analyzer Modul
7. ✅ Autonomous Manager
8. ✅ LLM Konfiguration (Tools registriert)
9. ✅ Verfügbares Budget (min. 10 USDT)

## Erwartete Ausgabe

```
================================================================================
PRÜFUNG DER VORAUSSETZUNGEN FÜR AUTOMATISCHE BOT-ERSTELLUNG
================================================================================

1. MongoDB Verbindung...
   ✓ MongoDB verbunden: cyphertrade

2. Binance Client...
   ✓ Binance Client initialisiert
   ✓ USDT Balance: 1000.00 USDT

3. Agent Manager...
   ✓ Agent Manager initialisiert
   ✓ Agents: ['nexuschat', 'cyphermind', 'cyphertrade', 'user_proxy']
   ✓ CypherMind gefunden: CypherMind
   ✓ UserProxy gefunden: UserProxy

...

================================================================================
ZUSAMMENFASSUNG
================================================================================
✓ Bestanden: 9
✗ Fehlgeschlagen: 0
Gesamt: 9

✓ ALLE VORAUSSETZUNGEN ERFÜLLT!
  CypherMind sollte in der Lage sein, autonome Bots zu starten.
```

## Häufige Probleme

### Problem: "ModuleNotFoundError"
**Lösung:** Stelle sicher, dass du im `backend/` Verzeichnis bist und alle Dependencies installiert sind:
```bash
cd /app/backend
source venv/bin/activate  # Falls venv vorhanden
pip install -r requirements.txt
```

### Problem: "Binance client not available"
**Lösung:** Prüfe `.env` Datei:
```bash
cat /app/backend/.env | grep BINANCE
```

### Problem: "CypherMind agent not found"
**Lösung:** Prüfe ob Agents korrekt initialisiert werden:
```bash
tail -50 /var/log/supervisor/cyphertrade-backend.log | grep -i "agent\|cyphermind"
```

### Problem: "Tools nicht registriert"
**Lösung:** Prüfe LLM-Konfiguration und ob Ollama-Modell Function Calling unterstützt:
```bash
ollama list
# Empfohlene Modelle: llama3.1, mistral, qwen2.5
```

## Nächste Schritte

Wenn alle Checks bestanden sind, sollte CypherMind automatisch Bots starten können.

Falls Checks fehlschlagen, behebe die angezeigten Probleme und führe das Skript erneut aus.

