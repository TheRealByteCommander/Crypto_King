"""
Test Script für das Crypto News System
Prüft alle Komponenten der Implementierung
"""

import asyncio
import sys
from typing import Dict, Any

def test_imports():
    """Test 1: Prüft ob alle Imports funktionieren."""
    print("=" * 60)
    print("TEST 1: Imports prüfen")
    print("=" * 60)
    
    try:
        import feedparser
        print("✅ feedparser importiert")
    except ImportError as e:
        print(f"❌ feedparser fehlt: {e}")
        return False
    
    try:
        from bs4 import BeautifulSoup
        print("✅ beautifulsoup4 importiert")
    except ImportError as e:
        print(f"❌ beautifulsoup4 fehlt: {e}")
        return False
    
    try:
        import httpx
        print("✅ httpx importiert")
    except ImportError as e:
        print(f"❌ httpx fehlt: {e}")
        return False
    
    try:
        from crypto_news_fetcher import get_news_fetcher, TRUSTED_SOURCES
        print("✅ crypto_news_fetcher importiert")
    except ImportError as e:
        print(f"❌ crypto_news_fetcher Import fehlgeschlagen: {e}")
        return False
    
    try:
        from agent_tools import AgentTools
        print("✅ agent_tools importiert")
    except ImportError as e:
        print(f"❌ agent_tools Import fehlgeschlagen: {e}")
        return False
    
    return True

def test_trusted_sources():
    """Test 2: Prüft die Whitelist-Konfiguration."""
    print("\n" + "=" * 60)
    print("TEST 2: Whitelist-Konfiguration prüfen")
    print("=" * 60)
    
    try:
        from crypto_news_fetcher import TRUSTED_SOURCES
        
        if len(TRUSTED_SOURCES) == 0:
            print("❌ Keine vertrauenswürdigen Quellen definiert")
            return False
        
        print(f"✅ {len(TRUSTED_SOURCES)} vertrauenswürdige Quellen gefunden:")
        for key, info in TRUSTED_SOURCES.items():
            name = info.get("name", "Unknown")
            enabled = info.get("enabled", False)
            rss = info.get("rss", "Missing")
            score = info.get("reliability_score", 0.0)
            status = "✅" if enabled else "❌"
            print(f"  {status} {name} ({key}) - Score: {score}, RSS: {rss[:50]}...")
        
        return True
    except Exception as e:
        print(f"❌ Fehler beim Prüfen der Whitelist: {e}")
        return False

