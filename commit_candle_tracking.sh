#!/bin/bash
# Script zum Committen und Pushen des Kerzen-Tracking-Systems

echo "🔄 Staging aller Änderungen..."

# Alle geänderten und neuen Dateien hinzufügen
git add backend/candle_tracker.py
git add backend/bot_manager.py
git add backend/agent_tools.py
git add backend/memory_manager.py
git add backend/agent_configs/cyphermind_config.yaml
git add README.md
git add MEMORY_SYSTEM.md
git add CANDLE_TRACKING_ANALYSE.md
git add CANDLE_TRACKING_IMPLEMENTATION.md
git add POSITION_TRACKING_UPDATE.md
git add CHANGELOG_CANDLE_TRACKING.md

echo "✅ Dateien hinzugefügt"
echo ""
echo "📊 Git Status:"
git status --short

echo ""
echo "💾 Committe Änderungen..."

git commit -m "Feat: Kerzen-Tracking-System implementiert - Pre-Trade, During-Trade und Post-Trade Tracking

- CandleTracker Klasse für kontinuierliches Kerzen-Tracking
- Pre-Trade: 200 Kerzen vor jedem Trade
- During-Trade: Alle Kerzen während Position offen ist  
- Post-Trade: 200 Kerzen nach jedem Verkauf
- Integration in Bot-Manager und Memory-System
- CypherMind Tool erweitert: get_bot_candles()
- Pattern-Extraktion aus Kerzen-Daten für Learning
- Vollständige Dokumentation aktualisiert"

echo "✅ Commit erstellt"
echo ""
echo "🚀 Pushe ins Repo..."
git push

echo ""
echo "✅ Fertig! Alle Änderungen wurden ins Repo gepusht."

