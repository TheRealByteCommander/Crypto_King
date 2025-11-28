import pandas as pd
import numpy as np
from ta.trend import SMAIndicator
import logging
from typing import Dict, Any, Literal, Optional

logger = logging.getLogger(__name__)

def _validate_data_and_indicators(df: pd.DataFrame, min_required_periods: int, indicator_values: Dict[str, Any], strategy_name: str) -> bool:
    """
    Validates that we have enough data and that indicator values are valid (not NaN).
    
    Args:
        df: DataFrame with market data
        min_required_periods: Minimum number of periods required for calculation
        indicator_values: Dictionary of indicator values to validate
        strategy_name: Name of the strategy for logging
    
    Returns:
        True if data is valid, False otherwise
    """
    # Check if we have enough data
    if len(df) < min_required_periods:
        logger.warning(f"{strategy_name}: Insufficient data. Required: {min_required_periods}, Got: {len(df)}")
        return False
    
    # Check if we have at least 2 rows for comparison (needed for crossover detection)
    if len(df) < 2:
        logger.warning(f"{strategy_name}: Need at least 2 data points for analysis. Got: {len(df)}")
        return False
    
    # Validate indicator values (check for NaN, None, or invalid values)
    for indicator_name, value in indicator_values.items():
        if pd.isna(value) or value is None:
            logger.warning(f"{strategy_name}: Invalid {indicator_name} value: {value} (NaN or None)")
            return False
        
        # RSI-specific validation (should be between 0 and 100)
        if indicator_name == 'rsi' or indicator_name == 'rsi_prev':
            if not (0 <= float(value) <= 100):
                logger.warning(f"{strategy_name}: Invalid RSI value: {value} (should be 0-100)")
                return False
    
    return True

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float, handling NaN and None."""
    if pd.isna(value) or value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

class TradingStrategy:
    """Base class for trading strategies."""
    
    def __init__(self, name: str):
        self.name = name
    
    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze market data and generate signal."""
        raise NotImplementedError

