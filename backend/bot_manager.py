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
            
            # Store configuration
            self.current_config = {
                "strategy": strategy,
                "symbol": symbol,
                "amount": amount,
                "started_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Save to database
            await self.db.bot_config.insert_one(self.current_config)
            
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
                
                # Round to appropriate decimals
                quantity = round(quantity, QUANTITY_DECIMAL_PLACES)
                
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
                    quantity = round(balance, QUANTITY_DECIMAL_PLACES)
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