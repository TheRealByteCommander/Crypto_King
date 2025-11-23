from binance.client import Client
from binance.exceptions import BinanceAPIException
from config import settings
import pandas as pd
import logging
from typing import Dict, Any, Optional, List, Tuple
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
    
    def get_24h_ticker_stats(self) -> List[Dict[str, Any]]:
        """Get 24h ticker statistics for all symbols."""
        try:
            tickers = self.client.get_ticker()
            ticker_list = []
            
            for ticker in tickers:
                price_change_percent = float(ticker.get('priceChangePercent', 0))
                # Filter: Only include symbols with significant price movement (at least 1% change)
                if abs(price_change_percent) >= 1.0:
                    ticker_list.append({
                        'symbol': ticker.get('symbol', ''),
                        'price': float(ticker.get('lastPrice', 0)),
                        'priceChange': float(ticker.get('priceChange', 0)),
                        'priceChangePercent': price_change_percent,
                        'highPrice': float(ticker.get('highPrice', 0)),
                        'lowPrice': float(ticker.get('lowPrice', 0)),
                        'volume': float(ticker.get('volume', 0)),
                        'quoteVolume': float(ticker.get('quoteVolume', 0))
                    })
            
            # Sort by absolute price change percent (volatility)
            ticker_list.sort(key=lambda x: abs(x['priceChangePercent']), reverse=True)
            
            logger.info(f"Retrieved {len(ticker_list)} volatile symbols (24h)")
            return ticker_list
        
        except BinanceAPIException as e:
            logger.error(f"Binance API error getting 24h ticker stats: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting 24h ticker stats: {e}")
            raise
    
    def get_30d_volatile_assets(self) -> List[Dict[str, Any]]:
        """Get most volatile assets based on 30-day historical data."""
        try:
            import numpy as np
            
            # Get 24h ticker first (this gives us all symbols with current data)
            logger.info("Getting 24h ticker data for initial screening...")
            tickers_24h = self.client.get_ticker()
            
            # Filter by significant 24h movement first (at least 3% change)
            # This reduces the number of symbols we need to analyze with 30-day data
            significant_tickers = [
                t for t in tickers_24h 
                if abs(float(t.get('priceChangePercent', 0))) >= 3.0
            ]
            
            # Sort by 24h volume and take top 50 for 30-day analysis
            sorted_tickers = sorted(
                significant_tickers,
                key=lambda x: float(x.get('quoteVolume', 0)),
                reverse=True
            )[:50]
            
            logger.info(f"Analyzing 30-day volatility for top {len(sorted_tickers)} symbols by volume...")
            
            volatile_assets = []
            
            # Process top symbols with 30-day data
            for idx, ticker in enumerate(sorted_tickers):
                symbol = ticker.get('symbol', '')
                if not symbol:
                    continue
                    
                try:
                    # Get 30 days of daily candles
                    klines = self.client.get_klines(symbol=symbol, interval="1d", limit=30)
                    
                    if len(klines) < 20:  # Need at least 20 days of data
                        continue
                    
                    # Extract closing prices
                    closes = [float(k[4]) for k in klines]  # index 4 is close price
                    
                    if len(closes) < 2 or closes[0] == 0:
                        continue
                    
                    # Calculate 30-day price change percent
                    price_change_30d = ((closes[-1] - closes[0]) / closes[0]) * 100
                    
                    # Calculate volatility (standard deviation of daily returns)
                    daily_returns = []
                    for i in range(1, len(closes)):
                        if closes[i-1] > 0:
                            daily_return = ((closes[i] - closes[i-1]) / closes[i-1]) * 100
                            daily_returns.append(daily_return)
                    
                    if len(daily_returns) < 5:  # Need at least 5 daily returns
                        continue
                    
                    volatility_30d = np.std(daily_returns) if daily_returns else 0
                    
                    # Calculate average volume (last 7 days)
                    recent_volumes = [float(k[5]) for k in klines[-7:]]  # index 5 is volume
                    avg_volume = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0
                    
                    # Use current price from ticker
                    current_price = float(ticker.get('lastPrice', closes[-1]))
                    
                    # Include if 30-day change is at least 3% or volatility is significant
                    if abs(price_change_30d) >= 3.0 or volatility_30d >= 2.5:
                        volatile_assets.append({
                            'symbol': symbol,
                            'price': current_price,
                            'priceChangePercent': round(price_change_30d, 2),
                            'volatility30d': round(volatility_30d, 2),
                            'highPrice': max(closes),
                            'lowPrice': min(closes),
                            'volume': avg_volume
                        })
                
                except Exception as e:
                    # Skip symbols that cause errors
                    logger.debug(f"Skipping {symbol} due to error: {e}")
                    continue
            
            # Sort by absolute 30-day price change (volatility indicator)
            volatile_assets.sort(key=lambda x: abs(x['priceChangePercent']), reverse=True)
            
            logger.info(f"Found {len(volatile_assets)} volatile assets (30-day analysis)")
            return volatile_assets
        
        except BinanceAPIException as e:
            logger.error(f"Binance API error getting 30d volatile assets: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting 30d volatile assets: {e}", exc_info=True)
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
        """Get all tradable symbols from Binance (all trading types and quote assets)."""
        try:
            exchange_info = self.client.get_exchange_info()
            tradable_symbols = []
            
            for symbol_info in exchange_info.get('symbols', []):
                # Include all symbols that are tradable:
                # 1. Have status = 'TRADING'
                # 2. Can be any trading type (SPOT, MARGIN, FUTURES, etc.)
                # 3. Can have any quote asset (USDT, BUSD, BTC, ETH, BNB, etc.)
                if symbol_info.get('status') == 'TRADING':
                    tradable_symbols.append({
                        'symbol': symbol_info.get('symbol', ''),
                        'baseAsset': symbol_info.get('baseAsset', ''),
                        'quoteAsset': symbol_info.get('quoteAsset', ''),
                        'type': symbol_info.get('type', 'UNKNOWN'),
                        'status': symbol_info.get('status', 'UNKNOWN')
                    })
            
            logger.info(f"Found {len(tradable_symbols)} tradable symbols on Binance (all types)")
            return sorted(tradable_symbols, key=lambda x: x['symbol'])
        
        except Exception as e:
            logger.error(f"Error getting tradable symbols: {e}")
            return []
    
    def is_symbol_tradable(self, symbol: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a symbol is tradable on Binance (all trading types and quote assets).
        Returns: (is_tradable: bool, error_message: Optional[str])
        """
        try:
            exchange_info = self.client.get_exchange_info()
            
            # Find the symbol
            symbol_upper = symbol.upper()
            for symbol_info in exchange_info.get('symbols', []):
                if symbol_info.get('symbol') == symbol_upper:
                    # Check if it's tradable (only status check, no type or quote asset restriction)
                    status = symbol_info.get('status', 'UNKNOWN')
                    if status != 'TRADING':
                        return False, f"Symbol {symbol_upper} exists but is not tradable (status: {status})"
                    
                    # Symbol is valid and tradable (any type, any quote asset)
                    symbol_type = symbol_info.get('type', 'UNKNOWN')
                    quote_asset = symbol_info.get('quoteAsset', 'UNKNOWN')
                    logger.info(f"Symbol {symbol_upper} validated: tradable {symbol_type} pair (quote: {quote_asset})")
                    return True, None
            
            # Symbol not found - get suggestions from all tradable symbols
            all_symbols = [s.get('symbol', '') for s in exchange_info.get('symbols', []) 
                          if s.get('status') == 'TRADING' and s.get('symbol')]
            similar = [s for s in all_symbols if symbol_upper in s or s.startswith(symbol_upper[:3])][:5]
            
            error_msg = f"Symbol {symbol_upper} not found on Binance"
            if similar:
                error_msg += f". Did you mean: {', '.join(similar)}?"
            else:
                # Get some popular examples (including different quote assets)
                popular_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT', 
                                  'BTCBUSD', 'ETHBTC', 'BNBBTC']
                popular = [s for s in all_symbols if s in popular_symbols]
                if popular:
                    error_msg += f". Popular symbols: {', '.join(popular[:5])}"
            
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
    
    def adjust_quantity_to_notional(self, symbol: str, quantity: float, price: float) -> Optional[float]:
        """
        Adjust quantity to meet Binance MIN_NOTIONAL filter requirements.
        Returns adjusted quantity or None if notional requirement cannot be met.
        """
        try:
            symbol_info = self.get_symbol_info(symbol)
            min_notional = symbol_info.get('min_notional', 0)
            
            if min_notional <= 0:
                # No notional requirement - quantity is fine as is
                return quantity
            
            # Calculate current notional value
            current_notional = quantity * price
            
            # Check if current notional meets minimum
            if current_notional >= min_notional:
                logger.info(f"Notional check passed for {symbol}: {current_notional:.2f} >= {min_notional:.2f}")
                return quantity
            
            # Need to increase quantity to meet notional requirement
            required_quantity = min_notional / price
            
            logger.info(f"Notional check failed for {symbol}: {current_notional:.2f} < {min_notional:.2f}, adjusting quantity from {quantity} to {required_quantity}")
            
            # Adjust the required quantity to lot size first
            adjusted_qty = self.adjust_quantity_to_lot_size(symbol, required_quantity)
            
            # Check again if adjusted quantity meets notional
            adjusted_notional = adjusted_qty * price
            if adjusted_notional < min_notional:
                # Still below minimum even after lot size adjustment
                # Try increasing by one step
                symbol_info_full = self.get_symbol_info(symbol)
                lot_size = symbol_info_full.get('lot_size', {})
                step_size = lot_size.get('step_size', 0)
                
                if step_size > 0:
                    # Try adding one more step
                    adjusted_qty = adjusted_qty + step_size
                    adjusted_notional = adjusted_qty * price
                
                if adjusted_notional < min_notional:
                    logger.warning(f"Cannot meet notional requirement for {symbol}: required {min_notional:.2f}, would be {adjusted_notional:.2f}")
                    return None
            
            logger.info(f"Adjusted quantity for notional: {quantity} -> {adjusted_qty} (notional: {adjusted_notional:.2f} >= {min_notional:.2f})")
            return adjusted_qty
            
        except Exception as e:
            logger.error(f"Error adjusting quantity to notional for {symbol}: {e}")
            return quantity  # Return original quantity on error