class MovingAverageCrossover(TradingStrategy):
    """Moving Average Crossover Strategy (SMA20 / SMA50)."""
    
    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        super().__init__("ma_crossover")
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze using MA crossover strategy."""
        try:
            # Validate minimum data requirements (need at least slow_period for slow SMA)
            min_periods = max(self.slow_period, 2)  # At least slow_period for SMA, but also need 2 for comparison
            if len(df) < min_periods:
                logger.warning(f"MA Crossover: Insufficient data. Required: {min_periods}, Got: {len(df)}")
                return {
                    "signal": "HOLD",
                    "reason": f"Insufficient data for MA calculation (need {min_periods} periods, got {len(df)})",
                    "confidence": 0.0,
                    "indicators": {"error": "insufficient_data"},
                    "timestamp": str(df.iloc[-1]['timestamp']) if len(df) > 0 else ""
                }
            
            # Calculate moving averages
            df['sma_fast'] = SMAIndicator(close=df['close'], window=self.fast_period).sma_indicator()
            df['sma_slow'] = SMAIndicator(close=df['close'], window=self.slow_period).sma_indicator()
            
            # Get last few rows
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2] if len(df) >= 2 else last_row
            
            # Validate SMA values
            sma_fast_current = last_row['sma_fast']
            sma_slow_current = last_row['sma_slow']
            sma_fast_prev = prev_row['sma_fast'] if len(df) >= 2 else sma_fast_current
            sma_slow_prev = prev_row['sma_slow'] if len(df) >= 2 else sma_slow_current
            
            # Check for NaN values
            if pd.isna(sma_fast_current) or pd.isna(sma_slow_current) or pd.isna(sma_fast_prev) or pd.isna(sma_slow_prev):
                logger.warning(f"MA Crossover: NaN values detected in SMA calculations")
                return {
                    "signal": "HOLD",
                    "reason": "SMA calculation returned NaN (insufficient historical data)",
                    "confidence": 0.0,
                    "indicators": {"error": "nan_values"},
                    "timestamp": str(last_row['timestamp'])
                }
            
            # Convert to safe floats
            sma_fast_current = _safe_float(sma_fast_current)
            sma_slow_current = _safe_float(sma_slow_current)
            sma_fast_prev = _safe_float(sma_fast_prev)
            sma_slow_prev = _safe_float(sma_slow_prev)
            current_price = _safe_float(last_row['close'])
            
            signal = "HOLD"
            reason = "No clear signal"
            confidence = 0.0
            
            # Check for crossover
            if sma_fast_current > sma_slow_current and sma_fast_prev <= sma_slow_prev:
                signal = "BUY"
                reason = f"Fast SMA ({self.fast_period}) crossed above Slow SMA ({self.slow_period})"
                # Calculate confidence based on distance
                distance = abs(sma_fast_current - sma_slow_current) / current_price if current_price > 0 else 0
                confidence = min(0.9, 0.6 + distance * 100)
            elif sma_fast_current < sma_slow_current and sma_fast_prev >= sma_slow_prev:
                signal = "SELL"
                reason = f"Fast SMA ({self.fast_period}) crossed below Slow SMA ({self.slow_period})"
                distance = abs(sma_fast_current - sma_slow_current) / current_price if current_price > 0 else 0
                confidence = min(0.9, 0.6 + distance * 100)
            
            result = {
                "signal": signal,
                "reason": reason,
                "confidence": confidence,
                "indicators": {
                    "sma_fast": sma_fast_current,
                    "sma_slow": sma_slow_current,
                    "current_price": current_price
                },
                "timestamp": str(last_row['timestamp'])
            }
            
            logger.info(f"MA Crossover: {signal} - {reason} (Confidence: {confidence:.2f})")
            return result
        
        except Exception as e:
            logger.error(f"Error in MA Crossover analysis: {e}", exc_info=True)
            raise


class RSIStrategy(TradingStrategy):
    """RSI (Relative Strength Index) Strategy."""
    
    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        super().__init__("rsi")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze using RSI strategy."""
        try:
            from ta.momentum import RSIIndicator
            
            # Validate minimum data requirements (RSI needs at least 'period' data points)
            min_periods = max(self.period, 2)  # At least period for RSI, but also need 2 for comparison
            if len(df) < min_periods:
                logger.warning(f"RSI Strategy: Insufficient data. Required: {min_periods}, Got: {len(df)}")
                return {
                    "signal": "HOLD",
                    "reason": f"Insufficient data for RSI calculation (need {min_periods} periods, got {len(df)})",
                    "confidence": 0.0,
                    "indicators": {"error": "insufficient_data"},
                    "timestamp": str(df.iloc[-1]['timestamp']) if len(df) > 0 else ""
                }
            
            # Calculate RSI
            df['rsi'] = RSIIndicator(close=df['close'], window=self.period).rsi()
            
            # Get last few rows
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2] if len(df) >= 2 else last_row
            
            # Validate RSI values
            rsi_current = last_row['rsi']
            rsi_prev = prev_row['rsi'] if len(df) >= 2 else rsi_current
            
            # Check for NaN values
            if pd.isna(rsi_current) or pd.isna(rsi_prev):
                logger.warning(f"RSI Strategy: NaN values detected. Current: {rsi_current}, Prev: {rsi_prev}")
                return {
                    "signal": "HOLD",
                    "reason": "RSI calculation returned NaN (insufficient historical data)",
                    "confidence": 0.0,
                    "indicators": {"error": "nan_values"},
                    "timestamp": str(last_row['timestamp'])
                }
            
            # Validate RSI range (should be 0-100)
            rsi_current = _safe_float(rsi_current, 50.0)  # Default to neutral if invalid
            rsi_prev = _safe_float(rsi_prev, 50.0)
            
            if not (0 <= rsi_current <= 100):
                logger.warning(f"RSI Strategy: Invalid RSI value: {rsi_current} (should be 0-100)")
                return {
                    "signal": "HOLD",
                    "reason": f"Invalid RSI value: {rsi_current:.2f}",
                    "confidence": 0.0,
                    "indicators": {"error": "invalid_rsi_value"},
                    "timestamp": str(last_row['timestamp'])
                }
            
            signal = "HOLD"
            reason = "RSI in neutral zone"
            confidence = 0.0
            
            # RSI crossing from oversold to above
            if rsi_current > self.oversold and rsi_prev <= self.oversold:
                signal = "BUY"
                reason = f"RSI crossed above oversold level ({self.oversold})"
                confidence = 0.7
            
            # RSI crossing from overbought to below
            elif rsi_current < self.overbought and rsi_prev >= self.overbought:
                signal = "SELL"
                reason = f"RSI crossed below overbought level ({self.overbought})"
                confidence = 0.7
            
            # Strong oversold
            elif rsi_current < 25:
                signal = "BUY"
                reason = f"RSI extremely oversold ({rsi_current:.1f})"
                confidence = 0.85
            
            # Strong overbought
            elif rsi_current > 75:
                signal = "SELL"
                reason = f"RSI extremely overbought ({rsi_current:.1f})"
                confidence = 0.85
            
            result = {
                "signal": signal,
                "reason": reason,
                "confidence": confidence,
                "indicators": {
                    "rsi": rsi_current,
                    "rsi_prev": rsi_prev,
                    "oversold_level": self.oversold,
                    "overbought_level": self.overbought,
                    "current_price": _safe_float(last_row['close'])
                },
                "timestamp": str(last_row['timestamp'])
            }
            
            logger.info(f"RSI Strategy: {signal} - {reason} (RSI: {rsi_current:.1f}, Confidence: {confidence:.2f})")
            return result
        
        except Exception as e:
            logger.error(f"Error in RSI analysis: {e}", exc_info=True)
            raise


