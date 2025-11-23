import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from bson import ObjectId
import uuid
from binance_client import BinanceClientWrapper
from strategies import get_strategy
from config import settings
from constants import (
    BOT_LOOP_INTERVAL_SECONDS,
    BOT_ERROR_RETRY_DELAY_SECONDS,
    MIN_PROFIT_LOSS_THRESHOLD,
    QUANTITY_DECIMAL_PLACES
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
    
    async def start(self, strategy: str, symbol: str, amount: float, timeframe: str = "5m", trading_mode: str = "SPOT") -> Dict[str, Any]:
        """Start the trading bot with specified parameters."""
        try:
            if self.is_running:
                return {"success": False, "message": f"Bot {self.bot_id} is already running"}
            
            # Initialize Binance client (can be shared across bots)
            self.binance_client = BinanceClientWrapper()
            
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
            
            # Initialize position tracking - check if we already have a position in this symbol
            await self._update_position_from_balance(symbol_upper)
            
            # Save to database with bot_id
            await self.db.bot_config.insert_one(self.current_config)
            
            # Analyze historical market data before starting bot loop
            await self._analyze_historical_market_context(symbol_upper, strategy)
            
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
                
                # Step 2: Analyze with strategy
                logger.info(f"Bot {self.bot_id}: Analyzing market data...")
                analysis = strategy_obj.analyze(market_data)
                
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
                
                # Step 3: Log analysis to CypherMind
                signal = analysis.get("signal", "HOLD")
                confidence = analysis.get("confidence", 0.0)
                reason = analysis.get("reason", "No specific reason")
                
                log_message = f"Market Analysis for {symbol}: {signal} signal (Confidence: {confidence:.2f}){price_info}\nReason: {reason}"
                await self.agent_manager.log_agent_message("CypherMind", log_message, "analysis")
                
                # Step 4: Execute trade if signal is strong enough
                if signal in ["BUY", "SELL"] and confidence >= 0.6:
                    logger.info(f"Bot {self.bot_id}: Strong {signal} signal detected (confidence: {confidence:.2f}), executing trade...")
                    await self._execute_trade(analysis)
                else:
                    logger.info(f"Bot {self.bot_id}: Signal: {signal}, Confidence: {confidence:.2f} - No trade executed (confidence too low or HOLD signal)")
                
                # Step 5: Wait before next iteration
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
                base_asset = symbol.replace("USDT", "").replace("BUSD", "").replace("BTC", "").replace("ETH", "")
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
                
        except Exception as e:
            logger.warning(f"Bot {self.bot_id}: Could not update position from balance: {e}")
            self.position = None
            self.position_size = 0.0
            self.position_entry_price = 0.0
    
    async def _get_total_spent(self) -> float:
        """Calculate total amount spent (BUY trades) for this bot."""
        try:
            # Sum all BUY trades for this bot
            pipeline = [
                {"$match": {"bot_id": self.bot_id, "side": "BUY"}},
                {"$group": {"_id": None, "total": {"$sum": "$quote_qty"}}}
            ]
            result = await self.db.trades.aggregate(pipeline).to_list(length=1)
            if result and len(result) > 0:
                return float(result[0].get("total", 0.0))
            return 0.0
        except Exception as e:
            logger.warning(f"Bot {self.bot_id}: Error calculating total spent: {e}")
            return 0.0
    
    async def _execute_trade(self, analysis: Dict[str, Any]):
        """Execute a trade based on analysis."""
        try:
            signal = analysis.get("signal")
            symbol = self.current_config["symbol"]
            configured_amount = self.current_config["amount"]
            
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
                
                # Use available amount (not full configured amount)
                amount_usdt = min(available_amount, configured_amount)
                logger.info(f"Bot {self.bot_id}: Amount check - Total spent: {total_spent:.2f} USDT, Available: {amount_usdt:.2f} USDT, Limit: {configured_amount:.2f} USDT")
                
                # Get current price
                current_price = self.binance_client.get_current_price(symbol)
                
                # Calculate quantity
                quantity = amount_usdt / current_price
                
                # Adjust quantity to match Binance LOT_SIZE filter requirements
                quantity = self.binance_client.adjust_quantity_to_lot_size(symbol, quantity)
                
                # Adjust quantity to meet MIN_NOTIONAL filter requirements
                adjusted_quantity = self.binance_client.adjust_quantity_to_notional(symbol, quantity, current_price)
                if adjusted_quantity is None:
                    logger.warning(f"Bot {self.bot_id}: Order value too small for {symbol}, skipping trade")
                    return
                quantity = adjusted_quantity
                
                # Validate balance
                trading_mode = self.current_config.get("trading_mode", "SPOT")
                balance = self.binance_client.get_account_balance("USDT", trading_mode)
                required_usdt = quantity * current_price
                if balance < required_usdt:
                    logger.warning(f"Bot {self.bot_id}: Insufficient USDT balance ({trading_mode}). Required: {required_usdt:.2f}, Available: {balance:.2f}")
                    return
                
                # Execute order
                trading_mode = self.current_config.get("trading_mode", "SPOT")
                order = self.binance_client.execute_order(symbol, "BUY", quantity, "MARKET", trading_mode)
                
                # Save trade to database
                trade = {
                    "bot_id": self.bot_id,
                    "symbol": symbol,
                    "side": "BUY",
                    "quantity": quantity,
                    "order_id": str(order.get("orderId", "")),
                    "status": order.get("status", ""),
                    "executed_qty": float(order.get("executedQty", 0)),
                    "quote_qty": float(order.get("cummulativeQuoteQty", 0)),
                    "entry_price": current_price,
                    "strategy": self.current_config["strategy"],
                    "trading_mode": trading_mode,
                    "confidence": analysis.get("confidence", 0.0),
                    "indicators": analysis.get("indicators", {}),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await self.db.trades.insert_one(trade)
                
                # Check total spent after trade
                total_spent_after = await self._get_total_spent()
                remaining = configured_amount - total_spent_after
                logger.info(f"Bot {self.bot_id}: BUY order executed: {quantity} {symbol} at {current_price} USDT | Total spent: {total_spent_after:.2f}/{configured_amount:.2f} USDT (Remaining: {remaining:.2f} USDT)")
                await self.agent_manager.log_agent_message(
                    "CypherTrade",
                    f"BUY order executed: {quantity} {symbol} at {current_price} USDT | Total spent: {total_spent_after:.2f}/{configured_amount:.2f} USDT (Remaining: {remaining:.2f} USDT) (Order ID: {order.get('orderId')})",
                    "trade"
                )
                
                # Update position tracking
                if self.position == "LONG":
                    # Add to existing position
                    self.position_size += quantity
                    # Update entry price (weighted average)
                    total_value = (self.position_size - quantity) * self.position_entry_price + quantity * current_price
                    self.position_entry_price = total_value / self.position_size if self.position_size > 0 else current_price
                else:
                    # Open new LONG position
                    self.position = "LONG"
                    self.position_size = quantity
                    self.position_entry_price = current_price
            
            elif signal == "SELL":
                # Update position status before executing SELL
                trading_mode = self.current_config.get("trading_mode", "SPOT")
                await self._update_position_from_balance(symbol, trading_mode)
                
                base_asset = symbol.replace("USDT", "").replace("BUSD", "").replace("BTC", "").replace("ETH", "")
                
                # Check current position
                if self.position == "LONG":
                    # We have a LONG position - close it
                    base_asset = symbol.replace("USDT", "").replace("BUSD", "").replace("BTC", "").replace("ETH", "")
                    balance = self.binance_client.get_account_balance(base_asset, trading_mode)
                    
                    if balance > 0:
                        # Adjust quantity to match Binance LOT_SIZE filter requirements
                        quantity = self.binance_client.adjust_quantity_to_lot_size(symbol, balance)
                        
                        # Adjust quantity to meet MIN_NOTIONAL filter requirements
                        current_price = self.binance_client.get_current_price(symbol)
                        adjusted_quantity = self.binance_client.adjust_quantity_to_notional(symbol, quantity, current_price)
                        if adjusted_quantity is None:
                            logger.warning(f"Bot {self.bot_id}: Order value too small for {symbol}, skipping trade")
                            return
                        quantity = adjusted_quantity
                        
                        # Execute order
                        order = self.binance_client.execute_order(symbol, "SELL", quantity, "MARKET", trading_mode)
                        
                        # Calculate profit/loss
                        pnl = None
                        pnl_percent = None
                        if self.position_entry_price > 0:
                            pnl = (current_price - self.position_entry_price) * quantity
                            pnl_percent = ((current_price - self.position_entry_price) / self.position_entry_price) * 100
                        
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
                            "entry_price": current_price,
                            "strategy": self.current_config["strategy"],
                            "trading_mode": trading_mode,
                            "confidence": analysis.get("confidence", 0.0),
                            "indicators": analysis.get("indicators", {}),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        if pnl is not None:
                            trade["pnl"] = pnl
                            trade["pnl_percent"] = pnl_percent
                            trade["position_entry_price"] = self.position_entry_price
                        
                        await self.db.trades.insert_one(trade)
                        
                        # Position closed
                        self.position = None
                        self.position_size = 0.0
                        self.position_entry_price = 0.0
                        
                        pnl_msg = f" | P/L: {pnl:+.2f} USDT ({pnl_percent:+.2f}%)" if pnl is not None else ""
                        logger.info(f"Bot {self.bot_id}: SELL order executed: {quantity} {symbol} at {current_price} USDT (LONG position closed{pnl_msg})")
                        await self.agent_manager.log_agent_message(
                            "CypherTrade",
                            f"SELL order executed: {quantity} {symbol} at {current_price} USDT (LONG position closed{pnl_msg}) (Order ID: {order.get('orderId')})",
                            "trade"
                        )
                
                elif self.position == "SHORT":
                    # We have a SHORT position - close it by buying
                    current_price = self.binance_client.get_current_price(symbol)
                    amount_usdt = self.current_config["amount"]
                    
                    # Calculate quantity to buy to close short
                    quantity = amount_usdt / current_price
                    quantity = self.binance_client.adjust_quantity_to_lot_size(symbol, quantity)
                    adjusted_quantity = self.binance_client.adjust_quantity_to_notional(symbol, quantity, current_price)
                    if adjusted_quantity is None:
                        logger.warning(f"Bot {self.bot_id}: Order value too small for {symbol}, skipping trade")
                        return
                    quantity = adjusted_quantity
                    
                    # Execute BUY order to close SHORT
                    order = self.binance_client.execute_order(symbol, "BUY", quantity, "MARKET", trading_mode)
                    
                    # Calculate profit/loss (for SHORT: profit when price goes down)
                    pnl = None
                    pnl_percent = None
                    if self.position_entry_price > 0:
                        pnl = (self.position_entry_price - current_price) * quantity
                        pnl_percent = ((self.position_entry_price - current_price) / self.position_entry_price) * 100
                    
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
                        "entry_price": current_price,
                        "strategy": self.current_config["strategy"],
                        "trading_mode": trading_mode,
                        "position_type": "SHORT_CLOSE",
                        "confidence": analysis.get("confidence", 0.0),
                        "indicators": analysis.get("indicators", {}),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    if pnl is not None:
                        trade["pnl"] = pnl
                        trade["pnl_percent"] = pnl_percent
                        trade["position_entry_price"] = self.position_entry_price
                    
                    await self.db.trades.insert_one(trade)
                    
                    # SHORT position closed
                    self.position = None
                    self.position_size = 0.0
                    self.position_entry_price = 0.0
                    
                    pnl_msg = f" | P/L: {pnl:+.2f} USDT ({pnl_percent:+.2f}%)" if pnl is not None else ""
                    logger.info(f"Bot {self.bot_id}: BUY order executed to close SHORT: {quantity} {symbol} at {current_price} USDT{pnl_msg}")
                    await self.agent_manager.log_agent_message(
                        "CypherTrade",
                        f"BUY order executed to close SHORT: {quantity} {symbol} at {current_price} USDT{pnl_msg} (Order ID: {order.get('orderId')})",
                        "trade"
                    )
                
                else:
                    # No position - check if we can open a SHORT position
                    if trading_mode in ["MARGIN", "FUTURES"]:
                        # Open SHORT position
                        amount_usdt = self.current_config["amount"]
                        current_price = self.binance_client.get_current_price(symbol)
                        
                        # Calculate quantity
                        quantity = amount_usdt / current_price
                        quantity = self.binance_client.adjust_quantity_to_lot_size(symbol, quantity)
                        adjusted_quantity = self.binance_client.adjust_quantity_to_notional(symbol, quantity, current_price)
                        if adjusted_quantity is None:
                            logger.warning(f"Bot {self.bot_id}: Order value too small for {symbol}, skipping trade")
                            return
                        quantity = adjusted_quantity
                        
                        # Execute SELL order to open SHORT (for Margin/Futures)
                        order = self.binance_client.execute_order(symbol, "SELL", quantity, "MARKET", trading_mode)
                        
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
                            "entry_price": current_price,
                            "strategy": self.current_config["strategy"],
                            "trading_mode": trading_mode,
                            "position_type": "SHORT_OPEN",
                            "confidence": analysis.get("confidence", 0.0),
                            "indicators": analysis.get("indicators", {}),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        await self.db.trades.insert_one(trade)
                        
                        # Update position tracking - SHORT position opened
                        self.position = "SHORT"
                        self.position_size = quantity
                        self.position_entry_price = current_price
                        
                        logger.info(f"Bot {self.bot_id}: SELL order executed to open SHORT: {quantity} {symbol} at {current_price} USDT ({trading_mode})")
                        await self.agent_manager.log_agent_message(
                            "CypherTrade",
                            f"SELL order executed to open SHORT position: {quantity} {symbol} at {current_price} USDT ({trading_mode}) (Order ID: {order.get('orderId')})",
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
            
            # Calculate quantity if not provided
            if quantity is None:
                if amount_usdt is None:
                    return {"success": False, "message": "Either quantity or amount_usdt must be provided"}
                
                if side == "BUY":
                    # Calculate quantity from amount in USDT
                    balance = self.binance_client.get_account_balance("USDT")
                    amount_to_use = min(amount_usdt, balance)
                    quantity = amount_to_use / current_price
                elif side == "SELL":
                    # Use amount_usdt as quantity for SELL (if provided)
                    # Otherwise, sell all available base asset
                    base_asset = symbol.replace("USDT", "")
                    balance = self.binance_client.get_account_balance(base_asset)
                    quantity = min(amount_usdt, balance) if amount_usdt else balance
            
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
            if side == "BUY":
                balance = self.binance_client.get_account_balance("USDT")
                required_usdt = quantity * current_price
                if balance < required_usdt:
                    return {"success": False, "message": f"Insufficient USDT balance. Required: {required_usdt:.2f}, Available: {balance:.2f}"}
            elif side == "SELL":
                base_asset = symbol.replace("USDT", "")
                balance = self.binance_client.get_account_balance(base_asset)
                if balance < quantity:
                    return {"success": False, "message": f"Insufficient {base_asset} balance. Required: {quantity}, Available: {balance}"}
            
            # Execute order
            order = self.binance_client.execute_order(symbol, side, quantity)
            
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
                await self._update_position_from_balance(self.current_config["symbol"])
            
            # Get current price if we have a position
            current_price = None
            unrealized_pnl = None
            unrealized_pnl_percent = None
            if self.position and self.binance_client and self.current_config:
                try:
                    current_price = self.binance_client.get_current_price(self.current_config["symbol"])
                    if self.position_entry_price > 0 and current_price:
                        if self.position == "LONG":
                            unrealized_pnl = (current_price - self.position_entry_price) * self.position_size
                            unrealized_pnl_percent = ((current_price - self.position_entry_price) / self.position_entry_price) * 100
                        elif self.position == "SHORT":
                            unrealized_pnl = (self.position_entry_price - current_price) * self.position_size
                            unrealized_pnl_percent = ((self.position_entry_price - current_price) / self.position_entry_price) * 100
                except Exception as e:
                    logger.warning(f"Could not get current price for status: {e}")
            
            status = {
                "bot_id": self.bot_id,
                "is_running": self.is_running,
                "config": config,
                "position": {
                    "type": self.position,  # "LONG", "SHORT", or None
                    "size": self.position_size,
                    "entry_price": self.position_entry_price,
                    "current_price": current_price,
                    "unrealized_pnl": unrealized_pnl,
                    "unrealized_pnl_percent": unrealized_pnl_percent
                },
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
