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
from bot_manager import get_bot_instance
from constants import BOT_BROADCAST_INTERVAL_SECONDS
from validators import validate_all_services, validate_mongodb_connection
from mcp_server import create_mcp_server

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection - use settings for consistency
try:
    mongo_url = settings.mongo_url
    db_name = settings.db_name
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    logger.info(f"MongoDB connected to {db_name}")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

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

# Initialize agents and bot
# Initialize agent_manager first, then bot (which will get agent_manager)
# We'll update agent_manager with bot and binance_client after bot is created
agent_manager = AgentManager(db, bot=None, binance_client=None)
bot = get_bot_instance(db, agent_manager)
# Update agent_manager with bot reference (binance_client will be available when bot starts)
agent_manager.bot = bot
# binance_client will be set when bot starts, but we can prepare the reference
# agent_manager.binance_client = bot.binance_client  # Will be set when bot starts

# Initialize MCP Server if enabled
mcp_server = create_mcp_server(db, agent_manager, bot)
if mcp_server:
    app.include_router(mcp_server.router)
    logger.info("MCP Server routes registered")

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
        "bot_running": bot.is_running,
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
        result = await agent_manager.chat_with_nexuschat(request.message, bot=bot, db=db)
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
    """Start the trading bot."""
    try:
        result = await bot.start(request.strategy, request.symbol, request.amount)
        
        # Convert ObjectId to strings before broadcasting and returning
        clean_result = convert_objectid_to_str(result)
        
        # Only broadcast status update if bot started successfully
        if result["success"]:
            await manager.broadcast({
                "type": "bot_started",
                "data": clean_result,
                "success": True
            })
        else:
            # Broadcast error message if bot failed to start
            await manager.broadcast({
                "type": "bot_start_failed",
                "data": clean_result,
                "success": False,
                "message": result["message"]
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
async def execute_manual_trade(request: ManualTradeRequest):
    """Execute a manual trade order."""
    try:
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

@api_router.post("/bot/stop", response_model=BotResponse)
async def stop_bot():
    """Stop the trading bot."""
    try:
        result = await bot.stop()
        
        # Broadcast status update
        await manager.broadcast({
            "type": "bot_stopped",
            "data": result
        })
        
        return BotResponse(
            success=result["success"],
            message=result["message"]
        )
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/bot/status")
async def get_bot_status():
    """Get current bot status."""
    try:
        status = await bot.get_status()
        # Convert ObjectId to strings before returning
        return convert_objectid_to_str(status)
    except Exception as e:
        logger.error(f"Error getting bot status: {e}")
        # Return error response instead of raising HTTPException
        # This ensures CORS headers are still sent
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
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/analyses", response_model=List[Analysis])
async def get_analyses(limit: int = 50):
    """Get market analyses."""
    try:
        analyses = await db.analyses.find({}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
        return analyses
    except Exception as e:
        logger.error(f"Error getting analyses: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/stats")
async def get_statistics():
    """Get overall statistics with learning insights."""
    try:
        total_trades = await db.trades.count_documents({})
        total_analyses = await db.analyses.count_documents({})
        total_logs = await db.agent_logs.count_documents({})
        
        # Get latest trades
        recent_trades = await db.trades.find({}, {"_id": 0}).sort("timestamp", -1).to_list(10)
        
        # Calculate P&L
        buy_trades = await db.trades.find({"side": "BUY"}, {"_id": 0}).to_list(1000)
        sell_trades = await db.trades.find({"side": "SELL"}, {"_id": 0}).to_list(1000)
        
        total_bought = sum(float(t.get("quote_qty", 0)) for t in buy_trades)
        total_sold = sum(float(t.get("quote_qty", 0)) for t in sell_trades)
        profit_loss = total_sold - total_bought
        
        # Get memory stats
        memory_stats = {
            "nexuschat": await db.memory_nexuschat.count_documents({}),
            "cyphermind": await db.memory_cyphermind.count_documents({}),
            "cyphertrade": await db.memory_cyphertrade.count_documents({})
        }
        
        return {
            "total_trades": total_trades,
            "total_analyses": total_analyses,
            "total_logs": total_logs,
            "profit_loss_usdt": round(profit_loss, 2),
            "total_bought_usdt": round(total_bought, 2),
            "total_sold_usdt": round(total_sold, 2),
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

@api_router.get("/market/volatile")
async def get_volatile_assets(limit: int = 20):
    """Get the most volatile assets (30-day analysis) for NexusChat dashboard."""
    try:
        # Create a temporary Binance client if bot is not running
        binance_client = bot.binance_client
        if binance_client is None:
            from binance_client import BinanceClientWrapper
            binance_client = BinanceClientWrapper()
        
        # Get 30-day volatile assets with timeout
        tickers = []
        try:
            logger.info("Getting 30-day volatile assets...")
            # Run 30-day analysis in thread pool with timeout
            try:
                tickers = await asyncio.wait_for(
                    asyncio.to_thread(binance_client.get_30d_volatile_assets),
                    timeout=20.0  # 20 seconds timeout
                )
                logger.info(f"30-day analysis completed: {len(tickers)} assets found")
            except asyncio.TimeoutError:
                logger.warning("30-day analysis timed out, using 24h ticker stats as fallback")
                tickers = binance_client.get_24h_ticker_stats()
            except Exception as analysis_error:
                logger.warning(f"30-day analysis failed: {analysis_error}, using 24h ticker stats as fallback")
                tickers = binance_client.get_24h_ticker_stats()
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
    """Background task to broadcast bot status updates."""
    while True:
        try:
            if bot.is_running:
                status = await bot.get_status()
                await manager.broadcast({
                    "type": "status_update",
                    "data": status
                })
            await asyncio.sleep(BOT_BROADCAST_INTERVAL_SECONDS)
        except Exception as e:
            logger.error(f"Error broadcasting updates: {e}")
            await asyncio.sleep(BOT_BROADCAST_INTERVAL_SECONDS)

@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup."""
    # Validate MongoDB connection on startup
    mongodb_valid, mongodb_error = await validate_mongodb_connection()
    if not mongodb_valid:
        logger.warning(f"MongoDB validation failed on startup: {mongodb_error}")
    else:
        logger.info("MongoDB connection validated on startup")
    
    asyncio.create_task(broadcast_updates())
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
    client.close()
    logger.info("Project CypherTrade shut down")