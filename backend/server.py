from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Request, status
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import json
import asyncio
import traceback

from config import settings
from agents import AgentManager
from bot_manager import BotManager, TradingBot
from constants import BOT_BROADCAST_INTERVAL_SECONDS
from validators import validate_all_services, validate_mongodb_connection
from mcp_server import create_mcp_server
from autonomous_manager import AutonomousManager
from trading_pairs_cache import get_trading_pairs_cache

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Suppress FLAML automl warning (we don't use flaml.automl, it's just a dependency)
import warnings
warnings.filterwarnings("ignore", message=".*flaml.automl is not available.*")

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection - use settings for consistency
# WICHTIG: MongoDB-Verbindung darf Import nicht blockieren!
try:
    mongo_url = settings.mongo_url
    db_name = settings.db_name
    client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)  # 5 Sekunden Timeout
    db = client[db_name]
    logger.info(f"MongoDB connection initialized for {db_name}")
    # Teste Verbindung nicht synchron beim Import (wird später getestet)
except Exception as e:
    logger.warning(f"Could not initialize MongoDB connection: {e}")
    # Erstelle Dummy-DB-Objekt, damit Import nicht fehlschlägt
    # Die Verbindung wird später bei Bedarf erneut versucht
    db = None
    logger.warning("MongoDB connection will be retried later")

# Create the main app without a prefix
app = FastAPI(
    title="Project CypherTrade API",
    description="AI-powered cryptocurrency trading system with Autogen agents",
    version="1.0.0"
)

# Add CORS middleware EARLY (before routes are added)
# Handle CORS origins: support both "*" and comma-separated list
cors_origins = ["*"]
if settings.cors_origins and settings.cors_origins.strip() and settings.cors_origins != "*":
    # Split by comma and strip whitespace
    cors_origins = [origin.strip() for origin in settings.cors_origins.split(',') if origin.strip()]

