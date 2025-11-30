"""
Candle Tracker - System für kontinuierliches Kerzen-Tracking
Sammelt die letzten 200 Kerzen für laufende Bots und verfolgt 200 Kerzen nach Verkäufen
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from binance_client import BinanceClientWrapper
import pandas as pd

logger = logging.getLogger(__name__)

# Konstanten für Tracking
PRE_TRADE_CANDLES = 200  # Anzahl Kerzen vor Trade
POST_TRADE_CANDLES = 200  # Anzahl Kerzen nach Verkauf
POSITION_TRACKING_UNLIMITED = True  # Position-Tracking sammelt alle Kerzen während Position offen ist
CANDLE_TRACKING_INTERVAL_SECONDS = 300  # 5 Minuten - entspricht Bot-Loop

class CandleTracker:
    """
    Tracking-System für Kerzendaten:
    - Pre-Trade: Sammle die letzten 200 Kerzen vor jeder Trade-Entscheidung
    - Post-Trade: Verfolge 200 Kerzen nach Verkauf für Learning
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, binance_client: BinanceClientWrapper):
        self.db = db
        self.binance_client = binance_client
        self.collection = db.bot_candles
        self.post_trade_tracking = {}  # {trade_id: tracking_info} für aktive Post-Trade-Tracks
        self.position_tracking = {}  # {bot_id: tracking_info} für aktive Position-Tracks
    
    async def track_pre_trade_candles(self, bot_id: str, symbol: str, timeframe: str, limit: int = PRE_TRADE_CANDLES) -> Dict[str, Any]:
        """
        Sammle und speichere die letzten 200 Kerzen vor einer Trade-Entscheidung.
        
        Args:
            bot_id: Bot-ID
            symbol: Trading-Symbol (z.B. BTCUSDT)
            timeframe: Timeframe (z.B. "5m")
            limit: Anzahl Kerzen (default: 200)
        
        Returns:
            Dict mit Tracking-Informationen
        """
        try:
            # Hole Kerzendaten von Binance
            market_data = self.binance_client.get_market_data(symbol, interval=timeframe, limit=limit)
            
            if market_data.empty or len(market_data) < 10:
                logger.warning(f"CandleTracker: Nicht genug Kerzendaten für {symbol} ({len(market_data)} Kerzen)")
                return {"success": False, "error": "Insufficient data"}
            
            # Konvertiere DataFrame zu Dict-Liste für MongoDB
            candles_data = []
            for _, row in market_data.iterrows():
                candle = {
                    "timestamp": row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp']),
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close']),
                    "volume": float(row['volume'])
                }
                candles_data.append(candle)
            
            # Speichere oder aktualisiere Pre-Trade-Tracking
            tracking_doc = {
                "bot_id": bot_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "phase": "pre_trade",
                "candles": candles_data,
                "count": len(candles_data),
                "start_timestamp": candles_data[0]["timestamp"] if candles_data else None,
                "end_timestamp": candles_data[-1]["timestamp"] if candles_data else None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "trade_id": None  # Kein Trade-Verknüpfung für Pre-Trade
            }
            
            # Update oder Insert
            await self.collection.update_one(
                {
                    "bot_id": bot_id,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "phase": "pre_trade"
                },
                {"$set": tracking_doc},
                upsert=True
            )
            
            logger.info(f"CandleTracker: Pre-Trade-Kerzen für Bot {bot_id} ({symbol}) aktualisiert: {len(candles_data)} Kerzen")
            
            return {
                "success": True,
                "bot_id": bot_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "phase": "pre_trade",
                "count": len(candles_data),
                "oldest_timestamp": candles_data[0]["timestamp"] if candles_data else None,
                "latest_timestamp": candles_data[-1]["timestamp"] if candles_data else None
            }
        
        except Exception as e:
            logger.error(f"CandleTracker: Fehler beim Pre-Trade-Tracking für Bot {bot_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def start_post_trade_tracking(self, bot_id: str, symbol: str, timeframe: str, trade_id: str) -> Dict[str, Any]:
        """
        Starte Post-Trade-Tracking nach einem Verkauf.
        Verfolge die nächsten 200 Kerzen nach dem Verkauf, um zu lernen, ob der Verkauf optimal war.
        
        Args:
            bot_id: Bot-ID
            symbol: Trading-Symbol
            timeframe: Timeframe
            trade_id: Order-ID des Trades
        
        Returns:
            Dict mit Tracking-Informationen
        """
        try:
            # Initialisiere Post-Trade-Tracking mit leeren Kerzen
            tracking_doc = {
                "bot_id": bot_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "phase": "post_trade",
                "trade_id": trade_id,
                "candles": [],
                "count": 0,
                "start_timestamp": datetime.now(timezone.utc).isoformat(),
                "end_timestamp": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "target_count": POST_TRADE_CANDLES
            }
            
            # Speichere initiales Tracking-Dokument
            await self.collection.insert_one(tracking_doc)
            
            # Speichere in Memory für Updates
            self.post_trade_tracking[trade_id] = {
                "bot_id": bot_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "target_count": POST_TRADE_CANDLES,
                "start_time": datetime.now(timezone.utc)
            }
            
            logger.info(f"CandleTracker: Post-Trade-Tracking gestartet für Trade {trade_id} (Bot {bot_id}, {symbol})")
            
            return {
                "success": True,
                "trade_id": trade_id,
                "bot_id": bot_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "phase": "post_trade",
                "target_count": POST_TRADE_CANDLES,
                "current_count": 0
            }
        
        except Exception as e:
            logger.error(f"CandleTracker: Fehler beim Starten von Post-Trade-Tracking für Trade {trade_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def update_post_trade_tracking(self, trade_id: str) -> Dict[str, Any]:
        """
        Aktualisiere Post-Trade-Tracking mit neuen Kerzen.
        Wird regelmäßig aufgerufen, bis 200 Kerzen erreicht sind.
        
        Args:
            trade_id: Order-ID des Trades
        
        Returns:
            Dict mit Tracking-Status
        """
        try:
            # Prüfe, ob Tracking aktiv ist
            if trade_id not in self.post_trade_tracking:
                # Versuche aus DB zu laden
                existing = await self.collection.find_one({"trade_id": trade_id, "phase": "post_trade"})
                if not existing:
                    return {"success": False, "error": "Post-Trade-Tracking nicht gefunden"}
                
                self.post_trade_tracking[trade_id] = {
                    "bot_id": existing["bot_id"],
                    "symbol": existing["symbol"],
                    "timeframe": existing["timeframe"],
                    "target_count": existing.get("target_count", POST_TRADE_CANDLES),
                    "start_time": datetime.fromisoformat(existing["start_timestamp"])
                }
            
            tracking_info = self.post_trade_tracking[trade_id]
            bot_id = tracking_info["bot_id"]
            symbol = tracking_info["symbol"]
            timeframe = tracking_info["timeframe"]
            target_count = tracking_info["target_count"]
            
            # Hole bestehende Kerzen
            existing_doc = await self.collection.find_one({"trade_id": trade_id, "phase": "post_trade"})
            if not existing_doc:
                return {"success": False, "error": "Tracking-Dokument nicht gefunden"}
            
            current_count = existing_doc.get("count", 0)
            
            # Prüfe, ob wir bereits genug Kerzen haben
            if current_count >= target_count:
                logger.debug(f"CandleTracker: Post-Trade-Tracking für Trade {trade_id} bereits abgeschlossen ({current_count}/{target_count})")
                return {
                    "success": True,
                    "trade_id": trade_id,
                    "status": "completed",
                    "current_count": current_count,
                    "target_count": target_count
                }
            
            # Berechne, wie viele neue Kerzen benötigt werden
            needed = target_count - current_count
            
            # Hole Kerzendaten seit Start des Trackings
            # Berechne Start-Zeitpunkt (nach dem Verkauf)
            start_time = tracking_info["start_time"]
            
            # Hole Kerzendaten (mehr als benötigt, um sicherzustellen, dass wir genug haben)
            market_data = self.binance_client.get_market_data(symbol, interval=timeframe, limit=min(needed + 10, 250))
            
            if market_data.empty:
                return {"success": False, "error": "Keine Kerzendaten verfügbar"}
            
            # Filtere Kerzen, die nach dem Start-Zeitpunkt liegen
            existing_candles = existing_doc.get("candles", [])
            existing_timestamps = {c["timestamp"] for c in existing_candles}
            
            new_candles = []
            for _, row in market_data.iterrows():
                candle_timestamp = row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp'])
                
                # Überspringe bereits vorhandene Kerzen
                if candle_timestamp in existing_timestamps:
                    continue
                
                # Füge nur Kerzen hinzu, die nach Start-Zeit liegen
                candle_datetime = pd.to_datetime(row['timestamp'])
                if candle_datetime >= start_time:
                    candle = {
                        "timestamp": candle_timestamp,
                        "open": float(row['open']),
                        "high": float(row['high']),
                        "low": float(row['low']),
                        "close": float(row['close']),
                        "volume": float(row['volume'])
                    }
                    new_candles.append(candle)
            
            # Kombiniere alte und neue Kerzen
            all_candles = existing_candles + new_candles
            
            # Sortiere nach Timestamp und begrenze auf target_count
            all_candles.sort(key=lambda x: x["timestamp"])
            all_candles = all_candles[:target_count]
            
            # Aktualisiere Dokument
            update_doc = {
                "candles": all_candles,
                "count": len(all_candles),
                "end_timestamp": all_candles[-1]["timestamp"] if all_candles else None,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.collection.update_one(
                {"trade_id": trade_id, "phase": "post_trade"},
                {"$set": update_doc}
            )
            
            is_completed = len(all_candles) >= target_count
            
            if is_completed:
                logger.info(f"CandleTracker: Post-Trade-Tracking für Trade {trade_id} abgeschlossen ({len(all_candles)}/{target_count} Kerzen)")
                # Entferne aus Memory (optional - kann auch drin bleiben für späteres Abfragen)
            
            return {
                "success": True,
                "trade_id": trade_id,
                "status": "completed" if is_completed else "in_progress",
                "current_count": len(all_candles),
                "target_count": target_count,
                "new_candles_added": len(new_candles)
            }
        
        except Exception as e:
            logger.error(f"CandleTracker: Fehler beim Aktualisieren von Post-Trade-Tracking für Trade {trade_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def get_bot_candles(self, bot_id: str, phase: str = "pre_trade", symbol: Optional[str] = None, timeframe: Optional[str] = None) -> Dict[str, Any]:
        """
        Hole gesammelte Kerzendaten für einen Bot.
        
        Args:
            bot_id: Bot-ID
            phase: "pre_trade", "post_trade", "during_trade" oder "all"
            symbol: Optional: Filter nach Symbol
            timeframe: Optional: Filter nach Timeframe
        
        Returns:
            Dict mit Kerzendaten
        """
        try:
            if phase == "all":
                query = {"bot_id": bot_id}
            else:
                query = {"bot_id": bot_id, "phase": phase}
                
            if symbol:
                query["symbol"] = symbol
            if timeframe:
                query["timeframe"] = timeframe
            
            # Für "during_trade" nur aktive oder geschlossene Positionen (nicht gelöschte)
            if phase == "during_trade":
                query["position_status"] = {"$in": ["open", "closed"]}
            
            docs = await self.collection.find(query).sort("updated_at", -1).to_list(100)
            
            results = []
            for doc in docs:
                results.append({
                    "bot_id": doc.get("bot_id"),
                    "symbol": doc.get("symbol"),
                    "timeframe": doc.get("timeframe"),
                    "phase": doc.get("phase"),
                    "trade_id": doc.get("trade_id"),
                    "count": doc.get("count", 0),
                    "start_timestamp": doc.get("start_timestamp"),
                    "end_timestamp": doc.get("end_timestamp"),
                    "updated_at": doc.get("updated_at"),
                    "candles": doc.get("candles", [])
                })
            
            return {
                "success": True,
                "count": len(results),
                "candles_data": results
            }
        
        except Exception as e:
            logger.error(f"CandleTracker: Fehler beim Abrufen von Kerzendaten für Bot {bot_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e), "count": 0, "candles_data": []}
    
    async def get_trade_candles(self, trade_id: str, phase: str = "post_trade") -> Dict[str, Any]:
        """
        Hole Kerzendaten für einen spezifischen Trade.
        
        Args:
            trade_id: Order-ID des Trades
            phase: "pre_trade" oder "post_trade"
        
        Returns:
            Dict mit Kerzendaten
        """
        try:
            doc = await self.collection.find_one({"trade_id": trade_id, "phase": phase})
            
            if not doc:
                return {
                    "success": False,
                    "error": "Keine Kerzendaten für diesen Trade gefunden",
                    "count": 0,
                    "candles": []
                }
            
            return {
                "success": True,
                "trade_id": trade_id,
                "bot_id": doc.get("bot_id"),
                "symbol": doc.get("symbol"),
                "timeframe": doc.get("timeframe"),
                "phase": doc.get("phase"),
                "count": doc.get("count", 0),
                "start_timestamp": doc.get("start_timestamp"),
                "end_timestamp": doc.get("end_timestamp"),
                "updated_at": doc.get("updated_at"),
                "candles": doc.get("candles", [])
            }
        
        except Exception as e:
            logger.error(f"CandleTracker: Fehler beim Abrufen von Trade-Kerzen für {trade_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e), "count": 0, "candles": []}
    
    async def start_position_tracking(self, bot_id: str, symbol: str, timeframe: str, buy_trade_id: str) -> Dict[str, Any]:
        """
        Starte Position-Tracking nach einem BUY.
        Sammelt kontinuierlich alle Kerzen während die Position offen ist.
        
        Args:
            bot_id: Bot-ID
            symbol: Trading-Symbol
            timeframe: Timeframe
            buy_trade_id: Order-ID des BUY-Trades
        
        Returns:
            Dict mit Tracking-Informationen
        """
        try:
            # Initialisiere Position-Tracking
            tracking_doc = {
                "bot_id": bot_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "phase": "during_trade",
                "buy_trade_id": buy_trade_id,
                "candles": [],
                "count": 0,
                "start_timestamp": datetime.now(timezone.utc).isoformat(),
                "end_timestamp": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "position_status": "open"
            }
            
            # Speichere initiales Tracking-Dokument
            await self.collection.insert_one(tracking_doc)
            
            # Speichere in Memory für Updates
            self.position_tracking[bot_id] = {
                "symbol": symbol,
                "timeframe": timeframe,
                "buy_trade_id": buy_trade_id,
                "start_time": datetime.now(timezone.utc)
            }
            
            logger.info(f"CandleTracker: Position-Tracking gestartet für Bot {bot_id} ({symbol}) nach BUY {buy_trade_id}")
            
            return {
                "success": True,
                "bot_id": bot_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "buy_trade_id": buy_trade_id,
                "phase": "during_trade",
                "status": "started"
            }
        
        except Exception as e:
            logger.error(f"CandleTracker: Fehler beim Starten von Position-Tracking für Bot {bot_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def update_position_tracking(self, bot_id: str) -> Dict[str, Any]:
        """
        Aktualisiere Position-Tracking mit neuen Kerzen.
        Wird regelmäßig aufgerufen, während die Position offen ist.
        
        Args:
            bot_id: Bot-ID
        
        Returns:
            Dict mit Tracking-Status
        """
        try:
            # Prüfe, ob Tracking aktiv ist
            if bot_id not in self.position_tracking:
                # Versuche aus DB zu laden
                existing = await self.collection.find_one({
                    "bot_id": bot_id,
                    "phase": "during_trade",
                    "position_status": "open"
                })
                if not existing:
                    return {"success": False, "error": "Position-Tracking nicht gefunden"}
                
                self.position_tracking[bot_id] = {
                    "symbol": existing["symbol"],
                    "timeframe": existing["timeframe"],
                    "buy_trade_id": existing.get("buy_trade_id"),
                    "start_time": datetime.fromisoformat(existing["start_timestamp"])
                }
            
            tracking_info = self.position_tracking[bot_id]
            symbol = tracking_info["symbol"]
            timeframe = tracking_info["timeframe"]
            start_time = tracking_info["start_time"]
            
            # Hole bestehende Kerzen
            existing_doc = await self.collection.find_one({
                "bot_id": bot_id,
                "phase": "during_trade",
                "position_status": "open"
            })
            if not existing_doc:
                return {"success": False, "error": "Tracking-Dokument nicht gefunden"}
            
            existing_candles = existing_doc.get("candles", [])
            existing_timestamps = {c["timestamp"] for c in existing_candles}
            
            # Hole neue Kerzen seit dem letzten Update (oder seit Start)
            # Hole mehr Kerzen als nötig, um sicherzustellen, dass wir alle bekommen
            market_data = self.binance_client.get_market_data(symbol, interval=timeframe, limit=100)
            
            if market_data.empty:
                return {"success": False, "error": "Keine Kerzendaten verfügbar"}
            
            # Filtere neue Kerzen (die nach Start-Zeit liegen und noch nicht vorhanden sind)
            new_candles = []
            for _, row in market_data.iterrows():
                candle_timestamp = row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp'])
                
                # Überspringe bereits vorhandene Kerzen
                if candle_timestamp in existing_timestamps:
                    continue
                
                # Füge nur Kerzen hinzu, die nach Start-Zeit liegen
                candle_datetime = pd.to_datetime(row['timestamp'])
                if candle_datetime >= start_time:
                    candle = {
                        "timestamp": candle_timestamp,
                        "open": float(row['open']),
                        "high": float(row['high']),
                        "low": float(row['low']),
                        "close": float(row['close']),
                        "volume": float(row['volume'])
                    }
                    new_candles.append(candle)
            
            # Kombiniere alte und neue Kerzen
            all_candles = existing_candles + new_candles
            
            # Sortiere nach Timestamp
            all_candles.sort(key=lambda x: x["timestamp"])
            
            # Aktualisiere Dokument
            update_doc = {
                "candles": all_candles,
                "count": len(all_candles),
                "end_timestamp": all_candles[-1]["timestamp"] if all_candles else None,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.collection.update_one(
                {"bot_id": bot_id, "phase": "during_trade", "position_status": "open"},
                {"$set": update_doc}
            )
            
            logger.debug(f"CandleTracker: Position-Tracking für Bot {bot_id} aktualisiert: {len(all_candles)} Kerzen gesammelt")
            
            return {
                "success": True,
                "bot_id": bot_id,
                "status": "tracking",
                "current_count": len(all_candles),
                "new_candles_added": len(new_candles)
            }
        
        except Exception as e:
            logger.error(f"CandleTracker: Fehler beim Aktualisieren von Position-Tracking für Bot {bot_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def stop_position_tracking(self, bot_id: str, sell_trade_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Stoppe Position-Tracking beim Verkauf (SELL).
        
        Args:
            bot_id: Bot-ID
            sell_trade_id: Optional: Order-ID des SELL-Trades
        
        Returns:
            Dict mit finalen Tracking-Informationen
        """
        try:
            # Finde aktives Position-Tracking
            tracking_doc = await self.collection.find_one({
                "bot_id": bot_id,
                "phase": "during_trade",
                "position_status": "open"
            })
            
            if not tracking_doc:
                return {"success": False, "error": "Aktives Position-Tracking nicht gefunden"}
            
            # Markiere als geschlossen
            update_doc = {
                "position_status": "closed",
                "sell_trade_id": sell_trade_id,
                "end_timestamp": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.collection.update_one(
                {"bot_id": bot_id, "phase": "during_trade", "position_status": "open"},
                {"$set": update_doc}
            )
            
            # Entferne aus Memory
            if bot_id in self.position_tracking:
                del self.position_tracking[bot_id]
            
            candle_count = tracking_doc.get("count", 0)
            logger.info(f"CandleTracker: Position-Tracking für Bot {bot_id} gestoppt ({candle_count} Kerzen gesammelt)")
            
            return {
                "success": True,
                "bot_id": bot_id,
                "buy_trade_id": tracking_doc.get("buy_trade_id"),
                "sell_trade_id": sell_trade_id,
                "candles_collected": candle_count,
                "start_timestamp": tracking_doc.get("start_timestamp"),
                "end_timestamp": update_doc["end_timestamp"]
            }
        
        except Exception as e:
            logger.error(f"CandleTracker: Fehler beim Stoppen von Position-Tracking für Bot {bot_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def cleanup_old_tracking(self, days_to_keep: int = 30):
        """
        Bereinige alte Tracking-Daten (älter als days_to_keep Tage).
        
        Args:
            days_to_keep: Anzahl Tage, die Daten behalten werden sollen
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            cutoff_iso = cutoff_date.isoformat()
            
            result = await self.collection.delete_many({
                "updated_at": {"$lt": cutoff_iso},
                "phase": {"$in": ["pre_trade", "post_trade", "during_trade"]}
            })
            
            logger.info(f"CandleTracker: {result.deleted_count} alte Tracking-Daten gelöscht (älter als {days_to_keep} Tage)")
            return result.deleted_count
        
        except Exception as e:
            logger.error(f"CandleTracker: Fehler beim Bereinigen alter Tracking-Daten: {e}", exc_info=True)
            return 0

