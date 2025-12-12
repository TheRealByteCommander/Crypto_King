import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from bson import ObjectId
import uuid
from binance_client import BinanceClientWrapper
from strategies import get_strategy
from config import settings
from market_phase_analyzer import MarketPhaseAnalyzer
from candle_tracker import CandleTracker
from constants import (
    BOT_LOOP_INTERVAL_SECONDS,
    BOT_ERROR_RETRY_DELAY_SECONDS,
    MIN_PROFIT_LOSS_THRESHOLD,
    QUANTITY_DECIMAL_PLACES,
    STOP_LOSS_PERCENT,
    TAKE_PROFIT_MIN_PERCENT,
    TAKE_PROFIT_TRAILING_PERCENT,
    LOW_PROFIT_THRESHOLD
)
import json

logger = logging.getLogger(__name__)

# Helper function to convert MongoDB ObjectId to string recursively
def convert_objectid_to_str(obj):
    """Recursively convert MongoDB ObjectId objects to strings."""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_objectid_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid_to_str(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_objectid_to_str(item) for item in obj)
    else:
        return obj

class TradingBot:
    """Main trading bot that orchestrates agents and executes strategies."""
    
    def __init__(self, db, agent_manager, bot_id: Optional[str] = None):
        self.db = db
        self.agent_manager = agent_manager
        self.bot_id = bot_id or str(uuid.uuid4())
        self.binance_client = None
        self.is_running = False
        self.current_config = None
        self.task = None
        self.position = None  # "LONG", "SHORT", or None - tracks current position
        self.position_size = 0.0  # Quantity of base asset in position
        self.position_entry_price = 0.0  # Entry price for current position
        self.position_high_price = 0.0  # Highest price since entry (for trailing stop take profit)
        self.position_entry_time = None  # Timestamp when position was opened (for tracking purposes)
        # Market phase analysis
        self.market_phase_analyzer = MarketPhaseAnalyzer()
        self.current_market_phase = None  # "BULLISH", "BEARISH", "SIDEWAYS"
        # Candle tracking (initialized when bot starts with binance_client)
        self.candle_tracker = None
    
    async def start(self, strategy: str, symbol: str, amount: float, timeframe: str = "5m", trading_mode: str = "SPOT") -> Dict[str, Any]:
        """Start the trading bot with specified parameters."""
        try:
            if self.is_running:
                return {"success": False, "message": f"Bot {self.bot_id} is already running"}
            
            # Initialize Binance client (can be shared across bots)
            self.binance_client = BinanceClientWrapper()
            
            # Initialize CandleTracker for continuous candle tracking
            self.candle_tracker = CandleTracker(self.db, self.binance_client)
            
            # Validate trading mode
            valid_modes = ["SPOT", "MARGIN", "FUTURES"]
            trading_mode_upper = trading_mode.upper()
            if trading_mode_upper not in valid_modes:
                return {
                    "success": False,
                    "message": f"Invalid trading mode '{trading_mode}'. Valid modes: {', '.join(valid_modes)}"
                }
            
            # WARNUNG: Binance Testnet unterstützt NUR Spot Trading!
            if settings.binance_testnet and trading_mode_upper in ["MARGIN", "FUTURES"]:
                return {
                    "success": False,
                    "message": f"⚠️ MARGIN und FUTURES Trading funktionieren NICHT auf Binance Testnet! Testnet unterstützt nur SPOT Trading. Für MARGIN/FUTURES benötigst du einen Binance Mainnet Account mit BINANCE_TESTNET=false"
                }
            
            # Validate symbol before starting
            symbol_upper = symbol.upper()
            is_tradable, error_msg = self.binance_client.is_symbol_tradable(symbol_upper)
            if not is_tradable:
                return {
                    "success": False,
                    "message": error_msg or f"Symbol {symbol_upper} is not tradable on Binance"
                }
            
            # Validate timeframe
            valid_timeframes = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
            if timeframe not in valid_timeframes:
                return {
                    "success": False,
                    "message": f"Invalid timeframe '{timeframe}'. Valid timeframes: {', '.join(valid_timeframes)}"
                }
            
            # Store configuration (use validated uppercase symbol)
            self.current_config = {
                "bot_id": self.bot_id,
                "strategy": strategy,
                "symbol": symbol_upper,
                "amount": amount,
                "timeframe": timeframe,
                "trading_mode": trading_mode_upper,
                "started_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Preserve autonomous bot flags if already set
            if hasattr(self, '_autonomous_flags'):
                self.current_config.update(self._autonomous_flags)
            
            # Initialize position tracking - check if we already have a position in this symbol
            await self._update_position_from_balance(symbol_upper)
            
            # Save to database with bot_id
            await self.db.bot_config.insert_one(self.current_config)
            
            # Analyze historical market data before starting bot loop
            await self._analyze_historical_market_context(symbol_upper, strategy)
            
            # Update AutonomousManager Binance client if available
            if hasattr(self.agent_manager, 'bot') and hasattr(self.agent_manager.bot, '_update_autonomous_manager'):
                await self.agent_manager.bot._update_autonomous_manager()
            
            self.is_running = True
            
            # Start bot loop in background
            self.task = asyncio.create_task(self._bot_loop())
            
            logger.info(f"Bot {self.bot_id} started with strategy: {strategy}, symbol: {symbol}, amount: {amount}")
            
            # Convert ObjectId to strings before returning
            config_copy = self.current_config.copy()
            return {
                "success": True,
                "message": f"Bot {self.bot_id} started successfully",
                "config": convert_objectid_to_str(config_copy),
                "bot_id": self.bot_id
            }
        except Exception as e:
            logger.error(f"Error starting bot {self.bot_id}: {e}", exc_info=True)
            return {"success": False, "message": str(e), "bot_id": self.bot_id}
    
    async def stop(self) -> Dict[str, Any]:
        """Stop the trading bot."""
        try:
            if not self.is_running:
                return {"success": False, "message": f"Bot {self.bot_id} is not running"}
            
            self.is_running = False
            
            # Cancel the bot loop task
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
                self.task = None
            
            # Update database
            if self.current_config:
                self.current_config["stopped_at"] = datetime.now(timezone.utc).isoformat()
                await self.db.bot_config.update_one(
                    {"bot_id": self.bot_id, "started_at": self.current_config["started_at"]},
                    {"$set": {"stopped_at": self.current_config["stopped_at"]}}
                )
            
            logger.info(f"Bot {self.bot_id} stopped")
            
            return {"success": True, "message": f"Bot {self.bot_id} stopped successfully", "bot_id": self.bot_id}
        
        except Exception as e:
            logger.error(f"Error stopping bot {self.bot_id}: {e}")
            return {"success": False, "message": str(e), "bot_id": self.bot_id}
    
    async def _analyze_historical_market_context(self, symbol: str, strategy: str):
        """Analyze historical market data to provide context before bot starts trading."""
        try:
            logger.info(f"Bot {self.bot_id}: Analyzing historical market context for {symbol}...")
            
            # Get multiple timeframes for comprehensive analysis
            intervals_and_limits = [
                ("5m", 100),   # Last ~8 hours (5min intervals)
                ("15m", 100),  # Last ~25 hours (15min intervals)
                ("1h", 100),   # Last ~4 days (1h intervals)
                ("4h", 100),   # Last ~17 days (4h intervals)
                ("1d", 30)     # Last 30 days
            ]
            
            market_context = {
                "symbol": symbol,
                "strategy": strategy,
                "current_price": None,
                "price_trends": {},
                "volatility_analysis": {},
                "volume_analysis": {},
                "historical_signals": [],
                "recommendation": None
            }
            
            # Get current price
            try:
                current_price = self.binance_client.get_current_price(symbol)
                market_context["current_price"] = current_price
            except Exception as e:
                logger.warning(f"Could not get current price for context analysis: {e}")
            
            # Analyze each timeframe
            strategy_obj = get_strategy(strategy)
            all_analyses = []
            
            for interval, limit in intervals_and_limits:
                try:
                    # Get market data for this timeframe
                    market_data = self.binance_client.get_market_data(symbol, interval=interval, limit=limit)
                    
                    # Analyze with strategy
                    analysis = strategy_obj.analyze(market_data)
                    all_analyses.append({
                        "interval": interval,
                        "analysis": analysis
                    })
                    
                    # Calculate additional metrics
                    df = market_data
                    price_change_pct = ((df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close']) * 100
                    volatility = df['close'].std() / df['close'].mean() * 100
                    avg_volume = df['volume'].mean()
                    
                    market_context["price_trends"][interval] = {
                        "price_change_pct": round(price_change_pct, 2),
                        "volatility": round(volatility, 2),
                        "avg_volume": round(avg_volume, 2),
                        "signal": analysis.get("signal", "HOLD"),
                        "confidence": analysis.get("confidence", 0.0)
                    }
                    
                except Exception as e:
                    logger.warning(f"Could not analyze {interval} timeframe: {e}")
                    continue
            
            # Overall market context summary
            if all_analyses:
                # Count signals across timeframes
                buy_signals = sum(1 for a in all_analyses if a["analysis"].get("signal") == "BUY")
                sell_signals = sum(1 for a in all_analyses if a["analysis"].get("signal") == "SELL")
                hold_signals = sum(1 for a in all_analyses if a["analysis"].get("signal") == "HOLD")
                
                # Calculate average confidence
                confidences = [a["analysis"].get("confidence", 0.0) for a in all_analyses]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                
                # Determine overall recommendation
                if buy_signals > sell_signals and buy_signals > hold_signals:
                    recommendation = f"Bullish trend detected across {buy_signals}/{len(all_analyses)} timeframes"
                elif sell_signals > buy_signals and sell_signals > hold_signals:
                    recommendation = f"Bearish trend detected across {sell_signals}/{len(all_analyses)} timeframes"
                else:
                    recommendation = f"Mixed signals across timeframes - {buy_signals} BUY, {sell_signals} SELL, {hold_signals} HOLD"
                
                market_context["recommendation"] = recommendation
                market_context["signal_summary"] = {
                    "buy_signals": buy_signals,
                    "sell_signals": sell_signals,
                    "hold_signals": hold_signals,
                    "avg_confidence": round(avg_confidence, 2)
                }
                
                # Get price range analysis
                try:
                    daily_data = self.binance_client.get_market_data(symbol, interval="1d", limit=30)
                    market_context["price_range"] = {
                        "30d_high": float(daily_data['high'].max()),
                        "30d_low": float(daily_data['low'].min()),
                        "30d_range_pct": round(((daily_data['high'].max() - daily_data['low'].min()) / daily_data['low'].min()) * 100, 2)
                    }
                    
                    # Current price position in range
                    if current_price:
                        price_position = ((current_price - market_context["price_range"]["30d_low"]) / 
                                        (market_context["price_range"]["30d_high"] - market_context["price_range"]["30d_low"])) * 100
                        market_context["price_range"]["current_position_pct"] = round(price_position, 2)
                except Exception as e:
                    logger.warning(f"Could not calculate price range: {e}")
            
            # Log comprehensive market context to CypherMind
            context_message = f"Historical Market Analysis for {symbol}:\n"
            context_message += f"Current Price: {market_context.get('current_price', 'N/A')} USDT\n"
            context_message += f"Overall Recommendation: {market_context.get('recommendation', 'No clear trend')}\n"
            
            if "signal_summary" in market_context:
                summary = market_context["signal_summary"]
                context_message += f"Signal Summary: {summary['buy_signals']} BUY, {summary['sell_signals']} SELL, {summary['hold_signals']} HOLD (Avg Confidence: {summary['avg_confidence']})\n"
            
            if "price_range" in market_context:
                price_range = market_context["price_range"]
                context_message += f"30-Day Range: {price_range.get('30d_low', 'N/A')} - {price_range.get('30d_high', 'N/A')} USDT ({price_range.get('30d_range_pct', 0)}% range)\n"
                if "current_position_pct" in price_range:
                    context_message += f"Current Price Position: {price_range['current_position_pct']}% of 30-day range\n"
            
            context_message += "\nTimeframe Analysis:\n"
            for interval, trend_data in market_context.get("price_trends", {}).items():
                context_message += f"  {interval}: {trend_data['signal']} signal, {trend_data['price_change_pct']}% price change, {trend_data['volatility']}% volatility\n"
            
            await self.agent_manager.log_agent_message(
                "CypherMind",
                context_message,
                "analysis"
            )
            
            # Store market context in memory for CypherMind
            cyphermind_memory = self.agent_manager.memory_manager.get_agent_memory("CypherMind")
            await cyphermind_memory.store_memory(
                memory_type="market_context",
                content=market_context,
                metadata={"symbol": symbol, "strategy": strategy, "type": "startup_analysis", "bot_id": self.bot_id}
            )
            
            logger.info(f"Bot {self.bot_id}: Historical market analysis completed for {symbol}")
            
        except Exception as e:
            logger.error(f"Error analyzing historical market context: {e}", exc_info=True)
            await self.agent_manager.log_agent_message(
                "CypherMind",
                f"Warning: Could not complete historical market analysis: {str(e)}",
                "error"
            )
    
    async def _bot_loop(self):
        """Main bot loop that runs the trading strategy."""
        logger.info(f"Bot {self.bot_id}: Starting bot loop...")
        
        strategy_obj = get_strategy(self.current_config["strategy"])
        symbol = self.current_config["symbol"]
        
        while self.is_running:
            try:
                # Step 1: Get market data with configured timeframe
                timeframe = self.current_config.get("timeframe", "5m")
                logger.info(f"Bot {self.bot_id}: Fetching market data (timeframe: {timeframe})...")
                market_data = self.binance_client.get_market_data(symbol, interval=timeframe, limit=100)
                
                # Step 1.5: Track Pre-Trade candles (200 candles for better predictions)
                if self.candle_tracker:
                    try:
                        await self.candle_tracker.track_pre_trade_candles(
                            bot_id=self.bot_id,
                            symbol=symbol,
                            timeframe=timeframe,
                            limit=200
                        )
                    except Exception as e:
                        logger.warning(f"Bot {self.bot_id}: Fehler beim Pre-Trade-Kerzen-Tracking: {e}")
                
                # Step 2: Analyze market phase
                market_phase_analysis = self.market_phase_analyzer.analyze_phase(market_data, lookback_periods=20)
                self.current_market_phase = market_phase_analysis.get("phase")
                
                # Log market phase to agents
                phase_desc = market_phase_analysis.get("description", "")
                phase_confidence = market_phase_analysis.get("confidence", 0.0)
                await self.agent_manager.log_agent_message(
                    "CypherMind",
                    f"📊 Market Phase Analysis: {phase_desc} (Confidence: {phase_confidence:.2f})",
                    "analysis"
                )
                
                # Step 3: Analyze with strategy
                logger.info(f"Bot {self.bot_id}: Analyzing market data...")
                analysis = strategy_obj.analyze(market_data)
                
                # Add market phase info to analysis
                analysis["market_phase"] = self.current_market_phase
                analysis["market_phase_analysis"] = market_phase_analysis
                
                # Get current price for logging
                try:
                    current_price = self.binance_client.get_current_price(symbol)
                    price_info = f" | Current Price: {current_price} USDT"
                except Exception as e:
                    logger.warning(f"Could not get current price for logging: {e}")
                    # Try to get price from analysis if available
                    price_info = ""
                    if "current_price" in analysis:
                        price_info = f" | Current Price: {analysis['current_price']} USDT"
                
                # Step 4: Log analysis to CypherMind
                signal = analysis.get("signal", "HOLD")
                confidence = analysis.get("confidence", 0.0)
                reason = analysis.get("reason", "No specific reason")
                
                # Store decision price and timestamp for delay/slippage tracking
                decision_price = current_price if 'current_price' in locals() else analysis.get("indicators", {}).get("current_price", 0.0)
                decision_timestamp = datetime.now(timezone.utc)
                
                # Include market phase in log message
                market_phase_info = ""
                if self.current_market_phase:
                    phase_confidence = market_phase_analysis.get("confidence", 0.0)
                    market_phase_info = f"\nMarket Phase: {self.current_market_phase} (Confidence: {phase_confidence:.2f})"
                
                log_message = f"📊 EMPFEHLUNG für {symbol}: {signal} Signal (Confidence: {confidence:.2f}){price_info}{market_phase_info}\nBegründung: {reason}\n\nHINWEIS: Dies ist eine Empfehlung - CypherTrade trifft die finale Entscheidung basierend auf Profitzielen (≥2%) und Stop-Loss (-5%)."
                await self.agent_manager.log_agent_message("CypherMind", log_message, "analysis")
                
                # Informiere auch CypherTrade über die Empfehlung
                await self.agent_manager.log_agent_message(
                    "CypherTrade",
                    f"📋 EMPFEHLUNG von CypherMind für {symbol}: {signal} Signal (Confidence: {confidence:.2f})\nBegründung: {reason}\n\nDu triffst die FINALE Entscheidung - prüfe Profitziele (≥2%), Stop-Loss (-5%) und verfügbare Balances.",
                    "recommendation"
                )
                
                # Step 5: Check stop loss and take profit for existing positions BEFORE executing new trades
                if self.position is not None and self.position_entry_price > 0:
                    await self._check_stop_loss_and_take_profit(symbol, analysis)
                
                # Step 5.5: Update Position-Tracking (wenn Position offen ist) und Post-Trade-Tracking
                if self.candle_tracker:
                    try:
                        # Update Position-Tracking, wenn Position offen ist
                        if self.position is not None:
                            await self.candle_tracker.update_position_tracking(self.bot_id)
                        
                        # Find active post-trade tracking for this bot
                        active_post_trades = await self.db.bot_candles.find({
                            "bot_id": self.bot_id,
                            "phase": "post_trade",
                            "count": {"$lt": 200}  # Noch nicht abgeschlossen
                        }).to_list(100)
                        
                        # Update each active post-trade tracking
                        for post_trade in active_post_trades:
                            trade_id = post_trade.get("trade_id")
                            if trade_id:
                                await self.candle_tracker.update_post_trade_tracking(trade_id)
                    except Exception as e:
                        logger.warning(f"Bot {self.bot_id}: Fehler beim Update von Position/Post-Trade-Tracking: {e}")
                
                # Step 6: Execute trade if signal is strong enough
                if signal in ["BUY", "SELL"] and confidence >= 0.6:
                    logger.info(f"Bot {self.bot_id}: Strong {signal} signal detected (confidence: {confidence:.2f}), executing trade...")
                    # Pass decision price and timestamp to track delay
                    await self._execute_trade(analysis, decision_price=decision_price, decision_timestamp=decision_timestamp)
                else:
                    logger.info(f"Bot {self.bot_id}: Signal: {signal}, Confidence: {confidence:.2f} - No trade executed (confidence too low or HOLD signal)")
                
                # Step 7: Wait before next iteration
                await asyncio.sleep(BOT_LOOP_INTERVAL_SECONDS)
                
            except asyncio.CancelledError:
                logger.info(f"Bot {self.bot_id}: Bot loop cancelled")
                break
            except Exception as e:
                logger.error(f"Bot {self.bot_id}: Error in bot loop: {e}", exc_info=True)
                await self.agent_manager.log_agent_message(
                    "CypherMind",
                    f"Error in trading loop: {str(e)}",
                    "error"
                )
                # Wait before retrying
                await asyncio.sleep(BOT_ERROR_RETRY_DELAY_SECONDS)
    
    async def _update_position_from_balance(self, symbol: str, trading_mode: str = "SPOT"):
        """Update position status based on current balance and trading mode."""
        try:
            trading_mode_upper = trading_mode.upper() if trading_mode else "SPOT"
            
            if trading_mode_upper == "SPOT":
                base_asset = BinanceClientWrapper.extract_base_asset(symbol)
                balance = self.binance_client.get_account_balance(base_asset, trading_mode_upper)
                
                if balance > 0:
                    self.position = "LONG"
                    self.position_size = balance
                    # Try to get entry price from last BUY trade for this bot
                    last_buy = await self.db.trades.find_one(
                        {"bot_id": self.bot_id, "symbol": symbol, "side": "BUY"},
                        sort=[("timestamp", -1)]
                    )
                    if last_buy:
                        self.position_entry_price = last_buy.get("entry_price", 0.0)
                else:
                    self.position = None
                    self.position_size = 0.0
                    self.position_entry_price = 0.0
                    self.position_high_price = 0.0
            
            elif trading_mode_upper == "MARGIN":
                # Check margin position
                margin_pos = self.binance_client.get_margin_position(symbol)
                if margin_pos:
                    self.position = margin_pos["type"]
                    self.position_size = margin_pos.get("borrowed", 0) or margin_pos.get("netAsset", 0)
                    # Try to get entry price from last trade
                    last_trade = await self.db.trades.find_one(
                        {"bot_id": self.bot_id, "symbol": symbol},
                        sort=[("timestamp", -1)]
                    )
                    if last_trade:
                        self.position_entry_price = last_trade.get("entry_price", 0.0)
                else:
                    self.position = None
                    self.position_size = 0.0
                    self.position_entry_price = 0.0
                    self.position_high_price = 0.0
            
            elif trading_mode_upper == "FUTURES":
                # Check futures position
                futures_pos = self.binance_client.get_futures_position(symbol)
                if futures_pos:
                    self.position = futures_pos["type"]
                    self.position_size = futures_pos["size"]
                    self.position_entry_price = futures_pos.get("entry_price", 0.0)
                else:
                    self.position = None
                    self.position_size = 0.0
                    self.position_entry_price = 0.0
            else:
                # Unknown trading mode - reset position
                self.position = None
                self.position_size = 0.0
                self.position_entry_price = 0.0
                self.position_high_price = 0.0
                
        except Exception as e:
            logger.warning(f"Bot {self.bot_id}: Could not update position from balance: {e}")
            self.position = None
            self.position_size = 0.0
            self.position_entry_price = 0.0
            self.position_high_price = 0.0
            self.position_entry_time = None
    
    async def _check_stop_loss_and_take_profit(self, symbol: str, analysis: Dict[str, Any]):
        """Check if stop loss or take profit should be triggered for current position."""
        try:
            if self.position is None or self.position_entry_price <= 0:
                return
            
            current_price = self.binance_client.get_current_price(symbol)
            trading_mode = self.current_config.get("trading_mode", "SPOT")
            
            # Calculate P&L percentage
            if self.position == "LONG":
                pnl_percent = ((current_price - self.position_entry_price) / self.position_entry_price) * 100
            elif self.position == "SHORT":
                pnl_percent = ((self.position_entry_price - current_price) / self.position_entry_price) * 100
            else:
                return
            
            # For LONG positions: Update highest price since entry (for trailing stop)
            if self.position == "LONG" and current_price > self.position_high_price:
                self.position_high_price = current_price
                logger.debug(f"Bot {self.bot_id}: Updated position high price to {self.position_high_price:.8f} (entry: {self.position_entry_price:.8f}, current: {current_price:.8f})")
            
            # Check stop loss (-2%)
            if pnl_percent <= STOP_LOSS_PERCENT:
                logger.warning(f"Bot {self.bot_id}: STOP LOSS triggered! Position: {self.position}, Entry: {self.position_entry_price}, Current: {current_price}, P&L: {pnl_percent:.2f}%")
                await self.agent_manager.log_agent_message(
                    "CypherTrade",
                    f"🛑 STOP LOSS triggered at {pnl_percent:.2f}% loss. Closing position to limit losses.",
                    "warning"
                )
                
                # Force close position
                if self.position == "LONG":
                    # Execute SELL to close LONG
                    base_asset = BinanceClientWrapper.extract_base_asset(symbol)
                    balance = self.binance_client.get_account_balance(base_asset, trading_mode)
                    if balance > 0:
                        quantity = self.binance_client.adjust_quantity_to_lot_size(symbol, balance)
                        adjusted_quantity = self.binance_client.adjust_quantity_to_notional(symbol, quantity, current_price)
                        if adjusted_quantity:
                            quantity = adjusted_quantity
                            order = self.binance_client.execute_order(symbol, "SELL", quantity, "MARKET", trading_mode)
                            
                            # Get execution price from order - KRITISCH: Kein Fallback, Kurs MUSS verfügbar sein!
                            execution_price = None
                            if order.get("fills"):
                                fills = order.get("fills", [])
                                if fills:
                                    total_qty = sum(float(f.get("qty", 0)) for f in fills)
                                    total_quote = sum(float(f.get("quoteQty", 0)) for f in fills)
                                    if total_qty > 0 and total_quote > 0:
                                        execution_price = total_quote / total_qty
                                    elif total_qty > 0:
                                        # Try to calculate from price in fills
                                        total_value = sum(float(f.get("price", 0)) * float(f.get("qty", 0)) for f in fills if f.get("price"))
                                        if total_value > 0:
                                            execution_price = total_value / total_qty
                            
                            if execution_price is None or execution_price <= 0:
                                if order.get("price"):
                                    execution_price = float(order.get("price"))
                                elif order.get("cummulativeQuoteQty") and order.get("executedQty"):
                                    executed_qty = float(order.get("executedQty", 0))
                                    if executed_qty > 0:
                                        execution_price = float(order.get("cummulativeQuoteQty")) / executed_qty
                            
                            # KRITISCH: Wenn execution_price nicht verfügbar, Trade abbrechen!
                            if execution_price is None or execution_price <= 0:
                                error_msg = f"KRITISCHER FEHLER: Execution price nicht verfügbar für STOP LOSS Order {order.get('orderId', 'N/A')}"
                                logger.error(f"Bot {self.bot_id}: {error_msg}. Order-Daten: {order}")
                                await self.agent_manager.log_agent_message(
                                    "CypherTrade",
                                    f"❌ {error_msg} - STOP LOSS kann nicht verarbeitet werden!",
                                    "error"
                                )
                                return
                            
                            # Calculate final P&L
                            pnl = (execution_price - self.position_entry_price) * quantity
                            pnl_percent_final = ((execution_price - self.position_entry_price) / self.position_entry_price) * 100
                            
                            # Calculate quote_qty (USDT value) - prefer from order, fallback to calculation
                            quote_qty_from_order = float(order.get("cummulativeQuoteQty", 0))
                            if quote_qty_from_order > 0:
                                quote_qty = quote_qty_from_order
                            else:
                                # Fallback: calculate from execution_price * quantity
                                quote_qty = execution_price * quantity
                                logger.debug(f"Bot {self.bot_id}: quote_qty not in order response, calculated: {quote_qty:.2f} USDT (price: {execution_price}, qty: {quantity})")
                            
                            # Save trade
                            trade = {
                                "bot_id": self.bot_id,
                                "symbol": symbol,
                                "side": "SELL",
                                "quantity": quantity,
                                "order_id": str(order.get("orderId", "")),
                                "status": order.get("status", ""),
                                "executed_qty": float(order.get("executedQty", 0)),
                                "quote_qty": quote_qty,  # USDT value - always set correctly
                                "entry_price": execution_price,
                                "execution_price": execution_price,
                                "strategy": self.current_config["strategy"],
                                "trading_mode": trading_mode,
                                "confidence": analysis.get("confidence", 0.0),
                                "indicators": analysis.get("indicators", {}),
                                "exit_reason": "STOP_LOSS",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "pnl": pnl,
                                "pnl_percent": pnl_percent_final,
                                "position_entry_price": self.position_entry_price
                            }
                            await self.db.trades.insert_one(trade)
                            
                            # Stop Position-Tracking before resetting position
                            if self.candle_tracker:
                                try:
                                    sell_trade_id = str(order.get("orderId", ""))
                                    await self.candle_tracker.stop_position_tracking(self.bot_id, sell_trade_id)
                                except Exception as e:
                                    logger.warning(f"Bot {self.bot_id}: Fehler beim Stoppen von Position-Tracking: {e}")
                            
                            # Stop Position-Tracking before resetting position
                            if self.candle_tracker:
                                try:
                                    sell_trade_id = str(order.get("orderId", ""))
                                    await self.candle_tracker.stop_position_tracking(self.bot_id, sell_trade_id)
                                except Exception as e:
                                    logger.warning(f"Bot {self.bot_id}: Fehler beim Stoppen von Position-Tracking: {e}")
                            
                            # Learn from closed position
                            if pnl is not None:
                                await self._learn_from_closed_position(trade, pnl, self.position_entry_price, current_price)
                            
                            # Reset position
                            self.position = None
                            self.position_size = 0.0
                            old_entry_price = self.position_entry_price
                            self.position_entry_price = 0.0
                            self.position_high_price = 0.0
                            
                            logger.info(f"Bot {self.bot_id}: STOP LOSS executed - SELL {quantity} {symbol} at {current_price} USDT (P&L: {pnl:+.2f} USDT, {pnl_percent_final:+.2f}%)")
                            await self.agent_manager.log_agent_message(
                                "CypherTrade",
                                f"STOP LOSS executed: SELL {quantity} {symbol} at {current_price} USDT (P&L: {pnl:+.2f} USDT, {pnl_percent_final:+.2f}%)",
                                "trade"
                            )
                elif self.position == "SHORT":
                    # Execute BUY to close SHORT
                    amount_usdt = self.current_config["amount"]
                    if current_price is None or current_price <= 0:
                        logger.error(f"Bot {self.bot_id}: Invalid current_price ({current_price}) for SHORT close, skipping trade")
                        return
                    quantity = amount_usdt / current_price
                    quantity = self.binance_client.adjust_quantity_to_lot_size(symbol, quantity)
                    adjusted_quantity = self.binance_client.adjust_quantity_to_notional(symbol, quantity, current_price)
                    if adjusted_quantity:
                        quantity = adjusted_quantity
                        order = self.binance_client.execute_order(symbol, "BUY", quantity, "MARKET", trading_mode)
                        
                        # Get execution price from order - KRITISCH: Kein Fallback!
                        try:
                            execution_price = self._get_execution_price_from_order(order, symbol, current_price)
                        except ValueError as e:
                            error_msg = f"STOP LOSS für SHORT Position fehlgeschlagen: {str(e)}"
                            logger.error(f"Bot {self.bot_id}: {error_msg}")
                            await self.agent_manager.log_agent_message("CypherTrade", f"❌ {error_msg}", "error")
                            return
                        
                        # Calculate final P&L (for SHORT: profit when price goes down)
                        pnl = (self.position_entry_price - execution_price) * quantity
                        pnl_percent_final = ((self.position_entry_price - execution_price) / self.position_entry_price) * 100
                        
                        # Calculate quote_qty (USDT value) - prefer from order, fallback to calculation
                        quote_qty_from_order = float(order.get("cummulativeQuoteQty", 0))
                        if quote_qty_from_order > 0:
                            quote_qty = quote_qty_from_order
                        else:
                            # Fallback: calculate from execution_price * quantity
                            quote_qty = execution_price * quantity
                            logger.debug(f"Bot {self.bot_id}: quote_qty not in order response, calculated: {quote_qty:.2f} USDT (price: {execution_price}, qty: {quantity})")
                        
                        # Save trade
                        trade = {
                            "bot_id": self.bot_id,
                            "symbol": symbol,
                            "side": "BUY",
                            "quantity": quantity,
                            "order_id": str(order.get("orderId", "")),
                            "status": order.get("status", ""),
                            "executed_qty": float(order.get("executedQty", 0)),
                            "quote_qty": quote_qty,  # USDT value - always set correctly
                            "entry_price": execution_price,
                            "execution_price": execution_price,
                            "strategy": self.current_config["strategy"],
                            "trading_mode": trading_mode,
                            "position_type": "SHORT_CLOSE",
                            "exit_reason": "STOP_LOSS",
                            "confidence": analysis.get("confidence", 0.0),
                            "indicators": analysis.get("indicators", {}),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "pnl": pnl,
                            "pnl_percent": pnl_percent_final,
                            "position_entry_price": self.position_entry_price
                        }
                        await self.db.trades.insert_one(trade)
                        
                        # Learn from closed position
                        if pnl is not None:
                            await self._learn_from_closed_position(trade, pnl, self.position_entry_price, current_price)
                        
                        # Reset position
                        self.position = None
                        self.position_size = 0.0
                        self.position_entry_price = 0.0
                        self.position_high_price = 0.0
                        self.position_entry_time = None
                        
                        logger.info(f"Bot {self.bot_id}: STOP LOSS executed - BUY {quantity} {symbol} to close SHORT at {current_price} USDT (P&L: {pnl:+.2f} USDT, {pnl_percent_final:+.2f}%)")
                        await self.agent_manager.log_agent_message(
                            "CypherTrade",
                            f"STOP LOSS executed: BUY {quantity} {symbol} to close SHORT at {current_price} USDT (P&L: {pnl:+.2f} USDT, {pnl_percent_final:+.2f}%)",
                            "trade"
                        )
                return
            
            # Check trailing stop take profit (for LONG positions only)
            # Sell when price falls 3% from highest price, but only if we're at least 2% in profit
            if self.position == "LONG" and self.position_high_price > 0:
                # Calculate percentage drop from high
                drop_from_high_percent = ((self.position_high_price - current_price) / self.position_high_price) * 100
                trailing_trigger_price = self.position_high_price * (1 - TAKE_PROFIT_TRAILING_PERCENT / 100)
                
                # Check if we should trigger trailing stop:
                # 1. Current price must be below trailing trigger (3% drop from high)
                # 2. We must be at least 2% in profit (pnl_percent >= TAKE_PROFIT_MIN_PERCENT)
                # 3. CRITICAL: Current P&L must still be positive (not negative) - prevent selling at loss
                # 4. Mindest-Haltedauer muss erreicht sein
                holding_time_valid, _ = self._check_minimum_holding_time(is_stop_loss=False)
                if current_price <= trailing_trigger_price and pnl_percent >= TAKE_PROFIT_MIN_PERCENT and pnl_percent > 0 and holding_time_valid:
                    logger.info(
                        f"Bot {self.bot_id}: TRAILING STOP TAKE PROFIT triggered! "
                        f"Position: {self.position}, Entry: {self.position_entry_price:.8f}, "
                        f"High: {self.position_high_price:.8f}, Current: {current_price:.8f}, "
                        f"Drop from high: {drop_from_high_percent:.2f}%, P&L: {pnl_percent:.2f}%"
                    )
                    await self.agent_manager.log_agent_message(
                        "CypherTrade",
                        f"✅ TRAILING STOP TAKE PROFIT triggered! Price dropped {drop_from_high_percent:.2f}% from high ({self.position_high_price:.8f}) to {current_price:.8f}. "
                        f"Closing position at {pnl_percent:.2f}% profit.",
                        "trade"
                    )
                
                # Force close position
                if self.position == "LONG":
                    # Double-check: Re-fetch current price right before execution to ensure we're still in profit
                    execution_price_check = self.binance_client.get_current_price(symbol)
                    execution_pnl_percent_check = ((execution_price_check - self.position_entry_price) / self.position_entry_price) * 100
                    
                    # CRITICAL: Only execute if we're still in profit at execution time
                    if execution_pnl_percent_check <= 0:
                        logger.warning(
                            f"Bot {self.bot_id}: TAKE PROFIT abortiert! Preis ist weiter gefallen. "
                            f"Entry: {self.position_entry_price:.8f}, Execution Price: {execution_price_check:.8f}, "
                            f"P&L: {execution_pnl_percent_check:.2f}%. Position bleibt offen."
                        )
                        await self.agent_manager.log_agent_message(
                            "CypherTrade",
                            f"⚠️ TAKE PROFIT abgebrochen: Preis weiter gefallen. P&L wäre {execution_pnl_percent_check:.2f}% gewesen.",
                            "warning"
                        )
                        return
                    
                    # Execute SELL to close LONG
                    base_asset = BinanceClientWrapper.extract_base_asset(symbol)
                    balance = self.binance_client.get_account_balance(base_asset, trading_mode)
                    if balance > 0:
                        quantity = self.binance_client.adjust_quantity_to_lot_size(symbol, balance)
                        adjusted_quantity = self.binance_client.adjust_quantity_to_notional(symbol, quantity, execution_price_check)
                        if adjusted_quantity:
                            quantity = adjusted_quantity
                            order = self.binance_client.execute_order(symbol, "SELL", quantity, "MARKET", trading_mode)
                            
                            # Get actual execution price from order - KRITISCH: Kein Fallback!
                            try:
                                execution_price = self._get_execution_price_from_order(order, symbol, execution_price_check)
                            except ValueError as e:
                                error_msg = f"TAKE PROFIT fehlgeschlagen: {str(e)}"
                                logger.error(f"Bot {self.bot_id}: {error_msg}")
                                await self.agent_manager.log_agent_message("CypherTrade", f"❌ {error_msg}", "error")
                                return
                            
                            # Calculate final P&L using actual execution price
                            pnl = (execution_price - self.position_entry_price) * quantity
                            pnl_percent_final = ((execution_price - self.position_entry_price) / self.position_entry_price) * 100
                            
                            # Calculate quote_qty (USDT value) - prefer from order, fallback to calculation
                            quote_qty_from_order = float(order.get("cummulativeQuoteQty", 0))
                            if quote_qty_from_order > 0:
                                quote_qty = quote_qty_from_order
                            else:
                                # Fallback: calculate from execution_price * quantity
                                quote_qty = execution_price * quantity
                                logger.debug(f"Bot {self.bot_id}: quote_qty not in order response, calculated: {quote_qty:.2f} USDT (price: {execution_price}, qty: {quantity})")
                            
                            # Save trade
                            trade = {
                                "bot_id": self.bot_id,
                                "symbol": symbol,
                                "side": "SELL",
                                "quantity": quantity,
                                "order_id": str(order.get("orderId", "")),
                                "status": order.get("status", ""),
                                "executed_qty": float(order.get("executedQty", 0)),
                                "quote_qty": quote_qty,  # USDT value - always set correctly
                                "entry_price": execution_price,
                                "exit_price": execution_price,
                                "execution_price": execution_price,
                                "strategy": self.current_config["strategy"],
                                "trading_mode": trading_mode,
                                "confidence": analysis.get("confidence", 0.0),
                                "indicators": analysis.get("indicators", {}),
                                "exit_reason": "TAKE_PROFIT",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "pnl": pnl,
                                "pnl_percent": pnl_percent_final,
                                "position_entry_price": self.position_entry_price
                            }
                            await self.db.trades.insert_one(trade)
                            
                            # Stop Position-Tracking before resetting position
                            if self.candle_tracker:
                                try:
                                    sell_trade_id = str(order.get("orderId", ""))
                                    await self.candle_tracker.stop_position_tracking(self.bot_id, sell_trade_id)
                                except Exception as e:
                                    logger.warning(f"Bot {self.bot_id}: Fehler beim Stoppen von Position-Tracking: {e}")
                            
                            # Learn from closed position
                            if pnl is not None:
                                await self._learn_from_closed_position(trade, pnl, self.position_entry_price, execution_price)
                            
                            # Reset position
                            self.position = None
                            self.position_size = 0.0
                            old_entry_price = self.position_entry_price
                            self.position_entry_price = 0.0
                            self.position_high_price = 0.0
                            
                            logger.info(f"Bot {self.bot_id}: TRAILING STOP TAKE PROFIT executed - SELL {quantity} {symbol} at {execution_price} USDT (P&L: {pnl:+.2f} USDT, {pnl_percent_final:+.2f}%)")
                            await self.agent_manager.log_agent_message(
                                "CypherTrade",
                                f"TAKE PROFIT executed: SELL {quantity} {symbol} at {execution_price} USDT (P&L: {pnl:+.2f} USDT, {pnl_percent_final:+.2f}%)",
                                "trade"
                            )
                elif self.position == "SHORT":
                    # Execute BUY to close SHORT
                    amount_usdt = self.current_config["amount"]
                    if current_price is None or current_price <= 0:
                        logger.error(f"Bot {self.bot_id}: Invalid current_price ({current_price}) for SHORT close, skipping trade")
                        return
                    quantity = amount_usdt / current_price
                    quantity = self.binance_client.adjust_quantity_to_lot_size(symbol, quantity)
                    adjusted_quantity = self.binance_client.adjust_quantity_to_notional(symbol, quantity, current_price)
                    if adjusted_quantity:
                        quantity = adjusted_quantity
                        order = self.binance_client.execute_order(symbol, "BUY", quantity, "MARKET", trading_mode)
                        
                        # Get execution price from order - KRITISCH: Kein Fallback!
                        try:
                            execution_price = self._get_execution_price_from_order(order, symbol, current_price)
                        except ValueError as e:
                            error_msg = f"STOP LOSS für SHORT Position fehlgeschlagen: {str(e)}"
                            logger.error(f"Bot {self.bot_id}: {error_msg}")
                            await self.agent_manager.log_agent_message("CypherTrade", f"❌ {error_msg}", "error")
                            return
                        
                        # Calculate final P&L (for SHORT: profit when price goes down)
                        pnl = (self.position_entry_price - execution_price) * quantity
                        pnl_percent_final = ((self.position_entry_price - execution_price) / self.position_entry_price) * 100
                        
                        # Calculate quote_qty (USDT value) - prefer from order, fallback to calculation
                        quote_qty_from_order = float(order.get("cummulativeQuoteQty", 0))
                        if quote_qty_from_order > 0:
                            quote_qty = quote_qty_from_order
                        else:
                            # Fallback: calculate from execution_price * quantity
                            quote_qty = execution_price * quantity
                            logger.debug(f"Bot {self.bot_id}: quote_qty not in order response, calculated: {quote_qty:.2f} USDT (price: {execution_price}, qty: {quantity})")
                        
                        # Save trade
                        trade = {
                            "bot_id": self.bot_id,
                            "symbol": symbol,
                            "side": "BUY",
                            "quantity": quantity,
                            "order_id": str(order.get("orderId", "")),
                            "status": order.get("status", ""),
                            "executed_qty": float(order.get("executedQty", 0)),
                            "quote_qty": quote_qty,  # USDT value - always set correctly
                            "entry_price": execution_price,
                            "execution_price": execution_price,
                            "strategy": self.current_config["strategy"],
                            "trading_mode": trading_mode,
                            "position_type": "SHORT_CLOSE",
                            "exit_reason": "TAKE_PROFIT",
                            "confidence": analysis.get("confidence", 0.0),
                            "indicators": analysis.get("indicators", {}),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "pnl": pnl,
                            "pnl_percent": pnl_percent_final,
                            "position_entry_price": self.position_entry_price
                        }
                        await self.db.trades.insert_one(trade)
                        
                        # Learn from closed position
                        if pnl is not None:
                            await self._learn_from_closed_position(trade, pnl, self.position_entry_price, current_price)
                        
                        # Reset position
                        self.position = None
                        self.position_size = 0.0
                        self.position_entry_price = 0.0
                        self.position_high_price = 0.0
                        self.position_entry_time = None
                        
                        logger.info(f"Bot {self.bot_id}: TAKE PROFIT executed - BUY {quantity} {symbol} to close SHORT at {current_price} USDT (P&L: {pnl:+.2f} USDT, {pnl_percent_final:+.2f}%)")
                        await self.agent_manager.log_agent_message(
                            "CypherTrade",
                            f"TAKE PROFIT executed: BUY {quantity} {symbol} to close SHORT at {current_price} USDT (P&L: {pnl:+.2f} USDT, {pnl_percent_final:+.2f}%)",
                            "trade"
                        )
                return
        
        except Exception as e:
            logger.error(f"Bot {self.bot_id}: Error checking stop loss/take profit: {e}", exc_info=True)
    
    async def _learn_from_closed_position(self, trade: Dict[str, Any], pnl: float, entry_price: float, exit_price: float):
        """Learn from a closed position - called for all relevant agents."""
        try:
            # Extract pnl_percent from trade dict (if available)
            pnl_percent = trade.get("pnl_percent")
            
            # Calculate pnl_percent if not available in trade dict
            if pnl_percent is None and entry_price > 0:
                pnl_percent = ((exit_price - entry_price) / entry_price) * 100
            
            # Determine outcome based on P&L (both absolute and percentage)
            # BELOHNUNGSSYSTEM: Trades mit ≥2% Profit werden als "high_success" markiert
            if pnl_percent is not None and pnl_percent >= TAKE_PROFIT_MIN_PERCENT:
                # Trade hat mindestens 2% Profit gemacht - Belohnung für Agents!
                outcome = "high_success"  # Spezieller Outcome für profitable Trades ≥2%
            elif pnl_percent is not None and pnl_percent > 0 and pnl_percent < LOW_PROFIT_THRESHOLD:
                # NEGATIVE BEWERTUNG: Trade hat Profit, aber <1% - Agents sollen auf Limits achten lernen
                outcome = "low_profit"  # Profitabel, aber zu niedrig - negative Bewertung
            elif pnl > MIN_PROFIT_LOSS_THRESHOLD:
                outcome = "success"
            elif pnl < -MIN_PROFIT_LOSS_THRESHOLD:
                outcome = "failure"
            else:
                # Even neutral outcomes provide learning value (e.g., break-even trades, small profits/losses)
                # Use absolute P&L to determine if it's slightly positive or negative
                if pnl > 0:
                    outcome = "neutral_positive"  # Small profit, but below threshold
                elif pnl < 0:
                    outcome = "neutral_negative"  # Small loss, but above threshold
                else:
                    outcome = "neutral"  # Exactly break-even
            
            # Prepare trade data for learning
            learning_trade = {
                "order_id": trade.get("order_id", ""),
                "symbol": trade.get("symbol", ""),
                "side": trade.get("side", ""),
                "strategy": trade.get("strategy", ""),
                "entry_price": entry_price,
                "exit_price": exit_price,
                "confidence": trade.get("confidence", 0.0),
                "indicators": trade.get("indicators", {}),
                "bot_id": self.bot_id,
                "pnl_percent": pnl_percent  # Include pnl_percent for reward system
            }
            
            # Get candle data for learning (if available)
            candle_data = None
            if self.candle_tracker:
                try:
                    trade_id = str(trade.get("order_id", ""))
                    symbol = trade.get("symbol", "")
                    buy_trade_id = trade.get("buy_trade_id")  # Falls vorhanden
                    
                    # Get pre-trade candles
                    pre_trade_result = await self.candle_tracker.get_bot_candles(self.bot_id, "pre_trade", symbol)
                    pre_trade_candles = None
                    if pre_trade_result.get("success") and pre_trade_result.get("candles_data"):
                        # Get most recent pre_trade candles for this symbol
                        for candle_set in pre_trade_result["candles_data"]:
                            if candle_set.get("symbol") == symbol:
                                pre_trade_candles = candle_set
                                break
                    
                    # Get position candles (during_trade) - wenn SELL, hole Position-Daten
                    during_trade_candles = None
                    if buy_trade_id:
                        # Versuche Position-Tracking-Daten über buy_trade_id zu finden
                        position_doc = await self.db.bot_candles.find_one({
                            "bot_id": self.bot_id,
                            "phase": "during_trade",
                            "buy_trade_id": buy_trade_id
                        })
                        if position_doc:
                            during_trade_candles = {
                                "count": position_doc.get("count", 0),
                                "candles": position_doc.get("candles", []),
                                "buy_trade_id": buy_trade_id,
                                "sell_trade_id": position_doc.get("sell_trade_id")
                            }
                    else:
                        # Fallback: Finde aktuelle geschlossene Position für diesen Bot
                        position_doc = await self.db.bot_candles.find_one({
                            "bot_id": self.bot_id,
                            "phase": "during_trade",
                            "symbol": symbol,
                            "position_status": "closed"
                        }, sort=[("updated_at", -1)])
                        if position_doc:
                            during_trade_candles = {
                                "count": position_doc.get("count", 0),
                                "candles": position_doc.get("candles", []),
                                "buy_trade_id": position_doc.get("buy_trade_id"),
                                "sell_trade_id": position_doc.get("sell_trade_id")
                            }
                    
                    # Get post-trade candles (if available)
                    post_trade_candles = None
                    if trade_id:
                        post_result = await self.candle_tracker.get_trade_candles(trade_id, "post_trade")
                        if post_result.get("success"):
                            post_trade_candles = {
                                "count": post_result.get("count", 0),
                                "candles": post_result.get("candles", [])
                            }
                    
                    if pre_trade_candles or during_trade_candles or post_trade_candles:
                        candle_data = {
                            "pre_trade": pre_trade_candles,
                            "during_trade": during_trade_candles,
                            "post_trade": post_trade_candles
                        }
                except Exception as e:
                    logger.warning(f"Bot {self.bot_id}: Fehler beim Abrufen von Kerzen-Daten für Learning: {e}")
            
            # Learn for CypherMind (decision maker) - with candle data
            cyphermind_memory = self.agent_manager.memory_manager.get_agent_memory("CypherMind")
            await cyphermind_memory.learn_from_trade(learning_trade, outcome, pnl, candle_data)
            pnl_percent_msg = f", {pnl_percent:+.2f}%" if pnl_percent is not None else ""
            reward_msg = " 🎯 BELOHNUNG: ≥2% Profit!" if outcome == "high_success" else ""
            warning_msg = " ⚠️ NEGATIVE BEWERTUNG: <1% Profit!" if outcome == "low_profit" else ""
            logger.info(f"Bot {self.bot_id}: CypherMind learned from trade: {outcome} (P&L: {pnl:.2f} USDT{pnl_percent_msg}){reward_msg}{warning_msg}" + (" - with candle patterns" if candle_data else ""))
            
            # Learn for CypherTrade (executor) - with candle data
            cyphertrade_memory = self.agent_manager.memory_manager.get_agent_memory("CypherTrade")
            await cyphertrade_memory.learn_from_trade(learning_trade, outcome, pnl, candle_data)
            logger.info(f"Bot {self.bot_id}: CypherTrade learned from trade: {outcome} (P&L: {pnl:.2f} USDT{pnl_percent_msg}){reward_msg}{warning_msg}")
            
            # Learn for NexusChat (UI agent) - learns from trade outcomes and user interactions
            # NexusChat learns from successful/failed trades to improve communication and trade confirmation accuracy
            nexuschat_memory = self.agent_manager.memory_manager.get_agent_memory("NexusChat")
            await nexuschat_memory.learn_from_trade(learning_trade, outcome, pnl, candle_data)
            logger.info(f"Bot {self.bot_id}: NexusChat learned from trade: {outcome} (P&L: {pnl:.2f} USDT{pnl_percent_msg}){reward_msg}{warning_msg}")
            
            # Store collective memory about trade outcome
            await self.agent_manager.memory_manager.store_collective_memory(
                memory_type="trade_completed",
                content={
                    "symbol": trade.get("symbol", ""),
                    "strategy": trade.get("strategy", ""),
                    "outcome": outcome,
                    "profit_loss": pnl,
                    "profit_loss_percent": pnl_percent,
                    "bot_id": self.bot_id,
                    "rewarded": outcome == "high_success",  # Mark if trade was rewarded (≥2% profit)
                    "low_profit_warning": outcome == "low_profit"  # Mark if trade had negative evaluation (<1% profit)
                }
            )
            
            # Start Post-Trade-Tracking after SELL (position closed)
            # Track next 200 candles to learn if selling was optimal timing
            if self.candle_tracker and trade.get("side") == "SELL":
                try:
                    symbol = trade.get("symbol", "")
                    timeframe = self.current_config.get("timeframe", "5m") if self.current_config else "5m"
                    trade_id = str(trade.get("order_id", ""))
                    
                    if trade_id:
                        tracking_result = await self.candle_tracker.start_post_trade_tracking(
                            bot_id=self.bot_id,
                            symbol=symbol,
                            timeframe=timeframe,
                            trade_id=trade_id
                        )
                        if tracking_result.get("success"):
                            logger.info(f"Bot {self.bot_id}: Post-Trade-Tracking gestartet für Trade {trade_id} ({symbol})")
                        else:
                            logger.warning(f"Bot {self.bot_id}: Post-Trade-Tracking konnte nicht gestartet werden: {tracking_result.get('error')}")
                except Exception as e:
                    logger.warning(f"Bot {self.bot_id}: Fehler beim Starten von Post-Trade-Tracking: {e}")
            
        except Exception as e:
            logger.error(f"Bot {self.bot_id}: Error learning from closed position: {e}", exc_info=True)
    
    async def _get_total_spent(self) -> float:
        """
        Calculate current net amount \"in use\" for this bot.
        
        Hintergrund:
        - Bisher wurde die Summe ALLER BUY-Trades verwendet.
          Nach einem vollständigen Buy+Sell-Zyklus war das Budget damit „verbraucht\"
          und der Bot konnte keine neuen Käufe mehr ausführen.
        - Jetzt wird das NETTO-Exposure berechnet: BUY-QuoteQty minus SELL-QuoteQty.
          Sobald eine Position vollständig geschlossen ist (BUY und SELL ausgeglichen),
          steht das volle Budget wieder zur Verfügung und der Bot kann weitertraden.
        """
        try:
            pipeline = [
                {"$match": {"bot_id": self.bot_id}},
                {
                    "$group": {
                        "_id": "$side",
                        "total": {"$sum": "$quote_qty"}
                    }
                }
            ]
            results = await self.db.trades.aggregate(pipeline).to_list(length=10)
            
            total_buy = 0.0
            total_sell = 0.0
            for row in results:
                side = row.get("_id")
                total = float(row.get("total", 0.0) or 0.0)
                if side == "BUY":
                    total_buy += total
                elif side == "SELL":
                    total_sell += total
            
            net_spent = max(0.0, total_buy - total_sell)
            return net_spent
        except Exception as e:
            logger.warning(f"Bot {self.bot_id}: Error calculating total spent: {e}")
            return 0.0
    
    def _get_execution_price_from_order(self, order: Dict[str, Any], symbol: str, current_price: float = None) -> float:
        """
        Berechnet execution_price aus Order-Daten.
        
        KRITISCH: Wenn Daten fehlen, wird versucht, die vollständigen Order-Daten von Binance abzurufen!
        
        Args:
            order: Order-Dict von Binance API
            symbol: Trading-Symbol
            current_price: Aktueller Kurs (nur für Fehlermeldungen)
        
        Returns:
            execution_price als float
        
        Raises:
            ValueError: Wenn execution_price nicht berechnet werden kann, auch nach Abruf der vollständigen Daten
        """
        execution_price = None
        
        # 1. Versuche aus fills zu berechnen (beste Quelle)
        if order.get("fills"):
            fills = order.get("fills", [])
            if fills:
                total_qty = sum(float(f.get("qty", 0)) for f in fills)
                total_quote = sum(float(f.get("quoteQty", 0)) for f in fills)
                if total_qty > 0 and total_quote > 0:
                    execution_price = total_quote / total_qty
                elif total_qty > 0:
                    # Wenn quoteQty fehlt, berechne aus price * qty
                    total_value = sum(float(f.get("price", 0)) * float(f.get("qty", 0)) for f in fills if f.get("price"))
                    if total_value > 0:
                        execution_price = total_value / total_qty
        
        # 2. Versuche aus cummulativeQuoteQty / executedQty
        if (execution_price is None or execution_price <= 0) and order.get("cummulativeQuoteQty") and order.get("executedQty"):
            executed_qty = float(order.get("executedQty", 0))
            if executed_qty > 0:
                execution_price = float(order.get("cummulativeQuoteQty")) / executed_qty
        
        # 3. Versuche aus order.get("price")
        if (execution_price is None or execution_price <= 0) and order.get("price"):
            execution_price = float(order.get("price"))
        
        # 4. KRITISCH: Wenn execution_price immer noch nicht verfügbar, hole vollständige Order-Daten von Binance!
        if execution_price is None or execution_price <= 0:
            order_id = order.get('orderId')
            if order_id and self.binance_client:
                logger.warning(f"Bot {self.bot_id}: Order-Daten unvollständig für Order {order_id}, hole vollständige Daten von Binance...")
                try:
                    trading_mode = self.current_config.get("trading_mode", "SPOT") if self.current_config else "SPOT"
                    full_order = self.binance_client.get_order_status(symbol, order_id, trading_mode)
                    
                    # Versuche erneut mit vollständigen Daten
                    if full_order.get("fills"):
                        fills = full_order.get("fills", [])
                        if fills:
                            total_qty = sum(float(f.get("qty", 0)) for f in fills)
                            total_quote = sum(float(f.get("quoteQty", 0)) for f in fills)
                            if total_qty > 0 and total_quote > 0:
                                execution_price = total_quote / total_qty
                    
                    if (execution_price is None or execution_price <= 0) and full_order.get("cummulativeQuoteQty") and full_order.get("executedQty"):
                        executed_qty = float(full_order.get("executedQty", 0))
                        if executed_qty > 0:
                            execution_price = float(full_order.get("cummulativeQuoteQty")) / executed_qty
                    
                    if (execution_price is None or execution_price <= 0) and full_order.get("price"):
                        execution_price = float(full_order.get("price"))
                    
                    if execution_price and execution_price > 0:
                        logger.info(f"Bot {self.bot_id}: Execution price erfolgreich aus vollständigen Order-Daten berechnet: {execution_price}")
                        return execution_price
                except Exception as fetch_error:
                    logger.error(f"Bot {self.bot_id}: Fehler beim Abrufen vollständiger Order-Daten: {fetch_error}")
        
        # KRITISCH: Wenn execution_price immer noch nicht verfügbar, Fehler werfen!
        if execution_price is None or execution_price <= 0:
            error_msg = (
                f"KRITISCHER FEHLER: Execution price nicht verfügbar für Order {order.get('orderId', 'N/A')} ({symbol}). "
                f"Order-Daten: fills={bool(order.get('fills'))}, "
                f"price={order.get('price')}, "
                f"cummulativeQuoteQty={order.get('cummulativeQuoteQty')}, "
                f"executedQty={order.get('executedQty')}, "
                f"current_price={current_price}. "
                f"Vollständige Order-Daten konnten nicht abgerufen werden."
            )
            logger.error(f"Bot {self.bot_id}: {error_msg}")
            raise ValueError(error_msg)
        
        return execution_price
    
    async def _execute_trade(self, analysis: Dict[str, Any], decision_price: float = None, decision_timestamp: datetime = None):
        """Execute a trade based on analysis.
        
        Args:
            analysis: Analysis result with signal and indicators
            decision_price: Price at time of signal generation (for slippage tracking)
            decision_timestamp: Timestamp when signal was generated (for delay tracking)
        """
        try:
            signal = analysis.get("signal")
            symbol = self.current_config["symbol"]
            configured_amount = self.current_config["amount"]
            
            # CRITICAL: Check stop loss and take profit BEFORE executing any new trade
            # This ensures positions are closed immediately when thresholds are reached,
            # even if a new signal comes in between the 5-minute bot loop checks
            if self.position is not None and self.position_entry_price > 0:
                current_price = self.binance_client.get_current_price(symbol)
                trading_mode = self.current_config.get("trading_mode", "SPOT")
                
                # Calculate P&L percentage
                if self.position == "LONG":
                    pnl_percent = ((current_price - self.position_entry_price) / self.position_entry_price) * 100
                elif self.position == "SHORT":
                    pnl_percent = ((self.position_entry_price - current_price) / self.position_entry_price) * 100
                else:
                    pnl_percent = 0
                
                # If position is at stop loss, close it first (trailing stop is handled in _check_stop_loss_and_take_profit)
                if pnl_percent <= STOP_LOSS_PERCENT:
                    logger.warning(f"Bot {self.bot_id}: Position at {pnl_percent:.2f}% P&L (Stop-Loss: {STOP_LOSS_PERCENT}%). Closing position before executing new trade.")
                    await self._check_stop_loss_and_take_profit(symbol, analysis)
                    # After closing position, check if we should still execute the new trade
                    # For BUY: continue (opening new position is fine)
                    # For SELL: skip (position already closed)
                    if signal == "SELL" and self.position is None:
                        logger.info(f"Bot {self.bot_id}: Position closed due to Stop-Loss/Take-Profit. Skipping SELL signal (no position to close).")
                        return
            
            # Track execution timing
            execution_timestamp = datetime.now(timezone.utc)
            delay_seconds = None
            if decision_timestamp:
                delay_seconds = (execution_timestamp - decision_timestamp).total_seconds()
            
            if signal == "BUY":
                # Check how much we've already spent
                total_spent = await self._get_total_spent()
                available_amount = configured_amount - total_spent
                
                if available_amount <= 0:
                    logger.warning(f"Bot {self.bot_id}: Amount limit reached! Total spent: {total_spent:.2f} USDT, Limit: {configured_amount:.2f} USDT. Skipping BUY trade.")
                    await self.agent_manager.log_agent_message(
                        "CypherTrade",
                        f"⚠️ Amount limit reached! Total spent: {total_spent:.2f} USDT / {configured_amount:.2f} USDT. Skipping BUY trade.",
                        "warning"
                    )
                    return
                
                # Get current price first
                current_price = self.binance_client.get_current_price(symbol)
                
                # Validate current price
                if current_price is None or current_price <= 0:
                    logger.error(f"Bot {self.bot_id}: Invalid current_price ({current_price}) for BUY order, skipping trade")
                    await self.agent_manager.log_agent_message(
                        "CypherTrade",
                        f"⚠️ Cannot execute BUY order: Invalid current price for {symbol} ({current_price})",
                        "error"
                    )
                    return
                
                # Get trading mode
                trading_mode = self.current_config.get("trading_mode", "SPOT")
                
                # Use intelligent quantity calculation that considers:
                # - Available budget (remaining amount)
                # - Available balance
                # - Binance filters (LOT_SIZE, MIN_NOTIONAL)
                quantity = self.binance_client.calculate_optimal_order_quantity(
                    symbol=symbol,
                    available_budget_usdt=available_amount,
                    current_price=current_price,
                    trading_mode=trading_mode
                )
                
                if quantity is None or quantity <= 0:
                    # Get symbol info for better error message
                    symbol_info = self.binance_client.get_symbol_info(symbol)
                    min_notional = symbol_info.get('min_notional', 10.0)
                    
                    # Extract quote asset from symbol
                    quote_asset = BinanceClientWrapper.extract_quote_asset(symbol)
                    balance = self.binance_client.get_account_balance(quote_asset, trading_mode)
                    
                    error_msg = f"⚠️ Cannot execute BUY order for {symbol}. "
                    if available_amount < min_notional:
                        error_msg += f"Available budget {available_amount:.8f} {quote_asset} is below minimum notional {min_notional:.8f} {quote_asset}. "
                    if balance < min_notional:
                        error_msg += f"Balance {balance:.8f} {quote_asset} is below minimum notional {min_notional:.8f} {quote_asset}. "
                    error_msg += f"(Total spent: {total_spent:.8f}/{configured_amount:.8f} {quote_asset})"
                    
                    logger.warning(f"Bot {self.bot_id}: {error_msg}")
                    await self.agent_manager.log_agent_message(
                        "CypherTrade",
                        error_msg,
                        "warning"
                    )
                    return
                
                # Final quantity validation
                final_order_value = quantity * current_price
                
                # Extract quote asset from symbol (e.g., SOLBTC -> BTC, ETHUSDT -> USDT)
                quote_asset = BinanceClientWrapper.extract_quote_asset(symbol)
                balance = self.binance_client.get_account_balance(quote_asset, trading_mode)
                
                # Double-check balance
                if balance < final_order_value:
                    logger.warning(f"Bot {self.bot_id}: Insufficient {quote_asset} balance ({trading_mode}). Required: {final_order_value:.8f}, Available: {balance:.8f}")
                    await self.agent_manager.log_agent_message(
                        "CypherTrade",
                        f"⚠️ Insufficient {quote_asset} balance. Required: {final_order_value:.8f} {quote_asset}, Available: {balance:.8f} {quote_asset}. Skipping BUY trade.",
                        "warning"
                    )
                    return
                
                # Double-check budget limit
                if final_order_value > available_amount:
                    logger.warning(f"Bot {self.bot_id}: Order value {final_order_value:.8f} {quote_asset} exceeds available budget {available_amount:.8f} {quote_asset}")
                    await self.agent_manager.log_agent_message(
                        "CypherTrade",
                        f"⚠️ Order value {final_order_value:.8f} {quote_asset} exceeds available budget {available_amount:.8f} {quote_asset}. Skipping BUY trade.",
                        "warning"
                    )
                    return
                
                logger.info(f"Bot {self.bot_id}: Executing BUY order - Quantity: {quantity}, Value: {final_order_value:.8f} {quote_asset}, Budget: {total_spent:.8f}/{configured_amount:.8f} {quote_asset} (Remaining: {available_amount - final_order_value:.8f} {quote_asset})")
                
                # Execute order
                execution_start_time = datetime.now(timezone.utc)
                order = self.binance_client.execute_order(symbol, "BUY", quantity, "MARKET", trading_mode)
                execution_end_time = datetime.now(timezone.utc)
                
                # Get actual execution price from order - KRITISCH: Kein Fallback, Kurs MUSS verfügbar sein!
                execution_price = None
                if order.get("fills"):
                    # Use average fill price if available
                    fills = order.get("fills", [])
                    if fills:
                        total_qty = sum(float(f.get("qty", 0)) for f in fills)
                        total_quote = sum(float(f.get("quoteQty", 0)) for f in fills)
                        if total_qty > 0 and total_quote > 0:
                            execution_price = total_quote / total_qty
                        elif total_qty > 0:
                            # If total_quote is 0 but total_qty > 0, calculate from fills
                            total_value = sum(float(f.get("price", 0)) * float(f.get("qty", 0)) for f in fills if f.get("price"))
                            if total_value > 0:
                                execution_price = total_value / total_qty
                
                # Fallback zu order.get("price") oder cummulativeQuoteQty/executedQty
                if execution_price is None or execution_price <= 0:
                    if order.get("price"):
                        execution_price = float(order.get("price"))
                    elif order.get("cummulativeQuoteQty") and order.get("executedQty"):
                        executed_qty = float(order.get("executedQty", 0))
                        if executed_qty > 0:
                            execution_price = float(order.get("cummulativeQuoteQty")) / executed_qty
                
                # KRITISCH: Wenn execution_price immer noch nicht verfügbar, Trade abbrechen!
                if execution_price is None or execution_price <= 0:
                    error_msg = f"KRITISCHER FEHLER: Execution price nicht verfügbar für Order {order.get('orderId', 'N/A')}. Order-Daten: {order}"
                    logger.error(f"Bot {self.bot_id}: {error_msg}")
                    await self.agent_manager.log_agent_message(
                        "CypherTrade",
                        f"❌ {error_msg} - Trade kann nicht verarbeitet werden!",
                        "error"
                    )
                    # Versuche Order zu stornieren falls möglich
                    try:
                        if order.get("orderId"):
                            self.binance_client.client.cancel_order(symbol=symbol, orderId=order.get("orderId"))
                            logger.info(f"Bot {self.bot_id}: Order {order.get('orderId')} storniert wegen fehlendem execution_price")
                    except Exception as cancel_error:
                        logger.warning(f"Bot {self.bot_id}: Konnte Order nicht stornieren: {cancel_error}")
                    return
                
                # Calculate delay and slippage
                execution_delay_seconds = None
                price_slippage = None
                price_slippage_percent = None
                
                if decision_timestamp:
                    execution_delay_seconds = (execution_start_time - decision_timestamp).total_seconds()
                
                if decision_price and decision_price > 0:
                    price_slippage = execution_price - decision_price
                    price_slippage_percent = ((execution_price - decision_price) / decision_price) * 100
                
                # Calculate quote_qty (USDT value) - prefer from order, fallback to calculation
                quote_qty_from_order = float(order.get("cummulativeQuoteQty", 0))
                if quote_qty_from_order > 0:
                    quote_qty = quote_qty_from_order
                else:
                    # Fallback: calculate from execution_price * quantity
                    quote_qty = execution_price * quantity
                    logger.debug(f"Bot {self.bot_id}: quote_qty not in order response, calculated: {quote_qty:.2f} USDT (price: {execution_price}, qty: {quantity})")
                
                # Save trade to database
                trade = {
                    "bot_id": self.bot_id,
                    "symbol": symbol,
                    "side": "BUY",
                    "quantity": quantity,
                    "order_id": str(order.get("orderId", "")),
                    "status": order.get("status", ""),
                    "executed_qty": float(order.get("executedQty", 0)),
                    "quote_qty": quote_qty,  # USDT value - always set correctly
                    "entry_price": execution_price,  # Use actual execution price
                    "decision_price": decision_price if decision_price else None,  # Price at signal generation
                    "execution_price": execution_price,  # Actual execution price
                    "price_slippage": price_slippage,  # Price difference
                    "price_slippage_percent": price_slippage_percent,  # Slippage in %
                    "decision_timestamp": decision_timestamp.isoformat() if decision_timestamp else None,
                    "execution_timestamp": execution_end_time.isoformat(),
                    "execution_delay_seconds": execution_delay_seconds,  # Delay in seconds
                    "strategy": self.current_config["strategy"],
                    "trading_mode": trading_mode,
                    "confidence": analysis.get("confidence", 0.0),
                    "indicators": analysis.get("indicators", {}),
                    "timestamp": execution_end_time.isoformat()
                }
                await self.db.trades.insert_one(trade)
                
                # Check total spent after trade
                total_spent_after = await self._get_total_spent()
                remaining = configured_amount - total_spent_after
                # Build detailed message with delay and slippage info
                delay_msg = f" | Delay: {execution_delay_seconds:.1f}s" if execution_delay_seconds else ""
                slippage_msg = f" | Slippage: {price_slippage_percent:+.2f}%" if price_slippage_percent is not None else ""
                
                logger.info(f"Bot {self.bot_id}: BUY order executed: {quantity} {symbol} at {execution_price} USDT | Total spent: {total_spent_after:.2f}/{configured_amount:.2f} USDT (Remaining: {remaining:.2f} USDT){delay_msg}{slippage_msg}")
                await self.agent_manager.log_agent_message(
                    "CypherTrade",
                    f"BUY order executed: {quantity} {symbol} at {execution_price} USDT | Total spent: {total_spent_after:.2f}/{configured_amount:.2f} USDT (Remaining: {remaining:.2f} USDT){delay_msg}{slippage_msg} (Order ID: {order.get('orderId')})",
                    "trade"
                )
                
                # Update position tracking (use execution_price instead of current_price)
                if self.position == "LONG":
                    # Add to existing position
                    self.position_size += quantity
                    # Update entry price (weighted average)
                    total_value = (self.position_size - quantity) * self.position_entry_price + quantity * execution_price
                    self.position_entry_price = total_value / self.position_size if self.position_size > 0 else execution_price
                    # Update high price if execution price is higher
                    if execution_price > self.position_high_price:
                        self.position_high_price = execution_price
                else:
                    # Open new LONG position
                    self.position = "LONG"
                    self.position_size = quantity
                    self.position_entry_price = execution_price
                    self.position_high_price = execution_price  # Initialize high price to entry price
                    self.position_entry_time = datetime.now(timezone.utc)  # Track entry time for position tracking
                    
                    # Start Position-Tracking für neue Position
                    if self.candle_tracker:
                        try:
                            buy_trade_id = str(order.get("orderId", ""))
                            timeframe = self.current_config.get("timeframe", "5m")
                            tracking_result = await self.candle_tracker.start_position_tracking(
                                bot_id=self.bot_id,
                                symbol=symbol,
                                timeframe=timeframe,
                                buy_trade_id=buy_trade_id
                            )
                            if tracking_result.get("success"):
                                logger.info(f"Bot {self.bot_id}: Position-Tracking gestartet nach BUY {buy_trade_id}")
                        except Exception as e:
                            logger.warning(f"Bot {self.bot_id}: Fehler beim Starten von Position-Tracking: {e}")
            
            elif signal == "SELL":
                # Update position status before executing SELL
                trading_mode = self.current_config.get("trading_mode", "SPOT")
                await self._update_position_from_balance(symbol, trading_mode)
                
                # Extract base asset correctly (supports all quote assets)
                base_asset = BinanceClientWrapper.extract_base_asset(symbol)
                
                # Check current position
                if self.position == "LONG":
                    # We have a LONG position - close it
                    base_asset = BinanceClientWrapper.extract_base_asset(symbol)
                    balance = self.binance_client.get_account_balance(base_asset, trading_mode)
                    
                    if balance <= 0:
                        logger.warning(f"Bot {self.bot_id}: No {base_asset} balance to sell. Balance: {balance}")
                        return
                    
                    # Get current price
                    current_price = self.binance_client.get_current_price(symbol)
                    
                    # CRITICAL: Validate that we're not selling at a loss (unless it's a forced close due to stop loss)
                    # Check if current price is below entry price (we would make a loss)
                    if current_price < self.position_entry_price:
                        # Calculate potential loss
                        pnl_percent = ((current_price - self.position_entry_price) / self.position_entry_price) * 100
                        
                        # Only allow selling at a loss if we're forced to (stop loss already checked earlier)
                        # This prevents accidental negative trades due to outdated price data
                        logger.warning(
                            f"Bot {self.bot_id}: ⚠️ SELL signal would result in LOSS: "
                            f"Current price {current_price} < Entry price {self.position_entry_price} "
                            f"({pnl_percent:.2f}% loss). Skipping SELL to prevent negative trade."
                        )
                        await self.agent_manager.log_agent_message(
                            "CypherTrade",
                            f"⚠️ SELL signal BLOCKED: Current price {current_price} is below entry price {self.position_entry_price} "
                            f"({pnl_percent:.2f}% loss). Would result in negative trade. Skipping.",
                            "warning"
                        )
                        return
                    
                    # CRITICAL: Validate minimum profit requirement (2% minimum)
                    # Calculate current profit percentage
                    pnl_percent = ((current_price - self.position_entry_price) / self.position_entry_price) * 100
                    
                    # Block SELL if profit is below minimum threshold (unless it's stop loss, which is checked earlier)
                    if pnl_percent < TAKE_PROFIT_MIN_PERCENT:
                        logger.warning(
                            f"Bot {self.bot_id}: ⚠️ SELL signal BLOCKED - Profit too low: "
                            f"Current profit {pnl_percent:.2f}% < Minimum required {TAKE_PROFIT_MIN_PERCENT}%. "
                            f"Entry: {self.position_entry_price}, Current: {current_price}. "
                            f"Position will remain open until minimum profit target is reached."
                        )
                        await self.agent_manager.log_agent_message(
                            "CypherTrade",
                            f"⚠️ SELL signal BLOCKED: Current profit {pnl_percent:.2f}% is below minimum required {TAKE_PROFIT_MIN_PERCENT}%. "
                            f"Position will remain open until profit target is reached.",
                            "warning"
                        )
                        return
                    
                    # Adjust quantity to match Binance LOT_SIZE filter requirements
                    quantity = self.binance_client.adjust_quantity_to_lot_size(symbol, balance)
                    
                    # Adjust quantity to meet MIN_NOTIONAL filter requirements
                    # No budget limit for SELL orders (we're selling what we have)
                    adjusted_quantity = self.binance_client.adjust_quantity_to_notional(symbol, quantity, current_price)
                    if adjusted_quantity is None:
                        # Check if the order value is too small
                        order_value = quantity * current_price
                        symbol_info = self.binance_client.get_symbol_info(symbol)
                        min_notional = symbol_info.get('min_notional', 10.0)
                        
                        error_msg = f"⚠️ Cannot execute SELL order for {symbol}. Order value {order_value:.2f} USDT is below minimum notional {min_notional:.2f} USDT. "
                        error_msg += f"Available balance: {balance} {base_asset}."
                        
                        logger.warning(f"Bot {self.bot_id}: {error_msg}")
                        await self.agent_manager.log_agent_message(
                            "CypherTrade",
                            error_msg,
                            "warning"
                        )
                        return
                    quantity = adjusted_quantity
                    
                    # Final check: ensure we're not trying to sell more than we have
                    if quantity > balance:
                        # Reduce to available balance
                        quantity = self.binance_client.adjust_quantity_to_lot_size(symbol, balance)
                        logger.info(f"Bot {self.bot_id}: Adjusted quantity to available balance: {quantity} {base_asset}")
                        
                        # CRITICAL: Re-check MIN_NOTIONAL after reducing quantity
                        # If quantity was reduced below MIN_NOTIONAL, we cannot execute the trade
                        adjusted_quantity_check = self.binance_client.adjust_quantity_to_notional(symbol, quantity, current_price)
                        if adjusted_quantity_check is None:
                            order_value = quantity * current_price
                            symbol_info = self.binance_client.get_symbol_info(symbol)
                            min_notional = symbol_info.get('min_notional', 10.0)
                            
                            error_msg = f"⚠️ Cannot execute SELL order for {symbol}. Available balance {balance} {base_asset} results in order value {order_value:.8f} below minimum notional {min_notional:.8f}. Cannot sell position."
                            
                            logger.warning(f"Bot {self.bot_id}: {error_msg}")
                            await self.agent_manager.log_agent_message(
                                "CypherTrade",
                                error_msg,
                                "warning"
                            )
                            return
                        
                        # Use the re-adjusted quantity if it's valid
                        if adjusted_quantity_check <= balance:
                            quantity = adjusted_quantity_check
                        else:
                            # Still too much, use balance
                            quantity = balance
                            logger.warning(f"Bot {self.bot_id}: Final quantity {quantity} {base_asset} may be below MIN_NOTIONAL, but using available balance")
                    
                    # Final validation: ensure quantity is positive and within balance
                    if quantity <= 0:
                        logger.warning(f"Bot {self.bot_id}: Invalid quantity {quantity} for SELL order. Balance: {balance} {base_asset}")
                        await self.agent_manager.log_agent_message(
                            "CypherTrade",
                            f"⚠️ Cannot execute SELL order: Invalid quantity {quantity} {base_asset}. Available balance: {balance} {base_asset}.",
                            "warning"
                        )
                        return
                    
                    if quantity > balance:
                        logger.warning(f"Bot {self.bot_id}: Quantity {quantity} exceeds balance {balance} {base_asset}. Using balance.")
                        quantity = self.binance_client.adjust_quantity_to_lot_size(symbol, balance)
                    
                    # Execute order
                    execution_start_time = datetime.now(timezone.utc)
                    order = self.binance_client.execute_order(symbol, "SELL", quantity, "MARKET", trading_mode)
                    execution_end_time = datetime.now(timezone.utc)
                    
                    # Get actual execution price from order - KRITISCH: Kein Fallback!
                    try:
                        execution_price = self._get_execution_price_from_order(order, symbol, current_price)
                    except ValueError as e:
                        error_msg = f"SELL Order fehlgeschlagen: {str(e)}"
                        logger.error(f"Bot {self.bot_id}: {error_msg}")
                        await self.agent_manager.log_agent_message("CypherTrade", f"❌ {error_msg}", "error")
                        return
                    
                    # Calculate delay and slippage
                    execution_delay_seconds = None
                    price_slippage = None
                    price_slippage_percent = None
                    
                    if decision_timestamp:
                        execution_delay_seconds = (execution_start_time - decision_timestamp).total_seconds()
                    
                    if decision_price and decision_price > 0:
                        price_slippage = execution_price - decision_price
                        price_slippage_percent = ((execution_price - decision_price) / decision_price) * 100
                    
                    # Calculate profit/loss
                    pnl = None
                    pnl_percent = None
                    exit_reason = "SIGNAL"  # Default: closed by signal
                    if self.position_entry_price > 0:
                        pnl = (execution_price - self.position_entry_price) * quantity
                        pnl_percent = ((execution_price - self.position_entry_price) / self.position_entry_price) * 100
                        
                        # Check if this trade should be marked as Stop-Loss or Take-Profit
                        if pnl_percent <= STOP_LOSS_PERCENT:
                            exit_reason = "STOP_LOSS"
                            logger.warning(f"Bot {self.bot_id}: SELL executed but position was at {pnl_percent:.2f}% (Stop-Loss threshold: {STOP_LOSS_PERCENT}%). Marking as STOP_LOSS.")
                        elif pnl_percent >= TAKE_PROFIT_MIN_PERCENT:
                            exit_reason = "TAKE_PROFIT"
                            logger.info(f"Bot {self.bot_id}: SELL executed but position was at {pnl_percent:.2f}% (Take-Profit threshold: >= {TAKE_PROFIT_MIN_PERCENT}%). Marking as TAKE_PROFIT.")
                    
                    # Calculate quote_qty (USDT value) - prefer from order, fallback to calculation
                    quote_qty_from_order = float(order.get("cummulativeQuoteQty", 0))
                    if quote_qty_from_order > 0:
                        quote_qty = quote_qty_from_order
                    else:
                        # Fallback: calculate from execution_price * quantity
                        quote_qty = execution_price * quantity
                        logger.debug(f"Bot {self.bot_id}: quote_qty not in order response, calculated: {quote_qty:.2f} USDT (price: {execution_price}, qty: {quantity})")
                    
                    # Save trade
                    trade = {
                        "bot_id": self.bot_id,
                        "symbol": symbol,
                        "side": "SELL",
                        "quantity": quantity,
                        "order_id": str(order.get("orderId", "")),
                        "status": order.get("status", ""),
                        "executed_qty": float(order.get("executedQty", 0)),
                        "quote_qty": quote_qty,  # USDT value - always set correctly
                        "entry_price": execution_price,  # Use actual execution price
                        "decision_price": decision_price if decision_price else None,  # Price at signal generation
                        "execution_price": execution_price,  # Actual execution price
                        "price_slippage": price_slippage,  # Price difference
                        "price_slippage_percent": price_slippage_percent,  # Slippage in %
                        "decision_timestamp": decision_timestamp.isoformat() if decision_timestamp else None,
                        "execution_timestamp": execution_end_time.isoformat(),
                        "execution_delay_seconds": execution_delay_seconds,  # Delay in seconds
                        "strategy": self.current_config["strategy"],
                        "trading_mode": trading_mode,
                        "exit_reason": exit_reason,  # Mark as STOP_LOSS, TAKE_PROFIT, or SIGNAL
                        "confidence": analysis.get("confidence", 0.0),
                        "indicators": analysis.get("indicators", {}),
                        "timestamp": execution_end_time.isoformat()
                    }
                    
                    if pnl is not None:
                        trade["pnl"] = pnl
                        trade["pnl_percent"] = pnl_percent
                        trade["position_entry_price"] = self.position_entry_price
                    
                    await self.db.trades.insert_one(trade)
                    
                    # Learn from closed position (if P&L is available)
                    # Store entry price before resetting position
                    old_entry_price = self.position_entry_price
                    if pnl is not None and old_entry_price > 0:
                        await self._learn_from_closed_position(trade, pnl, old_entry_price, current_price)
                    
                    # Stop Position-Tracking before resetting position
                    if self.candle_tracker:
                        try:
                            sell_trade_id = str(order.get("orderId", ""))
                            stop_result = await self.candle_tracker.stop_position_tracking(
                                bot_id=self.bot_id,
                                sell_trade_id=sell_trade_id
                            )
                            if stop_result.get("success"):
                                logger.info(f"Bot {self.bot_id}: Position-Tracking gestoppt nach SELL {sell_trade_id} ({stop_result.get('candles_collected', 0)} Kerzen gesammelt)")
                        except Exception as e:
                            logger.warning(f"Bot {self.bot_id}: Fehler beim Stoppen von Position-Tracking: {e}")
                    
                    # Position closed
                    self.position = None
                    self.position_size = 0.0
                    self.position_entry_price = 0.0
                    self.position_high_price = 0.0
                    
                    # Build detailed message with delay and slippage info
                    pnl_msg = f" | P/L: {pnl:+.2f} USDT ({pnl_percent:+.2f}%)" if pnl is not None else ""
                    delay_msg = f" | Delay: {execution_delay_seconds:.1f}s" if execution_delay_seconds else ""
                    slippage_msg = f" | Slippage: {price_slippage_percent:+.2f}%" if price_slippage_percent is not None else ""
                    
                    logger.info(f"Bot {self.bot_id}: SELL order executed: {quantity} {symbol} at {execution_price} USDT (LONG position closed{pnl_msg}{delay_msg}{slippage_msg})")
                    await self.agent_manager.log_agent_message(
                        "CypherTrade",
                        f"SELL order executed: {quantity} {symbol} at {execution_price} USDT (LONG position closed{pnl_msg}{delay_msg}{slippage_msg}) (Order ID: {order.get('orderId')})",
                        "trade"
                    )
                
                elif self.position == "SHORT":
                    # We have a SHORT position - close it by buying
                    current_price = self.binance_client.get_current_price(symbol)
                    
                    # CRITICAL: Validate minimum profit requirement (2% minimum) for SHORT positions
                    # For SHORT: profit when price goes down (entry_price > current_price)
                    pnl_percent = ((self.position_entry_price - current_price) / self.position_entry_price) * 100
                    
                    # Block BUY to close SHORT if profit is below minimum threshold (unless it's stop loss, which is checked earlier)
                    # KRITISCH: Prüfe Mindest-Haltedauer (außer bei Stop-Loss, der bereits früher geprüft wurde)
                    holding_time_valid, holding_info = self._check_minimum_holding_time(is_stop_loss=False)
                    if not holding_time_valid:
                        remaining_minutes = holding_info
                        logger.warning(
                            f"Bot {self.bot_id}: ⚠️ BUY to close SHORT signal BLOCKED - Minimum holding time not reached: "
                            f"Position held for {MIN_HOLDING_TIME_MINUTES - remaining_minutes:.1f} minutes, "
                            f"minimum required: {MIN_HOLDING_TIME_MINUTES} minutes. "
                            f"Remaining: {remaining_minutes:.1f} minutes. "
                            f"Current profit: {pnl_percent:.2f}%."
                        )
                        await self.agent_manager.log_agent_message(
                            "CypherTrade",
                            f"⚠️ BUY to close SHORT signal BLOCKED: Minimum holding time not reached. "
                            f"Position must be held for at least {MIN_HOLDING_TIME_MINUTES} minutes. "
                            f"Remaining: {remaining_minutes:.1f} minutes.",
                            "warning"
                        )
                        return
                    
                    if pnl_percent < TAKE_PROFIT_MIN_PERCENT:
                        logger.warning(
                            f"Bot {self.bot_id}: ⚠️ BUY to close SHORT signal BLOCKED - Profit too low: "
                            f"Current profit {pnl_percent:.2f}% < Minimum required {TAKE_PROFIT_MIN_PERCENT}%. "
                            f"Entry: {self.position_entry_price}, Current: {current_price}. "
                            f"Position will remain open until minimum profit target is reached."
                        )
                        await self.agent_manager.log_agent_message(
                            "CypherTrade",
                            f"⚠️ BUY to close SHORT signal BLOCKED: Current profit {pnl_percent:.2f}% is below minimum required {TAKE_PROFIT_MIN_PERCENT}%. "
                            f"Position will remain open until profit target is reached.",
                            "warning"
                        )
                        return
                    
                    amount_usdt = self.current_config["amount"]
                    
                    # Validate current price before division
                    if current_price is None or current_price <= 0:
                        logger.error(f"Bot {self.bot_id}: Invalid current_price ({current_price}) for SHORT close, skipping trade")
                        return
                    
                    # Calculate quantity to buy to close short
                    quantity = amount_usdt / current_price
                    quantity = self.binance_client.adjust_quantity_to_lot_size(symbol, quantity)
                    adjusted_quantity = self.binance_client.adjust_quantity_to_notional(symbol, quantity, current_price)
                    if adjusted_quantity is None:
                        logger.warning(f"Bot {self.bot_id}: Order value too small for {symbol}, skipping trade")
                        return
                    quantity = adjusted_quantity
                    
                    # Execute BUY order to close SHORT
                    execution_start_time = datetime.now(timezone.utc)
                    order = self.binance_client.execute_order(symbol, "BUY", quantity, "MARKET", trading_mode)
                    execution_end_time = datetime.now(timezone.utc)
                    
                    # Get actual execution price from order
                    execution_price = float(order.get("price", 0)) or current_price
                    if order.get("fills"):
                        fills = order.get("fills", [])
                        if fills:
                            total_qty = sum(float(f.get("qty", 0)) for f in fills)
                            total_quote = sum(float(f.get("quoteQty", 0)) for f in fills)
                            if total_qty > 0:
                                execution_price = total_quote / total_qty
                    
                    # Calculate delay and slippage
                    execution_delay_seconds = None
                    price_slippage = None
                    price_slippage_percent = None
                    
                    if decision_timestamp:
                        execution_delay_seconds = (execution_start_time - decision_timestamp).total_seconds()
                    
                    if decision_price and decision_price > 0:
                        price_slippage = execution_price - decision_price
                        price_slippage_percent = ((execution_price - decision_price) / decision_price) * 100
                    
                    # Calculate profit/loss (for SHORT: profit when price goes down)
                    pnl = None
                    pnl_percent = None
                    exit_reason = "SIGNAL"  # Default: closed by signal
                    if self.position_entry_price > 0:
                        pnl = (self.position_entry_price - execution_price) * quantity
                        pnl_percent = ((self.position_entry_price - execution_price) / self.position_entry_price) * 100
                        
                        # Check if this trade should be marked as Stop-Loss or Take-Profit
                        if pnl_percent <= STOP_LOSS_PERCENT:
                            exit_reason = "STOP_LOSS"
                            logger.warning(f"Bot {self.bot_id}: BUY to close SHORT executed but position was at {pnl_percent:.2f}% (Stop-Loss threshold: {STOP_LOSS_PERCENT}%). Marking as STOP_LOSS.")
                        elif pnl_percent >= TAKE_PROFIT_MIN_PERCENT:
                            exit_reason = "TAKE_PROFIT"
                            logger.info(f"Bot {self.bot_id}: BUY to close SHORT executed but position was at {pnl_percent:.2f}% (Take-Profit threshold: >= {TAKE_PROFIT_MIN_PERCENT}%). Marking as TAKE_PROFIT.")
                    
                    # Save trade
                    trade = {
                        "bot_id": self.bot_id,
                        "symbol": symbol,
                        "side": "BUY",  # BUY to close SHORT
                        "quantity": quantity,
                        "order_id": str(order.get("orderId", "")),
                        "status": order.get("status", ""),
                        "executed_qty": float(order.get("executedQty", 0)),
                        "quote_qty": float(order.get("cummulativeQuoteQty", 0)),
                        "entry_price": execution_price,  # Use actual execution price
                        "decision_price": decision_price if decision_price else None,
                        "execution_price": execution_price,
                        "price_slippage": price_slippage,
                        "price_slippage_percent": price_slippage_percent,
                        "decision_timestamp": decision_timestamp.isoformat() if decision_timestamp else None,
                        "execution_timestamp": execution_end_time.isoformat(),
                        "execution_delay_seconds": execution_delay_seconds,
                        "strategy": self.current_config["strategy"],
                        "trading_mode": trading_mode,
                        "position_type": "SHORT_CLOSE",
                        "exit_reason": exit_reason,  # Mark as STOP_LOSS, TAKE_PROFIT, or SIGNAL
                        "confidence": analysis.get("confidence", 0.0),
                        "indicators": analysis.get("indicators", {}),
                        "timestamp": execution_end_time.isoformat()
                    }
                    
                    if pnl is not None:
                        trade["pnl"] = pnl
                        trade["pnl_percent"] = pnl_percent
                        trade["position_entry_price"] = self.position_entry_price
                    
                    await self.db.trades.insert_one(trade)
                    
                    # Learn from closed position (if P&L is available)
                    # Store entry price before resetting position
                    old_entry_price = self.position_entry_price
                    if pnl is not None and old_entry_price > 0:
                        await self._learn_from_closed_position(trade, pnl, old_entry_price, current_price)
                    
                    # SHORT position closed
                    self.position = None
                    self.position_size = 0.0
                    self.position_entry_price = 0.0
                    self.position_high_price = 0.0
                    
                    pnl_msg = f" | P/L: {pnl:+.2f} USDT ({pnl_percent:+.2f}%)" if pnl is not None else ""
                    delay_msg = f" | Delay: {execution_delay_seconds:.1f}s" if execution_delay_seconds else ""
                    slippage_msg = f" | Slippage: {price_slippage_percent:+.2f}%" if price_slippage_percent is not None else ""
                    
                    logger.info(f"Bot {self.bot_id}: BUY order executed to close SHORT: {quantity} {symbol} at {execution_price} USDT{pnl_msg}{delay_msg}{slippage_msg}")
                    await self.agent_manager.log_agent_message(
                        "CypherTrade",
                        f"BUY order executed to close SHORT: {quantity} {symbol} at {execution_price} USDT{pnl_msg}{delay_msg}{slippage_msg} (Order ID: {order.get('orderId')})",
                        "trade"
                    )
                
                else:
                    # No position - check if we can open a SHORT position
                    if trading_mode in ["MARGIN", "FUTURES"]:
                        # Open SHORT position
                        amount_usdt = self.current_config["amount"]
                        current_price = self.binance_client.get_current_price(symbol)
                        
                        # Validate current price before division
                        if current_price is None or current_price <= 0:
                            logger.error(f"Bot {self.bot_id}: Invalid current_price ({current_price}) for SHORT open, skipping trade")
                            return
                        
                        # Calculate quantity
                        quantity = amount_usdt / current_price
                        quantity = self.binance_client.adjust_quantity_to_lot_size(symbol, quantity)
                        adjusted_quantity = self.binance_client.adjust_quantity_to_notional(symbol, quantity, current_price)
                        if adjusted_quantity is None:
                            logger.warning(f"Bot {self.bot_id}: Order value too small for {symbol}, skipping trade")
                            return
                        quantity = adjusted_quantity
                        
                        # Execute SELL order to open SHORT (for Margin/Futures)
                        execution_start_time = datetime.now(timezone.utc)
                        order = self.binance_client.execute_order(symbol, "SELL", quantity, "MARKET", trading_mode)
                        execution_end_time = datetime.now(timezone.utc)
                        
                        # Get actual execution price from order - KRITISCH: Kein Fallback!
                        try:
                            execution_price = self._get_execution_price_from_order(order, symbol, current_price)
                        except ValueError as e:
                            error_msg = f"SHORT Position öffnen fehlgeschlagen: {str(e)}"
                            logger.error(f"Bot {self.bot_id}: {error_msg}")
                            await self.agent_manager.log_agent_message("CypherTrade", f"❌ {error_msg}", "error")
                            return
                        
                        # Calculate delay and slippage
                        execution_delay_seconds = None
                        price_slippage = None
                        price_slippage_percent = None
                        
                        if decision_timestamp:
                            execution_delay_seconds = (execution_start_time - decision_timestamp).total_seconds()
                        
                        if decision_price and decision_price > 0:
                            price_slippage = execution_price - decision_price
                            price_slippage_percent = ((execution_price - decision_price) / decision_price) * 100
                        
                        # Save trade
                        trade = {
                            "bot_id": self.bot_id,
                            "symbol": symbol,
                            "side": "SELL",
                            "quantity": quantity,
                            "order_id": str(order.get("orderId", "")),
                            "status": order.get("status", ""),
                            "executed_qty": float(order.get("executedQty", 0)),
                            "quote_qty": float(order.get("cummulativeQuoteQty", 0)),
                            "entry_price": execution_price,  # Use actual execution price
                            "decision_price": decision_price if decision_price else None,
                            "execution_price": execution_price,
                            "price_slippage": price_slippage,
                            "price_slippage_percent": price_slippage_percent,
                            "decision_timestamp": decision_timestamp.isoformat() if decision_timestamp else None,
                            "execution_timestamp": execution_end_time.isoformat(),
                            "execution_delay_seconds": execution_delay_seconds,
                            "strategy": self.current_config["strategy"],
                            "trading_mode": trading_mode,
                            "position_type": "SHORT_OPEN",
                            "confidence": analysis.get("confidence", 0.0),
                            "indicators": analysis.get("indicators", {}),
                            "timestamp": execution_end_time.isoformat()
                        }
                        await self.db.trades.insert_one(trade)
                        
                        # Update position tracking - SHORT position opened
                        self.position = "SHORT"
                        self.position_entry_time = datetime.now(timezone.utc)  # Track entry time for position tracking
                        self.position_size = quantity
                        self.position_entry_price = execution_price
                        
                        delay_msg = f" | Delay: {execution_delay_seconds:.1f}s" if execution_delay_seconds else ""
                        slippage_msg = f" | Slippage: {price_slippage_percent:+.2f}%" if price_slippage_percent is not None else ""
                        
                        logger.info(f"Bot {self.bot_id}: SELL order executed to open SHORT: {quantity} {symbol} at {execution_price} USDT ({trading_mode}){delay_msg}{slippage_msg}")
                        await self.agent_manager.log_agent_message(
                            "CypherTrade",
                            f"SELL order executed to open SHORT position: {quantity} {symbol} at {execution_price} USDT ({trading_mode}){delay_msg}{slippage_msg} (Order ID: {order.get('orderId')})",
                            "trade"
                        )
                    else:
                        # SPOT mode - cannot open SHORT
                        logger.info(f"Bot {self.bot_id}: SELL signal received but no position to close. SPOT trading does not support short positions.")
                        await self.agent_manager.log_agent_message(
                            "CypherTrade",
                            f"SELL signal received but no position to close. SPOT trading only supports closing LONG positions. Use MARGIN or FUTURES mode for short trading.",
                            "info"
                        )
        
        except ValueError as e:
            # Specific validation errors (e.g., NOTIONAL, balance issues)
            error_msg = str(e)
            logger.warning(f"Bot {self.bot_id}: Trade execution validation error: {error_msg}")
            await self.agent_manager.log_agent_message(
                "CypherTrade",
                f"⚠️ Trade validation error: {error_msg}",
                "warning"
            )
        except Exception as e:
            logger.error(f"Bot {self.bot_id}: Trade execution error: {e}", exc_info=True)
            await self.agent_manager.log_agent_message(
                "CypherTrade",
                f"Trade execution error: {str(e)}",
                "error"
            )
    
    async def execute_manual_trade(self, symbol: str, side: str, quantity: Optional[float] = None, amount_usdt: Optional[float] = None) -> Dict[str, Any]:
        """Execute a manual trade order."""
        try:
            # Initialize Binance client if not already initialized
            if self.binance_client is None:
                # This allows manual trades even if the bot loop hasn't started yet
                self.binance_client = BinanceClientWrapper()
            
            # Get current price
            current_price = self.binance_client.get_current_price(symbol)
            
            # Validate current price
            if current_price is None or current_price <= 0:
                return {"success": False, "message": f"Invalid current price for {symbol}: {current_price}. Cannot execute trade."}
            
            # Calculate quantity if not provided
            if quantity is None:
                if amount_usdt is None:
                    return {"success": False, "message": "Either quantity or amount_usdt must be provided"}
                
                if side == "BUY":
                    # Calculate quantity from amount in quote asset
                    quote_asset = BinanceClientWrapper.extract_quote_asset(symbol)
                    balance = self.binance_client.get_account_balance(quote_asset, trading_mode=self.current_config.get("trading_mode", "SPOT"))
                    amount_to_use = min(amount_usdt, balance)
                    if current_price <= 0:
                        return {"success": False, "message": f"Invalid current price for {symbol}: {current_price}. Cannot calculate quantity."}
                    quantity = amount_to_use / current_price
                elif side == "SELL":
                    # Extract base asset correctly (supports all quote assets)
                    base_asset = BinanceClientWrapper.extract_base_asset(symbol)
                    trading_mode = self.current_config.get("trading_mode", "SPOT")
                    balance = self.binance_client.get_account_balance(base_asset, trading_mode)
                    
                    # If amount_usdt is provided, interpret it as quantity (not USDT amount for SELL)
                    # Otherwise, sell all available base asset
                    if amount_usdt is not None:
                        # amount_usdt is interpreted as quantity for SELL orders
                        quantity = min(amount_usdt, balance)
                    else:
                        quantity = balance
            
            # Adjust quantity to match Binance LOT_SIZE filter requirements
            quantity = self.binance_client.adjust_quantity_to_lot_size(symbol, quantity)
            
            # Adjust quantity to meet MIN_NOTIONAL filter requirements
            adjusted_quantity = self.binance_client.adjust_quantity_to_notional(symbol, quantity, current_price)
            if adjusted_quantity is None:
                return {
                    "success": False,
                    "message": f"Order value too small. Minimum notional value not met for {symbol}. Please increase quantity or amount."
                }
            quantity = adjusted_quantity
            
            if quantity <= 0:
                return {"success": False, "message": f"Insufficient balance for {side} order"}
            
            # Validate balance before executing
            trading_mode = self.current_config.get("trading_mode", "SPOT")
            if side == "BUY":
                quote_asset = BinanceClientWrapper.extract_quote_asset(symbol)
                balance = self.binance_client.get_account_balance(quote_asset, trading_mode)
                required_quote = quantity * current_price
                if balance < required_quote:
                    return {"success": False, "message": f"Insufficient {quote_asset} balance. Required: {required_quote:.8f}, Available: {balance:.8f}"}
            elif side == "SELL":
                base_asset = BinanceClientWrapper.extract_base_asset(symbol)
                balance = self.binance_client.get_account_balance(base_asset, trading_mode)
                if balance < quantity:
                    return {"success": False, "message": f"Insufficient {base_asset} balance. Required: {quantity:.8f}, Available: {balance:.8f}"}
            
            # Execute order
            trading_mode = self.current_config.get("trading_mode", "SPOT")
            order = self.binance_client.execute_order(symbol, side, quantity, "MARKET", trading_mode)
            
            # Save trade to database
            trade = {
                "bot_id": self.bot_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "order_id": str(order.get("orderId", "")),
                "status": order.get("status", ""),
                "executed_qty": float(order.get("executedQty", 0)),
                "quote_qty": float(order.get("cummulativeQuoteQty", 0)),
                "entry_price": current_price,
                "strategy": "manual",
                "confidence": 1.0,
                "indicators": {"current_price": current_price},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await self.db.trades.insert_one(trade)
            
            logger.info(f"Bot {self.bot_id}: Manual {side} order executed: {quantity} {symbol} at {current_price} USDT")
            
            return {
                "success": True,
                "message": f"{side} order executed successfully",
                "order": {
                    "orderId": str(order.get("orderId", "")),
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "price": current_price,
                    "executedQty": float(order.get("executedQty", 0)),
                    "cummulativeQuoteQty": float(order.get("cummulativeQuoteQty", 0)),
                    "status": order.get("status", "")
                }
            }
        
        except Exception as e:
            logger.error(f"Bot {self.bot_id}: Error executing manual trade: {e}", exc_info=True)
            return {"success": False, "message": str(e)}
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current bot status."""
        try:
            config = None
            if self.current_config:
                config = convert_objectid_to_str(self.current_config.copy())
            
            # Update position from balance if bot is running
            if self.is_running and self.current_config:
                trading_mode = self.current_config.get("trading_mode", "SPOT")
                await self._update_position_from_balance(self.current_config["symbol"], trading_mode)
            
            # Get current price and calculate asset info if we have a position
            current_price = None
            unrealized_pnl = None
            unrealized_pnl_percent = None
            asset_info = None
            
            if self.position and self.position_size > 0 and self.binance_client and self.current_config:
                try:
                    symbol = self.current_config["symbol"]
                    current_price = self.binance_client.get_current_price(symbol)
                    
                    # Extract base asset from symbol (e.g., BTCUSDT -> BTC)
                    base_asset = symbol.replace("USDT", "").replace("BUSD", "").replace("BTC", "").replace("ETH", "")
                    
                    if current_price:
                        value_usdt = self.position_size * current_price
                        
                        if self.position_entry_price > 0:
                            if self.position == "LONG":
                                unrealized_pnl = (current_price - self.position_entry_price) * self.position_size
                                unrealized_pnl_percent = ((current_price - self.position_entry_price) / self.position_entry_price) * 100
                            elif self.position == "SHORT":
                                unrealized_pnl = (self.position_entry_price - current_price) * self.position_size
                                unrealized_pnl_percent = ((self.position_entry_price - current_price) / self.position_entry_price) * 100
                        
                        asset_info = {
                            "asset": base_asset,
                            "symbol": symbol,
                            "quantity": round(self.position_size, 8),
                            "value_usdt": round(value_usdt, 2),
                            "entry_price": round(self.position_entry_price, 6) if self.position_entry_price > 0 else None,
                            "current_price": round(current_price, 6),
                            "position_type": self.position
                        }
                        
                except Exception as e:
                    logger.warning(f"Could not get asset info for status: {e}")
            
            status = {
                "bot_id": self.bot_id,
                "is_running": self.is_running,
                "config": config,
                "position": {
                    "type": self.position,  # "LONG", "SHORT", or None
                    "size": round(self.position_size, 8) if self.position_size > 0 else 0.0,
                    "entry_price": round(self.position_entry_price, 6) if self.position_entry_price > 0 else None,
                    "current_price": round(current_price, 6) if current_price else None,
                    "unrealized_pnl": round(unrealized_pnl, 2) if unrealized_pnl is not None else None,
                    "unrealized_pnl_percent": round(unrealized_pnl_percent, 2) if unrealized_pnl_percent is not None else None
                },
                "asset": asset_info,  # Asset information if holding a position
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return status
        except Exception as e:
            logger.error(f"Error getting bot status: {e}")
            return {
                "bot_id": self.bot_id,
                "is_running": False,
                "config": None,
                "position": None,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

class BotManager:
    """Manages multiple TradingBot instances."""
    
    def __init__(self, db, agent_manager):
        self.db = db
        self.agent_manager = agent_manager
        self.bots: Dict[str, TradingBot] = {}
        # Shared Binance client (can be reused across bots)
        self.shared_binance_client = None
    
    def get_bot(self, bot_id: Optional[str] = None) -> TradingBot:
        """Get or create a bot instance."""
        if bot_id is None:
            # Create new bot with new ID
            bot = TradingBot(self.db, self.agent_manager)
            self.bots[bot.bot_id] = bot
            return bot
        else:
            # Get existing bot or create new one with specified ID
            if bot_id not in self.bots:
                bot = TradingBot(self.db, self.agent_manager, bot_id=bot_id)
                self.bots[bot_id] = bot
            return self.bots[bot_id]
    
    def get_all_bots(self) -> Dict[str, TradingBot]:
        """Get all bot instances."""
        return self.bots
    
    def remove_bot(self, bot_id: str) -> bool:
        """Remove a bot instance (only if stopped)."""
        if bot_id in self.bots:
            bot = self.bots[bot_id]
            if not bot.is_running:
                del self.bots[bot_id]
                return True
        return False
    
    async def get_all_bots_status(self) -> Dict[str, Any]:
        """Get status of all bots."""
        statuses = {}
        for bot_id, bot in self.bots.items():
            statuses[bot_id] = await bot.get_status()
        return statuses

# Legacy function for backward compatibility
bot_instance: Optional[TradingBot] = None

def get_bot_instance(db, agent_manager, bot_id: Optional[str] = None) -> TradingBot:
    """Get or create bot instance (legacy - use BotManager instead)."""
    global bot_instance
    if bot_instance is None:
        bot_instance = TradingBot(db, agent_manager, bot_id=bot_id)
    return bot_instance