# Log CORS configuration for debugging
logger.info(f"CORS origins configured: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Initialize agents and bot manager
# WICHTIG: Initialisierung darf nicht fehlschlagen, wenn DB nicht verfügbar ist
agent_manager = None
bot_manager = None
default_bot = None

try:
    if db is not None:
        # Initialize agent_manager first, then bot_manager
        agent_manager = AgentManager(db, bot=None, binance_client=None)
        bot_manager = BotManager(db, agent_manager)
        # Update agent_manager with bot_manager reference
        agent_manager.bot = bot_manager
        # For backward compatibility, create a default bot instance
        default_bot = bot_manager.get_bot()
        logger.info("AgentManager and BotManager initialized successfully")
    else:
        logger.warning("DB not available during import - managers will be initialized on startup")
except Exception as e:
    logger.error(f"Failed to initialize AgentManager/BotManager during import: {e}", exc_info=True)
    logger.warning("Managers will be initialized on startup")

# Initialize MCP Server if enabled
# WICHTIG: MCP Server Initialisierung darf Import nicht blockieren
try:
    if db is not None and agent_manager is not None and bot_manager is not None:
        mcp_server = create_mcp_server(db, agent_manager, bot_manager)
        if mcp_server:
            app.include_router(mcp_server.router)
            logger.info("MCP Server routes registered")
    else:
        mcp_server = None
        logger.warning("MCP Server not initialized (DB or managers not available)")
except Exception as e:
    logger.warning(f"Could not initialize MCP Server: {e}")
    mcp_server = None

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                # Convert ObjectId to strings before sending
                clean_message = convert_objectid_to_str(message)
                await connection.send_json(clean_message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")

manager = ConnectionManager()

# Helper function to convert MongoDB ObjectId to string recursively
def convert_objectid_to_str(obj):
    """Recursively convert MongoDB ObjectId objects to strings."""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_objectid_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid_to_str(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_objectid_to_str(item) for item in obj)
    else:
        return obj

# Pydantic Models
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User message to NexusChat")

class ChatResponse(BaseModel):
    success: bool
    response: str
    agent: str
    timestamp: str

class BotStartRequest(BaseModel):
    strategy: str = "ma_crossover"
    symbol: str = "BTCUSDT"
    amount: float = 100.0
    timeframe: str = "5m"  # Trading timeframe: 1m, 5m, 15m, 30m, 1h, 4h, 1d
    trading_mode: str = "SPOT"  # SPOT, MARGIN, or FUTURES (enables short trading)
    bot_id: Optional[str] = None  # If not provided, creates new bot

class BotResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class ManualTradeRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol (e.g., BTCUSDT, SOLUSDT)")
    side: str = Field(..., pattern="^(BUY|SELL)$", description="Order side: BUY or SELL")
    quantity: Optional[float] = Field(None, description="Quantity to trade (e.g., 0.01 BTC)")
    amount_usdt: Optional[float] = Field(None, description="Amount in USDT to buy (only for BUY orders)")

class ManualTradeResponse(BaseModel):
    success: bool
    message: str
    order: Optional[Dict[str, Any]] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None

class Trade(BaseModel):
    model_config = ConfigDict(extra="ignore")
    symbol: str
    side: str
    quantity: float
    order_id: str
    status: str
    executed_qty: float
    quote_qty: float
    timestamp: str

class AgentLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    agent_name: str
    message: str
    message_type: str
    timestamp: str

class Analysis(BaseModel):
    model_config = ConfigDict(extra="ignore")
    symbol: str
    strategy: str
    analysis: Dict[str, Any]
    timestamp: str

# API Routes
@api_router.get("/")
async def root():
    return {
        "message": "Project CypherTrade API",
        "version": "1.0.0",
        "status": "online"
    }

@api_router.get("/health")
async def health_check():
    """Health check endpoint with service validation."""
    # Validate all services
    service_validation = await validate_all_services()
    
    # Determine overall health status
    all_services_valid = all(
        service["valid"] for service in service_validation.values()
    )
    
    return {
        "status": "healthy" if all_services_valid else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "bot_running": any(bot.is_running for bot in bot_manager.get_all_bots().values()),
        "active_bots": len([b for b in bot_manager.get_all_bots().values() if b.is_running]),
        "agents": {
            "nexuschat": settings.nexuschat_llm_provider,
            "cyphermind": settings.cyphermind_llm_provider,
            "cyphertrade": settings.cyphertrade_llm_provider
        },
        "services": service_validation
    }

@api_router.get("/agents")
async def list_agents():
    """List all agents and their configurations."""
    return {
        "agents": {
            "nexuschat": {
                "name": "NexusChat",
                "role": "User Interface Agent",
                "provider": settings.nexuschat_llm_provider,
                "model": settings.nexuschat_model
            },
            "cyphermind": {
                "name": "CypherMind",
                "role": "Decision & Strategy Agent",
                "provider": settings.cyphermind_llm_provider,
                "model": settings.cyphermind_model
            },
            "cyphertrade": {
                "name": "CypherTrade",
                "role": "Trade Execution Agent",
                "provider": settings.cyphertrade_llm_provider,
                "model": settings.cyphertrade_model
            }
        }
    }

@api_router.get("/strategies")
async def list_strategies():
    """List all available trading strategies."""
    from strategies import get_available_strategies
    strategies = get_available_strategies()
    return {
        "strategies": strategies,
        "default": settings.default_strategy
    }

@api_router.post("/chat", response_model=ChatResponse)
async def chat_with_nexuschat(request: ChatRequest):
    """Chat with NexusChat agent."""
    try:
        logger.info(f"Chat request received: {request.message[:100]}...")  # Log first 100 chars
        # Pass bot and db to chat_with_nexuschat so it can access real data
        result = await agent_manager.chat_with_nexuschat(request.message, bot=bot_manager, db=db)
        logger.info(f"Chat response generated: success={result.get('success')}, agent={result.get('agent')}")
        
        # Convert ObjectId to strings before returning
        clean_result = convert_objectid_to_str(result)
        
        # WebSocket-Broadcast entfernt - verhindert doppelte Nachrichten
        # Die API-Response reicht aus, WebSocket-Broadcast würde zu Duplikaten führen
        # await manager.broadcast({
        #     "type": "chat_message",
        #     "data": {
        #         "user": request.message,
        #         "agent": "NexusChat",
        #         "response": clean_result.get("response", ""),
        #         "timestamp": clean_result.get("timestamp")
        #     }
        # })
        
        return ChatResponse(**clean_result)
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return ChatResponse(
            success=False,
            response=f"Error: {str(e)}",
            agent="NexusChat",
            timestamp=datetime.now(timezone.utc).isoformat()
        )

@api_router.post("/bot/start", response_model=BotResponse)
async def start_bot(request: BotStartRequest):
    """Start a trading bot (creates new bot if bot_id not provided)."""
    try:
        # Get or create bot instance (bot_id is optional in request)
        try:
            bot_id = request.bot_id if request.bot_id else None
        except AttributeError:
            # Fallback if bot_id doesn't exist (shouldn't happen, but safe)
            bot_id = None
        bot = bot_manager.get_bot(bot_id)
        
        # Check if bot is already running
        if bot.is_running:
            return BotResponse(
                success=False,
                message=f"Bot {bot.bot_id} is already running",
                data=None
            )
        
        result = await bot.start(request.strategy, request.symbol, request.amount, request.timeframe, request.trading_mode)
        
        # Convert ObjectId to strings before broadcasting and returning
        clean_result = convert_objectid_to_str(result)
        
        # Only broadcast status update if bot started successfully
        if result["success"]:
            await manager.broadcast({
                "type": "bot_started",
                "data": clean_result,
                "success": True,
                "bot_id": bot.bot_id
            })
        else:
            # Broadcast error message if bot failed to start
            await manager.broadcast({
                "type": "bot_start_failed",
                "data": clean_result,
                "success": False,
                "message": result["message"],
                "bot_id": bot.bot_id
            })
        
        return BotResponse(
            success=result["success"],
            message=result["message"],
            data=clean_result.get("config")
        )
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)
        # Return error response instead of raising HTTPException
        # This ensures CORS headers are still sent
        return BotResponse(
            success=False,
            message=f"Error starting bot: {str(e)}",
            data=None
        )

@api_router.post("/trade/execute", response_model=ManualTradeResponse)
async def execute_manual_trade(request: ManualTradeRequest, bot_id: Optional[str] = None):
    """Execute a manual trade order (uses default bot if bot_id not provided)."""
    try:
        # Get bot instance (use default if not specified)
        if bot_id:
            bot = bot_manager.get_bot(bot_id)
        else:
            # Use default bot or create one
            bot = default_bot
        
        # Ensure bot has binance_client
        if bot.binance_client is None:
            # Initialize binance client if bot is not running
            if not bot.is_running:
                from binance_client import BinanceClientWrapper
                bot.binance_client = BinanceClientWrapper()
            else:
                return ManualTradeResponse(
                    success=False,
                    message="Binance client not available. Please start the bot first.",
                    order=None
                )
        
        result = await bot.execute_manual_trade(
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            amount_usdt=request.amount_usdt
        )
        
        if result["success"]:
            # Broadcast trade execution
            await manager.broadcast({
                "type": "trade_executed",
                "data": {
                    "symbol": result.get("symbol"),
                    "side": result.get("side"),
                    "quantity": result.get("quantity"),
                    "price": result.get("price"),
                    "order": result.get("order")
                }
            })
        
        return ManualTradeResponse(**result)
    
    except Exception as e:
        logger.error(f"Error executing manual trade: {e}", exc_info=True)
        return ManualTradeResponse(
            success=False,
            message=f"Error executing trade: {str(e)}",
            order=None
        )

@api_router.post("/bot/stop")
async def stop_bot(bot_id: Optional[str] = None):
    """Stop a trading bot (stops all bots if bot_id not provided)."""
    try:
        if bot_id:
            # Stop specific bot
            bot = bot_manager.get_bot(bot_id)
            result = await bot.stop()
            
            await manager.broadcast({
                "type": "bot_stopped",
                "data": result,
                "bot_id": bot_id
            })
            
            return BotResponse(
                success=result["success"],
                message=result["message"]
            )
        else:
            # Stop all running bots
            stopped_bots = []
            for bot_id, bot in bot_manager.get_all_bots().items():
                if bot.is_running:
                    result = await bot.stop()
                    stopped_bots.append({"bot_id": bot_id, "result": result})
                    await manager.broadcast({
                        "type": "bot_stopped",
                        "data": result,
                        "bot_id": bot_id
                    })
            
            return BotResponse(
                success=True,
                message=f"Stopped {len(stopped_bots)} bot(s)",
                data={"stopped_bots": stopped_bots}
            )
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/bot/status")
async def get_bot_status(bot_id: Optional[str] = None):
    """Get bot status (all bots if bot_id not provided)."""
    try:
        if bot_id:
            # Get specific bot status
            bot = bot_manager.get_bot(bot_id)
            status = await bot.get_status()
            return convert_objectid_to_str(status)
        else:
            # Get all bots status
            all_statuses = await bot_manager.get_all_bots_status()
            return convert_objectid_to_str(all_statuses)
    except Exception as e:
        logger.error(f"Error getting bot status: {e}")
        return {
            "error": True,
            "message": str(e),
            "is_running": False,
            "config": None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@api_router.get("/bot/report")
async def get_bot_report():
    """Get performance report."""
    try:
        report = await bot.get_report()
        return report
    except Exception as e:
        logger.error(f"Error getting report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/trades")
async def get_trades(limit: int = 100):  # Using default from constants would require refactoring
    """Get trade history."""
    try:
        trades = await db.trades.find({}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
        # Convert ObjectIds to strings in case they exist in nested structures
        cleaned_trades = []
        for trade in trades:
            try:
                # Clean the trade first
                cleaned_trade = convert_objectid_to_str(trade)
                # Ensure all required fields exist with defaults
                cleaned_trade.setdefault("symbol", "")
                cleaned_trade.setdefault("side", "")
                cleaned_trade.setdefault("quantity", 0.0)
                cleaned_trade.setdefault("order_id", "")
                cleaned_trade.setdefault("status", "")
                cleaned_trade.setdefault("executed_qty", 0.0)
                cleaned_trade.setdefault("quote_qty", 0.0)
                cleaned_trade.setdefault("timestamp", "")
                cleaned_trades.append(cleaned_trade)
            except Exception as trade_error:
                logger.warning(f"Error processing trade: {trade_error}, trade data: {trade}")
                continue
        
        return cleaned_trades
    except Exception as e:
        logger.error(f"Error getting trades: {e}", exc_info=True)
        # Return empty list instead of raising exception to prevent 500 errors
        return []

@api_router.get("/logs", response_model=List[AgentLog])
async def get_agent_logs(limit: int = 100):
    """Get agent communication logs."""
    try:
        logs = await db.agent_logs.find({}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
        return logs
    except Exception as e:
        logger.error(f"Error getting logs: {e}", exc_info=True)
        # Return empty list instead of raising exception to prevent frontend hanging
        return []

@api_router.get("/analyses", response_model=List[Analysis])
async def get_analyses(limit: int = 50):
    """Get market analyses."""
    try:
        analyses = await db.analyses.find({}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
        return analyses
    except Exception as e:
        logger.error(f"Error getting analyses: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/portfolio")
async def get_portfolio():
    """Get current portfolio overview with all assets held."""
    try:
        from binance_client import BinanceClientWrapper
        from collections import defaultdict
        
        binance_client = BinanceClientWrapper()
        portfolio_assets = defaultdict(lambda: {
            "quantity": 0.0,
            "value_usdt": 0.0,
            "entry_price": 0.0,
            "current_price": 0.0,
            "unrealized_pnl": 0.0,
            "unrealized_pnl_percent": 0.0,
            "bots": []
        })
        
        # Get all running bots
        all_bots = bot_manager.get_all_bots()
        
        for bot_id, bot in all_bots.items():
            if not bot.is_running or not bot.current_config:
                continue
            
            symbol = bot.current_config.get("symbol")
            trading_mode = bot.current_config.get("trading_mode", "SPOT")
            
            if not symbol:
                continue
            
            # Extract base asset from symbol (e.g., BTCUSDT -> BTC)
            base_asset = symbol.replace("USDT", "").replace("BUSD", "").replace("BTC", "").replace("ETH", "")
            
            try:
                # Get current balance for this asset
                balance = binance_client.get_account_balance(base_asset, trading_mode)
                
                if balance > 0.000001:  # Only include meaningful balances
                    # Get current price
                    current_price = binance_client.get_current_price(symbol)
                    
                    # Get entry price from bot's position tracking or last trade
                    entry_price = bot.position_entry_price if bot.position_entry_price > 0 else current_price
                    
                    # Calculate values
                    value_usdt = balance * current_price
                    unrealized_pnl = (current_price - entry_price) * balance if entry_price > 0 else 0.0
                    unrealized_pnl_percent = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0.0
                    
                    # Aggregate across all bots for same asset
                    portfolio_assets[base_asset]["quantity"] += balance
                    portfolio_assets[base_asset]["value_usdt"] += value_usdt
                    portfolio_assets[base_asset]["current_price"] = current_price
                    portfolio_assets[base_asset]["unrealized_pnl"] += unrealized_pnl
                    portfolio_assets[base_asset]["bots"].append({
                        "bot_id": bot_id,
                        "symbol": symbol,
                        "quantity": balance,
                        "trading_mode": trading_mode,
                        "position": bot.position,
                        "entry_price": entry_price
                    })
                    
                    # Update entry price (weighted average if multiple bots)
                    if entry_price > 0:
                        total_value = portfolio_assets[base_asset]["value_usdt"]
                        if total_value > 0:
                            portfolio_assets[base_asset]["entry_price"] = (
                                portfolio_assets[base_asset]["entry_price"] * (total_value - value_usdt) + 
                                entry_price * value_usdt
                            ) / total_value if portfolio_assets[base_asset]["entry_price"] > 0 else entry_price
                    
            except Exception as e:
                logger.warning(f"Error getting portfolio asset {base_asset} for bot {bot_id}: {e}")
                continue
        
        # Convert to list and calculate PnL percentage
        portfolio_list = []
        total_portfolio_value = 0.0
        
        for asset, data in portfolio_assets.items():
            if data["quantity"] > 0:
                # Recalculate PnL percentage with weighted entry price
                if data["entry_price"] > 0:
                    data["unrealized_pnl_percent"] = ((data["current_price"] - data["entry_price"]) / data["entry_price"] * 100)
                
                portfolio_list.append({
                    "asset": asset,
                    "quantity": round(data["quantity"], 8),
                    "value_usdt": round(data["value_usdt"], 2),
                    "entry_price": round(data["entry_price"], 6),
                    "current_price": round(data["current_price"], 6),
                    "unrealized_pnl": round(data["unrealized_pnl"], 2),
                    "unrealized_pnl_percent": round(data["unrealized_pnl_percent"], 2),
                    "bots": data["bots"]
                })
                total_portfolio_value += data["value_usdt"]
        
        # Sort by value (descending)
        portfolio_list.sort(key=lambda x: x["value_usdt"], reverse=True)
        
        # Also get USDT balance
        try:
            usdt_balance = binance_client.get_account_balance("USDT", "SPOT")
            total_portfolio_value += usdt_balance
        except Exception as e:
            logger.warning(f"Error getting USDT balance: {e}")
            usdt_balance = 0.0
        
        return {
            "success": True,
            "assets": portfolio_list,
            "usdt_balance": round(usdt_balance, 2),
            "total_portfolio_value": round(total_portfolio_value, 2),
            "total_unrealized_pnl": round(sum(a["unrealized_pnl"] for a in portfolio_list), 2),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting portfolio: {e}", exc_info=True)
        return {
            "success": False,
            "assets": [],
            "usdt_balance": 0.0,
            "total_portfolio_value": 0.0,
            "total_unrealized_pnl": 0.0,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@api_router.get("/stats")
async def get_statistics():
    """Get statistics with learning insights (overall + last 24h)."""
    try:
        # Overall counts
        total_trades = await db.trades.count_documents({})
        total_analyses = await db.analyses.count_documents({})
        total_logs = await db.agent_logs.count_documents({})
        
        # Last 24h window
        from datetime import timedelta
        now_utc = datetime.now(timezone.utc)
        cutoff_24h = now_utc - timedelta(hours=24)
        cutoff_24h_iso = cutoff_24h.isoformat()
        
        # Latest trades (overall, for history view)
        # Get latest trades
        recent_trades = await db.trades.find({}, {"_id": 0}).sort("timestamp", -1).to_list(10)
        
        # Calculate overall P&L (all time)
        buy_trades = await db.trades.find({"side": "BUY"}, {"_id": 0}).to_list(1000)
        sell_trades = await db.trades.find({"side": "SELL"}, {"_id": 0}).to_list(1000)
        
        total_bought = sum(float(t.get("quote_qty", 0)) for t in buy_trades)
        total_sold = sum(float(t.get("quote_qty", 0)) for t in sell_trades)
        profit_loss = total_sold - total_bought

        # --- Last 24h statistics (für Dashboard-Anzeigen) ---
        trades_24h_filter = {"timestamp": {"$gte": cutoff_24h_iso}}

        total_trades_24h = await db.trades.count_documents(trades_24h_filter)
        total_analyses_24h = await db.analyses.count_documents(
            {"timestamp": {"$gte": cutoff_24h_iso}}
        )
        total_logs_24h = await db.agent_logs.count_documents(
            {"timestamp": {"$gte": cutoff_24h_iso}}
        )

        buy_trades_24h = await db.trades.find(
            {"side": "BUY", "timestamp": {"$gte": cutoff_24h_iso}},
            {"_id": 0}
        ).to_list(1000)
        sell_trades_24h = await db.trades.find(
            {"side": "SELL", "timestamp": {"$gte": cutoff_24h_iso}},
            {"_id": 0}
        ).to_list(1000)

        total_bought_24h = sum(float(t.get("quote_qty", 0)) for t in buy_trades_24h)
        total_sold_24h = sum(float(t.get("quote_qty", 0)) for t in sell_trades_24h)
        profit_loss_24h = total_sold_24h - total_bought_24h
        
        # --- Last 7 days statistics (für Total Trades) ---
        cutoff_7d = now_utc - timedelta(days=7)
        cutoff_7d_iso = cutoff_7d.isoformat()
        trades_7d_filter = {"timestamp": {"$gte": cutoff_7d_iso}}
        total_trades_7d = await db.trades.count_documents(trades_7d_filter)
        
        # --- Depot Summe (Portfolio Value) ---
        depot_summe = 0.0
        try:
            from binance_client import BinanceClientWrapper
            binance_client = BinanceClientWrapper()
            # Get USDT balance
            usdt_balance = binance_client.get_account_balance("USDT", "SPOT")
            depot_summe += usdt_balance
            
            # Get all running bots and calculate portfolio value
            all_bots = bot_manager.get_all_bots()
            for bot_id, bot in all_bots.items():
                if not bot.is_running or not bot.current_config:
                    continue
                
                symbol = bot.current_config.get("symbol")
                trading_mode = bot.current_config.get("trading_mode", "SPOT")
                
                if not symbol:
                    continue
                
                # Extract base asset from symbol
                base_asset = symbol.replace("USDT", "").replace("BUSD", "").replace("BTC", "").replace("ETH", "")
                
                try:
                    balance = binance_client.get_account_balance(base_asset, trading_mode)
                    if balance > 0.000001:
                        current_price = binance_client.get_current_price(symbol)
                        depot_summe += balance * current_price
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Error calculating depot summe: {e}")
            depot_summe = 0.0
        
        # Get memory stats
        memory_stats = {
            "nexuschat": await db.memory_nexuschat.count_documents({}),
            "cyphermind": await db.memory_cyphermind.count_documents({}),
            "cyphertrade": await db.memory_cyphertrade.count_documents({})
        }
        
        return {
            # Overall (all time)
            "total_trades": total_trades,
            "total_analyses": total_analyses,
            "total_logs": total_logs,
            "profit_loss_usdt": round(profit_loss, 2),
            "total_bought_usdt": round(total_bought, 2),
            "total_sold_usdt": round(total_sold, 2),
            # Last 24h (für Dashboard-Anzeigen)
            "total_trades_24h": total_trades_24h,
            "total_analyses_24h": total_analyses_24h,
            "total_logs_24h": total_logs_24h,
            "profit_loss_usdt_24h": round(profit_loss_24h, 2),
            "total_bought_usdt_24h": round(total_bought_24h, 2),
            "total_sold_usdt_24h": round(total_sold_24h, 2),
            # Last 7 days (für Total Trades)
            "total_trades_7d": total_trades_7d,
            # Depot Summe (Portfolio Value)
            "depot_summe": round(depot_summe, 2),
            "stats_window": {
                "type": "last_24h",
                "cutoff_utc": cutoff_24h_iso,
                "now_utc": now_utc.isoformat()
            },
            "recent_trades": recent_trades,
            "memory_stats": memory_stats
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/memory/{agent_name}")
async def get_agent_memory(agent_name: str, limit: int = 20):
    """Get memory for a specific agent."""
    try:
        memory = agent_manager.memory_manager.get_agent_memory(agent_name)
        memories = await memory.retrieve_memories(limit=limit)
        return {
            "agent": agent_name,
            "memories": memories,
            "count": len(memories)
        }
    except Exception as e:
        logger.error(f"Error getting agent memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/memory/{agent_name}/lessons")
async def get_agent_lessons(agent_name: str, limit: int = 10):
    """Get recent lessons learned by an agent."""
    try:
        memory = agent_manager.memory_manager.get_agent_memory(agent_name)
        lessons = await memory.get_recent_lessons(limit=limit)
        return {
            "agent": agent_name,
            "lessons": lessons
        }
    except Exception as e:
        logger.error(f"Error getting agent lessons: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/memory/insights/collective")
async def get_collective_insights():
    """Get collective insights from all agents."""
    try:
        insights = await agent_manager.memory_manager.get_collective_insights()
        return insights
    except Exception as e:
        logger.error(f"Error getting collective insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/memory/pattern/{symbol}/{strategy}")
async def get_pattern_insights(symbol: str, strategy: str):
    """Get pattern insights for specific symbol and strategy."""
    try:
        memory = agent_manager.memory_manager.get_agent_memory("CypherMind")
        insights = await memory.get_pattern_insights(symbol, strategy)
        return insights
    except Exception as e:
        logger.error(f"Error getting pattern insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/trading-knowledge/update")
async def update_trading_knowledge_endpoint(force_refresh: bool = False):
    """Manually update trading knowledge for all agents."""
    try:
        logger.info(f"Manual trading knowledge update requested (force_refresh={force_refresh})")
        await agent_manager.update_trading_knowledge(force_refresh=force_refresh)
        
        # Store in memory
        if agent_manager.trading_knowledge:
            for agent_name in ["NexusChat", "CypherMind", "CypherTrade"]:
                memory = agent_manager.memory_manager.get_agent_memory(agent_name)
                await memory.store_memory(
                    memory_type="trading_knowledge",
                    content=agent_manager.trading_knowledge,
                    metadata={"source": "manual_update", "force_refresh": force_refresh}
                )
        
        return {
            "success": True,
            "message": "Trading knowledge updated successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error updating trading knowledge: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/trading-knowledge/status")
async def get_trading_knowledge_status():
    """Get status of trading knowledge (when it was last loaded, etc.)."""
    try:
        if agent_manager.trading_knowledge:
            loaded_at = agent_manager.trading_knowledge.get("loaded_at", "unknown")
            return {
                "success": True,
                "loaded": True,
                "loaded_at": loaded_at,
                "fallback": agent_manager.trading_knowledge.get("fallback", False)
            }
        else:
            return {
                "success": True,
                "loaded": False,
                "loaded_at": None
            }
    except Exception as e:
        logger.error(f"Error getting trading knowledge status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/market/volatile")
async def get_volatile_assets(limit: int = 20):
    """Get the most volatile assets (24h analysis for all USDT pairs) for NexusChat dashboard."""
    try:
        # Get binance_client from a running bot, or create a new one
        binance_client = None
        
        # Try to get binance_client from a running bot
        all_bots = bot_manager.get_all_bots()
        for bot in all_bots.values():
            if bot.binance_client:
                binance_client = bot.binance_client
                break
        
        # If no bot has a binance_client, create a new one
        if binance_client is None:
            from binance_client import BinanceClientWrapper
            binance_client = BinanceClientWrapper()
        
        # Get 24h volatile assets for all USDT pairs
        tickers = []
        try:
            logger.info("Getting 24h volatile assets for all USDT pairs...")
            # Run 24h analysis in thread pool with timeout
            try:
                tickers = await asyncio.wait_for(
                    asyncio.to_thread(binance_client.get_24h_volatile_assets_usdt),
                    timeout=30.0  # 30 seconds timeout (might take longer for all USDT pairs)
                )
                logger.info(f"24h analysis completed: {len(tickers)} USDT assets found")
            except asyncio.TimeoutError:
                logger.warning("24h analysis timed out, using fallback method")
                # Fallback: Use regular 24h ticker stats (faster but might miss some USDT pairs)
                tickers = binance_client.get_24h_ticker_stats()
                # Filter for USDT pairs only
                tickers = [t for t in tickers if t.get('symbol', '').endswith('USDT')]
            except Exception as analysis_error:
                logger.warning(f"24h analysis failed: {analysis_error}, using fallback method")
                # Fallback: Use regular 24h ticker stats
                tickers = binance_client.get_24h_ticker_stats()
                # Filter for USDT pairs only
                tickers = [t for t in tickers if t.get('symbol', '').endswith('USDT')]
        except Exception as e:
            logger.error(f"Failed to get volatile assets: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "assets": [],
                "count": 0
            }
        
        # Limit results
        limited_tickers = tickers[:limit] if tickers else []
        
        # Convert to response format
        result = {
            "success": True,
            "count": len(limited_tickers),
            "assets": limited_tickers,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return result
    except Exception as e:
        logger.error(f"Error getting volatile assets: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "assets": [],
            "count": 0
        }

# WebSocket endpoint for real-time updates
@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for messages
            data = await websocket.receive_text()
            # Echo back for testing
            await websocket.send_json({"type": "ping", "message": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Background task to broadcast updates
async def broadcast_updates():
    """Background task to broadcast bot status updates for all running bots."""
    while True:
        try:
            # Broadcast status for all running bots
            for bot_id, bot in bot_manager.get_all_bots().items():
                if bot.is_running:
                    status = await bot.get_status()
                    await manager.broadcast({
                        "type": "status_update",
                        "data": status,
                        "bot_id": bot_id
                    })
            await asyncio.sleep(BOT_BROADCAST_INTERVAL_SECONDS)
        except Exception as e:
            logger.error(f"Error broadcasting updates: {e}")
            await asyncio.sleep(BOT_BROADCAST_INTERVAL_SECONDS)

@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup."""
    global db, agent_manager, bot_manager, default_bot, mcp_server
    
    # KRITISCH: Initialisiere DB und Manager falls sie beim Import fehlgeschlagen sind
    if db is None:
        logger.info("Retrying MongoDB connection initialization...")
        try:
            mongo_url = settings.mongo_url
            db_name = settings.db_name
            client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=10000)  # 10 Sekunden Timeout
            db = client[db_name]
            logger.info(f"MongoDB connected to {db_name}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB on startup: {e}")
            # Versuche trotzdem fortzufahren, falls DB später verfügbar wird
    
    # Initialisiere AgentManager und BotManager falls sie beim Import fehlgeschlagen sind
    if agent_manager is None or bot_manager is None:
        logger.info("Retrying AgentManager/BotManager initialization...")
        try:
            if db is not None:
                agent_manager = AgentManager(db, bot=None, binance_client=None)
                bot_manager = BotManager(db, agent_manager)
                agent_manager.bot = bot_manager
                default_bot = bot_manager.get_bot()
                logger.info("AgentManager and BotManager initialized successfully on startup")
            else:
                logger.warning("Cannot initialize managers: DB not available")
        except Exception as e:
            logger.error(f"Failed to initialize managers on startup: {e}", exc_info=True)
    
    # Initialisiere MCP Server falls er beim Import fehlgeschlagen ist
    if mcp_server is None and db is not None and agent_manager is not None and bot_manager is not None:
        logger.info("Retrying MCP Server initialization...")
        try:
            mcp_server = create_mcp_server(db, agent_manager, bot_manager)
            if mcp_server:
                app.include_router(mcp_server.router)
                logger.info("MCP Server routes registered on startup")
        except Exception as e:
            logger.warning(f"Could not initialize MCP Server on startup: {e}")
    
    # Validate MongoDB connection on startup
    mongodb_valid, mongodb_error = await validate_mongodb_connection()
    if not mongodb_valid:
        logger.warning(f"MongoDB validation failed on startup: {mongodb_error}")
    else:
        logger.info("MongoDB connection validated on startup")
    
    asyncio.create_task(broadcast_updates())
    
    # Starte permanenten Kurs-Update-Loop für CypherTrade (alle 30 Sekunden)
    if bot_manager is not None:
        try:
            await bot_manager.start_price_update_loop()
            logger.info("Permanent price update loop started for CypherTrade (every 30 seconds)")
        except Exception as e:
            logger.error(f"Could not start price update loop: {e}", exc_info=True)
    
    # Starte Autonomous Manager
    global autonomous_manager
    try:
        # Versuche Binance-Client vom ersten Bot zu holen (falls vorhanden)
        binance_client = None
        all_bots = bot_manager.get_all_bots()
        for bot in all_bots.values():
            if bot.binance_client:
                binance_client = bot.binance_client
                break
        
        # Falls kein Bot läuft, erstelle einen temporären Binance Client
        if binance_client is None:
            try:
                from binance_client import BinanceClientWrapper
                logger.info("No running bot found, creating temporary Binance client for Autonomous Manager...")
                binance_client = BinanceClientWrapper()
                logger.info("Temporary Binance client created successfully")
            except Exception as client_error:
                logger.warning(f"Could not create temporary Binance client: {client_error}. Autonomous Manager will create one when needed.")
        
        autonomous_manager = AutonomousManager(
            agent_manager=agent_manager,
            bot_manager=bot_manager,
            db=db,
            binance_client=binance_client
        )
        await autonomous_manager.start()
        logger.info("Autonomous Manager started - CypherMind arbeitet jetzt autonom")
        
        # Initialize Trading Pairs Cache
        try:
            trading_pairs_cache = get_trading_pairs_cache(binance_client)
            await trading_pairs_cache.start()
            logger.info("Trading Pairs Cache started - wird alle 2 Stunden aktualisiert")
        except Exception as e:
            logger.warning(f"Could not start Trading Pairs Cache: {e}")
    except Exception as e:
        logger.error(f"Error starting Autonomous Manager: {e}", exc_info=True)
        logger.warning("Autonomous Manager will retry when a bot starts or when manually triggered.")
    
    # Update Binance-Client wenn ein Bot startet
    async def update_autonomous_manager_binance_client():
        """Aktualisiert den Binance-Client im AutonomousManager und Trading Pairs Cache wenn ein Bot startet."""
        if autonomous_manager and not autonomous_manager.binance_client:
            all_bots = bot_manager.get_all_bots()
            for bot in all_bots.values():
                if bot.binance_client:
                    autonomous_manager.binance_client = bot.binance_client
                    logger.info("Autonomous Manager Binance client updated")
                    break
        
        # Update Trading Pairs Cache Binance client
        try:
            trading_pairs_cache = get_trading_pairs_cache()
            if trading_pairs_cache and not trading_pairs_cache.binance_client:
                all_bots = bot_manager.get_all_bots()
                for bot in all_bots.values():
                    if bot.binance_client:
                        trading_pairs_cache.binance_client = bot.binance_client
                        if not trading_pairs_cache.update_task:
                            await trading_pairs_cache.start()
                        logger.info("Trading Pairs Cache Binance client updated")
                        break
        except Exception as e:
            logger.warning(f"Could not update Trading Pairs Cache: {e}")
    
    # Speichere Update-Funktion für später
    bot_manager._update_autonomous_manager = update_autonomous_manager_binance_client
    
    # Load trading knowledge for all agents
    try:
        logger.info("Loading trading knowledge for all agents...")
        await agent_manager.update_trading_knowledge(force_refresh=False)
        logger.info("Trading knowledge loaded successfully")
        
        # Store trading knowledge in memory for all agents
        if agent_manager.trading_knowledge:
            for agent_name in ["NexusChat", "CypherMind", "CypherTrade"]:
                memory = agent_manager.memory_manager.get_agent_memory(agent_name)
                await memory.store_memory(
                    memory_type="trading_knowledge",
                    content=agent_manager.trading_knowledge,
                    metadata={"source": "startup", "auto_loaded": True}
                )
            logger.info("Trading knowledge stored in agent memories")
        
    except Exception as e:
        logger.warning(f"Could not load trading knowledge: {e}. Will continue without it.")
    
    # Start background task for periodic trading knowledge updates (every 24 hours)
    async def periodic_trading_knowledge_update():
        """Periodic task to update trading knowledge every 24 hours."""
        while True:
            try:
                await asyncio.sleep(86400)  # 24 hours in seconds
                logger.info("Starting periodic trading knowledge update...")
                await agent_manager.update_trading_knowledge(force_refresh=True)
                
                # Update memory
                if agent_manager.trading_knowledge:
                    for agent_name in ["NexusChat", "CypherMind", "CypherTrade"]:
                        memory = agent_manager.memory_manager.get_agent_memory(agent_name)
                        await memory.store_memory(
                            memory_type="trading_knowledge",
                            content=agent_manager.trading_knowledge,
                            metadata={"source": "periodic_update", "auto_loaded": True}
                        )
                logger.info("Periodic trading knowledge update completed")
            except Exception as e:
                logger.error(f"Error in periodic trading knowledge update: {e}")
    
    # Start the background task
    asyncio.create_task(periodic_trading_knowledge_update())
    logger.info("Periodic trading knowledge update task started (updates every 24 hours)")
    
    logger.info("Project CypherTrade started successfully")

# Include the router in the main app
# Health check endpoint (before API router to avoid prefix)
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

app.include_router(api_router)

# Global exception handlers (MUST be after router inclusion)
# These ensure CORS headers are sent even on errors
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP exception handler with CORS headers."""
    origin = request.headers.get("origin", "*")
    if origin == "null":
        origin = "*"
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": True, "message": exc.detail},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Validation exception handler with CORS headers."""
    origin = request.headers.get("origin", "*")
    if origin == "null":
        origin = "*"
    
    return JSONResponse(
        status_code=422,
        content={"error": True, "message": "Validation error", "details": exc.errors()},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler that ensures CORS headers are always sent."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    origin = request.headers.get("origin", "*")
    if origin == "null":
        origin = "*"
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": str(exc),
            "type": type(exc).__name__
        },
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.on_event("shutdown")
async def shutdown_db_client():
    """Close MongoDB connection and stop background tasks on application shutdown."""
    try:
        # Stoppe permanenten Kurs-Update-Loop
        if bot_manager is not None:
            try:
                await bot_manager.stop_price_update_loop()
                logger.info("Price update loop stopped")
            except Exception as e:
                logger.warning(f"Error stopping price update loop: {e}")
        
        # Schließe MongoDB-Verbindung
        if 'client' in globals() and client:
            client.close()
            logger.info("MongoDB connection closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    logger.info("Project CypherTrade shut down")