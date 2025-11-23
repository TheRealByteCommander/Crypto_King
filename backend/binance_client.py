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
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol information including filters (lot size, step size, etc.)."""
        try:
            exchange_info = self.client.get_exchange_info()
            for s in exchange_info['symbols']:
                if s['symbol'] == symbol:
                    filters = {}
                    for f in s.get('filters', []):
                        if f['filterType'] == 'LOT_SIZE':
                            filters['lot_size'] = {
                                'min_qty': float(f.get('minQty', 0)),
                                'max_qty': float(f.get('maxQty', 0)),
                                'step_size': float(f.get('stepSize', 0))
                            }
                        elif f['filterType'] == 'MIN_NOTIONAL':
                            filters['min_notional'] = float(f.get('minNotional', 0))
                    logger.info(f"Symbol info for {symbol}: {filters}")
                    return filters
            logger.warning(f"Symbol {symbol} not found in exchange info")
            return {}
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return {}
    
    def get_tradable_symbols(self) -> List[Dict[str, Any]]:
        """Get all tradable symbols from Binance (USDT pairs only)."""
        try:
            exchange_info = self.client.get_exchange_info()
            tradable_symbols = []
            
            for symbol_info in exchange_info['symbols']:
                # Only include symbols that:
                # 1. Have status = 'TRADING'
                # 2. Are SPOT trading type
                # 3. End with USDT (or can be filtered for other quote assets)
                if (symbol_info['status'] == 'TRADING' and 
                    symbol_info['type'] == 'SPOT' and
                    symbol_info['quoteAsset'] == 'USDT'):
                    tradable_symbols.append({
                        'symbol': symbol_info['symbol'],
                        'baseAsset': symbol_info['baseAsset'],
                        'quoteAsset': symbol_info['quoteAsset'],
                        'status': symbol_info['status']
                    })
            
            logger.info(f"Found {len(tradable_symbols)} tradable USDT pairs on Binance")
            return sorted(tradable_symbols, key=lambda x: x['symbol'])
        
        except Exception as e:
            logger.error(f"Error getting tradable symbols: {e}")
            return []
    
    def is_symbol_tradable(self, symbol: str) -> tuple[bool, Optional[str]]:
        """
        Check if a symbol is tradable on Binance.
        Returns: (is_tradable: bool, error_message: Optional[str])
        """
        try:
            exchange_info = self.client.get_exchange_info()
            
            # Find the symbol
            symbol_upper = symbol.upper()
            for symbol_info in exchange_info['symbols']:
                if symbol_info['symbol'] == symbol_upper:
                    # Check if it's tradable
                    if symbol_info['status'] != 'TRADING':
                        return False, f"Symbol {symbol_upper} exists but is not tradable (status: {symbol_info['status']})"
                    
                    if symbol_info['type'] != 'SPOT':
                        return False, f"Symbol {symbol_upper} exists but is not a SPOT trading pair (type: {symbol_info['type']})"
                    
                    if symbol_info['quoteAsset'] != 'USDT':
                        return False, f"Symbol {symbol_upper} exists but is not a USDT pair (quote: {symbol_info['quoteAsset']})"
                    
                    # Symbol is valid and tradable
                    logger.info(f"Symbol {symbol_upper} validated: tradable SPOT USDT pair")
                    return True, None
            
            # Symbol not found - get suggestions
            all_symbols = [s['symbol'] for s in exchange_info['symbols'] if s['quoteAsset'] == 'USDT']
            similar = [s for s in all_symbols if symbol_upper in s or s.startswith(symbol_upper[:3])][:5]
            
            error_msg = f"Symbol {symbol_upper} not found on Binance"
            if similar:
                error_msg += f". Did you mean: {', '.join(similar)}?"
            else:
                # Get some popular examples
                popular = [s for s in all_symbols if s in ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']]
                if popular:
                    error_msg += f". Popular symbols: {', '.join(popular)}"
            
            return False, error_msg
        
        except BinanceAPIException as e:
            logger.error(f"Binance API error checking symbol {symbol}: {e}")
            return False, f"Binance API error: {str(e)}"
        except Exception as e:
            logger.error(f"Error checking symbol {symbol}: {e}")
            return False, f"Error validating symbol: {str(e)}"
    
    def adjust_quantity_to_lot_size(self, symbol: str, quantity: float) -> float:
        """Adjust quantity to match Binance LOT_SIZE filter requirements."""
        try:
            symbol_info = self.get_symbol_info(symbol)
            lot_size = symbol_info.get('lot_size')
            
            if not lot_size:
                # If no lot size info available, round to 6 decimal places as fallback
                logger.warning(f"No lot size info for {symbol}, using default rounding")
                return round(quantity, 6)
            
            step_size = lot_size.get('step_size', 0)
            min_qty = lot_size.get('min_qty', 0)
            max_qty = lot_size.get('max_qty', 0)
            
            # Calculate precision from step_size
            # e.g., step_size = 0.001 -> precision = 3
            if step_size > 0:
                # Count decimal places in step_size
                step_str = f"{step_size:.10f}".rstrip('0')
                if '.' in step_str:
                    precision = len(step_str.split('.')[1])
                else:
                    precision = 0
                
                # Round down to nearest step_size
                adjusted_qty = (quantity // step_size) * step_size
                adjusted_qty = round(adjusted_qty, precision)
            else:
                adjusted_qty = round(quantity, 6)
            
            # Apply min/max constraints
            if min_qty > 0 and adjusted_qty < min_qty:
                logger.warning(f"Quantity {adjusted_qty} below min_qty {min_qty} for {symbol}, using min_qty")
                adjusted_qty = min_qty
            if max_qty > 0 and adjusted_qty > max_qty:
                logger.warning(f"Quantity {adjusted_qty} above max_qty {max_qty} for {symbol}, using max_qty")
                adjusted_qty = max_qty
            
            logger.info(f"Adjusted quantity for {symbol}: {quantity} -> {adjusted_qty} (step_size={step_size}, min={min_qty}, max={max_qty})")
            return adjusted_qty
            
        except Exception as e:
            logger.error(f"Error adjusting quantity to lot size for {symbol}: {e}")
            # Fallback to default rounding
            return round(quantity, 6)