"""
Agent Tools - Functions that agents can call to access real data and execute actions
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from binance_client import BinanceClientWrapper
from binance.exceptions import BinanceAPIException
from trading_pairs_cache import get_trading_pairs_cache
from constants import TAKE_PROFIT_MIN_PERCENT, STOP_LOSS_PERCENT
import httpx

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
                                "description": "Maximum number of coins to analyze and return (default: 20, max: 50)",
                                "default": 20,
                                "minimum": 1,
                                "maximum": 50
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
                    "description": "Start an autonomous trading bot with automatic budget calculation. Budget is set to average budget of running bots, but maximum 40% of available capital. CypherMind can start maximum 6 autonomous bots (KEY-FEATURE). Each bot will learn from its trades. Bots are automatically stopped after 24h if performance is insufficient (< 0% P&L).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Trading symbol (e.g., BTCUSDT, ETHUSDT)"
                            },
                            "strategy": {
                                "type": "string",
                                "enum": ["ma_crossover", "rsi", "macd", "bollinger_bands", "combined", "grid"],
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
            },
            {
                "type": "function",
                "function": {
                    "name": "get_bot_candles",
                    "description": "Get tracked candle data for a bot. Returns the last 200 candles before trades (pre_trade) or 200 candles after sales (post_trade). Use this to analyze patterns and improve predictions.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "bot_id": {
                                "type": "string",
                                "description": "Bot ID to get candles for"
                            },
                            "phase": {
                                "type": "string",
                                "enum": ["pre_trade", "post_trade", "during_trade", "all"],
                                "description": "Which phase to get candles from: 'pre_trade' (200 candles before trades), 'during_trade' (all candles while position is open), 'post_trade' (200 candles after sales), or 'all' (default: 'pre_trade')",
                                "default": "pre_trade"
                            }
                        },
                        "required": ["bot_id"]
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
                    "description": "Execute a trading order on Binance. Use this ONLY when explicitly instructed by CypherMind with a clear BUY/SELL signal. CRITICAL: For SELL orders, quantity must be the amount of BASE ASSET to sell (e.g., 0.01 BTC), NOT the USDT value. Always validate quantity is positive and greater than 0 before executing. REQUIRED: Before executing SELL orders, ALWAYS call get_current_price() first to check current market price vs entry price. SELL orders that would result in losses (current price < entry price) are automatically blocked to prevent negative trades.",
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
                symbol = parameters.get("symbol")
                if not symbol:
                    return {"error": "Symbol parameter is required", "success": False}
                
                # PRÜFE ZUERST DEN PERMANENTEN KURS-CACHE (alle 30 Sekunden aktualisiert)
                # Dies ist besonders effizient für CypherTrade, da die Kurse permanent verfügbar sind
                if self.bot:
                    # Prüfe ob bot ein BotManager ist (hat price_cache)
                    from bot_manager import BotManager
                    if isinstance(self.bot, BotManager):
                        cached_price = self.bot.get_current_price_for_symbol(symbol)
                        if cached_price is not None:
                            logger.debug(f"get_current_price: Using cached price for {symbol}: {cached_price}")
                            return {
                                "success": True,
                                "price": cached_price,
                                "symbol": symbol,
                                "source": "cache",
                                "note": "Price from permanent update loop (updated every 30 seconds)"
                            }
                    # Prüfe ob bot ein TradingBot ist und Zugriff auf BotManager hat
                    elif hasattr(self.bot, 'agent_manager') and hasattr(self.bot.agent_manager, 'bot'):
                        bot_manager = self.bot.agent_manager.bot
                        if isinstance(bot_manager, BotManager):
                            cached_price = bot_manager.get_current_price_for_symbol(symbol)
                            if cached_price is not None:
                                logger.debug(f"get_current_price: Using cached price for {symbol}: {cached_price}")
                                return {
                                    "success": True,
                                    "price": cached_price,
                                    "symbol": symbol,
                                    "source": "cache",
                                    "note": "Price from permanent update loop (updated every 30 seconds)"
                                }
                
                # Fallback: Direkter Binance-Abruf wenn Cache nicht verfügbar
                if self.binance_client is None:
                    return {"error": "Binance client not available", "success": False}
                price = self.binance_client.get_current_price(symbol)
                return {
                    "success": True,
                    "price": price,
                    "symbol": symbol,
                    "source": "binance",
                    "note": "Price fetched directly from Binance (cache not available)"
                }
            
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
                
                # CRITICAL: Before executing SELL orders, ALWAYS check current price, profit limits, and holding period
                if side == "SELL":
                    try:
                        # Get current price
                        current_price = self.binance_client.get_current_price(symbol)
                        
                        if current_price is None or current_price <= 0:
                            error_msg = f"⚠️ SELL order BLOCKED: Cannot get valid current price for {symbol}. Cannot execute SELL without price validation."
                            logger.warning(f"Agent execute_order: {error_msg}")
                            return {
                                "error": error_msg,
                                "success": False
                            }
                        
                        # Check if we have position tracking data
                        if self.bot and hasattr(self.bot, 'position_entry_price') and hasattr(self.bot, 'position'):
                            if self.bot.position == "LONG" and self.bot.position_entry_price > 0:
                                # Calculate P&L percentage
                                pnl_percent = ((current_price - self.bot.position_entry_price) / self.bot.position_entry_price) * 100
                                
                                # CRITICAL: Check if selling would result in a loss (Stop-Loss exception)
                                if current_price < self.bot.position_entry_price:
                                    # Only allow if it's a stop-loss situation (≤ -5%)
                                    if pnl_percent > STOP_LOSS_PERCENT:
                                        error_msg = (
                                            f"⚠️ SELL order BLOCKED: Current price {current_price} is below entry price "
                                            f"{self.bot.position_entry_price} ({pnl_percent:.2f}% loss). "
                                            f"This would result in a negative trade. Only Stop-Loss (≤{STOP_LOSS_PERCENT}%) is allowed."
                                        )
                                        logger.warning(f"Agent execute_order: {error_msg}")
                                        return {
                                            "error": error_msg,
                                            "success": False,
                                            "current_price": current_price,
                                            "entry_price": self.bot.position_entry_price,
                                            "potential_loss_percent": pnl_percent
                                        }
                                    else:
                                        # Stop-Loss situation - allow trade
                                        logger.warning(
                                            f"Agent execute_order: SELL allowed for Stop-Loss - "
                                            f"Current price {current_price} < Entry price {self.bot.position_entry_price} "
                                            f"({pnl_percent:.2f}% loss, Stop-Loss threshold: {STOP_LOSS_PERCENT}%)"
                                        )
                                
                                # CRITICAL: Validate minimum profit requirement (2% minimum) - unless it's Stop-Loss
                                elif pnl_percent < TAKE_PROFIT_MIN_PERCENT:
                                    error_msg = (
                                        f"⚠️ SELL order BLOCKED: Current profit {pnl_percent:.2f}% is below minimum required "
                                        f"{TAKE_PROFIT_MIN_PERCENT}%. Entry: {self.bot.position_entry_price}, Current: {current_price}. "
                                        f"Position must remain open until minimum profit target is reached."
                                    )
                                    logger.warning(f"Agent execute_order: {error_msg}")
                                    return {
                                        "error": error_msg,
                                        "success": False,
                                        "current_price": current_price,
                                        "entry_price": self.bot.position_entry_price,
                                        "current_profit_percent": pnl_percent,
                                        "minimum_required_profit": TAKE_PROFIT_MIN_PERCENT
                                    }
                                
                                # CRITICAL: Check minimum holding period (15 minutes)
                                if hasattr(self.bot, 'position_entry_time') and self.bot.position_entry_time:
                                    holding_duration = datetime.now(timezone.utc) - self.bot.position_entry_time
                                    min_holding_minutes = 15
                                    if holding_duration.total_seconds() < (min_holding_minutes * 60):
                                        remaining_seconds = (min_holding_minutes * 60) - holding_duration.total_seconds()
                                        remaining_minutes = int(remaining_seconds / 60)
                                        error_msg = (
                                            f"⚠️ SELL order BLOCKED: Minimum holding period not met. "
                                            f"Position held for {holding_duration.total_seconds()/60:.1f} minutes, "
                                            f"minimum required: {min_holding_minutes} minutes. "
                                            f"Remaining: {remaining_minutes} minutes. "
                                            f"(Exception: Stop-Loss at ≤{STOP_LOSS_PERCENT}% is always allowed)"
                                        )
                                        # Only block if it's not a Stop-Loss situation
                                        if pnl_percent > STOP_LOSS_PERCENT:
                                            logger.warning(f"Agent execute_order: {error_msg}")
                                            return {
                                                "error": error_msg,
                                                "success": False,
                                                "holding_duration_minutes": holding_duration.total_seconds() / 60,
                                                "minimum_required_minutes": min_holding_minutes,
                                                "current_profit_percent": pnl_percent
                                            }
                                
                                # All validations passed
                                logger.info(
                                    f"Agent execute_order: SELL validated - Current price {current_price} >= "
                                    f"Entry price {self.bot.position_entry_price} ({pnl_percent:.2f}% profit). "
                                    f"Minimum profit requirement ({TAKE_PROFIT_MIN_PERCENT}%) met."
                                )
                            elif self.bot.position == "SHORT" and self.bot.position_entry_price > 0:
                                # For SHORT positions: profit when price falls
                                pnl_percent = ((self.bot.position_entry_price - current_price) / self.bot.position_entry_price) * 100
                                
                                # Check Stop-Loss (for SHORT: loss when price rises)
                                if current_price > self.bot.position_entry_price:
                                    if pnl_percent > STOP_LOSS_PERCENT:
                                        error_msg = (
                                            f"⚠️ BUY to close SHORT order BLOCKED: Current price {current_price} is above entry price "
                                            f"{self.bot.position_entry_price} ({pnl_percent:.2f}% loss for SHORT). "
                                            f"Only Stop-Loss (≤{STOP_LOSS_PERCENT}%) is allowed."
                                        )
                                        logger.warning(f"Agent execute_order: {error_msg}")
                                        return {
                                            "error": error_msg,
                                            "success": False,
                                            "current_price": current_price,
                                            "entry_price": self.bot.position_entry_price,
                                            "potential_loss_percent": pnl_percent
                                        }
                                
                                # Validate minimum profit requirement for SHORT
                                elif pnl_percent < TAKE_PROFIT_MIN_PERCENT:
                                    error_msg = (
                                        f"⚠️ BUY to close SHORT order BLOCKED: Current profit {pnl_percent:.2f}% is below minimum required "
                                        f"{TAKE_PROFIT_MIN_PERCENT}%. Entry: {self.bot.position_entry_price}, Current: {current_price}. "
                                        f"Position must remain open until minimum profit target is reached."
                                    )
                                    logger.warning(f"Agent execute_order: {error_msg}")
                                    return {
                                        "error": error_msg,
                                        "success": False,
                                        "current_price": current_price,
                                        "entry_price": self.bot.position_entry_price,
                                        "current_profit_percent": pnl_percent,
                                        "minimum_required_profit": TAKE_PROFIT_MIN_PERCENT
                                    }
                                
                                logger.info(
                                    f"Agent execute_order: BUY to close SHORT validated - "
                                    f"Current price {current_price}, Entry price {self.bot.position_entry_price} "
                                    f"({pnl_percent:.2f}% profit). Minimum profit requirement ({TAKE_PROFIT_MIN_PERCENT}%) met."
                                )
                        else:
                            # No position tracking - log warning but allow trade (agents might be managing multiple bots)
                            logger.warning(
                                f"Agent execute_order: SELL order for {symbol} - No position tracking data available. "
                                f"Current price: {current_price}. Proceeding with caution. "
                                f"WARNING: Profit and holding period limits cannot be validated without position tracking!"
                            )
                    except Exception as e:
                        logger.error(f"Error validating current price before SELL order: {e}", exc_info=True)
                        return {
                            "error": f"Failed to validate current price before SELL order: {str(e)}. Cannot execute SELL without price validation.",
                            "success": False
                        }
                
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
                # Convert ObjectId to string and ensure USDT values are properly calculated
                from bson import ObjectId
                formatted_trades = []
                for trade in trades:
                    if '_id' in trade and isinstance(trade['_id'], ObjectId):
                        trade['_id'] = str(trade['_id'])
                    
                    # Ensure quote_qty (USDT value) is properly set
                    quote_qty = trade.get('quote_qty', 0)
                    execution_price = trade.get('execution_price') or trade.get('entry_price')
                    quantity = trade.get('quantity', 0)
                    
                    # If quote_qty is 0 or missing, calculate it from execution_price * quantity
                    if (not quote_qty or quote_qty == 0) and execution_price and execution_price > 0 and quantity > 0:
                        quote_qty = execution_price * quantity
                        trade['quote_qty'] = quote_qty
                        trade['quote_qty_calculated'] = True  # Flag to indicate it was calculated
                    
                    # Add formatted USDT value for easier display
                    trade['value_usdt'] = quote_qty
                    
                    formatted_trades.append(trade)
                
                return {"success": True, "count": len(formatted_trades), "trades": formatted_trades}
            
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
            
            elif tool_name == "search_trading_information":
                # Web search for trading information
                query = parameters.get("query", "")
                max_results = parameters.get("max_results", 5)
                
                if not query:
                    return {"error": "Search query is required", "success": False}
                
                try:
                    # Use DuckDuckGo Instant Answer API (free, no API key required)
                    # Fallback to a simple web search approach
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        # Try DuckDuckGo HTML search (simple approach)
                        search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        }
                        
                        response = await client.get(search_url, headers=headers, follow_redirects=True)
                        response.raise_for_status()
                        
                        # Parse HTML results (simple extraction)
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        results = []
                        # Extract search results (DuckDuckGo HTML structure)
                        result_divs = soup.find_all('div', class_='result')[:max_results]
                        
                        for div in result_divs:
                            title_elem = div.find('a', class_='result__a')
                            snippet_elem = div.find('a', class_='result__snippet')
                            
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                                url = title_elem.get('href', '')
                                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                                
                                results.append({
                                    "title": title,
                                    "url": url,
                                    "snippet": snippet
                                })
                        
                        if results:
                            return {
                                "success": True,
                                "query": query,
                                "results": results,
                                "count": len(results),
                                "message": f"Found {len(results)} results for '{query}'"
                            }
                        else:
                            # Fallback: return a message that search was attempted
                            return {
                                "success": True,
                                "query": query,
                                "results": [],
                                "count": 0,
                                "message": f"Search completed for '{query}' but no results found. Try a different query or check if information is available from other sources."
                            }
                
                except Exception as e:
                    logger.error(f"Error searching for trading information: {e}", exc_info=True)
                    return {
                        "success": False,
                        "error": f"Search failed: {str(e)}",
                        "query": query,
                        "message": f"Could not search for '{query}'. Please try a different query or use other available tools."
                    }
            
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
                    logger.info(f"🔍 CypherMind: analyze_optimal_coins called by {agent_name} with params: {parameters}")
                    if self.binance_client is None:
                        logger.error("CypherMind: Binance client not available for analyze_optimal_coins")
                        return {"error": "Binance client not available", "success": False}
                    
                    max_coins = parameters.get("max_coins", 20)
                    min_score = parameters.get("min_score", 0.2)
                    exclude_symbols = parameters.get("exclude_symbols", None)
                    logger.info(f"CypherMind: Analyzing coins - max_coins={max_coins}, min_score={min_score}")
                    
                    # Validate parameters
                    if max_coins < 1 or max_coins > 50:  # Erhöht von 20 auf 50
                        max_coins = 20
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
                    
                    # Fallback: Wenn keine Coins mit min_score gefunden, versuche mit niedrigerer Schwelle
                    if len(results) == 0 and min_score >= 0.3:
                        logger.info(f"No coins found with min_score={min_score}, trying with lower threshold (0.2)")
                        results = await analyzer.find_optimal_coins(
                            min_score=0.2,
                            max_coins=max_coins,
                            exclude_symbols=exclude_symbols
                        )
                        if results:
                            logger.info(f"Found {len(results)} coins with lower threshold (0.2)")
                    
                    logger.info(f"✅ CypherMind: analyze_optimal_coins completed - found {len(results)} coins")
                    if results:
                        top_coins = results[:3]
                        logger.info(f"CypherMind: Top coins: {[(c.get('symbol'), c.get('score', 0)) for c in top_coins]}")
                    
                    return {
                        "success": True,
                        "count": len(results),
                        "coins": results,
                        "min_score_used": min_score if len(results) > 0 or min_score < 0.3 else 0.2
                    }
                except Exception as e:
                    logger.error(f"Error analyzing optimal coins: {e}", exc_info=True)
                    return {"error": f"Error analyzing coins: {str(e)}", "success": False}
            
            elif tool_name == "start_autonomous_bot":
                try:
                    logger.info(f"🚀 CypherMind: start_autonomous_bot called by {agent_name} with params: {parameters}")
                    if agent_name != "CypherMind":
                        logger.warning(f"start_autonomous_bot called by {agent_name}, but only CypherMind can start bots")
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
                    
                    # Import MAX_AUTONOMOUS_BOTS from autonomous_manager
                    from autonomous_manager import MAX_AUTONOMOUS_BOTS
                    
                    if len(cyphermind_bots) >= MAX_AUTONOMOUS_BOTS:
                        return {
                            "error": f"CypherMind has already started {len(cyphermind_bots)} autonomous bots (maximum: {MAX_AUTONOMOUS_BOTS})",
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
                    
                    # Create new bot (always create new one for autonomous bots)
                    new_bot = self.bot.get_bot()
                    
                    # CRITICAL: Check if bot is already running
                    if new_bot.is_running:
                        logger.warning(f"Bot {new_bot.bot_id} is already running, creating new bot instance")
                        # Create a new bot with a new ID
                        new_bot = self.bot.get_bot()
                    
                    # Mark as started by CypherMind BEFORE starting
                    if new_bot.current_config is None:
                        new_bot.current_config = {}
                    new_bot.current_config["started_by"] = "CypherMind"
                    new_bot.current_config["autonomous"] = True
                    
                    # CRITICAL: Double-check bot is not running before starting
                    if new_bot.is_running:
                        return {
                            "success": False,
                            "error": f"Bot {new_bot.bot_id} is already running. Cannot start autonomous bot."
                        }
                    
                    # Start bot
                    logger.info(f"🚀 CypherMind: Attempting to start autonomous bot: symbol={symbol}, strategy={strategy}, budget={calculated_budget:.2f} USDT")
                    result = await new_bot.start(strategy, symbol, calculated_budget, timeframe, trading_mode)
                    logger.info(f"CypherMind: Bot start result: success={result.get('success')}, message={result.get('message', 'N/A')[:100]}")
                    
                    if result.get("success"):
                        # Verify bot is actually running
                        if not new_bot.is_running:
                            logger.error(f"Bot {new_bot.bot_id} start() returned success but bot is not running!")
                            return {
                                "success": False,
                                "error": "Bot start reported success but bot is not actually running"
                            }
                        
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
                        
                        # Verify bot is in database
                        db_bot = await self.db.bot_config.find_one({"bot_id": new_bot.bot_id})
                        if not db_bot:
                            logger.error(f"Bot {new_bot.bot_id} not found in database after start!")
                            return {
                                "success": False,
                                "error": "Bot was started but not found in database"
                            }
                        
                        logger.info(f"✅ CypherMind successfully started autonomous bot: {new_bot.bot_id} for {symbol} with budget {calculated_budget} USDT (is_running={new_bot.is_running}, in_db={db_bot is not None})")
                        
                        return {
                            "success": True,
                            "bot_id": new_bot.bot_id,
                            "symbol": symbol,
                            "strategy": strategy,
                            "budget": calculated_budget,
                            "message": f"Autonomous bot started successfully with budget {calculated_budget:.2f} USDT (avg: {avg_budget:.2f}, max 40%: {max_budget_from_capital:.2f})"
                        }
                    else:
                        error_msg = result.get("message", "Failed to start bot")
                        logger.error(f"❌ Failed to start autonomous bot: {error_msg}")
                        return {
                            "success": False,
                            "error": error_msg
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
            
            elif tool_name == "get_bot_candles":
                try:
                    if agent_name != "CypherMind":
                        return {"error": "Only CypherMind can access bot candles", "success": False}
                    
                    if self.bot is None:
                        return {"error": "Bot manager not available", "success": False}
                    
                    from bot_manager import BotManager
                    if not isinstance(self.bot, BotManager):
                        return {"error": "Bot manager not available", "success": False}
                    
                    bot_id = parameters.get("bot_id")
                    phase = parameters.get("phase", "pre_trade")
                    
                    if not bot_id:
                        return {"error": "bot_id parameter is required", "success": False}
                    
                    # Get the bot instance
                    all_bots = self.bot.get_all_bots()
                    if bot_id not in all_bots:
                        return {"error": f"Bot {bot_id} not found", "success": False}
                    
                    bot_instance = all_bots[bot_id]
                    
                    # Check if bot has candle_tracker
                    if not hasattr(bot_instance, 'candle_tracker') or bot_instance.candle_tracker is None:
                        return {"error": "Candle tracker not available for this bot", "success": False}
                    
                    candle_tracker = bot_instance.candle_tracker
                    
                    # Get candles based on phase
                    if phase == "both":
                        pre_result = await candle_tracker.get_bot_candles(bot_id, "pre_trade")
                        post_result = await candle_tracker.get_bot_candles(bot_id, "post_trade")
                        
                        return {
                            "success": True,
                            "bot_id": bot_id,
                            "pre_trade": pre_result,
                            "post_trade": post_result
                        }
                    else:
                        result = await candle_tracker.get_bot_candles(bot_id, phase)
                        
                        return {
                            "success": True,
                            "bot_id": bot_id,
                            "phase": phase,
                            "result": result
                        }
                
                except Exception as e:
                    logger.error(f"Error getting bot candles: {e}", exc_info=True)
                    return {"error": f"Error getting candles: {str(e)}", "success": False}
            
            else:
                return {"error": f"Unknown tool: {tool_name}", "success": False}
        
        except BinanceAPIException as e:
            logger.error(f"Binance API error in tool {tool_name}: {e}")
            return {"error": f"Binance API error: {str(e)}", "success": False}
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return {"error": f"Tool execution error: {str(e)}", "success": False}