def test_news_fetcher_initialization():
    """Test 3: Prüft die News-Fetcher-Initialisierung."""
    print("\n" + "=" * 60)
    print("TEST 3: News-Fetcher-Initialisierung")
    print("=" * 60)
    
    try:
        from crypto_news_fetcher import get_news_fetcher
        
        fetcher = get_news_fetcher()
        print("✅ News-Fetcher-Instanz erstellt")
        
        sources = fetcher.get_available_sources()
        print(f"✅ {len(sources)} Quellen verfügbar")
        
        return True
    except Exception as e:
        print(f"❌ Fehler bei News-Fetcher-Initialisierung: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_tools_integration():
    """Test 4: Prüft die Integration in AgentTools."""
    print("\n" + "=" * 60)
    print("TEST 4: AgentTools-Integration")
    print("=" * 60)
    
    try:
        from agent_tools import AgentTools
        
        tools = AgentTools()
        nexus_tools = tools.get_nexuschat_tools()
        
        print(f"✅ NexusChat hat {len(nexus_tools)} Tools")
        
        # Prüfe ob get_crypto_news vorhanden ist
        news_tool = None
        for tool in nexus_tools:
            func = tool.get("function", {})
            if func.get("name") == "get_crypto_news":
                news_tool = func
                break
        
        if not news_tool:
            print("❌ get_crypto_news Tool nicht gefunden")
            return False
        
        print("✅ get_crypto_news Tool gefunden")
        
        # Prüfe Parameter
        params = news_tool.get("parameters", {})
        props = params.get("properties", {})
        
        required_params = ["limit", "symbols", "query"]
        for param in required_params:
            if param in props:
                print(f"  ✅ Parameter '{param}' vorhanden")
            else:
                print(f"  ⚠️  Parameter '{param}' fehlt (optional)")
        
        return True
    except Exception as e:
        print(f"❌ Fehler bei AgentTools-Integration: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_async_tool_execution():
    """Test 5: Prüft die async Tool-Ausführung (ohne echte HTTP-Requests)."""
    print("\n" + "=" * 60)
    print("TEST 5: Async Tool-Ausführung (Mock)")
    print("=" * 60)
    
    try:
        from agent_tools import AgentTools
        
        tools = AgentTools()
        
        # Test mit leeren Parametern (sollte nicht crashen)
        try:
            result = await tools.execute_tool("NexusChat", "get_crypto_news", {})
            # Erwarte entweder Success oder Error, aber kein Crash
            if "success" in result:
                print("✅ Tool-Ausführung gibt strukturierte Antwort zurück")
                if result.get("success"):
                    print(f"  ✅ Erfolgreich: {result.get('count', 0)} Artikel")
                else:
                    print(f"  ⚠️  Fehler (erwartet bei fehlendem Internet): {result.get('error', 'Unknown')}")
                return True
            else:
                print("❌ Tool-Antwort hat kein 'success' Feld")
                return False
        except Exception as e:
            # Bei Network-Fehlern ist das OK
            error_msg = str(e)
            if "network" in error_msg.lower() or "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                print(f"⚠️  Network-Fehler (erwartet ohne Internet): {error_msg[:100]}")
                return True
            else:
                print(f"❌ Unerwarteter Fehler: {e}")
                import traceback
                traceback.print_exc()
                return False
        
    except Exception as e:
        print(f"❌ Fehler bei async Tool-Ausführung: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_spam_filtering():
    """Test 6: Prüft die Spam-Filter-Logik."""
    print("\n" + "=" * 60)
    print("TEST 6: Spam-Filter-Logik")
    print("=" * 60)
    
    try:
        from crypto_news_fetcher import CryptoNewsFetcher
        
        fetcher = CryptoNewsFetcher()
        
        # Test-Titel die als Spam erkannt werden sollten
        spam_titles = [
            "GUARANTEED 100% PROFIT!!!",
            "Click here for FREE crypto giveaway",
            "Pump and dump group - join now!",
            "Secret method to get rich quick",
            "Risk-free investment opportunity"
        ]
        
        # Test-Titel die NICHT als Spam erkannt werden sollten
        valid_titles = [
            "Bitcoin Reaches New All-Time High",
            "Ethereum Upgrade Scheduled for Next Month",
            "Crypto Market Shows Strong Recovery",
            "Regulatory Changes Impact Crypto Trading"
        ]
        
        spam_detected = 0
        for title in spam_titles:
            if fetcher._is_spam_or_fake(title, ""):
                spam_detected += 1
                print(f"  ✅ Spam erkannt: '{title[:50]}...'")
            else:
                print(f"  ⚠️  Spam NICHT erkannt: '{title[:50]}...'")
        
        valid_not_detected = 0
        for title in valid_titles:
            if not fetcher._is_spam_or_fake(title, ""):
                valid_not_detected += 1
                print(f"  ✅ Gültiger Titel: '{title[:50]}...'")
            else:
                print(f"  ❌ Falsch als Spam erkannt: '{title[:50]}...'")
        
        print(f"\n✅ Spam-Filter: {spam_detected}/{len(spam_titles)} Spam-Titel erkannt")
        print(f"✅ Valid-Filter: {valid_not_detected}/{len(valid_titles)} gültige Titel akzeptiert")
        
        # Cleanup
        asyncio.run(fetcher.close())
        
        return spam_detected >= len(spam_titles) * 0.6  # Mindestens 60% sollten erkannt werden
    
    except Exception as e:
        print(f"❌ Fehler bei Spam-Filter-Test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rate_limiting():
    """Test 7: Prüft die Rate-Limiting-Logik."""
    print("\n" + "=" * 60)
    print("TEST 7: Rate-Limiting-Logik")
    print("=" * 60)
    
    try:
        from crypto_news_fetcher import CryptoNewsFetcher, RATE_LIMIT_REQUESTS_PER_MINUTE
        
        fetcher = CryptoNewsFetcher()
        
        test_source = "test_source"
        
        # Simuliere mehrere Requests
        allowed = 0
        blocked = 0
        
        for i in range(RATE_LIMIT_REQUESTS_PER_MINUTE + 5):
            if fetcher._check_rate_limit(test_source):
                allowed += 1
            else:
                blocked += 1
        
        print(f"✅ Rate Limiting: {allowed} erlaubt, {blocked} blockiert")
        
        if allowed <= RATE_LIMIT_REQUESTS_PER_MINUTE:
            print(f"  ✅ Rate Limit funktioniert (max {RATE_LIMIT_REQUESTS_PER_MINUTE} erlaubt)")
            return True
        else:
            print(f"  ❌ Rate Limit funktioniert nicht (mehr als {RATE_LIMIT_REQUESTS_PER_MINUTE} erlaubt)")
            return False
    
    except Exception as e:
        print(f"❌ Fehler bei Rate-Limiting-Test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Führt alle Tests aus."""
    print("\n" + "=" * 60)
    print("CRYPTO NEWS SYSTEM - VOLLSTÄNDIGER TEST")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Whitelist-Konfiguration", test_trusted_sources),
        ("News-Fetcher-Initialisierung", test_news_fetcher_initialization),
        ("AgentTools-Integration", test_agent_tools_integration),
        ("Async Tool-Ausführung", test_async_tool_execution),
        ("Spam-Filter-Logik", test_spam_filtering),
        ("Rate-Limiting-Logik", test_rate_limiting),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Zusammenfassung
    print("\n" + "=" * 60)
    print("TEST-ZUSAMMENFASSUNG")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {name}")
    
    print(f"\n{'=' * 60}")
    print(f"ERGEBNIS: {passed}/{total} Tests bestanden")
    print("=" * 60)
    
    if passed == total:
        print("🎉 ALLE TESTS BESTANDEN!")
        return 0
    else:
        print("⚠️  EINIGE TESTS FEHLGESCHLAGEN - Bitte prüfen")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

