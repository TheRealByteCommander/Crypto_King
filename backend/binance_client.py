from binance.client import Client
from binance.exceptions import BinanceAPIException
from config import settings
import pandas as pd
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class BinanceClientWrapper:
    """Wrapper for Binance API client with error handling."""
    
    def __init__(self):
        """Initialize Binance client."""
        try:
            self.client = Client(
                settings.binance_api_key,
                settings.binance_api_secret,
                testnet=settings.binance_testnet
            )
            logger.info(f"Binance client initialized (testnet={settings.binance_testnet})")
        except Exception as e:
            logger.error(f"Failed to initialize Binance client: {e}")
            raise
    
    def get_market_data(self, symbol: str, interval: str = "5m", limit: int = 100) -> pd.DataFrame:
        """Get historical kline data from Binance."""
        try:
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Convert to appropriate types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            logger.info(f"Retrieved {len(df)} klines for {symbol}")
            return df
        
        except BinanceAPIException as e:
            logger.error(f"Binance API error getting market data: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            raise
    
    def get_account_balance(self, asset: str = "USDT") -> float:
        """Get account balance for a specific asset."""
        try:
            account = self.client.get_account()
            for balance in account['balances']:
                if balance['asset'] == asset:
                    free_balance = float(balance['free'])
                    logger.info(f"Account balance for {asset}: {free_balance}")
                    return free_balance
            return 0.0
        except BinanceAPIException as e:
            logger.error(f"Binance API error getting balance: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            raise
    
    def execute_order(self, symbol: str, side: str, quantity: float, order_type: str = "MARKET") -> Dict[str, Any]:
        """Execute a buy or sell order."""
        try:
            logger.info(f"Executing {side} order: {quantity} {symbol} ({order_type})")
            
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type=order_type,
                quantity=quantity
            )
            
            logger.info(f"Order executed successfully: {order['orderId']}")
            return {
                "orderId": order['orderId'],
                "status": order['status'],
                "executedQty": float(order['executedQty']),
                "cummulativeQuoteQty": float(order.get('cummulativeQuoteQty', 0)),
                "transactTime": order['transactTime']
            }
        
        except BinanceAPIException as e:
            logger.error(f"Binance API error executing order: {e}")
            raise
        except Exception as e:
            logger.error(f"Error executing order: {e}")
            raise
    
    def get_order_status(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Get status of a specific order."""
        try:
            order = self.client.get_order(symbol=symbol, orderId=order_id)
            return {
                "orderId": order['orderId'],
                "status": order['status'],
                "executedQty": float(order['executedQty']),
                "cummulativeQuoteQty": float(order.get('cummulativeQuoteQty', 0))
            }
        except BinanceAPIException as e:
            logger.error(f"Binance API error getting order status: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            raise
    
    def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol."""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            logger.info(f"Current price for {symbol}: {price}")
            return price
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            raise