class MACDStrategy(TradingStrategy):
    """MACD (Moving Average Convergence Divergence) Strategy."""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        super().__init__("macd")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze using MACD strategy."""
        try:
            from ta.trend import MACD
            
            # Validate minimum data requirements (MACD needs at least slow_period + signal_period)
            min_periods = max(self.slow_period + self.signal_period, 2)  # At least slow+signal for MACD, but also need 2 for comparison
            if len(df) < min_periods:
                logger.warning(f"MACD Strategy: Insufficient data. Required: {min_periods}, Got: {len(df)}")
                return {
                    "signal": "HOLD",
                    "reason": f"Insufficient data for MACD calculation (need {min_periods} periods, got {len(df)})",
                    "confidence": 0.0,
                    "indicators": {"error": "insufficient_data"},
                    "timestamp": str(df.iloc[-1]['timestamp']) if len(df) > 0 else ""
                }
            
            # Calculate MACD
            macd_indicator = MACD(
                close=df['close'],
                window_fast=self.fast_period,
                window_slow=self.slow_period,
                window_sign=self.signal_period
            )
            
            df['macd'] = macd_indicator.macd()
            df['macd_signal'] = macd_indicator.macd_signal()
            df['macd_diff'] = macd_indicator.macd_diff()
            
            # Get last few rows
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2] if len(df) >= 2 else last_row
            
            # Validate MACD values
            macd = last_row['macd']
            macd_signal = last_row['macd_signal']
            macd_prev = prev_row['macd'] if len(df) >= 2 else macd
            macd_signal_prev = prev_row['macd_signal'] if len(df) >= 2 else macd_signal
            
            # Check for NaN values
            if pd.isna(macd) or pd.isna(macd_signal) or pd.isna(macd_prev) or pd.isna(macd_signal_prev):
                logger.warning(f"MACD Strategy: NaN values detected in MACD calculations")
                return {
                    "signal": "HOLD",
                    "reason": "MACD calculation returned NaN (insufficient historical data)",
                    "confidence": 0.0,
                    "indicators": {"error": "nan_values"},
                    "timestamp": str(last_row['timestamp'])
                }
            
            # Convert to safe floats
            macd = _safe_float(macd)
            macd_signal = _safe_float(macd_signal)
            macd_prev = _safe_float(macd_prev)
            macd_signal_prev = _safe_float(macd_signal_prev)
            macd_diff = _safe_float(last_row['macd_diff'], 0.0)
            current_price = _safe_float(last_row['close'])
            
            signal = "HOLD"
            reason = "No clear MACD signal"
            confidence = 0.0
            
            # MACD crosses above signal line
            if macd > macd_signal and macd_prev <= macd_signal_prev:
                signal = "BUY"
                reason = f"MACD crossed above signal line"
                confidence = 0.75
            
            # MACD crosses below signal line
            elif macd < macd_signal and macd_prev >= macd_signal_prev:
                signal = "SELL"
                reason = f"MACD crossed below signal line"
                confidence = 0.75
            
            result = {
                "signal": signal,
                "reason": reason,
                "confidence": confidence,
                "indicators": {
                    "macd": macd,
                    "macd_signal": macd_signal,
                    "macd_diff": macd_diff,
                    "current_price": current_price
                },
                "timestamp": str(last_row['timestamp'])
            }
            
            logger.info(f"MACD Strategy: {signal} - {reason} (Confidence: {confidence:.2f})")
            return result
        
        except Exception as e:
            logger.error(f"Error in MACD analysis: {e}", exc_info=True)
            raise


class BollingerBandsStrategy(TradingStrategy):
    """Bollinger Bands Strategy."""
    
    def __init__(self, period: int = 20, std_dev: int = 2):
        super().__init__("bollinger_bands")
        self.period = period
        self.std_dev = std_dev
    
    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze using Bollinger Bands strategy."""
        try:
            from ta.volatility import BollingerBands
            
            # Validate minimum data requirements (Bollinger Bands needs at least 'period' data points)
            min_periods = max(self.period, 2)  # At least period for BB, but also need 2 for comparison
            if len(df) < min_periods:
                logger.warning(f"Bollinger Bands: Insufficient data. Required: {min_periods}, Got: {len(df)}")
                return {
                    "signal": "HOLD",
                    "reason": f"Insufficient data for Bollinger Bands calculation (need {min_periods} periods, got {len(df)})",
                    "confidence": 0.0,
                    "indicators": {"error": "insufficient_data"},
                    "timestamp": str(df.iloc[-1]['timestamp']) if len(df) > 0 else ""
                }
            
            # Calculate Bollinger Bands
            bb = BollingerBands(close=df['close'], window=self.period, window_dev=self.std_dev)
            
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_middle'] = bb.bollinger_mavg()
            df['bb_lower'] = bb.bollinger_lband()
            
            # Get last row
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2] if len(df) >= 2 else last_row
            
            # Validate Bollinger Bands values
            price = last_row['close']
            prev_price = prev_row['close'] if len(df) >= 2 else price
            upper = last_row['bb_upper']
            lower = last_row['bb_lower']
            middle = last_row['bb_middle']
            
            # Check for NaN values
            if pd.isna(upper) or pd.isna(lower) or pd.isna(middle) or pd.isna(price):
                logger.warning(f"Bollinger Bands: NaN values detected in calculations")
                return {
                    "signal": "HOLD",
                    "reason": "Bollinger Bands calculation returned NaN (insufficient historical data)",
                    "confidence": 0.0,
                    "indicators": {"error": "nan_values"},
                    "timestamp": str(last_row['timestamp'])
                }
            
            # Convert to safe floats
            price = _safe_float(price)
            prev_price = _safe_float(prev_price)
            upper = _safe_float(upper)
            lower = _safe_float(lower)
            middle = _safe_float(middle)
            
            # Validate that bands are in correct order (upper > middle > lower)
            if not (upper >= middle >= lower):
                logger.warning(f"Bollinger Bands: Invalid band order. Upper: {upper}, Middle: {middle}, Lower: {lower}")
                return {
                    "signal": "HOLD",
                    "reason": "Invalid Bollinger Bands calculation (bands not in correct order)",
                    "confidence": 0.0,
                    "indicators": {"error": "invalid_band_order"},
                    "timestamp": str(last_row['timestamp'])
                }
            
            signal = "HOLD"
            reason = "Price within bands"
            confidence = 0.0
            
            # Price bounced off lower band
            if prev_price <= lower and price > lower:
                signal = "BUY"
                reason = f"Price bounced off lower Bollinger Band"
                confidence = 0.7
            
            # Price bounced off upper band
            elif prev_price >= upper and price < upper:
                signal = "SELL"
                reason = f"Price bounced off upper Bollinger Band"
                confidence = 0.7
            
            # Price well below lower band (oversold)
            elif price < lower * 0.98:
                signal = "BUY"
                reason = f"Price significantly below lower band (oversold)"
                confidence = 0.8
            
            # Price well above upper band (overbought)
            elif price > upper * 1.02:
                signal = "SELL"
                reason = f"Price significantly above upper band (overbought)"
                confidence = 0.8
            
            result = {
                "signal": signal,
                "reason": reason,
                "confidence": confidence,
                "indicators": {
                    "bb_upper": upper,
                    "bb_middle": middle,
                    "bb_lower": lower,
                    "current_price": price
                },
                "timestamp": str(last_row['timestamp'])
            }
            
            logger.info(f"Bollinger Bands: {signal} - {reason} (Confidence: {confidence:.2f})")
            return result
        
        except Exception as e:
            logger.error(f"Error in Bollinger Bands analysis: {e}", exc_info=True)
            raise


