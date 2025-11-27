"""
Autonomous Manager - Verwaltet autonome Trading-Aktivitäten von CypherMind
- Periodische News-Abrufe und Weiterleitung an Agents
- Automatische Coin-Analyse und Bot-Start
- Proaktives Trading für maximalen Profit
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from agents import AgentManager
from bot_manager import BotManager
from binance_client import BinanceClientWrapper

logger = logging.getLogger(__name__)

# Constants
AUTONOMOUS_ANALYSIS_INTERVAL_SECONDS = 3600  # 1 Stunde
NEWS_FETCH_INTERVAL_SECONDS = 1800  # 30 Minuten
MIN_COIN_SCORE_FOR_BOT_START = 0.4  # Mindest-Score für Bot-Start
MAX_AUTONOMOUS_BOTS = 2


class AutonomousManager:
    """Verwaltet autonome Trading-Aktivitäten."""
    
    def __init__(self, agent_manager: AgentManager, bot_manager: BotManager, db, binance_client: Optional[BinanceClientWrapper] = None):
        self.agent_manager = agent_manager
        self.bot_manager = bot_manager
        self.db = db
        self.binance_client = binance_client
        self.is_running = False
        self.last_news_fetch = None
        self.last_analysis = None
        
    async def start(self):
        """Startet den autonomen Manager."""
        if self.is_running:
            logger.warning("AutonomousManager is already running")
            return
        
        self.is_running = True
        logger.info("AutonomousManager started - CypherMind wird jetzt autonom arbeiten")
        
        # Starte Background-Tasks
        asyncio.create_task(self._news_fetch_loop())
        asyncio.create_task(self._autonomous_analysis_loop())
        
    async def stop(self):
        """Stoppt den autonomen Manager."""
        self.is_running = False
        logger.info("AutonomousManager stopped")
    
    async def _news_fetch_loop(self):
        """Periodisch News abrufen und direkt an CypherMind/CypherTrade weiterleiten."""
        logger.info("News fetch loop started")
        
        while self.is_running:
            try:
                # Warte initial 60 Sekunden, damit System hochgefahren ist
                if self.last_news_fetch is None:
                    await asyncio.sleep(60)
                
                # Prüfe ob News-Fetcher verfügbar ist
                try:
                    from crypto_news_fetcher import get_news_fetcher
                    news_fetcher = get_news_fetcher()
                except ImportError:
                    logger.warning("crypto_news_fetcher not available, skipping news fetch")
                    await asyncio.sleep(NEWS_FETCH_INTERVAL_SECONDS)
                    continue
                
                # Hole wichtige News
                logger.info("Fetching important crypto news...")
                articles = await news_fetcher.fetch_news(
                    limit_per_source=5,
                    max_total=20
                )
                
                # Filtere wichtige News (Score >= 0.6)
                important_articles = news_fetcher.filter_important_news(articles, min_importance_score=0.6)
                
                if important_articles:
                    logger.info(f"Found {len(important_articles)} important news articles, sharing with agents...")
                    
                    # Teile News direkt mit CypherMind und CypherTrade
                    await self.agent_manager.share_news_with_agents(
                        articles=important_articles,
                        target_agents=["both"],
                        priority="high"
                    )
                    
                    # Aktiviere CypherMind direkt mit News-Kontext
                    await self._activate_cyphermind_with_news(important_articles)
                
                self.last_news_fetch = datetime.now(timezone.utc)
                
            except Exception as e:
                logger.error(f"Error in news fetch loop: {e}", exc_info=True)
            
            await asyncio.sleep(NEWS_FETCH_INTERVAL_SECONDS)
    
    async def _activate_cyphermind_with_news(self, articles: List[Dict[str, Any]]):
        """Aktiviert CypherMind direkt mit News-Kontext und erwartet proaktive Reaktion."""
        try:
            # Erstelle News-Zusammenfassung
            news_summary = "WICHTIGE MARKT-NEWS:\n\n"
            symbols_mentioned = set()
            for article in articles[:5]:  # Top 5 News
                news_summary += f"- {article.get('title', 'No Title')} (Source: {article.get('source', 'Unknown')})\n"
                news_summary += f"  {article.get('summary', 'No summary')[:200]}...\n"
                # Sammle erwähnte Symbole
                article_symbols = article.get('symbols', [])
                symbols_mentioned.update(article_symbols)
                if article_symbols:
                    news_summary += f"  Relevante Coins: {', '.join(article_symbols)}\n"
                news_summary += "\n"
            
            # Sende direkt an CypherMind
            cyphermind = self.agent_manager.get_agent("CypherMind")
            user_proxy = self.agent_manager.get_agent("UserProxy")
            
            message = (
                f"{news_summary}\n"
                "AUFGABE:\n"
                "1. Analysiere diese News auf Trading-Opportunities.\n"
                "2. Führe eine Coin-Analyse durch (analyze_optimal_coins) für betroffene Coins.\n"
                "3. Wenn gute Opportunities gefunden werden (Score >= 0.4): Starte SOFORT autonome Bots.\n"
                "4. Ziel: Profit aus News-getriebenen Marktbewegungen.\n"
                "5. Reagiere PROAKTIV - nutze diese Opportunities für maximalen Profit."
            )
            
            # Sende Nachricht an CypherMind und erwarte Antwort (CypherMind soll Tools aufrufen)
            user_proxy.send(
                message=message,
                recipient=cyphermind,
                request_reply=True,
                max_turns=5  # Erlaube mehrere Tool-Aufrufe
            )
            
            logger.info(f"CypherMind activated with news context ({len(articles)} articles, {len(symbols_mentioned)} symbols)")
            
        except Exception as e:
            logger.error(f"Error activating CypherMind with news: {e}", exc_info=True)
    
    async def _autonomous_analysis_loop(self):
        """Periodisch Coin-Analyse durchführen und Bots starten wenn nötig."""
        logger.info("Autonomous analysis loop started")
        
        while self.is_running:
            try:
                # Warte initial 5 Minuten, damit System hochgefahren ist
                if self.last_analysis is None:
                    await asyncio.sleep(300)
                
                # Prüfe ob Coin-Analyzer verfügbar ist
                try:
                    from coin_analyzer import CoinAnalyzer
                    if self.binance_client is None:
                        logger.warning("Binance client not available, skipping autonomous analysis")
                        await asyncio.sleep(AUTONOMOUS_ANALYSIS_INTERVAL_SECONDS)
                        continue
                except ImportError:
                    logger.warning("coin_analyzer not available, skipping autonomous analysis")
                    await asyncio.sleep(AUTONOMOUS_ANALYSIS_INTERVAL_SECONDS)
                    continue
                
                # Prüfe wie viele autonome Bots bereits laufen
                all_bots = self.bot_manager.get_all_bots()
                autonomous_bots = [
                    bot for bot in all_bots.values()
                    if bot.is_running 
                    and bot.current_config 
                    and bot.current_config.get("autonomous", False)
                ]
                
                if len(autonomous_bots) >= MAX_AUTONOMOUS_BOTS:
                    logger.info(f"Max autonomous bots ({MAX_AUTONOMOUS_BOTS}) already running, skipping analysis")
                    self.last_analysis = datetime.now(timezone.utc)
                    await asyncio.sleep(AUTONOMOUS_ANALYSIS_INTERVAL_SECONDS)
                    continue
                
                logger.info("Starting autonomous coin analysis...")
                
                # Aktiviere CypherMind für autonome Analyse
                await self._activate_cyphermind_for_analysis()
                
                self.last_analysis = datetime.now(timezone.utc)
                
            except Exception as e:
                logger.error(f"Error in autonomous analysis loop: {e}", exc_info=True)
            
            await asyncio.sleep(AUTONOMOUS_ANALYSIS_INTERVAL_SECONDS)
    
    async def _activate_cyphermind_for_analysis(self):
        """Aktiviert CypherMind für autonome Coin-Analyse und Bot-Start."""
        try:
            # Hole Status aller laufenden Bots
            all_bots = self.bot_manager.get_all_bots()
            running_bots = [bot for bot in all_bots.values() if bot.is_running]
            autonomous_bots = [
                bot for bot in running_bots
                if bot.current_config and bot.current_config.get("autonomous", False)
            ]
            
            # Erstelle Kontext-Nachricht
            context_message = (
                "AUTONOME ANALYSE-AUFGABE:\n\n"
                f"Aktuell laufen {len(running_bots)} Bots insgesamt, davon {len(autonomous_bots)} autonome Bots.\n"
                f"Du kannst noch {MAX_AUTONOMOUS_BOTS - len(autonomous_bots)} autonome Bots starten.\n\n"
                "AUFGABE:\n"
                "1. Führe eine Coin-Analyse durch (analyze_optimal_coins) um die besten Trading-Opportunities zu finden.\n"
                "2. Wenn du Coins mit Score >= 0.4 findest, starte autonome Bots für die besten Coins.\n"
                "3. Wähle die beste Strategie für jeden Coin basierend auf der Analyse.\n"
                "4. Ziel: Maximaler Profit durch optimale Coin-Auswahl und Strategie-Kombination.\n\n"
                "WICHTIG:\n"
                "- Berücksichtige News-Informationen in deiner Analyse.\n"
                "- Starte nur Bots wenn die Profit-Chance hoch ist (Score >= 0.4).\n"
                "- Max. 2 autonome Bots insgesamt.\n"
                "- Budget wird automatisch berechnet (Durchschnitt, max. 40% Kapital).\n"
            )
            
            # Sende direkt an CypherMind
            cyphermind = self.agent_manager.get_agent("CypherMind")
            user_proxy = self.agent_manager.get_agent("UserProxy")
            
            # Sende Nachricht und erwarte Antwort (CypherMind soll Tools aufrufen)
            user_proxy.send(
                message=context_message,
                recipient=cyphermind,
                request_reply=True,
                max_turns=5  # Erlaube mehrere Tool-Aufrufe
            )
            
            logger.info("CypherMind activated for autonomous analysis")
            
        except Exception as e:
            logger.error(f"Error activating CypherMind for analysis: {e}", exc_info=True)

