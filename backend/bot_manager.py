import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from bson import ObjectId
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
    
    def __init__(self, db, agent_manager):
        self.db = db
        self.agent_manager = agent_manager
        self.binance_client = None
        self.is_running = False
        self.current_config = None
        self.task = None
    
    async def start(self, strategy: str, symbol: str, amount: float) -> Dict[str, Any]:
        """Start the trading bot with specified parameters."""
        try:
            if self.is_running:
                return {"success": False, "message": "Bot is already running"}
            
            # Initialize Binance client
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
                "strategy": strategy,
                "symbol": symbol_upper,
                "amount": amount,
                "started_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Save to database
            await self.db.bot_config.insert_one(self.current_config)
            
            # Analyze historical market data before starting bot loop
            await self._analyze_historical_market_context(symbol_upper, strategy)
            
            self.is_running = True
            
            # Start bot loop in background
            self.task = asyncio.create_task(self._bot_loop())
            
            logger.info(f"Bot started with strategy: {strategy}, symbol: {symbol}, amount: {amount}")
            
            # Convert ObjectId to strings before returning
            clean_config = convert_objectid_to_str(self.current_config)
            
            return {
                "success": True,
                "message": f"Bot started successfully with {strategy} strategy",
                "config": clean_config
            }
        
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            return {"success": False, "message": str(e)}
    
    async def stop(self) -> Dict[str, Any]:
        """Stop the trading bot."""
        try:
            if not self.is_running:
                return {"success": False, "message": "Bot is not running"}
            
            self.is_running = False
            
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
            
            # Update database
            if self.current_config:
                self.current_config["stopped_at"] = datetime.now(timezone.utc).isoformat()
                await self.db.bot_config.update_one(
                    {"started_at": self.current_config["started_at"]},
                    {"$set": {"stopped_at": self.current_config["stopped_at"]}}
                )
            
            logger.info("Bot stopped")
            
            return {"success": True, "message": "Bot stopped successfully"}
        
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
            return {"success": False, "message": str(e)}
    
    async def _analyze_historical_market_context(self, symbol: str, strategy: str):
        """Analyze historical market data to provide context before bot starts trading."""
        try:
            logger.info(f"Analyzing historical market context for {symbol}...")
            
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
                metadata={"symbol": symbol, "strategy": strategy, "type": "startup_analysis"}
            )
            
            logger.info(f"Historical market analysis completed for {symbol}")
            
        except Exception as e:
            logger.error(f"Error analyzing historical market context: {e}", exc_info=True)
            await self.agent_manager.log_agent_message(
                "CypherMind",
                f"Warning: Could not complete historical market analysis: {str(e)}",
                "error"
            )
    
    async def _bot_loop(self):
        """Main bot loop that runs the trading strategy."""
        logger.info("Starting bot loop...")
        
        strategy_obj = get_strategy(self.current_config["strategy"])
        symbol = self.current_config["symbol"]
        
        while self.is_running:
            try:
                # Step 1: Get market data
                logger.info("Fetching market data...")
                market_data = self.binance_client.get_market_data(symbol, interval="5m", limit=100)
                
                # Step 2: Analyze with strategy
                logger.info("Analyzing market data...")
                analysis = strategy_obj.analyze(market_data)
                
                # Get current price for logging
                try:
                    current_price = self.binance_client.get_current_price(symbol)
                    price_info = f" | Current Price: {current_price} USDT"
                except Exception as e:
                    logger.warning(f"Could not get current price for logging: {e}")
                    # Try to get price from analysis if available
                    price_info = ""
                    if "indicators" in analysis and "current_price" in analysis["indicators"]:
                        price_info = f" | Current Price: {analysis['indicators']['current_price']} USDT"
                    elif "current_price" in analysis:
                        price_info = f" | Current Price: {analysis['current_price']} USDT"
                
                # Log analysis with current price
                await self.agent_manager.log_agent_message(
                    "CypherMind",
                    f"Analysis: {analysis['signal']} - {analysis['reason']}{price_info}",
                    "analysis"
                )
                
                # Save analysis to database
                await self.db.analyses.insert_one({
                    "symbol": symbol,
                    "strategy": self.current_config["strategy"],
                    "analysis": analysis,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                # Step 3: Execute trade if signal is not HOLD
                if analysis["signal"] in ["BUY", "SELL"]:
                    await self._execute_trade(analysis)
                
                # Wait for next iteration
                await asyncio.sleep(BOT_LOOP_INTERVAL_SECONDS)
            
            except asyncio.CancelledError:
                logger.info("Bot loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in bot loop: {e}")
                await asyncio.sleep(BOT_ERROR_RETRY_DELAY_SECONDS)
    
    async def _execute_trade(self, analysis: Dict[str, Any]):
        """Execute a trade based on analysis."""
        try:
            symbol = self.current_config["symbol"]
            signal = analysis["signal"]
            strategy = self.current_config.get("strategy", "unknown")
            
            # Check memory for insights before trading
            cyphermind_memory = self.agent_manager.memory_manager.get_agent_memory("CypherMind")
            pattern_insights = await cyphermind_memory.get_pattern_insights(symbol, strategy)
            
            # Log insights for decision making
            if pattern_insights.get("total_trades", 0) > 0:
                logger.info(f"Pattern insights for {symbol}/{strategy}: {pattern_insights.get('recommendation')}")
                await self.agent_manager.log_agent_message(
                    "CypherMind",
                    f"Historical performance: {pattern_insights.get('success_rate', 0):.1f}% success rate, "
                    f"Avg P&L: ${pattern_insights.get('avg_profit_per_trade', 0):.2f}",
                    "analysis"
                )
            
            # Get current price
            current_price = self.binance_client.get_current_price(symbol)
            
            # Calculate quantity
            if signal == "BUY":
                # Calculate how much to buy with available capital
                balance = self.binance_client.get_account_balance("USDT")
                amount_to_use = min(self.current_config["amount"], balance)
                quantity = amount_to_use / current_price
                
                # Adjust quantity to match Binance LOT_SIZE filter requirements
                quantity = self.binance_client.adjust_quantity_to_lot_size(symbol, quantity)
                
                # Adjust quantity to meet MIN_NOTIONAL filter requirements
                adjusted_quantity = self.binance_client.adjust_quantity_to_notional(symbol, quantity, current_price)
                if adjusted_quantity is None:
                    logger.warning(f"Cannot meet notional requirement for {symbol}. Order value too small.")
                    await self.agent_manager.log_agent_message(
                        "CypherTrade",
                        f"BUY order skipped: Order value too small to meet Binance minimum notional requirement for {symbol}",
                        "error"
                    )
                    return
                
                quantity = adjusted_quantity
                final_notional = quantity * current_price
                logger.info(f"Final order for {symbol}: {quantity} @ {current_price} = {final_notional:.2f} USDT")
                
                if quantity > 0:
                    logger.info(f"Executing BUY: {quantity} {symbol}")
                    order = self.binance_client.execute_order(symbol, "BUY", quantity)
                    
                    # Save trade to database
                    await self._save_trade(symbol, "BUY", quantity, order, analysis)
                    
                    await self.agent_manager.log_agent_message(
                        "CypherTrade",
                        f"BUY order executed: {quantity} {symbol} at {current_price}",
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
                    adjusted_quantity = self.binance_client.adjust_quantity_to_notional(symbol, quantity, current_price)
                    if adjusted_quantity is None:
                        logger.warning(f"Cannot meet notional requirement for {symbol}. Order value too small.")
                        await self.agent_manager.log_agent_message(
                            "CypherTrade",
                            f"SELL order skipped: Order value too small to meet Binance minimum notional requirement for {symbol}",
                            "error"
                        )
                        return
                    
                    quantity = adjusted_quantity
                    final_notional = quantity * current_price
                    logger.info(f"Final order for {symbol}: {quantity} @ {current_price} = {final_notional:.2f} USDT")
                    
                    logger.info(f"Executing SELL: {quantity} {symbol}")
                    order = self.binance_client.execute_order(symbol, "SELL", quantity)
                    
                    # Save trade to database
                    await self._save_trade(symbol, "SELL", quantity, order, analysis)
                    
                    # Calculate profit/loss for learning
                    await self._evaluate_and_learn_from_trade(symbol, "SELL", quantity, current_price)
                    
                    await self.agent_manager.log_agent_message(
                        "CypherTrade",
                        f"SELL order executed: {quantity} {symbol} at {current_price}",
                        "trade"
                    )
        
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            await self.agent_manager.log_agent_message(
                "CypherTrade",
                f"Trade execution error: {str(e)}",
                "error"
            )
    
    async def execute_manual_trade(self, symbol: str, side: str, quantity: float = None, amount_usdt: float = None) -> Dict[str, Any]:
        """Execute a manual trade order (can be called from API)."""
        try:
            # Ensure binance_client is available
            if self.binance_client is None:
                logger.warning(f"Binance client is None, creating new client (bot.is_running={self.is_running})")
                # Always create binance client if it's None, regardless of bot status
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
            logger.info(f"Executing manual {side} order: {quantity} {symbol}")
            order = self.binance_client.execute_order(symbol, side, quantity)
            
            # Create a minimal analysis dict for saving trade
            analysis = {
                "signal": side,
                "reason": f"Manual trade requested by user",
                "confidence": 1.0,
                "indicators": {"current_price": current_price}
            }
            
            # Save trade to database
            await self._save_trade(symbol, side, quantity, order, analysis)
            
            # Log the trade
            await self.agent_manager.log_agent_message(
                "CypherTrade",
                f"Manual {side} order executed: {quantity} {symbol} at {current_price} USDT",
                "trade"
            )
            
            # Calculate profit/loss for learning (only for SELL)
            if side == "SELL":
                await self._evaluate_and_learn_from_trade(symbol, "SELL", quantity, current_price)
            
            return {
                "success": True,
                "message": f"{side} order executed successfully",
                "order": order,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": current_price
            }
        
        except Exception as e:
            logger.error(f"Error executing manual trade: {e}", exc_info=True)
            await self.agent_manager.log_agent_message(
                "CypherTrade",
                f"Manual trade execution error: {str(e)}",
                "error"
            )
            return {"success": False, "message": f"Error executing trade: {str(e)}"}
    
    async def _save_trade(self, symbol: str, side: str, quantity: float, order: Dict[str, Any], analysis: Dict[str, Any] = None):
        """Save trade to database and update agent memory."""
        try:
            current_price = self.binance_client.get_current_price(symbol)
            
            trade = {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "order_id": order["orderId"],
                "status": order["status"],
                "executed_qty": order["executedQty"],
                "quote_qty": order["cummulativeQuoteQty"],
                "entry_price": current_price,
                "strategy": self.current_config.get("strategy", "unknown"),
                "confidence": analysis.get("confidence", 0.0) if analysis else 0.0,
                "indicators": analysis.get("indicators", {}) if analysis else {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self.db.trades.insert_one(trade)
            logger.info(f"Trade saved to database: {trade}")
            
            # Store trade in CypherTrade's memory for future reference
            cyphertrade_memory = self.agent_manager.memory_manager.get_agent_memory("CypherTrade")
            await cyphertrade_memory.store_memory(
                memory_type="trade_execution",
                content=trade,
                metadata={"side": side, "symbol": symbol}
            )
        
        except Exception as e:
            logger.error(f"Error saving trade: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current bot status."""
        try:
            # Convert ObjectId to strings before returning
            clean_config = convert_objectid_to_str(self.current_config) if self.current_config else None
            
            status = {
                "is_running": self.is_running,
                "config": clean_config,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            if self.is_running and self.binance_client:
                # Get account balances
                try:
                    usdt_balance = self.binance_client.get_account_balance("USDT")
                    symbol = self.current_config.get("symbol", "BTCUSDT") if self.current_config else "BTCUSDT"
                    base_asset = symbol.replace("USDT", "")
                    base_balance = self.binance_client.get_account_balance(base_asset)
                    
                    status["balances"] = {
                        "USDT": usdt_balance,
                        base_asset: base_balance
                    }
                except Exception as e:
                    logger.error(f"Error getting balances: {e}")
            
            return status
        
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"error": str(e)}
    
    async def _evaluate_and_learn_from_trade(self, symbol: str, side: str, quantity: float, exit_price: float):
        """Evaluate completed trade and learn from it."""
        try:
            # Find the corresponding BUY trade
            buy_trade = await self.db.trades.find_one({
                "symbol": symbol,
                "side": "BUY"
            }, sort=[("timestamp", -1)])
            
            if not buy_trade:
                logger.warning("No corresponding BUY trade found for learning")
                return
            
            entry_price = buy_trade.get("entry_price", 0)
            if entry_price == 0:
                return
            
            # Calculate profit/loss
            profit_loss = (exit_price - entry_price) * quantity
            profit_loss_pct = ((exit_price - entry_price) / entry_price) * 100
            
            # Determine outcome
            if profit_loss > 0:
                outcome = "success"
            elif profit_loss < -MIN_PROFIT_LOSS_THRESHOLD:
                outcome = "failure"
            else:
                outcome = "neutral"
            
            # Prepare trade data for learning
            trade_data = {
                "order_id": buy_trade.get("order_id"),
                "symbol": symbol,
                "side": side,
                "strategy": buy_trade.get("strategy", "unknown"),
                "entry_price": entry_price,
                "exit_price": exit_price,
                "confidence": buy_trade.get("confidence", 0.0),
                "indicators": buy_trade.get("indicators", {})
            }
            
            # Let CypherMind learn from this trade
            cyphermind_memory = self.agent_manager.memory_manager.get_agent_memory("CypherMind")
            await cyphermind_memory.learn_from_trade(trade_data, outcome, profit_loss)
            
            logger.info(f"Learned from trade: {outcome}, P&L: ${profit_loss:.2f} ({profit_loss_pct:.2f}%)")
            
            # Log the learning
            await self.agent_manager.log_agent_message(
                "CypherMind",
                f"Learning: {outcome} trade with {buy_trade.get('strategy')} - P&L: ${profit_loss:.2f}",
                "learning"
            )
        
        except Exception as e:
            logger.error(f"Error evaluating and learning from trade: {e}")
    
    async def get_report(self) -> Dict[str, Any]:
        """Generate performance report with learning insights."""
        try:
            # Get all trades
            trades = await self.db.trades.find({}).to_list(1000)
            
            # Calculate statistics
            total_trades = len(trades)
            buy_trades = [t for t in trades if t["side"] == "BUY"]
            sell_trades = [t for t in trades if t["side"] == "SELL"]
            
            total_bought = sum(float(t.get("quote_qty", 0)) for t in buy_trades)
            total_sold = sum(float(t.get("quote_qty", 0)) for t in sell_trades)
            
            profit_loss = total_sold - total_bought
            
            # Get learning insights from CypherMind
            cyphermind_memory = self.agent_manager.memory_manager.get_agent_memory("CypherMind")
            recent_lessons = await cyphermind_memory.get_recent_lessons(limit=5)
            
            # Get collective insights
            collective_insights = await self.agent_manager.memory_manager.get_collective_insights()
            
            report = {
                "total_trades": total_trades,
                "buy_trades": len(buy_trades),
                "sell_trades": len(sell_trades),
                "total_bought_usdt": round(total_bought, 2),
                "total_sold_usdt": round(total_sold, 2),
                "profit_loss_usdt": round(profit_loss, 2),
                "recent_lessons": recent_lessons,
                "agent_insights": collective_insights,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return report
        
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {"error": str(e)}

bot_instance: Optional[TradingBot] = None

def get_bot_instance(db, agent_manager) -> TradingBot:
    """Get or create bot instance."""
    global bot_instance
    if bot_instance is None:
        bot_instance = TradingBot(db, agent_manager)
    return bot_instance