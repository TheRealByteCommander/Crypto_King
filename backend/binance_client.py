from binance.client import Client
from binance.exceptions import BinanceAPIException
from config import settings
import pandas as pd
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class BinanceClientWrapper:
    """Wrapper for Binance API client with error handling. Supports SPOT, MARGIN, and FUTURES trading."""
    
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
    
    def get_account_balance(self, asset: str = "USDT", trading_mode: str = "SPOT") -> float:
        """
        Get account balance for a specific asset.
        
        Args:
            asset: Asset symbol (e.g., 'USDT', 'BTC')
            trading_mode: 'SPOT', 'MARGIN', or 'FUTURES'
        """
        try:
            if trading_mode == "SPOT":
                account = self.client.get_account()
                for balance in account['balances']:
                    if balance['asset'] == asset:
                        free_balance = float(balance['free'])
                        logger.info(f"SPOT account balance for {asset}: {free_balance}")
                        return free_balance
            elif trading_mode == "MARGIN":
                # Margin account balance
                margin_account = self.client.get_margin_account()
                for balance in margin_account['userAssets']:
                    if balance['asset'] == asset:
                        free_balance = float(balance['free'])
                        logger.info(f"MARGIN account balance for {asset}: {free_balance}")
                        return free_balance
            elif trading_mode == "FUTURES":
                # Futures account balance
                futures_account = self.client.futures_account()
                if asset == "USDT":
                    # For USDT futures, get USDT balance
                    balance = float(futures_account.get('availableBalance', 0))
                    logger.info(f"FUTURES account balance (USDT): {balance}")
                    return balance
                else:
                    # For other assets, check positions
                    positions = futures_account.get('positions', [])
                    for pos in positions:
                        if pos['symbol'] == asset and pos['positionSide'] == 'BOTH':
                            amount = float(pos.get('positionAmt', 0))
                            logger.info(f"FUTURES position for {asset}: {amount}")
                            return abs(amount)
            return 0.0
        except BinanceAPIException as e:
            logger.error(f"Binance API error getting balance: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            raise
    
    def get_margin_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get margin position for a symbol."""
        try:
            margin_account = self.client.get_margin_account()
            
            # Extract base asset from symbol (e.g., BTCUSDT -> BTC)
            base_asset = symbol.replace("USDT", "").replace("BUSD", "").replace("BTC", "").replace("ETH", "")
            
            # Check if we have a position (borrowed assets indicate short position)
            for asset in margin_account.get('userAssets', []):
                if asset['asset'] == base_asset:
                    borrowed = float(asset.get('borrowed', 0))
                    net_asset = float(asset.get('netAsset', 0))
                    if borrowed > 0 or net_asset != 0:
                        return {
                            "type": "SHORT" if borrowed > 0 else "LONG",
                            "symbol": symbol,
                            "borrowed": borrowed,
                            "netAsset": net_asset
                        }
            
            return None
        except Exception as e:
            logger.warning(f"Could not get margin position for {symbol}: {e}")
            return None
    
    def get_futures_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get futures position for a symbol."""
        try:
            positions = self.client.futures_position_information(symbol=symbol)
            for pos in positions:
                position_amt = float(pos.get('positionAmt', 0))
                if abs(position_amt) > 0.0001:  # Ignore very small positions
                    return {
                        "type": "SHORT" if position_amt < 0 else "LONG",
                        "symbol": symbol,
                        "size": abs(position_amt),
                        "entry_price": float(pos.get('entryPrice', 0)),
                        "unrealized_pnl": float(pos.get('unRealizedProfit', 0)),
                        "leverage": float(pos.get('leverage', 1))
                    }
            return None
        except Exception as e:
            logger.warning(f"Could not get futures position for {symbol}: {e}")
            return None
    
    def execute_order(self, symbol: str, side: str, quantity: float, order_type: str = "MARKET", trading_mode: str = "SPOT") -> Dict[str, Any]:
        """
        Execute a buy or sell order.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            side: 'BUY' or 'SELL'
            quantity: Quantity to trade
            order_type: Order type (default: 'MARKET')
            trading_mode: 'SPOT', 'MARGIN', or 'FUTURES'
        """
        try:
            logger.info(f"Executing {side} order: {quantity} {symbol} ({order_type}) - Mode: {trading_mode}")
            
            if trading_mode == "SPOT":
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    quantity=quantity
                )
            elif trading_mode == "MARGIN":
                # Margin trading - allows short positions
                # WARNUNG: Funktioniert NICHT auf Testnet!
                if settings.binance_testnet:
                    raise ValueError("MARGIN Trading wird auf Binance Testnet nicht unterstützt. Testnet unterstützt nur SPOT Trading.")
                
                order = self.client.create_margin_order(
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    quantity=quantity
                )
            elif trading_mode == "FUTURES":
                # Futures trading - supports both long and short positions
                # WARNUNG: Funktioniert NICHT auf Testnet!
                if settings.binance_testnet:
                    raise ValueError("FUTURES Trading wird auf Binance Testnet nicht unterstützt. Testnet unterstützt nur SPOT Trading.")
                
                # For futures, we need to specify position side: 'LONG' or 'SHORT'
                position_side = "LONG" if side == "BUY" else "SHORT"
                
                # Futures uses different endpoint
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    quantity=quantity,
                    positionSide=position_side
                )
            else:
                raise ValueError(f"Unsupported trading mode: {trading_mode}")
            
            logger.info(f"Order executed successfully: {order.get('orderId', order.get('order_id', 'N/A'))}")
            return {
                "orderId": order.get('orderId') or order.get('order_id'),
                "status": order.get('status', order.get('status')),
                "executedQty": float(order.get('executedQty', order.get('executedQty', 0))),
                "cummulativeQuoteQty": float(order.get('cummulativeQuoteQty', order.get('cumQuote', 0))),
                "transactTime": order.get('transactTime', order.get('updateTime', 0))
            }
        
        except BinanceAPIException as e:
            error_code = e.code if hasattr(e, 'code') else None
            error_msg = str(e)
            
            # Handle specific error codes
            if error_code == -1013:
                # MIN_NOTIONAL or LOT_SIZE filter failure
                logger.error(f"Binance API error -1013 (Filter failure): {error_msg}")
                raise ValueError(f"Order failed filter validation: {error_msg}. This usually means the order value is too small (MIN_NOTIONAL) or quantity doesn't match LOT_SIZE requirements.")
            elif error_code == -2010:
                # Insufficient balance
                logger.error(f"Binance API error -2010 (Insufficient balance): {error_msg}")
                raise ValueError(f"Insufficient balance: {error_msg}")
            elif error_code == -2011:
                # Unknown order sent
                logger.error(f"Binance API error -2011 (Unknown order): {error_msg}")
                raise ValueError(f"Order not found or already filled: {error_msg}")
            else:
                logger.error(f"Binance API error (code {error_code}): {error_msg}")
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
            
            # Filter by significant 24h movement first (at least 1% change for better coverage)
            # This reduces the number of symbols we need to analyze with 30-day data
            significant_tickers = [
                t for t in tickers_24h 
                if abs(float(t.get('priceChangePercent', 0))) >= 1.0
            ]
            
            # If not enough symbols, use all symbols sorted by volume
            if len(significant_tickers) < 50:
                # Use top 50 by volume regardless of 24h change
                all_tickers = sorted(
                    tickers_24h,
                    key=lambda x: float(x.get('quoteVolume', 0)),
                    reverse=True
                )[:50]
                significant_tickers = all_tickers
            
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
                    
                    # Include if 30-day change is at least 1% or volatility is significant (1%)
                    # Lowered thresholds to ensure we get results
                    if abs(price_change_30d) >= 1.0 or volatility_30d >= 1.0:
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
    
    @staticmethod
    def extract_quote_asset(symbol: str) -> str:
        """
        Extrahiert das Quote-Asset aus einem Trading-Symbol.
        
        Args:
            symbol: Trading-Symbol (z.B. "SOLBTC", "ETHUSDT", "BNBBTC")
        
        Returns:
            Quote-Asset (z.B. "BTC", "USDT", "ETH", "BUSD", "BNB")
        """
        symbol_upper = symbol.upper()
        
        # Bekannte Quote-Assets (sortiert nach Länge, längere zuerst)
        quote_assets = ["USDT", "BUSD", "USDC", "TUSD", "BTC", "ETH", "BNB", "DAI", "PAX", "USDP"]
        
        for quote in quote_assets:
            if symbol_upper.endswith(quote):
                return quote
        
        # Fallback: Versuche aus Exchange Info zu holen (wenn Client verfügbar)
        # Für statische Extraktion: Default zu USDT
        logger.warning(f"Could not extract quote asset from {symbol}, defaulting to USDT")
        return "USDT"
    
    @staticmethod
    def extract_base_asset(symbol: str) -> str:
        """
        Extrahiert das Base-Asset aus einem Trading-Symbol.
        
        Args:
            symbol: Trading-Symbol (z.B. "SOLBTC", "ETHUSDT", "BNBBTC")
        
        Returns:
            Base-Asset (z.B. "SOL", "ETH", "BNB")
        """
        symbol_upper = symbol.upper()
        quote_asset = BinanceClientWrapper.extract_quote_asset(symbol_upper)
        if quote_asset:
            base_asset = symbol_upper[:-len(quote_asset)]
            return base_asset
        return symbol_upper
    
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
    
    def adjust_quantity_to_notional(self, symbol: str, quantity: float, price: float, max_value_usdt: Optional[float] = None) -> Optional[float]:
        """
        Adjust quantity to meet Binance MIN_NOTIONAL filter requirements.
        Takes into account maximum allowed value in USDT (for budget limits).
        Returns adjusted quantity or None if notional requirement cannot be met.
        
        Args:
            symbol: Trading symbol
            quantity: Initial quantity
            price: Current price
            max_value_usdt: Maximum allowed order value in USDT (optional, for budget limits)
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
                # Check if within budget limit (if specified)
                if max_value_usdt is not None and current_notional > max_value_usdt:
                    # Quantity would exceed budget - reduce it
                    logger.warning(f"Order value {current_notional:.2f} exceeds budget limit {max_value_usdt:.2f} USDT, adjusting quantity")
                    max_quantity = max_value_usdt / price
                    adjusted_qty = self.adjust_quantity_to_lot_size(symbol, max_quantity)
                    adjusted_notional = adjusted_qty * price
                    
                    # Check if adjusted quantity still meets notional
                    if adjusted_notional < min_notional:
                        logger.warning(f"Cannot meet notional requirement {min_notional:.2f} within budget limit {max_value_usdt:.2f} USDT")
                        return None
                    
                    logger.info(f"Notional check passed with budget constraint: {adjusted_notional:.2f} USDT (limit: {max_value_usdt:.2f})")
                    return adjusted_qty
                
                logger.info(f"Notional check passed for {symbol}: {current_notional:.2f} >= {min_notional:.2f}")
                return quantity
            
            # Need to increase quantity to meet notional requirement
            required_quantity = min_notional / price
            
            # Check if required quantity would exceed budget (if specified)
            required_notional = required_quantity * price
            if max_value_usdt is not None and required_notional > max_value_usdt:
                logger.warning(f"Cannot meet notional requirement {min_notional:.2f} USDT: would need {required_notional:.2f} USDT but budget limit is {max_value_usdt:.2f} USDT")
                return None
            
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
                    
                    # Check budget limit again after step increase
                    if max_value_usdt is not None and adjusted_notional > max_value_usdt:
                        logger.warning(f"Adjusted quantity {adjusted_notional:.2f} USDT exceeds budget limit {max_value_usdt:.2f} USDT")
                        return None
                
                if adjusted_notional < min_notional:
                    logger.warning(f"Cannot meet notional requirement for {symbol}: required {min_notional:.2f}, would be {adjusted_notional:.2f}")
                    return None
            
            logger.info(f"Adjusted quantity for notional: {quantity} -> {adjusted_qty} (notional: {adjusted_notional:.2f} >= {min_notional:.2f})")
            return adjusted_qty
            
        except Exception as e:
            logger.error(f"Error adjusting quantity to notional for {symbol}: {e}")
            return quantity  # Return original quantity on error
    
    def calculate_optimal_order_quantity(self, symbol: str, available_budget_usdt: float, 
                                        current_price: float, trading_mode: str = "SPOT") -> Optional[float]:
        """
        Calculate optimal order quantity considering:
        - Available budget in quote asset (USDT, BTC, ETH, etc.)
        - Binance LOT_SIZE filter
        - Binance MIN_NOTIONAL filter
        - Available balance
        
        Args:
            symbol: Trading symbol (e.g., "SOLBTC", "ETHUSDT")
            available_budget_usdt: Available budget in quote asset (the amount parameter)
            current_price: Current price of the symbol
            trading_mode: Trading mode (SPOT, MARGIN, FUTURES)
        
        Returns optimal quantity or None if order cannot be executed.
        """
        try:
            # Extract quote asset from symbol
            quote_asset = self.extract_quote_asset(symbol)
            
            # Get available balance for the quote asset
            balance_quote = self.get_account_balance(quote_asset, trading_mode)
            
            # Use the minimum of budget and balance
            max_usable_amount = min(available_budget_usdt, balance_quote)
            
            if max_usable_amount <= 0:
                logger.warning(f"No available budget or balance for {symbol}. Budget: {available_budget_usdt:.8f} {quote_asset}, Balance: {balance_quote:.8f} {quote_asset}")
                return None
            
            # Get symbol info for filters
            symbol_info = self.get_symbol_info(symbol)
            min_notional = symbol_info.get('min_notional', 10.0)  # Default to 10 if not found (in quote asset)
            
            # Check if available amount meets minimum notional
            if max_usable_amount < min_notional:
                logger.warning(f"Available amount {max_usable_amount:.8f} {quote_asset} is below minimum notional {min_notional:.8f} {quote_asset} for {symbol}")
                return None
            
            # Calculate quantity from available amount
            quantity = max_usable_amount / current_price
            
            # Adjust to lot size
            quantity = self.adjust_quantity_to_lot_size(symbol, quantity)
            
            # Adjust to meet notional requirement (with budget constraint)
            adjusted_quantity = self.adjust_quantity_to_notional(symbol, quantity, current_price, max_value_usdt=max_usable_amount)
            
            # Note: max_value_usdt parameter name is kept for backward compatibility, but it now represents the quote asset amount
            
            if adjusted_quantity is None:
                logger.warning(f"Cannot calculate valid quantity for {symbol} with budget {max_usable_amount:.2f} USDT")
                return None
            
            # Final check: ensure notional is met and within budget
            final_notional = adjusted_quantity * current_price
            if final_notional < min_notional:
                logger.warning(f"Final quantity {adjusted_quantity} results in notional {final_notional:.2f} below minimum {min_notional:.2f}")
                return None
            
            if final_notional > max_usable_amount:
                logger.warning(f"Final quantity {adjusted_quantity} results in notional {final_notional:.2f} above available {max_usable_amount:.2f}")
                return None
            
            logger.info(f"Optimal quantity for {symbol}: {adjusted_quantity} (value: {final_notional:.2f} USDT, budget: {max_usable_amount:.2f} USDT)")
            return adjusted_quantity
            
        except Exception as e:
            logger.error(f"Error calculating optimal order quantity for {symbol}: {e}")
            return None