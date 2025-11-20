import pandas as pd
from ta.trend import SMAIndicator
import logging
from typing import Dict, Any, Literal

logger = logging.getLogger(__name__)

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
            # Calculate moving averages
            df['sma_fast'] = SMAIndicator(close=df['close'], window=self.fast_period).sma_indicator()
            df['sma_slow'] = SMAIndicator(close=df['close'], window=self.slow_period).sma_indicator()
            
            # Get last few rows
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            signal = "HOLD"
            reason = "No clear signal"
            confidence = 0.0
            
            # Check for crossover
            if last_row['sma_fast'] > last_row['sma_slow'] and prev_row['sma_fast'] <= prev_row['sma_slow']:
                signal = "BUY"
                reason = f"Fast SMA ({self.fast_period}) crossed above Slow SMA ({self.slow_period})"
                # Calculate confidence based on distance
                distance = abs(last_row['sma_fast'] - last_row['sma_slow']) / last_row['close']
                confidence = min(0.9, 0.6 + distance * 100)
            elif last_row['sma_fast'] < last_row['sma_slow'] and prev_row['sma_fast'] >= prev_row['sma_slow']:
                signal = "SELL"
                reason = f"Fast SMA ({self.fast_period}) crossed below Slow SMA ({self.slow_period})"
                distance = abs(last_row['sma_fast'] - last_row['sma_slow']) / last_row['close']
                confidence = min(0.9, 0.6 + distance * 100)
            
            result = {
                "signal": signal,
                "reason": reason,
                "confidence": confidence,
                "indicators": {
                    "sma_fast": float(last_row['sma_fast']),
                    "sma_slow": float(last_row['sma_slow']),
                    "current_price": float(last_row['close'])
                },
                "timestamp": str(last_row['timestamp'])
            }
            
            logger.info(f"MA Crossover: {signal} - {reason} (Confidence: {confidence:.2f})")
            return result
        
        except Exception as e:
            logger.error(f"Error in MA Crossover analysis: {e}")
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
            
            # Calculate RSI
            df['rsi'] = RSIIndicator(close=df['close'], window=self.period).rsi()
            
            # Get last few rows
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            signal = "HOLD"
            reason = "RSI in neutral zone"
            confidence = 0.0
            
            rsi_current = last_row['rsi']
            rsi_prev = prev_row['rsi']
            
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
                    "rsi": float(rsi_current),
                    "rsi_prev": float(rsi_prev),
                    "oversold_level": self.oversold,
                    "overbought_level": self.overbought,
                    "current_price": float(last_row['close'])
                },
                "timestamp": str(last_row['timestamp'])
            }
            
            logger.info(f"RSI Strategy: {signal} - {reason} (RSI: {rsi_current:.1f}, Confidence: {confidence:.2f})")
            return result
        
        except Exception as e:
            logger.error(f"Error in RSI analysis: {e}")
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
            prev_row = df.iloc[-2]
            
            signal = "HOLD"
            reason = "No clear MACD signal"
            confidence = 0.0
            
            macd = last_row['macd']
            macd_signal = last_row['macd_signal']
            macd_prev = prev_row['macd']
            macd_signal_prev = prev_row['macd_signal']
            
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
                    "macd": float(macd),
                    "macd_signal": float(macd_signal),
                    "macd_diff": float(last_row['macd_diff']),
                    "current_price": float(last_row['close'])
                },
                "timestamp": str(last_row['timestamp'])
            }
            
            logger.info(f"MACD Strategy: {signal} - {reason} (Confidence: {confidence:.2f})")
            return result
        
        except Exception as e:
            logger.error(f"Error in MACD analysis: {e}")
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
            
            # Calculate Bollinger Bands
            bb = BollingerBands(close=df['close'], window=self.period, window_dev=self.std_dev)
            
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_middle'] = bb.bollinger_mavg()
            df['bb_lower'] = bb.bollinger_lband()
            
            # Get last row
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            signal = "HOLD"
            reason = "Price within bands"
            confidence = 0.0
            
            price = last_row['close']
            prev_price = prev_row['close']
            upper = last_row['bb_upper']
            lower = last_row['bb_lower']
            middle = last_row['bb_middle']
            
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
                    "bb_upper": float(upper),
                    "bb_middle": float(middle),
                    "bb_lower": float(lower),
                    "current_price": float(price)
                },
                "timestamp": str(last_row['timestamp'])
            }
            
            logger.info(f"Bollinger Bands: {signal} - {reason} (Confidence: {confidence:.2f})")
            return result
        
        except Exception as e:
            logger.error(f"Error in Bollinger Bands analysis: {e}")
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
            # Get signals from all strategies
            ma_result = self.ma_strategy.analyze(df.copy())
            rsi_result = self.rsi_strategy.analyze(df.copy())
            macd_result = self.macd_strategy.analyze(df.copy())
            
            # Count signals
            buy_signals = sum([
                ma_result['signal'] == 'BUY',
                rsi_result['signal'] == 'BUY',
                macd_result['signal'] == 'BUY'
            ])
            
            sell_signals = sum([
                ma_result['signal'] == 'SELL',
                rsi_result['signal'] == 'SELL',
                macd_result['signal'] == 'SELL'
            ])
            
            # Determine final signal
            signal = "HOLD"
            reason = "Mixed signals from indicators"
            confidence = 0.0
            
            if buy_signals >= 2:
                signal = "BUY"
                reason = f"{buy_signals}/3 indicators suggest BUY"
                confidence = 0.6 + (buy_signals / 3) * 0.3
            elif sell_signals >= 2:
                signal = "SELL"
                reason = f"{sell_signals}/3 indicators suggest SELL"
                confidence = 0.6 + (sell_signals / 3) * 0.3
            
            result = {
                "signal": signal,
                "reason": reason,
                "confidence": confidence,
                "sub_strategies": {
                    "ma_crossover": ma_result,
                    "rsi": rsi_result,
                    "macd": macd_result
                },
                "indicators": {
                    "buy_signals": buy_signals,
                    "sell_signals": sell_signals,
                    "current_price": float(df.iloc[-1]['close'])
                },
                "timestamp": str(df.iloc[-1]['timestamp'])
            }
            
            logger.info(f"Combined Strategy: {signal} - {reason} (Confidence: {confidence:.2f})")
            return result
        
        except Exception as e:
            logger.error(f"Error in Combined strategy analysis: {e}")
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