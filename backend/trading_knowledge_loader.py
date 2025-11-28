"""
Trading Knowledge Loader - Lädt Trading-Wissen aus Web-Ressourcen für Agents
"""

import logging
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
import json

logger = logging.getLogger(__name__)

# Trading Knowledge Sources (können erweitert werden)
TRADING_KNOWLEDGE_SOURCES = {
    "crypto_trading_basics": {
        "name": "Crypto Trading Basics",
        "url": "https://www.investopedia.com/cryptocurrency-4427699",
        "enabled": True,
        "category": "basics"
    },
    "technical_analysis": {
        "name": "Technical Analysis",
        "url": "https://www.investopedia.com/technical-analysis-4689657",
        "enabled": True,
        "category": "analysis"
    },
    "market_phases": {
        "name": "Market Phases Trading",
        "url": "https://www.investopedia.com/trading/bull-and-bear-markets-4843774",
        "enabled": True,
        "category": "market_phases"
    }
}

# Strategie-Mapping für verschiedene Marktphasen
STRATEGY_MARKET_PHASE_MAPPING = {
    "BULLISH": {
        "best_strategies": ["ma_crossover", "macd", "combined"],
        "description": "Bullische Märkte: MA Crossover und MACD funktionieren gut bei Aufwärtstrends",
        "recommendations": [
            "Verwende Trend-folgende Strategien wie MA Crossover",
            "MACD ist effektiv bei starken Trends",
            "RSI kann Overbought-Signale geben, aber vorsichtig sein",
            "Bollinger Bands helfen bei Volatilitätserkennung"
        ]
    },
    "BEARISH": {
        "best_strategies": ["rsi", "bollinger_bands", "combined"],
        "description": "Bärische Märkte: RSI und Bollinger Bands helfen bei Oversold-Erkennung",
        "recommendations": [
            "RSI ist nützlich für Oversold-Bounce-Erkennung",
            "Bollinger Bands zeigen Volatilitätsspitzen",
            "Vorsicht bei Trend-folgenden Strategien",
            "Kombinierte Strategien können robust sein"
        ]
    },
    "SIDEWAYS": {
        "best_strategies": ["rsi", "bollinger_bands", "combined"],
        "description": "Seitwärtsmärkte: Range-Trading-Strategien sind am besten",
        "recommendations": [
            "RSI funktioniert gut bei Range-Bound Märkten",
            "Bollinger Bands zeigen Support/Resistance",
            "Range-Trading: Kaufen bei Support, Verkaufen bei Resistance",
            "Kombinierte Strategien für bessere Filterung"
        ]
    }
}

