"""
Trading Pairs Cache - Cached alle verfügbaren Handelspaare von Binance
Aktualisiert alle 2 Stunden automatisch
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from binance_client import BinanceClientWrapper

logger = logging.getLogger(__name__)

# Cache-Update-Intervall: 2 Stunden
CACHE_UPDATE_INTERVAL_SECONDS = 7200  # 2 Stunden


class TradingPairsCache:
    """Cached alle verfügbaren Handelspaare von Binance."""
    
    def __init__(self, binance_client: Optional[BinanceClientWrapper] = None):
        self.binance_client = binance_client
        self.cache: Dict[str, Any] = {
            "pairs": [],
            "pairs_by_base": {},  # {baseAsset: [pairs]}
            "pairs_by_quote": {},  # {quoteAsset: [pairs]}
            "last_updated": None,
            "total_count": 0
        }
        self.is_updating = False
        self.update_task = None
    
    async def start(self):
        """Startet den Cache-Update-Task."""
        if self.update_task is None:
            logger.info("Starting Trading Pairs Cache updater (2h interval)")
            # Initial update
            await self.update_cache()
            # Start periodic update
            self.update_task = asyncio.create_task(self._update_loop())
    
    async def stop(self):
        """Stoppt den Cache-Update-Task."""
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
            self.update_task = None
    
    async def _update_loop(self):
        """Periodischer Update-Loop (alle 2 Stunden)."""
        while True:
            try:
                await asyncio.sleep(CACHE_UPDATE_INTERVAL_SECONDS)
                await self.update_cache()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in trading pairs cache update loop: {e}", exc_info=True)
                # Retry after 5 minutes on error
                await asyncio.sleep(300)
    
    async def update_cache(self) -> bool:
        """Aktualisiert den Cache mit allen verfügbaren Handelspaaren."""
        if self.is_updating:
            logger.warning("Cache update already in progress, skipping")
            return False
        
        if not self.binance_client:
            logger.warning("Binance client not available, cannot update cache")
            return False
        
        self.is_updating = True
        try:
            logger.info("Updating trading pairs cache...")
            
            # Get all tradable symbols from Binance
            pairs = self.binance_client.get_tradable_symbols()
            
            if not pairs:
                logger.warning("No tradable pairs retrieved from Binance")
                return False
            
            # Organize pairs by base and quote asset
            pairs_by_base = {}
            pairs_by_quote = {}
            
            for pair in pairs:
                base_asset = pair.get("baseAsset", "")
                quote_asset = pair.get("quoteAsset", "")
                
                # Group by base asset
                if base_asset not in pairs_by_base:
                    pairs_by_base[base_asset] = []
                pairs_by_base[base_asset].append(pair)
                
                # Group by quote asset
                if quote_asset not in pairs_by_quote:
                    pairs_by_quote[quote_asset] = []
                pairs_by_quote[quote_asset].append(pair)
            
            # Update cache
            self.cache = {
                "pairs": pairs,
                "pairs_by_base": pairs_by_base,
                "pairs_by_quote": pairs_by_quote,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "total_count": len(pairs)
            }
            
            logger.info(f"Trading pairs cache updated: {len(pairs)} pairs (last updated: {self.cache['last_updated']})")
            return True
            
        except Exception as e:
            logger.error(f"Error updating trading pairs cache: {e}", exc_info=True)
            return False
        finally:
            self.is_updating = False
    
    def get_all_pairs(self) -> List[Dict[str, Any]]:
        """Gibt alle gecachten Handelspaare zurück."""
        return self.cache.get("pairs", [])
    
    def get_pairs_by_base(self, base_asset: str) -> List[Dict[str, Any]]:
        """Gibt alle Paare für einen Base-Asset zurück (z.B. 'SOL' -> ['SOLUSDT', 'SOLBTC', 'SOLETH', ...])."""
        base_upper = base_asset.upper()
        return self.cache.get("pairs_by_base", {}).get(base_upper, [])
    
    def get_pairs_by_quote(self, quote_asset: str) -> List[Dict[str, Any]]:
        """Gibt alle Paare für einen Quote-Asset zurück (z.B. 'BTC' -> ['SOLBTC', 'ETHBTC', 'BNBBTC', ...])."""
        quote_upper = quote_asset.upper()
        return self.cache.get("pairs_by_quote", {}).get(quote_upper, [])
    
    def search_pairs(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Sucht nach Handelspaaren basierend auf Query.
        
        Args:
            query: Suchbegriff (z.B. "SOL", "BTC", "SOLBTC")
            limit: Maximale Anzahl Ergebnisse
        
        Returns:
            Liste von passenden Paaren
        """
        query_upper = query.upper()
        results = []
        
        for pair in self.cache.get("pairs", []):
            symbol = pair.get("symbol", "")
            base = pair.get("baseAsset", "")
            quote = pair.get("quoteAsset", "")
            
            # Match symbol, base, or quote
            if (query_upper in symbol or 
                query_upper in base or 
                query_upper in quote or
                symbol.startswith(query_upper)):
                results.append(pair)
                if len(results) >= limit:
                    break
        
        return results
    
    def is_pair_available(self, symbol: str) -> bool:
        """Prüft ob ein Symbol im Cache verfügbar ist."""
        symbol_upper = symbol.upper()
        for pair in self.cache.get("pairs", []):
            if pair.get("symbol", "").upper() == symbol_upper:
                return True
        return False
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Gibt Cache-Informationen zurück."""
        return {
            "total_pairs": self.cache.get("total_count", 0),
            "last_updated": self.cache.get("last_updated"),
            "is_updating": self.is_updating,
            "quote_assets": list(self.cache.get("pairs_by_quote", {}).keys()),
            "base_assets_count": len(self.cache.get("pairs_by_base", {}))
        }


# Global instance
_trading_pairs_cache: Optional[TradingPairsCache] = None


def get_trading_pairs_cache(binance_client: Optional[BinanceClientWrapper] = None) -> TradingPairsCache:
    """Gibt die globale Trading-Pairs-Cache-Instanz zurück."""
    global _trading_pairs_cache
    if _trading_pairs_cache is None:
        _trading_pairs_cache = TradingPairsCache(binance_client)
    elif binance_client and not _trading_pairs_cache.binance_client:
        _trading_pairs_cache.binance_client = binance_client
    return _trading_pairs_cache

