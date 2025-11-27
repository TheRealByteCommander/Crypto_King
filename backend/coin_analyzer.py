"""
Coin Analyzer - Analysiert Coins für optimale Trading-Entscheidungen
Kombiniert Echtzeitkurse, technische Indikatoren und News
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import pandas as pd
from binance_client import BinanceClientWrapper
from crypto_news_fetcher import get_news_fetcher
from strategies import get_strategy

logger = logging.getLogger(__name__)

class CoinAnalyzer:
    """Analysiert Coins für optimale Trading-Entscheidungen."""
    
    def __init__(self, binance_client: BinanceClientWrapper):
        self.binance_client = binance_client
        self.news_fetcher = get_news_fetcher()
    
    async def analyze_coin(self, symbol: str, strategies: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Analysiert einen einzelnen Coin.
        
        Args:
            symbol: Trading-Symbol (z.B. "BTCUSDT")
            strategies: Liste von Strategien zum Testen (None = alle)
        
        Returns:
            Analyse-Ergebnis mit Score, Empfehlungen, etc.
        """
        try:
            if strategies is None:
                strategies = ["ma_crossover", "rsi", "macd", "bollinger_bands", "combined"]
            
            # 1. Echtzeitkurs
            current_price = self.binance_client.get_current_price(symbol)
            if not current_price or current_price <= 0:
                return {
                    "symbol": symbol,
                    "error": "Could not get current price",
                    "score": 0.0
                }
            
            # 2. Marktdaten für verschiedene Timeframes
            timeframes = ["5m", "15m", "1h", "4h"]
            market_data = {}
            for tf in timeframes:
                try:
                    df = self.binance_client.get_market_data(symbol, tf, 100)
                    if len(df) > 0:
                        market_data[tf] = df
                except Exception as e:
                    logger.warning(f"Could not get market data for {symbol} {tf}: {e}")
            
            if not market_data:
                return {
                    "symbol": symbol,
                    "error": "Could not get market data",
                    "score": 0.0
                }
            
            # 3. Technische Analyse für jede Strategie
            strategy_scores = {}
            best_strategy = None
            best_score = 0.0
            
            for strategy_name in strategies:
                try:
                    strategy = get_strategy(strategy_name)
                    if not strategy:
                        continue
                    
                    # Teste auf verschiedenen Timeframes
                    strategy_results = []
                    for tf, df in market_data.items():
                        try:
                            signal, confidence, indicators = strategy.analyze(df)
                            
                            # Bewerte Signal
                            signal_score = 0.0
                            if signal == "BUY":
                                signal_score = confidence * 0.5  # BUY = positiv
                            elif signal == "SELL":
                                signal_score = -confidence * 0.3  # SELL = negativ (aber weniger negativ)
                            # HOLD = 0.0
                            
                            strategy_results.append({
                                "timeframe": tf,
                                "signal": signal,
                                "confidence": confidence,
                                "score": signal_score,
                                "indicators": indicators
                            })
                        except Exception as e:
                            logger.warning(f"Error analyzing {strategy_name} for {symbol} {tf}: {e}")
                    
                    # Berechne Durchschnitts-Score für diese Strategie
                    if strategy_results:
                        avg_score = sum(r["score"] for r in strategy_results) / len(strategy_results)
                        avg_confidence = sum(r["confidence"] for r in strategy_results) / len(strategy_results)
                        
                        strategy_scores[strategy_name] = {
                            "score": avg_score,
                            "confidence": avg_confidence,
                            "results": strategy_results
                        }
                        
                        if avg_score > best_score:
                            best_score = avg_score
                            best_strategy = strategy_name
                
                except Exception as e:
                    logger.warning(f"Error testing strategy {strategy_name} for {symbol}: {e}")
            
            # 4. Volatilität berechnen (24h)
            volatility = 0.0
            if "1h" in market_data:
                df_1h = market_data["1h"]
                if len(df_1h) >= 24:
                    prices = df_1h["close"].tail(24)
                    price_changes = prices.pct_change().dropna()
                    volatility = price_changes.std() * 100  # In Prozent
            
            # 5. Trend-Analyse
            trend_score = 0.0
            trend_direction = "NEUTRAL"
            if "4h" in market_data:
                df_4h = market_data["4h"]
                if len(df_4h) >= 20:
                    sma_short = df_4h["close"].tail(10).mean()
                    sma_long = df_4h["close"].tail(20).mean()
                    if sma_short > sma_long * 1.02:  # 2% über langem SMA
                        trend_score = 0.3
                        trend_direction = "UP"
                    elif sma_short < sma_long * 0.98:  # 2% unter langem SMA
                        trend_score = -0.2
                        trend_direction = "DOWN"
            
            # 6. News-Analyse
            news_score = 0.0
            news_count = 0
            try:
                # Suche nach News für diesen Coin
                base_asset = symbol.replace("USDT", "").replace("BUSD", "").replace("BTC", "").replace("ETH", "")
                news_articles = await self.news_fetcher.fetch_news(
                    symbols=[base_asset],
                    limit_per_source=3,
                    max_total=10
                )
                
                # Bewerte News
                for article in news_articles:
                    importance = article.get("importance_score", 0.0)
                    if importance > 0.5:  # Wichtige News
                        news_score += importance * 0.2
                        news_count += 1
                
                # Cap news_score
                news_score = min(news_score, 0.5)
            
            except Exception as e:
                logger.warning(f"Error fetching news for {symbol}: {e}")
            
            # 7. Gesamt-Score berechnen
            # Kombiniere: Strategie-Score (40%), Trend (20%), Volatilität (20%), News (20%)
            total_score = (
                best_score * 0.4 +  # Beste Strategie
                trend_score * 0.2 +  # Trend
                min(volatility / 10, 0.5) * 0.2 +  # Volatilität (normalisiert)
                news_score * 0.2  # News
            )
            
            # 8. Profit-Potenzial schätzen
            profit_potential = "LOW"
            if total_score > 0.4:
                profit_potential = "HIGH"
            elif total_score > 0.2:
                profit_potential = "MEDIUM"
            
            return {
                "symbol": symbol,
                "current_price": current_price,
                "score": round(total_score, 3),
                "profit_potential": profit_potential,
                "best_strategy": best_strategy,
                "best_strategy_score": round(best_score, 3),
                "best_strategy_confidence": round(strategy_scores.get(best_strategy, {}).get("confidence", 0.0), 3) if best_strategy else 0.0,
                "trend": trend_direction,
                "trend_score": round(trend_score, 3),
                "volatility_24h": round(volatility, 2),
                "news_score": round(news_score, 3),
                "news_count": news_count,
                "strategy_scores": {
                    k: {"score": round(v["score"], 3), "confidence": round(v["confidence"], 3)}
                    for k, v in strategy_scores.items()
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error analyzing coin {symbol}: {e}", exc_info=True)
            return {
                "symbol": symbol,
                "error": str(e),
                "score": 0.0
            }
    
    async def analyze_multiple_coins(self, symbols: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Analysiert mehrere Coins und gibt die besten zurück.
        
        Args:
            symbols: Liste von Trading-Symbolen
            limit: Max. Anzahl der besten Coins zurückgeben
        
        Returns:
            Liste von Analyse-Ergebnissen, sortiert nach Score (höchste zuerst)
        """
        results = []
        
        for symbol in symbols:
            try:
                analysis = await self.analyze_coin(symbol)
                if "error" not in analysis:
                    results.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
        
        # Sortiere nach Score (höchste zuerst)
        results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        
        return results[:limit]
    
    async def find_optimal_coins(self, 
                                  min_score: float = 0.2,
                                  max_coins: int = 10,
                                  exclude_symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Findet optimale Coins für Trading.
        
        Args:
            min_score: Mindest-Score für Coin
            max_coins: Max. Anzahl Coins zurückgeben
            exclude_symbols: Symbole die ausgeschlossen werden sollen
        
        Returns:
            Liste der besten Coins mit Analysen
        """
        try:
            # Hole alle handelbaren Symbole
            all_symbols = self.binance_client.get_tradable_symbols()
            
            # Filtere nach USDT-Paaren und entferne ausgeschlossene
            usdt_symbols = [
                s.get("symbol", "") for s in all_symbols
                if s.get("symbol", "").endswith("USDT") and 
                (exclude_symbols is None or s.get("symbol", "") not in exclude_symbols)
            ]
            
            # Begrenze auf Top 50 nach Volumen (um Zeit zu sparen)
            # Für echte Implementierung könnte man hier nach 24h-Volumen filtern
            symbols_to_analyze = usdt_symbols[:50]
            
            logger.info(f"Analyzing {len(symbols_to_analyze)} coins for optimal trading opportunities...")
            
            # Analysiere alle Coins
            results = await self.analyze_multiple_coins(symbols_to_analyze, limit=max_coins * 2)
            
            # Filtere nach min_score
            filtered_results = [r for r in results if r.get("score", 0.0) >= min_score]
            
            return filtered_results[:max_coins]
        
        except Exception as e:
            logger.error(f"Error finding optimal coins: {e}", exc_info=True)
            return []

