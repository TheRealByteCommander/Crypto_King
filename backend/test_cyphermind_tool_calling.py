#!/usr/bin/env python3
"""
Test-Skript: Prüft ob CypherMind Tools aufrufen kann
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from agents import AgentManager
from bot_manager import BotManager
from binance_client import BinanceClientWrapper
from motor.motor_asyncio import AsyncIOMotorClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_cyphermind_tool_calling():
    """Testet ob CypherMind Tools aufrufen kann."""
    print("=" * 80)
    print("TEST: CypherMind Tool-Aufrufe")
    print("=" * 80)
    print()
    
    try:
        # 1. Setup
        print("1. Initialisiere Komponenten...")
        mongo_url = settings.mongo_url
        db_name = settings.db_name
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        binance_client = BinanceClientWrapper()
        
        agent_manager = AgentManager(db, bot=None, binance_client=binance_client)
        bot_manager = BotManager(db, agent_manager)
        agent_manager.bot = bot_manager
        
        print("   ✓ Komponenten initialisiert")
        print()
        
        # 2. Hole CypherMind und UserProxy
        print("2. Hole Agents...")
        cyphermind = agent_manager.get_agent("CypherMind")
        user_proxy = agent_manager.get_agent("UserProxy")
        print(f"   ✓ CypherMind: {cyphermind.name}")
        print(f"   ✓ UserProxy: {user_proxy.name}")
        print()
        
        # 3. Teste direkten Tool-Aufruf
        print("3. Teste direkten Tool-Aufruf (analyze_optimal_coins)...")
        try:
            from agent_tools import AgentTools
            agent_tools = AgentTools(bot=bot_manager, binance_client=binance_client, db=db)
            
            # Teste Tool-Aufruf direkt
            result = await agent_tools.execute_tool(
                "CypherMind",
                "analyze_optimal_coins",
                {"max_coins": 5, "min_score": 0.3}
            )
            
            if result.get("success"):
                print(f"   ✓ Tool-Aufruf erfolgreich!")
                print(f"   ✓ Gefundene Coins: {result.get('count', 0)}")
                if result.get('coins'):
                    print(f"   ✓ Top Coin: {result['coins'][0].get('symbol', 'N/A')} (Score: {result['coins'][0].get('score', 0):.2f})")
            else:
                print(f"   ✗ Tool-Aufruf fehlgeschlagen: {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"   ✗ Fehler beim Tool-Aufruf: {e}")
            import traceback
            traceback.print_exc()
        print()
        
        # 4. Teste CypherMind Aktivierung mit Tool-Aufruf
        print("4. Teste CypherMind Aktivierung mit Tool-Aufruf...")
        print("   (Dies kann einige Sekunden dauern...)")
        
        message = (
            "TEST-AUFGABE:\n\n"
            "Rufe SOFORT das Tool 'analyze_optimal_coins' auf mit:\n"
            "- max_coins=5\n"
            "- min_score=0.3\n\n"
            "WICHTIG: Du MUSST das Tool direkt aufrufen - keine Diskussion!"
        )
        
        try:
            import autogen
            loop = asyncio.get_event_loop()
            
            def run_chat():
                try:
                    user_proxy.initiate_chat(
                        recipient=cyphermind,
                        message=message,
                        max_turns=3,
                        clear_history=False,
                        silent=False
                    )
                except Exception as chat_error:
                    logger.error(f"Error in initiate_chat: {chat_error}", exc_info=True)
                    raise
            
            # Führe Chat in Executor aus
            await loop.run_in_executor(None, run_chat)
            print("   ✓ CypherMind Aktivierung abgeschlossen")
            print("   ⚠ Prüfe ob CypherMind das Tool aufgerufen hat (siehe Logs)")
        except Exception as e:
            print(f"   ✗ Fehler bei CypherMind Aktivierung: {e}")
            import traceback
            traceback.print_exc()
        print()
        
        # 5. Prüfe LLM Config
        print("5. Prüfe LLM Konfiguration...")
        llm_config = agent_manager._get_llm_config("cyphermind")
        print(f"   ✓ Model: {llm_config['config_list'][0].get('model', 'N/A')}")
        print(f"   ✓ Base URL: {llm_config['config_list'][0].get('base_url', 'N/A')}")
        
        if "functions" in llm_config:
            functions = llm_config["functions"]
            print(f"   ✓ Functions registriert: {len(functions)}")
            function_names = [f["function"]["name"] for f in functions if "function" in f]
            print(f"   ✓ Tool-Namen: {', '.join(function_names[:5])}...")
            
            if "analyze_optimal_coins" in function_names:
                print("   ✓ analyze_optimal_coins ist registriert")
            else:
                print("   ✗ analyze_optimal_coins ist NICHT registriert!")
        else:
            print("   ✗ KEINE Functions in LLM Config!")
        print()
        
        print("=" * 80)
        print("TEST ABGESCHLOSSEN")
        print("=" * 80)
        print()
        print("HINWEISE:")
        print("- Wenn Tool-Aufruf direkt funktioniert, aber CypherMind es nicht aufruft:")
        print("  → Das Modell unterstützt möglicherweise kein Function Calling")
        print("  → Versuche ein anderes Modell (z.B. llama3.1, mistral, qwen2.5)")
        print("- Prüfe die Backend-Logs für detaillierte Fehlermeldungen:")
        print("  tail -f /var/log/supervisor/cyphertrade-backend.log | grep -i 'cyphermind\|tool'")
        print()
        
    except Exception as e:
        print(f"✗ FEHLER: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_cyphermind_tool_calling())

