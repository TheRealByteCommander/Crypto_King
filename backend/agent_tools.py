"""
Agent Tools - Functions that agents can call to access real data and execute actions
"""

import logging
from typing import Dict, Any, Optional
from binance_client import BinanceClientWrapper
from binance.exceptions import BinanceAPIException

logger = logging.getLogger(__name__)


class AgentTools:
    """Tools that agents can use to access real-time data and execute actions."""
    
    def __init__(self, bot=None, binance_client: Optional[BinanceClientWrapper] = None, db=None):
        """Initialize agent tools with bot, binance client, and database."""
        self.bot = bot
        self.binance_client = binance_client
        self.db = db
    
    def get_cyphermind_tools(self):
        """Get tools available for CypherMind agent (market data access)."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_current_price",
                    "description": "Get the current real-time price for a trading symbol (e.g., BTCUSDT, ETHUSDT). Returns the current market price in USDT.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "The trading symbol (e.g., BTCUSDT, ETHUSDT)"
                            }
                        },
                        "required": ["symbol"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_market_data",
                    "description": "Get historical kline (candlestick) data for technical analysis. Returns OHLCV data for the specified time period.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "The trading symbol (e.g., BTCUSDT)"
                            },
                            "interval": {
                                "type": "string",
                                "enum": ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"],
                                "description": "The kline interval (default: 5m)",
                                "default": "5m"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of klines to retrieve (default: 100, max: 1000)",
                                "default": 100,
                                "minimum": 1,
                                "maximum": 1000
                            }
                        },
                        "required": ["symbol"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_bot_status",
                    "description": "Get the current status of the trading bot, including running state, strategy, symbol, and configuration.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_recent_analyses",
                    "description": "Get recent market analyses to understand current market conditions and trends.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Number of recent analyses to retrieve (default: 5)",
                                "default": 5
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_tradable_symbols",
                    "description": "Get all tradable cryptocurrency symbols available on Binance (all trading types: SPOT, MARGIN, FUTURES, etc., and all quote assets: USDT, BUSD, BTC, ETH, BNB, etc.). Use this to check which coins/pairs are available for trading, including major cryptos, altcoins, and meme coins.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search": {
                                "type": "string",
                                "description": "Optional: Search filter to find symbols containing this text (e.g., 'DOGE', 'SHIB', 'BTC')"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "validate_symbol",
                    "description": "Validate if a trading symbol exists and is tradable on Binance. Use this before suggesting trades or answering questions about specific cryptocurrencies.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "The trading symbol to validate (e.g., BTCUSDT, DOGEUSDT, SHIBUSDT)"
                            }
                        },
                        "required": ["symbol"]
                    }
                }
            }
        ]
    
    def get_cyphertrade_tools(self):
        """Get tools available for CypherTrade agent (trade execution)."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_current_price",
                    "description": "Get the current real-time price for a trading symbol before executing an order.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "The trading symbol (e.g., BTCUSDT)"
                            }
                        },
                        "required": ["symbol"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_account_balance",
                    "description": "Get account balance for a specific asset (e.g., USDT, BTC) to check available funds before placing an order.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "asset": {
                                "type": "string",
                                "description": "The asset symbol (e.g., USDT, BTC)",
                                "default": "USDT"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_order",
                    "description": "Execute a trading order on Binance. Use this ONLY when explicitly instructed by CypherMind with a clear BUY/SELL signal.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "The trading symbol (e.g., BTCUSDT)"
                            },
                            "side": {
                                "type": "string",
                                "enum": ["BUY", "SELL"],
                                "description": "The order side: BUY or SELL"
                            },
                            "quantity": {
                                "type": "number",
                                "description": "The quantity to trade (e.g., 0.01 BTC)"
                            },
                            "order_type": {
                                "type": "string",
                                "enum": ["MARKET", "LIMIT"],
                                "description": "The order type (default: MARKET)",
                                "default": "MARKET"
                            }
                        },
                        "required": ["symbol", "side", "quantity"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_order_status",
                    "description": "Check the status of a previously placed order.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "The trading symbol"
                            },
                            "order_id": {
                                "type": "integer",
                                "description": "The order ID to check"
                            }
                        },
                        "required": ["symbol", "order_id"]
                    }
                }
            }
        ]
    
    def get_nexuschat_tools(self):
        """Get tools available for NexusChat agent (status and information)."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_bot_status",
                    "description": "Get the current status of the trading bot, including running state, strategy, symbol, and balances.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_price",
                    "description": "Get the current real-time price for a trading symbol to provide accurate information to the user.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "The trading symbol (e.g., BTCUSDT)"
                            }
                        },
                        "required": ["symbol"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_trade_history",
                    "description": "Get recent trade history to show the user past trading activity.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Number of recent trades to retrieve (default: 10)",
                                "default": 10
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_recent_analyses",
                    "description": "Get recent market analyses to explain current market conditions to the user.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Number of recent analyses to retrieve (default: 5)",
                                "default": 5
                            }
                        },
                        "required": []
                    }
                }
            }
        ]
    
    async def execute_tool(self, agent_name: str, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool function based on agent name and tool name."""
        try:
            if tool_name == "get_current_price":
                if self.binance_client is None:
                    return {"error": "Binance client not available", "success": False}
                symbol = parameters.get("symbol")
                if not symbol:
                    return {"error": "Symbol parameter is required", "success": False}
                price = self.binance_client.get_current_price(symbol)
                return {"success": True, "price": price, "symbol": symbol}
            
            elif tool_name == "get_market_data":
                if self.binance_client is None:
                    return {"error": "Binance client not available", "success": False}
                symbol = parameters.get("symbol")
                interval = parameters.get("interval", "5m")
                limit = parameters.get("limit", 100)
                if not symbol:
                    return {"error": "Symbol parameter is required", "success": False}
                df = self.binance_client.get_market_data(symbol, interval, limit)
                # Convert DataFrame to dict for JSON serialization
                result = {
                    "symbol": symbol,
                    "interval": interval,
                    "count": len(df),
                    "latest": {
                        "timestamp": df.iloc[-1]['timestamp'].isoformat() if hasattr(df.iloc[-1]['timestamp'], 'isoformat') else str(df.iloc[-1]['timestamp']),
                        "open": float(df.iloc[-1]['open']),
                        "high": float(df.iloc[-1]['high']),
                        "low": float(df.iloc[-1]['low']),
                        "close": float(df.iloc[-1]['close']),
                        "volume": float(df.iloc[-1]['volume'])
                    },
                    "data": df.tail(20).to_dict('records')  # Last 20 candles
                }
                return {"success": True, "result": result}
            
            elif tool_name == "get_account_balance":
                if self.binance_client is None:
                    return {"error": "Binance client not available", "success": False}
                asset = parameters.get("asset", "USDT")
                balance = self.binance_client.get_account_balance(asset)
                return {"success": True, "asset": asset, "balance": balance}
            
            elif tool_name == "execute_order":
                if self.binance_client is None:
                    return {"error": "Binance client not available", "success": False}
                if agent_name != "CypherTrade":
                    return {"error": "Only CypherTrade agent can execute orders", "success": False}
                symbol = parameters.get("symbol")
                side = parameters.get("side")
                quantity = parameters.get("quantity")
                order_type = parameters.get("order_type", "MARKET")
                if not all([symbol, side, quantity]):
                    return {"error": "Missing required parameters: symbol, side, quantity", "success": False}
                result = self.binance_client.execute_order(symbol, side, quantity, order_type)
                return {"success": True, "result": result}
            
            elif tool_name == "get_order_status":
                if self.binance_client is None:
                    return {"error": "Binance client not available", "success": False}
                symbol = parameters.get("symbol")
                order_id = parameters.get("order_id")
                if not all([symbol, order_id]):
                    return {"error": "Missing required parameters: symbol, order_id", "success": False}
                result = self.binance_client.get_order_status(symbol, order_id)
                return {"success": True, "result": result}
            
            elif tool_name == "get_bot_status":
                if self.bot is None:
                    return {"error": "Bot not available", "success": False}
                status = await self.bot.get_status()
                return {"success": True, "result": status}
            
            elif tool_name == "get_trade_history":
                if self.db is None:
                    return {"error": "Database not available", "success": False}
                limit = parameters.get("limit", 10)
                trades = await self.db.trades.find({}).sort("timestamp", -1).limit(limit).to_list(limit)
                # Convert ObjectId to string
                from bson import ObjectId
                for trade in trades:
                    if '_id' in trade and isinstance(trade['_id'], ObjectId):
                        trade['_id'] = str(trade['_id'])
                return {"success": True, "count": len(trades), "trades": trades}
            
            elif tool_name == "get_recent_analyses":
                if self.db is None:
                    return {"error": "Database not available", "success": False}
                limit = parameters.get("limit", 5)
                analyses = await self.db.analyses.find({}).sort("timestamp", -1).limit(limit).to_list(limit)
                # Convert ObjectId to string
                from bson import ObjectId
                for analysis in analyses:
                    if '_id' in analysis and isinstance(analysis['_id'], ObjectId):
                        analysis['_id'] = str(analysis['_id'])
                return {"success": True, "count": len(analyses), "analyses": analyses}
            
            elif tool_name == "get_tradable_symbols":
                if self.binance_client is None:
                    # Try to create a temporary client for this request
                    try:
                        temp_client = BinanceClientWrapper()
                        symbols = temp_client.get_tradable_symbols()
                        search = parameters.get("search", "").upper()
                        if search:
                            symbols = [s for s in symbols if search in s.get('symbol', '') or 
                                      search in s.get('baseAsset', '') or 
                                      search in s.get('quoteAsset', '') or
                                      search in s.get('type', '')]
                        return {"success": True, "count": len(symbols), "symbols": symbols}
                    except Exception as e:
                        return {"error": f"Binance client not available: {str(e)}", "success": False}
                search = parameters.get("search", "").upper()
                symbols = self.binance_client.get_tradable_symbols()
                if search:
                    symbols = [s for s in symbols if search in s.get('symbol', '') or 
                              search in s.get('baseAsset', '') or 
                              search in s.get('quoteAsset', '') or
                              search in s.get('type', '')]
                return {"success": True, "count": len(symbols), "symbols": symbols}
            
            elif tool_name == "validate_symbol":
                if self.binance_client is None:
                    # Try to create a temporary client for this request
                    try:
                        temp_client = BinanceClientWrapper()
                        symbol = parameters.get("symbol", "").upper()
                        is_tradable, error_msg = temp_client.is_symbol_tradable(symbol)
                        return {
                            "success": True,
                            "symbol": symbol,
                            "is_tradable": is_tradable,
                            "message": error_msg if not is_tradable else f"{symbol} is valid and tradable"
                        }
                    except Exception as e:
                        return {"error": f"Binance client not available: {str(e)}", "success": False}
                symbol = parameters.get("symbol", "").upper()
                is_tradable, error_msg = self.binance_client.is_symbol_tradable(symbol)
                return {
                    "success": True,
                    "symbol": symbol,
                    "is_tradable": is_tradable,
                    "message": error_msg if not is_tradable else f"{symbol} is valid and tradable"
                }
            
            else:
                return {"error": f"Unknown tool: {tool_name}", "success": False}
        
        except BinanceAPIException as e:
            logger.error(f"Binance API error in tool {tool_name}: {e}")
            return {"error": f"Binance API error: {str(e)}", "success": False}
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return {"error": f"Tool execution error: {str(e)}", "success": False}

