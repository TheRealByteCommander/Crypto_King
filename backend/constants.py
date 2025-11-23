"""
Application constants to replace magic numbers.
"""

# Trading Bot Constants
BOT_LOOP_INTERVAL_SECONDS = 300  # 5 minutes
BOT_ERROR_RETRY_DELAY_SECONDS = 60  # 1 minute
BOT_BROADCAST_INTERVAL_SECONDS = 10  # 10 seconds

# Trading Strategy Constants
DEFAULT_FAST_MA_PERIOD = 20
DEFAULT_SLOW_MA_PERIOD = 50
DEFAULT_RSI_PERIOD = 14
DEFAULT_RSI_OVERSOLD = 30
DEFAULT_RSI_OVERBOUGHT = 70
DEFAULT_MACD_FAST_PERIOD = 12
DEFAULT_MACD_SLOW_PERIOD = 26
DEFAULT_MACD_SIGNAL_PERIOD = 9
DEFAULT_BOLLINGER_PERIOD = 20
DEFAULT_BOLLINGER_STD_DEV = 2

# Risk Management Constants
MIN_PROFIT_LOSS_THRESHOLD = 2.0  # $2 minimum loss to consider as failure
QUANTITY_DECIMAL_PLACES = 6

# Binance Trading Fees
BINANCE_TAKER_FEE = 0.001  # 0.1% fee for market orders (taker)
BINANCE_MAKER_FEE = 0.001  # 0.1% fee for limit orders (maker, if not immediately filled)
TOTAL_TRADE_FEE = 0.002  # 0.2% total fee for complete trade (buy + sell)
MIN_PROFIT_AFTER_FEES = 0.003  # 0.3% minimum profit after fees required for a trade

# Memory Constants
MAX_SHORT_TERM_MEMORY = 50
DEFAULT_MEMORY_RETRIEVAL_LIMIT = 20
DEFAULT_MEMORY_DAYS_BACK = 30
DEFAULT_MEMORY_CLEANUP_DAYS = 90

# API Constants
DEFAULT_TRADES_LIMIT = 100
DEFAULT_LOGS_LIMIT = 100
DEFAULT_ANALYSES_LIMIT = 50
DEFAULT_MEMORY_LIMIT = 20
DEFAULT_LESSONS_LIMIT = 10

# WebSocket Constants
WS_RECONNECT_DELAY_MS = 5000  # 5 seconds

