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
AUTONOMOUS_ANALYSIS_INTERVAL_SECONDS = 1800  # 30 Minuten - permanente Überprüfung
NEWS_FETCH_INTERVAL_SECONDS = 1800  # 30 Minuten
MIN_COIN_SCORE_FOR_BOT_START = 0.4  # Mindest-Score für Bot-Start
MAX_AUTONOMOUS_BOTS = 6  # Key-Feature: Bis zu 6 autonome Bots
BOT_PERFORMANCE_CHECK_INTERVAL_SECONDS = 3600  # 1 Stunde - Performance-Check
BOT_MIN_RUNTIME_HOURS = 24  # Mindest-Laufzeit vor Performance-Check
BOT_MIN_PROFIT_THRESHOLD = 0.0  # Mindest-Profit in % nach 24h (0% = break-even)


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
        self.last_performance_check = None
        
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
        asyncio.create_task(self._bot_performance_monitor_loop())  # Permanente Performance-Überwachung
        
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
                f"Du kannst noch {MAX_AUTONOMOUS_BOTS - len(autonomous_bots)} autonome Bots starten (max. {MAX_AUTONOMOUS_BOTS} insgesamt).\n\n"
                "AUFGABE - KEY-FEATURE AUTOMATISCHE BOT-ERSTELLUNG:\n"
                "1. Führe eine Coin-Analyse durch (analyze_optimal_coins, max_coins=20) um die besten Trading-Opportunities zu finden.\n"
                "2. Prüfe ALLE handelbaren USDT-Paare - nicht nur die Top 10!\n"
                "3. Wenn du Coins mit Score >= 0.4 findest, starte autonome Bots für die besten Coins.\n"
                "4. Wähle die beste Strategie für jeden Coin basierend auf der Analyse.\n"
                "5. Ziel: Maximaler Profit durch optimale Coin-Auswahl und Strategie-Kombination.\n\n"
                "WICHTIG:\n"
                "- Berücksichtige News-Informationen in deiner Analyse.\n"
                "- Starte nur Bots wenn die Profit-Chance hoch ist (Score >= 0.4).\n"
                "- Max. 6 autonome Bots insgesamt (KEY-FEATURE!).\n"
                "- Budget wird automatisch berechnet (Durchschnitt, max. 40% Kapital).\n"
                "- Das System stoppt automatisch erfolglose Bots nach 24h und startet sofort eine neue Analyse.\n"
                "- Du wirst PERMANENT aktiviert (alle 30 Minuten) für optimale Bot-Verwaltung.\n"
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
    
    async def _bot_performance_monitor_loop(self):
        """Permanente Überwachung der autonomen Bot-Performance und automatisches Stoppen erfolgloser Bots."""
        logger.info("Bot performance monitor loop started")
        
        while self.is_running:
            try:
                # Warte initial 1 Stunde, damit Bots Zeit haben zu starten
                if self.last_performance_check is None:
                    await asyncio.sleep(3600)
                
                logger.info("Checking autonomous bot performance...")
                
                # Hole alle laufenden Bots
                all_bots = self.bot_manager.get_all_bots()
                autonomous_bots = [
                    bot for bot in all_bots.values()
                    if bot.is_running
                    and bot.current_config
                    and bot.current_config.get("autonomous", False)
                    and bot.current_config.get("started_by") == "CypherMind"  # Nur autonome Bots, keine User-Bots
                ]
                
                if not autonomous_bots:
                    logger.debug("No autonomous bots running, skipping performance check")
                    self.last_performance_check = datetime.now(timezone.utc)
                    await asyncio.sleep(BOT_PERFORMANCE_CHECK_INTERVAL_SECONDS)
                    continue
                
                logger.info(f"Checking performance of {len(autonomous_bots)} autonomous bots...")
                
                bots_to_stop = []
                current_time = datetime.now(timezone.utc)
                
                for bot in autonomous_bots:
                    try:
                        # Prüfe Bot-Laufzeit
                        started_at_str = bot.current_config.get("started_at")
                        if not started_at_str:
                            continue
                        
                        started_at = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
                        runtime_hours = (current_time - started_at).total_seconds() / 3600
                        
                        # Nur Bots prüfen, die mindestens 24h laufen
                        if runtime_hours < BOT_MIN_RUNTIME_HOURS:
                            logger.debug(f"Bot {bot.bot_id} running for {runtime_hours:.1f}h, skipping (min: {BOT_MIN_RUNTIME_HOURS}h)")
                            continue
                        
                        # Berechne Bot-Performance (Gesamt-P&L)
                        performance = await self._calculate_bot_performance(bot)
                        
                        if performance is None:
                            logger.warning(f"Could not calculate performance for bot {bot.bot_id}")
                            continue
                        
                        total_pnl_percent = performance.get("total_pnl_percent", 0.0)
                        total_trades = performance.get("total_trades", 0)
                        
                        logger.info(
                            f"Bot {bot.bot_id} ({bot.current_config.get('symbol')}, {bot.current_config.get('strategy')}): "
                            f"Runtime: {runtime_hours:.1f}h, P&L: {total_pnl_percent:.2f}%, Trades: {total_trades}"
                        )
                        
                        # Stoppe Bot wenn Performance unter Schwellenwert
                        if total_pnl_percent < BOT_MIN_PROFIT_THRESHOLD:
                            logger.warning(
                                f"Bot {bot.bot_id} has negative/insufficient performance "
                                f"({total_pnl_percent:.2f}% after {runtime_hours:.1f}h). Stopping bot."
                            )
                            bots_to_stop.append({
                                "bot": bot,
                                "reason": f"Insufficient performance: {total_pnl_percent:.2f}% after {runtime_hours:.1f}h",
                                "performance": performance
                            })
                    
                    except Exception as e:
                        logger.error(f"Error checking performance for bot {bot.bot_id}: {e}", exc_info=True)
                        continue
                
                # Stoppe erfolglose Bots
                for bot_info in bots_to_stop:
                    bot = bot_info["bot"]
                    reason = bot_info["reason"]
                    performance = bot_info["performance"]
                    
                    try:
                        logger.info(f"Stopping bot {bot.bot_id}: {reason}")
                        
                        # Stoppe Bot
                        stop_result = await bot.stop()
                        
                        if stop_result.get("success"):
                            # Logge Stopp-Grund
                            await self.agent_manager.log_agent_message(
                                "AutonomousManager",
                                f"Autonomer Bot {bot.bot_id} ({bot.current_config.get('symbol')}, {bot.current_config.get('strategy')}) wurde gestoppt.\n"
                                f"Grund: {reason}\n"
                                f"Performance: {performance.get('total_pnl_percent', 0):.2f}% P&L, {performance.get('total_trades', 0)} Trades",
                                "bot_stopped"
                            )
                            
                            # Kurz warten, dann sofort neue Analyse starten
                            await asyncio.sleep(5)
                            
                            # Aktiviere CypherMind für sofortige Re-Analyse
                            await self._activate_cyphermind_for_analysis()
                            
                        else:
                            logger.error(f"Failed to stop bot {bot.bot_id}: {stop_result.get('message')}")
                    
                    except Exception as e:
                        logger.error(f"Error stopping bot {bot.bot_id}: {e}", exc_info=True)
                
                self.last_performance_check = datetime.now(timezone.utc)
                
            except Exception as e:
                logger.error(f"Error in bot performance monitor loop: {e}", exc_info=True)
            
            await asyncio.sleep(BOT_PERFORMANCE_CHECK_INTERVAL_SECONDS)
    
    async def _calculate_bot_performance(self, bot) -> Optional[Dict[str, Any]]:
        """Berechnet die Performance eines Bots basierend auf seinen Trades."""
        try:
            from motor.motor_asyncio import AsyncIOMotorDatabase
            
            if not isinstance(self.db, AsyncIOMotorDatabase):
                return None
            
            bot_id = bot.bot_id
            symbol = bot.current_config.get("symbol")
            
            # Hole alle Trades dieses Bots
            trades = await self.db.trades.find({
                "bot_id": bot_id,
                "symbol": symbol
            }).to_list(1000)  # Max 1000 Trades
            
            if not trades:
                return {
                    "total_trades": 0,
                    "total_pnl": 0.0,
                    "total_pnl_percent": 0.0,
                    "winning_trades": 0,
                    "losing_trades": 0
                }
            
            # Berechne Gesamt-P&L
            total_pnl = 0.0
            total_invested = 0.0
            winning_trades = 0
            losing_trades = 0
            closed_positions = 0
            
            # Sortiere Trades nach Timestamp (älteste zuerst)
            trades_sorted = sorted(trades, key=lambda x: x.get("timestamp", ""))
            
            # Berechne P&L für geschlossene Positionen
            for trade in trades_sorted:
                side = trade.get("side", "")
                position_type = trade.get("position_type", "")
                
                # Für geschlossene Positionen: Berechne P&L
                if side == "SELL" and position_type in ["LONG_CLOSE", "SHORT_CLOSE"]:
                    entry_price = trade.get("entry_price", 0)
                    exit_price = trade.get("execution_price", 0)
                    quantity = trade.get("quantity", 0)
                    pnl_percent = trade.get("pnl_percent")  # Falls bereits berechnet
                    
                    if entry_price > 0 and exit_price > 0 and quantity > 0:
                        if position_type == "LONG_CLOSE":
                            # LONG: Profit wenn exit > entry
                            pnl = (exit_price - entry_price) * quantity
                            if pnl_percent is None:
                                pnl_percent = ((exit_price - entry_price) / entry_price) * 100
                        else:  # SHORT_CLOSE
                            # SHORT: Profit wenn entry > exit
                            pnl = (entry_price - exit_price) * quantity
                            if pnl_percent is None:
                                pnl_percent = ((entry_price - exit_price) / entry_price) * 100
                        
                        total_pnl += pnl
                        total_invested += entry_price * quantity
                        closed_positions += 1
                        
                        if pnl > 0:
                            winning_trades += 1
                        elif pnl < 0:
                            losing_trades += 1
                
                # Für BUY Trades: Zähle als Investition (wenn noch keine Position geschlossen wurde)
                elif side == "BUY" and position_type in ["LONG_OPEN", None]:
                    # Investition wird bei SELL berücksichtigt
                    pass
            
            # Berechne Gesamt-P&L Prozent
            if total_invested > 0:
                total_pnl_percent = (total_pnl / total_invested) * 100
            elif closed_positions > 0:
                # Fallback: Durchschnittlicher P&L Prozent
                total_pnl_percent = (total_pnl / closed_positions) if closed_positions > 0 else 0.0
            else:
                total_pnl_percent = 0.0
            
            return {
                "total_trades": len(trades),
                "closed_positions": closed_positions,
                "total_pnl": round(total_pnl, 2),
                "total_pnl_percent": round(total_pnl_percent, 2),
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "total_invested": round(total_invested, 2)
            }
        
        except Exception as e:
            logger.error(f"Error calculating bot performance: {e}", exc_info=True)
            return None