class TradingKnowledgeLoader:
    """Lädt und verwaltet Trading-Wissen für Agents."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["trading_knowledge"]
        self.http_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self.cache = {}
        self.cache_ttl = timedelta(hours=24)  # 24 Stunden Cache
    
    async def load_trading_knowledge(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Lädt Trading-Wissen aus verschiedenen Quellen.
        
        Args:
            force_refresh: Wenn True, lädt neu auch wenn Cache vorhanden
            
        Returns:
            Dict mit Trading-Wissen
        """
        try:
            # Prüfe Cache
            if not force_refresh:
                cached = await self._get_cached_knowledge()
                if cached:
                    logger.info("Using cached trading knowledge")
                    return cached
            
            # Lade Wissen aus verschiedenen Quellen
            knowledge = {
                "market_phases": self._get_market_phase_knowledge(),
                "strategy_mapping": STRATEGY_MARKET_PHASE_MAPPING,
                "trading_basics": self._get_trading_basics_knowledge(),
                "indicator_guidelines": self._get_indicator_guidelines(),
                "risk_management": self._get_risk_management_knowledge(),
                "loaded_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Speichere in Cache
            await self._cache_knowledge(knowledge)
            
            logger.info("Trading knowledge loaded successfully")
            return knowledge
        
        except Exception as e:
            logger.error(f"Error loading trading knowledge: {e}", exc_info=True)
            return self._get_fallback_knowledge()
    
    def _get_market_phase_knowledge(self) -> Dict[str, Any]:
        """Gibt Wissen über Marktphasen zurück."""
        return {
            "BULLISH": {
                "characteristics": [
                    "Steigende Preise über längeren Zeitraum",
                    "Höhere Hochs und höhere Tiefs",
                    "Positive Momentum-Indikatoren",
                    "Starke Kaufsignale"
                ],
                "trading_approach": [
                    "Trend-folgende Strategien nutzen",
                    "Buy the dip Strategie",
                    "Trailing Stop für Gewinnmitnahme",
                    "Vorsicht vor Overbought-Signalen"
                ]
            },
            "BEARISH": {
                "characteristics": [
                    "Fallende Preise über längeren Zeitraum",
                    "Tiefere Hochs und tiefere Tiefs",
                    "Negative Momentum-Indikatoren",
                    "Starke Verkaufssignale"
                ],
                "trading_approach": [
                    "Defensive Strategien bevorzugen",
                    "Oversold-Bounce-Erkennung",
                    "Schnelle Gewinnmitnahme",
                    "Strikte Stop-Loss-Regeln"
                ]
            },
            "SIDEWAYS": {
                "characteristics": [
                    "Seitwärtsbewegung ohne klaren Trend",
                    "Range-Bound Preise",
                    "Niedrige Volatilität möglich",
                    "Wechselnde Signale"
                ],
                "trading_approach": [
                    "Range-Trading-Strategien",
                    "Support/Resistance-Levels nutzen",
                    "Kombinierte Indikatoren für bessere Signale",
                    "Vorsicht bei Breakout-Fälschungen"
                ]
            }
        }
    
    def _get_trading_basics_knowledge(self) -> Dict[str, Any]:
        """Gibt grundlegendes Trading-Wissen zurück."""
        return {
            "principles": [
                "Profitabilität nach Gebühren ist entscheidend",
                "Risikomanagement ist wichtiger als Gewinnmaximierung",
                "Nicht alle Signale handeln - Qualität über Quantität",
                "Marktphasen beeinflussen Strategie-Wirksamkeit",
                "Diversifikation reduziert Risiken"
            ],
            "common_mistakes": [
                "Überhäufiges Trading führt zu hohen Gebühren",
                "Ignorieren von Stop-Loss-Regeln",
                "Emotionale Entscheidungen statt datenbasierte",
                "Nicht Berücksichtigung von Marktphasen",
                "Zu hohes Risiko pro Trade"
            ],
            "best_practices": [
                "Immer Stop-Loss und Take-Profit setzen",
                "Marktphase berücksichtigen bei Strategie-Auswahl",
                "Geduld: Warten auf qualitativ hochwertige Signale",
                "Lernen aus vergangenen Trades",
                "Kombinierte Indikatoren für bessere Signale"
            ]
        }
    
    def _get_indicator_guidelines(self) -> Dict[str, Any]:
        """Gibt Richtlinien für verschiedene Indikatoren zurück."""
        return {
            "ma_crossover": {
                "best_for": ["BULLISH", "SIDEWAYS"],
                "description": "Funktioniert gut in Trend-Märkten",
                "usage": "Kaufen wenn Fast MA über Slow MA kreuzt, verkaufen bei umgekehrtem Crossover"
            },
            "rsi": {
                "best_for": ["BEARISH", "SIDEWAYS"],
                "description": "Effektiv für Overbought/Oversold-Erkennung",
                "usage": "Oversold (<30) = potenzieller Kauf, Overbought (>70) = potenzieller Verkauf"
            },
            "macd": {
                "best_for": ["BULLISH", "BEARISH"],
                "description": "Trend-Stärke und Momentum",
                "usage": "MACD Line über Signal Line = Bullish, umgekehrt = Bearish"
            },
            "bollinger_bands": {
                "best_for": ["SIDEWAYS", "BULLISH"],
                "description": "Volatilität und Support/Resistance",
                "usage": "Preis am unteren Band = potenzieller Kauf, am oberen Band = potenzieller Verkauf"
            },
            "combined": {
                "best_for": ["BULLISH", "BEARISH", "SIDEWAYS"],
                "description": "Kombiniert mehrere Indikatoren für robuste Signale",
                "usage": "Erfordert Übereinstimmung mehrerer Indikatoren für höhere Confidence"
            }
        }
    
    def _get_risk_management_knowledge(self) -> Dict[str, Any]:
        """Gibt Risikomanagement-Wissen zurück."""
        return {
            "rules": [
                "Niemals mehr als 2% des Kapitals pro Trade riskieren",
                "Stop-Loss immer setzen (aktuell -2%)",
                "Trailing Stop für Gewinnmitnahme nutzen",
                "Diversifikation über verschiedene Assets",
                "Gebühren bei jeder Entscheidung berücksichtigen"
            ],
            "position_sizing": [
                "Basierend auf verfügbarem Kapital",
                "Berücksichtigung von Volatilität",
                "Nie mehr als verfügbares Budget",
                "Anpassung basierend auf Confidence-Level"
            ],
            "profit_targets": [
                "Trailing Stop: 3% Rückgang vom Höchstpreis",
                "Mindestens 2% Gewinn vor aktivierung",
                "Levels: 2%, 5%, 8%, 11%, etc.",
                "Nie unter Gebühren-Schwelle verkaufen"
            ]
        }
    
    async def _get_cached_knowledge(self) -> Optional[Dict[str, Any]]:
        """Holt gecachtes Wissen aus der Datenbank."""
        try:
            cached = await self.collection.find_one(
                {"type": "trading_knowledge"},
                sort=[("loaded_at", -1)]
            )
            
            if cached:
                loaded_at = datetime.fromisoformat(cached.get("loaded_at", ""))
                if datetime.now(timezone.utc) - loaded_at < self.cache_ttl:
                    return cached.get("content", {})
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting cached knowledge: {e}")
            return None
    
    async def _cache_knowledge(self, knowledge: Dict[str, Any]):
        """Speichert Wissen im Cache."""
        try:
            await self.collection.update_one(
                {"type": "trading_knowledge"},
                {
                    "$set": {
                        "type": "trading_knowledge",
                        "content": knowledge,
                        "loaded_at": datetime.now(timezone.utc).isoformat()
                    }
                },
                upsert=True
            )
        
        except Exception as e:
            logger.error(f"Error caching knowledge: {e}")
    
    def _get_fallback_knowledge(self) -> Dict[str, Any]:
        """Gibt Fallback-Wissen zurück falls Laden fehlschlägt."""
        return {
            "market_phases": self._get_market_phase_knowledge(),
            "strategy_mapping": STRATEGY_MARKET_PHASE_MAPPING,
            "trading_basics": self._get_trading_basics_knowledge(),
            "indicator_guidelines": self._get_indicator_guidelines(),
            "risk_management": self._get_risk_management_knowledge(),
            "loaded_at": datetime.now(timezone.utc).isoformat(),
            "fallback": True
        }
    
    def get_strategy_for_phase(self, phase: str) -> Dict[str, Any]:
        """Gibt empfohlene Strategien für eine Marktphase zurück."""
        return STRATEGY_MARKET_PHASE_MAPPING.get(phase.upper(), {
            "best_strategies": ["combined"],
            "description": "Unbekannte Marktphase - kombinierte Strategie empfohlen",
            "recommendations": ["Vorsichtige Trading-Entscheidungen treffen"]
        })

