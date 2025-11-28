"""
Market Phase Analyzer - Erkennung von Bullish, Bearish und Sideways Märkten
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Literal, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

MarketPhase = Literal["BULLISH", "BEARISH", "SIDEWAYS"]

class MarketPhaseAnalyzer:
    """Analysiert Marktphasen basierend auf Preisbewegungen und Indikatoren."""
    
    def __init__(self):
        self.bullish_threshold = 2.0  # 2% Preissteigerung für Bullish
        self.bearish_threshold = -2.0  # -2% Preisrückgang für Bearish
        self.sideways_threshold = 0.5  # <0.5% Bewegung = Sideways
    
    def analyze_phase(self, df: pd.DataFrame, lookback_periods: int = 20) -> Dict[str, Any]:
        """
        Analysiert die aktuelle Marktphase basierend auf historischen Daten.
        
        Args:
            df: DataFrame mit OHLCV-Daten
            lookback_periods: Anzahl der Perioden für Analyse
            
        Returns:
            Dict mit phase, confidence, indicators, description
        """
        try:
            if len(df) < lookback_periods:
                logger.warning(f"Insufficient data for phase analysis. Need {lookback_periods}, got {len(df)}")
                return {
                    "phase": "UNKNOWN",
                    "confidence": 0.0,
                    "indicators": {},
                    "description": "Insufficient data"
                }
            
            # Use last N periods for analysis
            recent_data = df.tail(lookback_periods).copy()
            
            # Calculate price changes
            first_price = float(recent_data.iloc[0]['close'])
            last_price = float(recent_data.iloc[-1]['close'])
            price_change_pct = ((last_price - first_price) / first_price) * 100
            
            # Calculate trend strength
            highs = recent_data['high'].values
            lows = recent_data['low'].values
            closes = recent_data['close'].values
            
            # Calculate moving averages for trend
            sma_short = pd.Series(closes).rolling(window=5).mean().iloc[-1]
            sma_long = pd.Series(closes).rolling(window=lookback_periods).mean().iloc[-1]
            
            # Calculate volatility (standard deviation of returns)
            returns = pd.Series(closes).pct_change().dropna()
            volatility = returns.std() * 100
            
            # Calculate higher highs / lower lows pattern
            higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
            lower_lows = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])
            
            # Calculate momentum (rate of change)
            momentum = ((closes[-1] - closes[0]) / closes[0]) * 100
            
            # Determine phase
            phase = self._determine_phase(
                price_change_pct=price_change_pct,
                momentum=momentum,
                volatility=volatility,
                sma_short=sma_short,
                sma_long=sma_long,
                higher_highs=higher_highs,
                lower_lows=lower_lows,
                lookback_periods=lookback_periods
            )
            
            # Calculate confidence based on multiple factors
            confidence = self._calculate_confidence(
                price_change_pct=price_change_pct,
                momentum=momentum,
                volatility=volatility,
                sma_alignment=(sma_short, sma_long),
                higher_highs=higher_highs,
                lower_lows=lower_lows,
                lookback_periods=lookback_periods
            )
            
            # Generate description
            description = self._generate_description(phase, price_change_pct, momentum, volatility)
            
            return {
                "phase": phase,
                "confidence": confidence,
                "indicators": {
                    "price_change_pct": round(price_change_pct, 2),
                    "momentum": round(momentum, 2),
                    "volatility": round(volatility, 2),
                    "sma_short": round(float(sma_short), 8),
                    "sma_long": round(float(sma_long), 8),
                    "higher_highs": higher_highs,
                    "lower_lows": lower_lows,
                    "trend_strength": round(abs(momentum), 2)
                },
                "description": description
            }
        
        except Exception as e:
            logger.error(f"Error analyzing market phase: {e}", exc_info=True)
            return {
                "phase": "UNKNOWN",
                "confidence": 0.0,
                "indicators": {},
                "description": f"Error: {str(e)}"
            }
    
    def _determine_phase(self, price_change_pct: float, momentum: float, volatility: float,
                        sma_short: float, sma_long: float, higher_highs: int, lower_lows: int,
                        lookback_periods: int) -> MarketPhase:
        """Bestimmt die Marktphase basierend auf verschiedenen Indikatoren."""
        
        # Check for strong trends first
        if price_change_pct > self.bullish_threshold and momentum > 1.0:
            # Additional confirmation: higher highs and SMA alignment
            if higher_highs > lower_lows and sma_short > sma_long:
                return "BULLISH"
            elif higher_highs > lower_lows * 2:  # Strong bullish pattern
                return "BULLISH"
        
        if price_change_pct < self.bearish_threshold and momentum < -1.0:
            # Additional confirmation: lower lows and SMA alignment
            if lower_lows > higher_highs and sma_short < sma_long:
                return "BEARISH"
            elif lower_lows > higher_highs * 2:  # Strong bearish pattern
                return "BEARISH"
        
        # Check for sideways market
        if abs(price_change_pct) < self.sideways_threshold:
            return "SIDEWAYS"
        
        # Check volatility and range-bound movement
        if volatility < 1.0 and abs(momentum) < 0.5:
            return "SIDEWAYS"
        
        # Default classification based on price change
        if price_change_pct > 0:
            return "BULLISH"
        elif price_change_pct < 0:
            return "BEARISH"
        else:
            return "SIDEWAYS"
    
    def _calculate_confidence(self, price_change_pct: float, momentum: float, volatility: float,
                             sma_alignment: tuple, higher_highs: int, lower_lows: int,
                             lookback_periods: int) -> float:
        """Berechnet das Confidence-Level für die Marktphasen-Erkennung (0.0-1.0)."""
        
        sma_short, sma_long = sma_alignment
        
        # Base confidence from price change magnitude
        base_confidence = min(abs(price_change_pct) / 5.0, 1.0)  # Max confidence at 5% change
        
        # Momentum confirmation
        momentum_confirmation = min(abs(momentum) / 3.0, 1.0)
        
        # SMA alignment confirmation
        sma_confirmation = 1.0 if (sma_short > sma_long and price_change_pct > 0) or \
                                  (sma_short < sma_long and price_change_pct < 0) else 0.5
        
        # Pattern confirmation (higher highs / lower lows)
        total_patterns = higher_highs + lower_lows
        if total_patterns > 0:
            if price_change_pct > 0:
                pattern_confirmation = higher_highs / max(total_patterns, 1)
            else:
                pattern_confirmation = lower_lows / max(total_patterns, 1)
        else:
            pattern_confirmation = 0.5
        
        # Volatility adjustment (lower volatility = higher confidence in trend)
        volatility_factor = max(0.5, 1.0 - (volatility / 5.0))
        
        # Weighted average
        confidence = (
            base_confidence * 0.3 +
            momentum_confirmation * 0.25 +
            sma_confirmation * 0.25 +
            pattern_confirmation * 0.2
        ) * volatility_factor
        
        return round(min(max(confidence, 0.0), 1.0), 2)
    
    def _generate_description(self, phase: MarketPhase, price_change_pct: float,
                             momentum: float, volatility: float) -> str:
        """Generiert eine beschreibende Nachricht für die Marktphase."""
        
        if phase == "BULLISH":
            return f"Bullischer Markt erkannt: Preissteigerung {price_change_pct:.2f}%, Momentum {momentum:.2f}%, Volatilität {volatility:.2f}%"
        elif phase == "BEARISH":
            return f"Bärischer Markt erkannt: Preisrückgang {abs(price_change_pct):.2f}%, Momentum {momentum:.2f}%, Volatilität {volatility:.2f}%"
        elif phase == "SIDEWAYS":
            return f"Seitwärtsmarkt erkannt: Preisbewegung {price_change_pct:.2f}%, Momentum {momentum:.2f}%, Volatilität {volatility:.2f}%"
        else:
            return "Unklare Marktphase"

