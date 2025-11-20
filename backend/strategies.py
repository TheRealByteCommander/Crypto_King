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
            
            # Check for crossover
            if last_row['sma_fast'] > last_row['sma_slow'] and prev_row['sma_fast'] <= prev_row['sma_slow']:
                signal = "BUY"
                reason = f"Fast SMA ({self.fast_period}) crossed above Slow SMA ({self.slow_period})"
            elif last_row['sma_fast'] < last_row['sma_slow'] and prev_row['sma_fast'] >= prev_row['sma_slow']:
                signal = "SELL"
                reason = f"Fast SMA ({self.fast_period}) crossed below Slow SMA ({self.slow_period})"
            
            result = {
                "signal": signal,
                "reason": reason,
                "indicators": {
                    "sma_fast": float(last_row['sma_fast']),
                    "sma_slow": float(last_row['sma_slow']),
                    "current_price": float(last_row['close'])
                },
                "timestamp": str(last_row['timestamp'])
            }
            
            logger.info(f"Strategy analysis: {signal} - {reason}")
            return result
        
        except Exception as e:
            logger.error(f"Error in strategy analysis: {e}")
            raise

def get_strategy(strategy_name: str) -> TradingStrategy:
    """Factory function to get strategy instance."""
    strategies = {
        "ma_crossover": MovingAverageCrossover()
    }
    
    if strategy_name not in strategies:
        raise ValueError(f"Unknown strategy: {strategy_name}")
    
    return strategies[strategy_name]