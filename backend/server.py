from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import json
import asyncio

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
agent_manager = AgentManager(db)
bot = get_bot_instance(db, agent_manager)

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
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")

manager = ConnectionManager()

# Pydantic Models
class BotStartRequest(BaseModel):
    strategy: str = "ma_crossover"
    symbol: str = "BTCUSDT"
    amount: float = 100.0

class BotResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

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

@api_router.post("/bot/start", response_model=BotResponse)
async def start_bot(request: BotStartRequest):
    """Start the trading bot."""
    try:
        result = await bot.start(request.strategy, request.symbol, request.amount)
        
        # Broadcast status update
        await manager.broadcast({
            "type": "bot_started",
            "data": result
        })
        
        return BotResponse(
            success=result["success"],
            message=result["message"],
            data=result.get("config")
        )
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        return status
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

@api_router.get("/trades", response_model=List[Trade])
async def get_trades(limit: int = 100):  # Using default from constants would require refactoring
    """Get trade history."""
    try:
        trades = await db.trades.find({}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
        return trades
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
app.include_router(api_router)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
    logger.info("Project CypherTrade shut down")