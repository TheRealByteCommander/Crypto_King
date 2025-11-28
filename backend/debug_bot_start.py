"""
Debugging-Script: Prüft warum keine autonomen Bots gestartet werden
Führt alle wichtigen Checks durch und gibt detaillierte Diagnose
"""

import asyncio
import logging
from datetime import datetime, timezone
from binance_client import BinanceClientWrapper
from coin_analyzer import CoinAnalyzer
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_binance_client():
    """Prüft ob Binance Client funktioniert."""
    print("\n=== 1. Binance Client Check ===")
    try:
        client = BinanceClientWrapper()
        balance = client.get_account_balance("USDT", "SPOT")
        print(f"✅ Binance Client OK")
        print(f"   USDT Balance: {balance:.2f} USDT")
        
        # Prüfe ob genug Kapital vorhanden
        min_required = 25.0  # Für 1 Bot
        if balance < min_required:
            print(f"⚠️  WARNUNG: Balance zu niedrig ({balance:.2f} < {min_required})")
            print(f"   Empfohlen: Mindestens {min_required} USDT für 1 Bot")
        else:
            print(f"✅ Balance ausreichend für Bot-Start")
        
        # Test API-Verbindung
        price = client.get_current_price("BTCUSDT")
        print(f"   Test API Call: BTCUSDT = {price:.2f} USDT")
        return True, balance
    except Exception as e:
        print(f"❌ Binance Client FEHLER: {e}")
        return False, 0.0

async def check_coin_analyzer():
    """Prüft ob Coin Analyzer funktioniert und Coins findet."""
    print("\n=== 2. Coin Analyzer Check ===")
    try:
        client = BinanceClientWrapper()
        analyzer = CoinAnalyzer(client)
        
        # Test mit verschiedenen Schwellen
        print("Teste mit min_score=0.4 (Standard)...")
        results_04 = await analyzer.find_optimal_coins(min_score=0.4, max_coins=10)
        print(f"   Gefunden: {len(results_04)} Coins mit Score >= 0.4")
        
        if len(results_04) == 0:
            print("⚠️  Keine Coins mit Score >= 0.4 gefunden!")
            print("   Teste mit min_score=0.2 (niedrigere Schwelle)...")
            results_02 = await analyzer.find_optimal_coins(min_score=0.2, max_coins=10)
            print(f"   Gefunden: {len(results_02)} Coins mit Score >= 0.2")
            
            if len(results_02) > 0:
                print("   Top 5 Coins (Score >= 0.2):")
                for i, coin in enumerate(results_02[:5], 1):
                    print(f"   {i}. {coin['symbol']}: Score={coin['score']:.3f}, Strategy={coin.get('best_strategy', 'N/A')}")
                print("   💡 LÖSUNG: Schwelle temporär auf 0.2 senken oder mehr Coins analysieren")
            else:
                print("❌ Auch mit Score >= 0.2 keine Coins gefunden!")
                print("   Mögliche Ursachen:")
                print("   - Markt ist sehr flach (keine starken Signale)")
                print("   - Alle Strategien geben HOLD/SELL")
                print("   - Binance API Probleme")
        else:
            print("✅ Coins mit Score >= 0.4 gefunden!")
            print("   Top 5 Coins:")
            for i, coin in enumerate(results_04[:5], 1):
                print(f"   {i}. {coin['symbol']}: Score={coin['score']:.3f}, Strategy={coin.get('best_strategy', 'N/A')}")
        
        return len(results_04) > 0, results_04
    except Exception as e:
        print(f"❌ Coin Analyzer FEHLER: {e}")
        import traceback
        traceback.print_exc()
        return False, []

async def check_autonomous_manager_status():
    """Prüft ob Autonomous Manager läuft."""
    print("\n=== 3. Autonomous Manager Check ===")
    try:
        # Prüfe ob MongoDB verfügbar ist
        client = AsyncIOMotorClient(settings.mongodb_url)
        db = client.cyphertrade
        
        # Prüfe letzte Agent-Logs
        logs = await db.agent_logs.find({
            "agent_name": {"$in": ["CypherMind", "AutonomousManager"]}
        }).sort("timestamp", -1).limit(10).to_list(10)
        
        if logs:
            print(f"✅ Agent-Logs gefunden ({len(logs)} Einträge)")
            print("   Letzte 3 Einträge:")
            for log in logs[:3]:
                timestamp = log.get("timestamp", "N/A")
                msg = log.get("message", "")[:100]
                print(f"   - {timestamp}: {msg}...")
        else:
            print("⚠️  Keine Agent-Logs gefunden")
            print("   Autonomous Manager wurde möglicherweise noch nicht aktiviert")
        
        # Prüfe laufende Bots
        bot_configs = await db.bot_config.find({"is_running": True}).to_list(100)
        autonomous_bots = [b for b in bot_configs if b.get("autonomous", False)]
        
        print(f"\n   Laufende Bots: {len(bot_configs)}")
        print(f"   Autonome Bots: {len(autonomous_bots)}")
        
        if len(autonomous_bots) >= 6:
            print("⚠️  Max. autonome Bots (6) bereits erreicht")
        else:
            print(f"✅ Noch {6 - len(autonomous_bots)} autonome Bot-Slots verfügbar")
        
        return True
    except Exception as e:
        print(f"❌ Autonomous Manager Check FEHLER: {e}")
        return False