class CombinedStrategy(TradingStrategy):
    """Combined Strategy using multiple indicators."""
    
    def __init__(self):
        super().__init__("combined")
        self.ma_strategy = MovingAverageCrossover()
        self.rsi_strategy = RSIStrategy()
        self.macd_strategy = MACDStrategy()
    
    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze using combined strategies."""
        try:
            # Get signals from all strategies (with error handling)
            ma_result = None
            rsi_result = None
            macd_result = None
            
            try:
                ma_result = self.ma_strategy.analyze(df.copy())
            except Exception as e:
                logger.warning(f"Combined Strategy: MA Crossover failed: {e}")
                ma_result = {"signal": "HOLD", "confidence": 0.0}
            
            try:
                rsi_result = self.rsi_strategy.analyze(df.copy())
            except Exception as e:
                logger.warning(f"Combined Strategy: RSI failed: {e}")
                rsi_result = {"signal": "HOLD", "confidence": 0.0}
            
            try:
                macd_result = self.macd_strategy.analyze(df.copy())
            except Exception as e:
                logger.warning(f"Combined Strategy: MACD failed: {e}")
                macd_result = {"signal": "HOLD", "confidence": 0.0}
            
            # Count signals (only count valid signals, not errors)
            buy_signals = 0
            sell_signals = 0
            
            if ma_result and ma_result.get('signal') and 'error' not in ma_result.get('indicators', {}):
                if ma_result['signal'] == 'BUY':
                    buy_signals += 1
                elif ma_result['signal'] == 'SELL':
                    sell_signals += 1
            
            if rsi_result and rsi_result.get('signal') and 'error' not in rsi_result.get('indicators', {}):
                if rsi_result['signal'] == 'BUY':
                    buy_signals += 1
                elif rsi_result['signal'] == 'SELL':
                    sell_signals += 1
            
            if macd_result and macd_result.get('signal') and 'error' not in macd_result.get('indicators', {}):
                if macd_result['signal'] == 'BUY':
                    buy_signals += 1
                elif macd_result['signal'] == 'SELL':
                    sell_signals += 1
            
            # Determine final signal
            signal = "HOLD"
            reason = "Mixed signals from indicators"
            confidence = 0.0
            
            total_valid_strategies = sum([
                1 if ma_result and 'error' not in ma_result.get('indicators', {}) else 0,
                1 if rsi_result and 'error' not in rsi_result.get('indicators', {}) else 0,
                1 if macd_result and 'error' not in macd_result.get('indicators', {}) else 0
            ])
            
            if total_valid_strategies == 0:
                reason = "All strategies failed (insufficient data or calculation errors)"
                confidence = 0.0
            elif buy_signals >= 2:
                signal = "BUY"
                reason = f"{buy_signals}/{total_valid_strategies} indicators suggest BUY"
                confidence = 0.6 + (buy_signals / max(total_valid_strategies, 1)) * 0.3
            elif sell_signals >= 2:
                signal = "SELL"
                reason = f"{sell_signals}/{total_valid_strategies} indicators suggest SELL"
                confidence = 0.6 + (sell_signals / max(total_valid_strategies, 1)) * 0.3
            else:
                reason = f"Mixed signals: {buy_signals} BUY, {sell_signals} SELL from {total_valid_strategies} valid indicators"
            
            result = {
                "signal": signal,
                "reason": reason,
                "confidence": confidence,
                "sub_strategies": {
                    "ma_crossover": ma_result or {"signal": "HOLD", "error": "calculation_failed"},
                    "rsi": rsi_result or {"signal": "HOLD", "error": "calculation_failed"},
                    "macd": macd_result or {"signal": "HOLD", "error": "calculation_failed"}
                },
                "indicators": {
                    "buy_signals": buy_signals,
                    "sell_signals": sell_signals,
                    "valid_strategies": total_valid_strategies,
                    "current_price": _safe_float(df.iloc[-1]['close']) if len(df) > 0 else 0.0
                },
                "timestamp": str(df.iloc[-1]['timestamp']) if len(df) > 0 else ""
            }
            
            logger.info(f"Combined Strategy: {signal} - {reason} (Confidence: {confidence:.2f}, Valid: {total_valid_strategies}/3)")
            return result
        
        except Exception as e:
            logger.error(f"Error in Combined strategy analysis: {e}", exc_info=True)
            raise


def get_strategy(strategy_name: str) -> TradingStrategy:
    """Factory function to get strategy instance."""
    strategies = {
        "ma_crossover": MovingAverageCrossover(),
        "rsi": RSIStrategy(),
        "macd": MACDStrategy(),
        "bollinger_bands": BollingerBandsStrategy(),
        "combined": CombinedStrategy()
    }
    
    if strategy_name not in strategies:
        raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(strategies.keys())}")
    
    return strategies[strategy_name]


def get_available_strategies() -> Dict[str, str]:
    """Get list of available strategies with descriptions."""
    return {
        "ma_crossover": "Moving Average Crossover (SMA 20/50)",
        "rsi": "RSI - Relative Strength Index",
        "macd": "MACD - Moving Average Convergence Divergence",
        "bollinger_bands": "Bollinger Bands - Volatility Strategy",
        "combined": "Combined Strategy (MA + RSI + MACD)"
    }