"""
Agent Tools - Functions that agents can call to access real data and execute actions
"""

import logging
from typing import Dict, Any, Optional, List
from binance_client import BinanceClientWrapper
from binance.exceptions import BinanceAPIException
from trading_pairs_cache import get_trading_pairs_cache

# Optional imports for news and coin analysis features
try:
    from crypto_news_fetcher import get_news_fetcher
    NEWS_FETCHER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"crypto_news_fetcher not available: {e}. News features will be disabled.")
    NEWS_FETCHER_AVAILABLE = False
    get_news_fetcher = None

try:
    from coin_analyzer import CoinAnalyzer
    COIN_ANALYZER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"coin_analyzer not available: {e}. Coin analysis features will be disabled.")
    COIN_ANALYZER_AVAILABLE = False
    CoinAnalyzer = None

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
                    "description": "Validate if a trading symbol exists and is tradable on Binance. Supports all quote assets (USDT, BTC, ETH, BUSD, BNB, etc.). Use this before suggesting trades or answering questions about specific cryptocurrencies.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "The trading symbol to validate (e.g., BTCUSDT, SOLBTC, ETHBTC, DOGEUSDT, SHIBUSDT)"
                            }
                        },
                        "required": ["symbol"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_available_trading_pairs",
                    "description": "Get all available trading pairs from cached data (updated every 2 hours). Supports filtering by base asset, quote asset, or search query. Use this to quickly check which trading pairs are available without making API calls.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "base_asset": {
                                "type": "string",
                                "description": "Optional: Filter by base asset (e.g., 'SOL' returns all SOL pairs: SOLUSDT, SOLBTC, SOLETH, etc.)"
                            },
                            "quote_asset": {
                                "type": "string",
                                "description": "Optional: Filter by quote asset (e.g., 'BTC' returns all BTC pairs: SOLBTC, ETHBTC, BNBBTC, etc.)"
                            },
                            "search": {
                                "type": "string",
                                "description": "Optional: Search query to find pairs containing this text (e.g., 'SOL', 'BTC')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 50, max: 200)",
                                "default": 50,
                                "minimum": 1,
                                "maximum": 200
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_optimal_coins",
                    "description": "Analyze multiple cryptocurrencies to find the best trading opportunities. Combines real-time prices, technical indicators, and news to calculate a profit potential score. Use this to identify optimal coins and strategies for maximum profit.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "max_coins": {
                                "type": "integer",
                                "description": "Maximum number of coins to analyze and return (default: 10, max: 20)",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 20
                            },
                            "min_score": {
                                "type": "number",
                                "description": "Minimum score threshold (0.0-1.0, default: 0.2). Only coins with score >= min_score are returned.",
                                "default": 0.2,
                                "minimum": 0.0,
                                "maximum": 1.0
                            },
                            "exclude_symbols": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "Optional: List of symbols to exclude from analysis (e.g., ['BTCUSDT', 'ETHUSDT'])"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "start_autonomous_bot",
                    "description": "Start an autonomous trading bot with automatic budget calculation. Budget is set to average budget of running bots, but maximum 40% of available capital. CypherMind can start maximum 2 autonomous bots. Each bot will learn from its trades.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Trading symbol (e.g., BTCUSDT, ETHUSDT)"
                            },
                            "strategy": {
                                "type": "string",
                                "enum": ["ma_crossover", "rsi", "macd", "bollinger_bands", "combined"],
                                "description": "Trading strategy to use"
                            },
                            "timeframe": {
                                "type": "string",
                                "enum": ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"],
                                "description": "Trading timeframe (default: 5m)",
                                "default": "5m"
                            },
                            "trading_mode": {
                                "type": "string",
                                "enum": ["SPOT", "MARGIN", "FUTURES"],
                                "description": "Trading mode (default: SPOT)",
                                "default": "SPOT"
                            }
                        },
                        "required": ["symbol", "strategy"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_autonomous_bots_status",
                    "description": "Get status of all autonomous bots started by CypherMind. Returns list of bots with their performance and learning progress.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
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
                    "description": "Execute a trading order on Binance. Use this ONLY when explicitly instructed by CypherMind with a clear BUY/SELL signal. CRITICAL: For SELL orders, quantity must be the amount of BASE ASSET to sell (e.g., 0.01 BTC), NOT the USDT value. Always validate quantity is positive and greater than 0 before executing.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "The trading symbol (e.g., BTCUSDT, SOLBTC, ETHUSDT)"
                            },
                            "side": {
                                "type": "string",
                                "enum": ["BUY", "SELL"],
                                "description": "The order side: BUY or SELL"
                            },
                            "quantity": {
                                "type": "number",
                                "description": "The quantity to trade in BASE ASSET (e.g., 0.01 BTC, 10 SOL). For SELL orders, this is the amount of base asset to sell. For BUY orders, this is the amount of base asset to buy. MUST be a positive number greater than 0.",
                                "minimum": 0.00000001
                            },
                            "order_type": {
                                "type": "string",
                                "enum": ["MARKET", "LIMIT"],
                                "description": "The order type (default: MARKET)",
                                "default": "MARKET"
                            },
                            "trading_mode": {
                                "type": "string",
                                "enum": ["SPOT", "MARGIN", "FUTURES"],
                                "description": "The trading mode (default: SPOT). Uses bot's configured trading mode if not specified.",
                                "default": "SPOT"
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
            },
            {
                "type": "function",
                "function": {
                    "name": "get_available_trading_pairs",
                    "description": "Get all available trading pairs from cached data (updated every 2 hours). Supports filtering by base asset, quote asset, or search query. Use this to quickly check which trading pairs are available for trade execution.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "base_asset": {
                                "type": "string",
                                "description": "Optional: Filter by base asset (e.g., 'SOL' returns all SOL pairs: SOLUSDT, SOLBTC, SOLETH, etc.)"
                            },
                            "quote_asset": {
                                "type": "string",
                                "description": "Optional: Filter by quote asset (e.g., 'BTC' returns all BTC pairs: SOLBTC, ETHBTC, BNBBTC, etc.)"
                            },
                            "search": {
                                "type": "string",
                                "description": "Optional: Search query to find pairs containing this text (e.g., 'SOL', 'BTC')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 50, max: 200)",
                                "default": 50,
                                "minimum": 1,
                                "maximum": 200
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
                    "description": "Validate if a trading symbol exists and is tradable on Binance. Supports all quote assets (USDT, BTC, ETH, BUSD, BNB, etc.). Use this before executing trades to ensure the symbol is valid.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "The trading symbol to validate (e.g., BTCUSDT, SOLBTC, ETHBTC, DOGEUSDT)"
                            }
                        },
                        "required": ["symbol"]
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
                    "name": "get_market_data",
                    "description": "Get historical kline (candlestick) data for any trading symbol. Returns OHLCV (Open, High, Low, Close, Volume) data for technical analysis and learning. Use this to analyze price trends, patterns, and historical performance. Supports all timeframes from 1 minute to 1 month.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "The trading symbol (e.g., BTCUSDT, ETHUSDT, SOLBTC)"
                            },
                            "interval": {
                                "type": "string",
                                "enum": ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"],
                                "description": "The kline interval (timeframe). Use '1d' for daily data, '1h' for hourly, '5m' for 5-minute candles, etc. (default: 5m)",
                                "default": "5m"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of historical candles to retrieve (default: 100, max: 1000). Use higher limits (e.g., 500-1000) for longer-term analysis.",
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
                    "name": "get_trade_history",
                    "description": "Get recent trade history to show the user past trading activity. This includes all executed trades with their P&L, entry/exit prices, and outcomes.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Number of recent trades to retrieve (default: 10, max: 100)",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 100
                            },
                            "symbol": {
                                "type": "string",
                                "description": "Optional: Filter trades by symbol (e.g., 'BTCUSDT', 'ETHUSDT')"
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
            },
            {
                "type": "function",
                "function": {
                    "name": "get_crypto_news",
                    "description": "Get recent cryptocurrency news from trusted sources (CoinDesk, CoinTelegraph, CryptoSlate, etc.). News is filtered for spam and fake content. Use this to provide users with current market news and trends.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of news articles to retrieve (default: 10, max: 20)",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 20
                            },
                            "symbols": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "Optional: Filter news for specific cryptocurrencies (e.g., ['BTC', 'ETH', 'SOL']). If not provided, returns general crypto news."
                            },
                            "query": {
                                "type": "string",
                                "description": "Optional: Search for news articles containing specific keywords (e.g., 'Bitcoin ETF', 'Ethereum upgrade')"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "share_news_with_agents",
                    "description": "Share important cryptocurrency news with CypherMind and CypherTrade agents. This allows them to consider market news in their trading decisions. Only share news that is relevant for trading (regulations, major events, market movements, etc.).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "articles": {
                                "type": "array",
                                "items": {
                                    "type": "object"
                                },
                                "description": "Array of news articles to share. Each article should have 'title', 'summary', 'link', and optionally 'symbols' (e.g., ['BTC', 'ETH'])."
                            },
                            "target_agents": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["CypherMind", "CypherTrade", "both"]
                                },
                                "description": "Which agents to share news with: 'CypherMind' (for trading decisions), 'CypherTrade' (for risk management), or 'both' (default).",
                                "default": ["both"]
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                                "description": "Priority level of the news (default: 'medium'). High priority news is shared immediately, medium/low can be batched.",
                                "default": "medium"
                            }
                        },
                        "required": ["articles"]
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
                # Convert timestamps to ISO format strings
                df_copy = df.copy()
                if 'timestamp' in df_copy.columns:
                    df_copy['timestamp'] = df_copy['timestamp'].apply(
                        lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x)
                    )
                
                result = {
                    "symbol": symbol,
                    "interval": interval,
                    "count": len(df),
                    "oldest": {
                        "timestamp": df.iloc[0]['timestamp'].isoformat() if hasattr(df.iloc[0]['timestamp'], 'isoformat') else str(df.iloc[0]['timestamp']),
                        "open": float(df.iloc[0]['open']),
                        "high": float(df.iloc[0]['high']),
                        "low": float(df.iloc[0]['low']),
                        "close": float(df.iloc[0]['close']),
                        "volume": float(df.iloc[0]['volume'])
                    },
                    "latest": {
                        "timestamp": df.iloc[-1]['timestamp'].isoformat() if hasattr(df.iloc[-1]['timestamp'], 'isoformat') else str(df.iloc[-1]['timestamp']),
                        "open": float(df.iloc[-1]['open']),
                        "high": float(df.iloc[-1]['high']),
                        "low": float(df.iloc[-1]['low']),
                        "close": float(df.iloc[-1]['close']),
                        "volume": float(df.iloc[-1]['volume'])
                    },
                    "data": df_copy.to_dict('records')  # All candles (up to limit)
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
                trading_mode = parameters.get("trading_mode", "SPOT")
                
                # Validate required parameters
                if not symbol or not side:
                    return {"error": "Missing required parameters: symbol and side are required", "success": False}
                
                if quantity is None or quantity <= 0:
                    return {"error": "Missing or invalid quantity parameter. Quantity must be a positive number.", "success": False}
                
                # Validate quantity is a number
                try:
                    quantity = float(quantity)
                    if quantity <= 0:
                        return {"error": "Quantity must be greater than 0", "success": False}
                except (ValueError, TypeError):
                    return {"error": f"Invalid quantity parameter: {quantity}. Must be a number.", "success": False}
                
                # Get trading mode from bot if available, otherwise use default
                if self.bot and hasattr(self.bot, 'current_config'):
                    trading_mode = self.bot.current_config.get("trading_mode", trading_mode)
                
                result = self.binance_client.execute_order(symbol, side, quantity, order_type, trading_mode)
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
                # Handle BotManager - get first running bot or default bot
                from bot_manager import BotManager
                if isinstance(self.bot, BotManager):
                    # Get first running bot, or default bot
                    running_bots = [b for b in self.bot.get_all_bots().values() if b.is_running]
                    if running_bots:
                        actual_bot = running_bots[0]
                    else:
                        actual_bot = self.bot.get_bot()
                    status = await actual_bot.get_status()
                else:
                    status = await self.bot.get_status()
                return {"success": True, "result": status}
            
            elif tool_name == "get_trade_history":
                if self.db is None:
                    return {"error": "Database not available", "success": False}
                limit = parameters.get("limit", 10)
                symbol = parameters.get("symbol", None)
                
                # Build query
                query = {}
                if symbol:
                    query["symbol"] = symbol.upper()
                
                trades = await self.db.trades.find(query).sort("timestamp", -1).limit(limit).to_list(limit)
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
                symbol = parameters.get("symbol", "").upper()
                
                # Try cache first (faster)
                if self.trading_pairs_cache:
                    try:
                        is_available = self.trading_pairs_cache.is_pair_available(symbol)
                        if is_available:
                            return {
                                "success": True,
                                "symbol": symbol,
                                "is_tradable": True,
                                "message": f"{symbol} is valid and tradable (from cache)"
                            }
                    except Exception as e:
                        logger.warning(f"Error checking cache for symbol {symbol}: {e}")
                
                # Fallback to direct API validation
                if self.binance_client is None:
                    # Try to create a temporary client for this request
                    try:
                        temp_client = BinanceClientWrapper()
                        is_tradable, error_msg = temp_client.is_symbol_tradable(symbol)
                        return {
                            "success": True,
                            "symbol": symbol,
                            "is_tradable": is_tradable,
                            "message": error_msg if not is_tradable else f"{symbol} is valid and tradable"
                        }
                    except Exception as e:
                        return {"error": f"Binance client not available: {str(e)}", "success": False}
                is_tradable, error_msg = self.binance_client.is_symbol_tradable(symbol)
                return {
                    "success": True,
                    "symbol": symbol,
                    "is_tradable": is_tradable,
                    "message": error_msg if not is_tradable else f"{symbol} is valid and tradable"
                }
            
            elif tool_name == "get_crypto_news":
                if not NEWS_FETCHER_AVAILABLE:
                    return {
                        "error": "News feature not available. Please install dependencies: pip install feedparser beautifulsoup4",
                        "success": False
                    }
                try:
                    news_fetcher = get_news_fetcher()
                    limit = parameters.get("limit", 10)
                    symbols = parameters.get("symbols", None)
                    query = parameters.get("query", None)
                    
                    # Validate limit
                    if limit < 1 or limit > 20:
                        limit = 10
                    
                    # Fetch news
                    if query:
                        articles = await news_fetcher.search_news(query, limit=limit)
                    else:
                        articles = await news_fetcher.fetch_news(
                            limit_per_source=5,
                            max_total=limit,
                            symbols=symbols
                        )
                    
                    return {
                        "success": True,
                        "count": len(articles),
                        "articles": articles
                    }
                except Exception as e:
                    logger.error(f"Error fetching crypto news: {e}", exc_info=True)
                    return {"error": f"Error fetching news: {str(e)}", "success": False}
            
            elif tool_name == "share_news_with_agents":
                try:
                    # This tool requires agent_manager to be available
                    agent_manager = None
                    
                    # Try to get agent_manager from bot
                    if self.bot:
                        # Check if bot has agent_manager (TradingBot)
                        if hasattr(self.bot, 'agent_manager'):
                            agent_manager = self.bot.agent_manager
                        # Check if bot is BotManager and has agent_manager
                        elif hasattr(self.bot, 'get_bot'):
                            from bot_manager import BotManager
                            if isinstance(self.bot, BotManager):
                                # Get first running bot or default bot
                                running_bots = [b for b in self.bot.get_all_bots().values() if b.is_running]
                                if running_bots:
                                    actual_bot = running_bots[0]
                                else:
                                    actual_bot = self.bot.get_bot()
                                if hasattr(actual_bot, 'agent_manager'):
                                    agent_manager = actual_bot.agent_manager
                    
                    if agent_manager is None:
                        return {"error": "Agent manager not available. News sharing requires active bot.", "success": False}
                    
                    articles = parameters.get("articles", [])
                    target_agents = parameters.get("target_agents", ["both"])
                    priority = parameters.get("priority", "medium")
                    
                    if not articles:
                        return {"error": "No articles provided", "success": False}
                    
                    # Share news with agents
                    result = await agent_manager.share_news_with_agents(
                        articles=articles,
                        target_agents=target_agents,
                        priority=priority
                    )
                    
                    return {
                        "success": True,
                        "shared_with": result.get("shared_with", []),
                        "count": len(articles),
                        "message": result.get("message", "News shared successfully")
                    }
                except Exception as e:
                    logger.error(f"Error sharing news with agents: {e}", exc_info=True)
                    return {"error": f"Error sharing news: {str(e)}", "success": False}
            
            elif tool_name == "analyze_optimal_coins":
                try:
                    if self.binance_client is None:
                        return {"error": "Binance client not available", "success": False}
                    
                    max_coins = parameters.get("max_coins", 10)
                    min_score = parameters.get("min_score", 0.2)
                    exclude_symbols = parameters.get("exclude_symbols", None)
                    
                    # Validate parameters
                    if max_coins < 1 or max_coins > 20:
                        max_coins = 10
                    if min_score < 0.0 or min_score > 1.0:
                        min_score = 0.2
                    
                    # Create analyzer
                    analyzer = CoinAnalyzer(self.binance_client)
                    
                    # Find optimal coins
                    results = await analyzer.find_optimal_coins(
                        min_score=min_score,
                        max_coins=max_coins,
                        exclude_symbols=exclude_symbols
                    )
                    
                    return {
                        "success": True,
                        "count": len(results),
                        "coins": results
                    }
                except Exception as e:
                    logger.error(f"Error analyzing optimal coins: {e}", exc_info=True)
                    return {"error": f"Error analyzing coins: {str(e)}", "success": False}
            
            elif tool_name == "start_autonomous_bot":
                try:
                    if agent_name != "CypherMind":
                        return {"error": "Only CypherMind can start autonomous bots", "success": False}
                    
                    if self.bot is None:
                        return {"error": "Bot manager not available", "success": False}
                    
                    from bot_manager import BotManager
                    if not isinstance(self.bot, BotManager):
                        return {"error": "Bot manager not available", "success": False}
                    
                    symbol = parameters.get("symbol", "").upper()
                    strategy = parameters.get("strategy", "combined")
                    timeframe = parameters.get("timeframe", "5m")
                    trading_mode = parameters.get("trading_mode", "SPOT")
                    
                    if not symbol:
                        return {"error": "Symbol is required", "success": False}
                    
                    # Check how many autonomous bots CypherMind has already started
                    all_bots = self.bot.get_all_bots()
                    cyphermind_bots = [
                        bot for bot in all_bots.values()
                        if bot.is_running and 
                        bot.current_config and
                        bot.current_config.get("started_by") == "CypherMind"
                    ]
                    
                    if len(cyphermind_bots) >= 2:
                        return {
                            "error": f"CypherMind has already started {len(cyphermind_bots)} autonomous bots (maximum: 2)",
                            "success": False
                        }
                    
                    # Calculate budget
                    # 1. Get average budget of running bots
                    running_bots = [b for b in all_bots.values() if b.is_running]
                    avg_budget = 100.0  # Default
                    if running_bots:
                        total_budget = sum(b.current_config.get("amount", 0) for b in running_bots if b.current_config)
                        avg_budget = total_budget / len(running_bots) if running_bots else 100.0
                    
                    # 2. Get available capital
                    if self.binance_client is None:
                        # Try to create temporary client
                        try:
                            temp_client = BinanceClientWrapper()
                            available_capital = temp_client.get_account_balance("USDT", trading_mode)
                        except:
                            available_capital = 1000.0  # Fallback
                    else:
                        available_capital = self.binance_client.get_account_balance("USDT", trading_mode)
                    
                    # 3. Calculate budget: min(avg_budget, 40% of available capital)
                    max_budget_from_capital = available_capital * 0.4
                    calculated_budget = min(avg_budget, max_budget_from_capital)
                    
                    # Ensure minimum budget
                    if calculated_budget < 10.0:
                        calculated_budget = 10.0
                    
                    # Create new bot
                    new_bot = self.bot.get_bot()
                    
                    # Mark as started by CypherMind
                    if new_bot.current_config is None:
                        new_bot.current_config = {}
                    new_bot.current_config["started_by"] = "CypherMind"
                    new_bot.current_config["autonomous"] = True
                    
                    # Start bot
                    result = await new_bot.start(strategy, symbol, calculated_budget, timeframe, trading_mode)
                    
                    if result.get("success"):
                        # Update config in database with autonomous flags
                        update_data = {
                            "started_by": "CypherMind",
                            "autonomous": True,
                            "calculated_budget": calculated_budget,
                            "avg_budget_of_running": avg_budget,
                            "available_capital_at_start": available_capital
                        }
                        # Merge with existing config
                        if new_bot.current_config:
                            update_data.update(new_bot.current_config)
                        
                        await self.db.bot_config.update_one(
                            {"bot_id": new_bot.bot_id},
                            {"$set": update_data}
                        )
                        
                        # Also update in-memory config
                        if new_bot.current_config:
                            new_bot.current_config.update(update_data)
                        
                        logger.info(f"CypherMind started autonomous bot: {new_bot.bot_id} for {symbol} with budget {calculated_budget} USDT")
                        
                        return {
                            "success": True,
                            "bot_id": new_bot.bot_id,
                            "symbol": symbol,
                            "strategy": strategy,
                            "budget": calculated_budget,
                            "message": f"Autonomous bot started successfully with budget {calculated_budget:.2f} USDT (avg: {avg_budget:.2f}, max 40%: {max_budget_from_capital:.2f})"
                        }
                    else:
                        return {
                            "success": False,
                            "error": result.get("message", "Failed to start bot")
                        }
                
                except Exception as e:
                    logger.error(f"Error starting autonomous bot: {e}", exc_info=True)
                    return {"error": f"Error starting bot: {str(e)}", "success": False}
            
            elif tool_name == "get_autonomous_bots_status":
                try:
                    if agent_name != "CypherMind":
                        return {"error": "Only CypherMind can check autonomous bots status", "success": False}
                    
                    if self.bot is None:
                        return {"error": "Bot manager not available", "success": False}
                    
                    from bot_manager import BotManager
                    if not isinstance(self.bot, BotManager):
                        return {"error": "Bot manager not available", "success": False}
                    
                    all_bots = self.bot.get_all_bots()
                    cyphermind_bots = []
                    
                    for bot_id, bot in all_bots.items():
                        if bot.current_config and bot.current_config.get("started_by") == "CypherMind":
                            status = await bot.get_status()
                            cyphermind_bots.append({
                                "bot_id": bot_id,
                                "status": status,
                                "is_running": bot.is_running
                            })
                    
                    return {
                        "success": True,
                        "count": len(cyphermind_bots),
                        "bots": cyphermind_bots
                    }
                
                except Exception as e:
                    logger.error(f"Error getting autonomous bots status: {e}", exc_info=True)
                    return {"error": f"Error getting status: {str(e)}", "success": False}
            
            else:
                return {"error": f"Unknown tool: {tool_name}", "success": False}
        
        except BinanceAPIException as e:
            logger.error(f"Binance API error in tool {tool_name}: {e}")
            return {"error": f"Binance API error: {str(e)}", "success": False}
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return {"error": f"Tool execution error: {str(e)}", "success": False}