async def check_ollama():
    """Prüft ob Ollama verfügbar ist."""
    print("\n=== 4. Ollama LLM Check ===")
    try:
        import httpx
        
        # Prüfe Ollama API
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.cyphermind_base_url}/api/tags", timeout=5.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                print(f"✅ Ollama erreichbar")
                print(f"   Verfügbare Modelle: {len(models)}")
                if models:
                    print(f"   Modelle: {', '.join([m.get('name', 'N/A') for m in models[:3]])}")
                return True
            else:
                print(f"⚠️  Ollama antwortet mit Status {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Ollama nicht erreichbar: {e}")
        print("   Prüfe ob Ollama läuft: curl http://localhost:11434/api/tags")
        return False

async def check_strategies():
    """Prüft ob Strategien funktionieren."""
    print("\n=== 5. Strategien Check ===")
    try:
        from strategies import get_strategy
        client = BinanceClientWrapper()
        
        # Test mit BTCUSDT
        df = client.get_market_data("BTCUSDT", "5m", 100)
        
        strategies_to_test = ["rsi", "macd", "ma_crossover", "bollinger_bands", "combined"]
        
        print("Teste Strategien mit BTCUSDT (5m, 100 candles):")
        for strategy_name in strategies_to_test:
            try:
                strategy = get_strategy(strategy_name)
                result = strategy.analyze(df)
                signal = result.get("signal", "N/A")
                confidence = result.get("confidence", 0.0)
                print(f"   {strategy_name:20s}: {signal:4s} (Confidence: {confidence:.2f})")
            except Exception as e:
                print(f"   {strategy_name:20s}: ❌ FEHLER - {e}")
        
        return True
    except Exception as e:
        print(f"❌ Strategien Check FEHLER: {e}")
        return False

async def main():
    """Führt alle Checks durch."""
    print("=" * 60)
    print("DEBUG: Warum werden keine autonomen Bots gestartet?")
    print("=" * 60)
    
    results = {}
    
    # Check 1: Binance Client
    binance_ok, balance = await check_binance_client()
    results["binance"] = binance_ok
    
    # Check 2: Coin Analyzer
    analyzer_ok, coins = await check_coin_analyzer()
    results["analyzer"] = analyzer_ok
    
    # Check 3: Autonomous Manager
    manager_ok = await check_autonomous_manager_status()
    results["manager"] = manager_ok
    
    # Check 4: Ollama
    ollama_ok = await check_ollama()
    results["ollama"] = ollama_ok
    
    # Check 5: Strategien
    strategies_ok = await check_strategies()
    results["strategies"] = strategies_ok
    
    # Zusammenfassung
    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    
    all_ok = all(results.values())
    
    if all_ok:
        print("✅ Alle Checks bestanden!")
        if len(coins) == 0:
            print("\n⚠️  ABER: Keine Coins mit Score >= 0.4 gefunden")
            print("   → Mögliche Lösungen:")
            print("   1. Warten auf bessere Marktbedingungen")
            print("   2. Schwelle temporär auf 0.2 senken")
            print("   3. Mehr Coins analysieren (max_coins erhöhen)")
        else:
            print(f"\n✅ {len(coins)} Coins mit Score >= 0.4 gefunden")
            print("   → Bots sollten starten können!")
    else:
        print("❌ Einige Checks fehlgeschlagen:")
        for check, ok in results.items():
            status = "✅" if ok else "❌"
            print(f"   {status} {check}")
        
        print("\n💡 Nächste Schritte:")
        if not results["binance"]:
            print("   1. Binance API-Key und Secret prüfen")
            print("   2. Internet-Verbindung prüfen")
        if not results["analyzer"]:
            print("   1. Coin Analyzer Dependencies prüfen")
            print("   2. Binance API-Verbindung prüfen")
        if not results["ollama"]:
            print("   1. Ollama starten: ollama serve")
            print("   2. Ollama-URL in config prüfen")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())

