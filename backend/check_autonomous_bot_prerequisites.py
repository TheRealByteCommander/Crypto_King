#!/usr/bin/env python3
"""
Diagnose-Skript: Prüft alle Voraussetzungen für automatische Bot-Erstellung
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from agents import AgentManager
from bot_manager import BotManager
from autonomous_manager import AutonomousManager
from binance_client import BinanceClientWrapper
from motor.motor_asyncio import AsyncIOMotorClient
from agent_tools import AgentTools

async def check_prerequisites():
    """Prüft alle Voraussetzungen für automatische Bot-Erstellung."""
    print("=" * 80)
    print("PRÜFUNG DER VORAUSSETZUNGEN FÜR AUTOMATISCHE BOT-ERSTELLUNG")
    print("=" * 80)
    print()
    
    checks_passed = 0
    checks_failed = 0
    
    # 1. MongoDB Verbindung
    print("1. MongoDB Verbindung...")
    try:
        mongo_url = settings.mongo_url
        db_name = settings.db_name
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        await client.admin.command('ping')
        print(f"   ✓ MongoDB verbunden: {db_name}")
        checks_passed += 1
    except Exception as e:
        print(f"   ✗ MongoDB Fehler: {e}")
        checks_failed += 1
        return
    
    # 2. Binance Client
    print("\n2. Binance Client...")
    try:
        binance_client = BinanceClientWrapper()
        balance = binance_client.get_account_balance("USDT", "SPOT")
        print(f"   ✓ Binance Client initialisiert")
        print(f"   ✓ USDT Balance: {balance} USDT")
        checks_passed += 1
    except Exception as e:
        print(f"   ✗ Binance Client Fehler: {e}")
        checks_failed += 1
    
    # 3. Agent Manager
    print("\n3. Agent Manager...")
    try:
        agent_manager = AgentManager(db, bot=None, binance_client=binance_client)
        print(f"   ✓ Agent Manager initialisiert")
        print(f"   ✓ Agents: {list(agent_manager.agents.keys())}")
        
        # Prüfe CypherMind
        try:
            cyphermind = agent_manager.get_agent("CypherMind")
            print(f"   ✓ CypherMind gefunden: {cyphermind.name}")
            checks_passed += 1
        except Exception as e:
            print(f"   ✗ CypherMind nicht gefunden: {e}")
            checks_failed += 1
        
        # Prüfe UserProxy
        try:
            user_proxy = agent_manager.get_agent("UserProxy")
            print(f"   ✓ UserProxy gefunden: {user_proxy.name}")
            checks_passed += 1
        except Exception as e:
            print(f"   ✗ UserProxy nicht gefunden: {e}")
            checks_failed += 1
    except Exception as e:
        print(f"   ✗ Agent Manager Fehler: {e}")
        checks_failed += 1
    
    # 4. Bot Manager
    print("\n4. Bot Manager...")
    try:
        bot_manager = BotManager(db, agent_manager)
        all_bots = bot_manager.get_all_bots()
        autonomous_bots = [
            bot for bot in all_bots.values()
            if bot.is_running and bot.current_config and bot.current_config.get("autonomous", False)
        ]
        print(f"   ✓ Bot Manager initialisiert")
        print(f"   ✓ Laufende Bots: {len([b for b in all_bots.values() if b.is_running])}")
        print(f"   ✓ Autonome Bots: {len(autonomous_bots)}")
        checks_passed += 1
    except Exception as e:
        print(f"   ✗ Bot Manager Fehler: {e}")
        checks_failed += 1
    
    # 5. Agent Tools
    print("\n5. Agent Tools...")
    try:
        agent_tools = AgentTools(bot=bot_manager, binance_client=binance_client, db=db)
        cyphermind_tools = agent_tools.get_cyphermind_tools()
        tool_names = [tool["function"]["name"] for tool in cyphermind_tools]
        print(f"   ✓ CypherMind Tools: {len(cyphermind_tools)} Tools")
        print(f"   ✓ Tools: {', '.join(tool_names[:5])}...")
        
        # Prüfe ob analyze_optimal_coins vorhanden
        if "analyze_optimal_coins" in tool_names:
            print(f"   ✓ analyze_optimal_coins Tool vorhanden")
            checks_passed += 1
        else:
            print(f"   ✗ analyze_optimal_coins Tool NICHT gefunden!")
            checks_failed += 1
        
        # Prüfe ob start_autonomous_bot vorhanden
        if "start_autonomous_bot" in tool_names:
            print(f"   ✓ start_autonomous_bot Tool vorhanden")
            checks_passed += 1
        else:
            print(f"   ✗ start_autonomous_bot Tool NICHT gefunden!")
            checks_failed += 1
    except Exception as e:
        print(f"   ✗ Agent Tools Fehler: {e}")
        checks_failed += 1
    
    # 6. Coin Analyzer
    print("\n6. Coin Analyzer...")
    try:
        from coin_analyzer import CoinAnalyzer
        analyzer = CoinAnalyzer(binance_client)
        print(f"   ✓ Coin Analyzer verfügbar")
        checks_passed += 1
    except ImportError as e:
        print(f"   ✗ Coin Analyzer nicht verfügbar: {e}")
        checks_failed += 1
    except Exception as e:
        print(f"   ✗ Coin Analyzer Fehler: {e}")
        checks_failed += 1
    
    # 7. Autonomous Manager
    print("\n7. Autonomous Manager...")
    try:
        autonomous_manager = AutonomousManager(
            agent_manager=agent_manager,
            bot_manager=bot_manager,
            db=db,
            binance_client=binance_client
        )
        print(f"   ✓ Autonomous Manager initialisiert")
        print(f"   ✓ Is Running: {autonomous_manager.is_running}")
        checks_passed += 1
    except Exception as e:
        print(f"   ✗ Autonomous Manager Fehler: {e}")
        checks_failed += 1
    
    # 8. LLM Konfiguration
    print("\n8. LLM Konfiguration...")
    try:
        cyphermind_config = agent_manager._get_llm_config("cyphermind")
        print(f"   ✓ CypherMind LLM Config vorhanden")
        print(f"   ✓ Model: {cyphermind_config['config_list'][0].get('model', 'N/A')}")
        print(f"   ✓ Base URL: {cyphermind_config['config_list'][0].get('base_url', 'N/A')}")
        
        # Prüfe ob Functions registriert sind
        if "functions" in cyphermind_config:
            functions = cyphermind_config["functions"]
            print(f"   ✓ Functions registriert: {len(functions)} Tools")
            function_names = [f["function"]["name"] for f in functions if "function" in f]
            if "analyze_optimal_coins" in function_names:
                print(f"   ✓ analyze_optimal_coins in LLM Config")
                checks_passed += 1
            else:
                print(f"   ✗ analyze_optimal_coins NICHT in LLM Config!")
                checks_failed += 1
        else:
            print(f"   ✗ KEINE Functions in LLM Config!")
            checks_failed += 1
    except Exception as e:
        print(f"   ✗ LLM Konfiguration Fehler: {e}")
        checks_failed += 1
    
    # 9. Verfügbares Budget
    print("\n9. Verfügbares Budget...")
    try:
        available_capital = binance_client.get_account_balance("USDT", "SPOT")
        max_budget = available_capital * 0.4
        min_budget = 10.0
        
        if available_capital >= min_budget:
            print(f"   ✓ Verfügbares Kapital: {available_capital:.2f} USDT")
            print(f"   ✓ Max Budget (40%): {max_budget:.2f} USDT")
            print(f"   ✓ Min Budget: {min_budget:.2f} USDT")
            checks_passed += 1
        else:
            print(f"   ✗ Zu wenig Kapital: {available_capital:.2f} USDT (min: {min_budget} USDT)")
            checks_failed += 1
    except Exception as e:
        print(f"   ✗ Budget-Prüfung Fehler: {e}")
        checks_failed += 1
    
    # Zusammenfassung
    print("\n" + "=" * 80)
    print("ZUSAMMENFASSUNG")
    print("=" * 80)
    print(f"✓ Bestanden: {checks_passed}")
    print(f"✗ Fehlgeschlagen: {checks_failed}")
    print(f"Gesamt: {checks_passed + checks_failed}")
    
    if checks_failed == 0:
        print("\n✓ ALLE VORAUSSETZUNGEN ERFÜLLT!")
        print("  CypherMind sollte in der Lage sein, autonome Bots zu starten.")
    else:
        print(f"\n✗ {checks_failed} VORAUSSETZUNG(EN) FEHLEN!")
        print("  Bitte die oben genannten Fehler beheben.")
    
    print()

if __name__ == "__main__":
    asyncio.run(check_prerequisites())

