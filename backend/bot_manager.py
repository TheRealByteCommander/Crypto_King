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
    
    async def start(self, strategy: str, symbol: str, amount: float) -> Dict[str, Any]:
        """Start the trading bot with specified parameters."""
        try:
            if self.is_running:
                return {"success": False, "message": f"Bot {self.bot_id} is already running"}
            
            # Initialize Binance client (can be shared across bots)
            self.binance_client = BinanceClientWrapper()
            
            # Validate symbol before starting
            symbol_upper = symbol.upper()
            is_tradable, error_msg = self.binance_client.is_symbol_tradable(symbol_upper)
            if not is_tradable:
                return {
                    "success": False,
                    "message": error_msg or f"Symbol {symbol_upper} is not tradable on Binance"
                }
            
            # Store configuration (use validated uppercase symbol)
            self.current_config = {
                "bot_id": self.bot_id,
                "strategy": strategy,
                "symbol": symbol_upper,
                "amount": amount,
                "started_at": datetime.now(timezone.utc).isoformat()
            }
            
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
                # Step 1: Get market data
                logger.info(f"Bot {self.bot_id}: Fetching market data...")
                market_data = self.binance_client.get_market_data(symbol, interval="5m", limit=100)
                
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
    
    async def _execute_trade(self, analysis: Dict[str, Any]):
        """Execute a trade based on analysis."""
        try:
            signal = analysis.get("signal")
            symbol = self.current_config["symbol"]
            
            if signal == "BUY":
                # Buy with configured amount
                amount_usdt = self.current_config["amount"]
                
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
                balance = self.binance_client.get_account_balance("USDT")
                required_usdt = quantity * current_price
                if balance < required_usdt:
                    logger.warning(f"Bot {self.bot_id}: Insufficient USDT balance. Required: {required_usdt:.2f}, Available: {balance:.2f}")
                    return
                
                # Execute order
                order = self.binance_client.execute_order(symbol, "BUY", quantity)
                
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
                    "confidence": analysis.get("confidence", 0.0),
                    "indicators": analysis.get("indicators", {}),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await self.db.trades.insert_one(trade)
                
                logger.info(f"Bot {self.bot_id}: BUY order executed: {quantity} {symbol} at {current_price} USDT")
                await self.agent_manager.log_agent_message(
                    "CypherTrade",
                    f"BUY order executed: {quantity} {symbol} at {current_price} USDT (Order ID: {order.get('orderId')})",
                    "trade"
                )
            
            elif signal == "SELL":
                # Sell all available base asset
                base_asset = symbol.replace("USDT", "")
                balance = self.binance_client.get_account_balance(base_asset)
                
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
                    order = self.binance_client.execute_order(symbol, "SELL", quantity)
                    
                    # Save trade to database
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
                        "confidence": analysis.get("confidence", 0.0),
                        "indicators": analysis.get("indicators", {}),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    await self.db.trades.insert_one(trade)
                    
                    logger.info(f"Bot {self.bot_id}: SELL order executed: {quantity} {symbol} at {current_price} USDT")
                    await self.agent_manager.log_agent_message(
                        "CypherTrade",
                        f"SELL order executed: {quantity} {symbol} at {current_price} USDT (Order ID: {order.get('orderId')})",
                        "trade"
                    )
                else:
                    logger.warning(f"Bot {self.bot_id}: No {base_asset} balance available for SELL order")
        
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
            
            return {
                "bot_id": self.bot_id,
                "is_running": self.is_running,
                "config": config,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting bot status: {e}")
            return {
                "bot_id": self.bot_id,
                "is_running": False,
                "config": None,
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
