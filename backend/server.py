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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(
    title="Project CypherTrade API",
    description="AI-powered cryptocurrency trading system with Autogen agents",
    version="1.0.0"
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize agents and bot
agent_manager = AgentManager(db)
bot = get_bot_instance(db, agent_manager)

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
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "bot_running": bot.is_running,
        "agents": {
            "nexuschat": settings.nexuschat_llm_provider,
            "cyphermind": settings.cyphermind_llm_provider,
            "cyphertrade": settings.cyphertrade_llm_provider
        }
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
        raise HTTPException(status_code=500, detail=str(e))

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
async def get_trades(limit: int = 100):
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
    """Get overall statistics."""
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
        
        return {
            "total_trades": total_trades,
            "total_analyses": total_analyses,
            "total_logs": total_logs,
            "profit_loss_usdt": round(profit_loss, 2),
            "total_bought_usdt": round(total_bought, 2),
            "total_sold_usdt": round(total_sold, 2),
            "recent_trades": recent_trades
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
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
            await asyncio.sleep(10)  # Broadcast every 10 seconds
        except Exception as e:
            logger.error(f"Error broadcasting updates: {e}")
            await asyncio.sleep(10)

@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup."""
    asyncio.create_task(broadcast_updates())
    logger.info("Project CypherTrade started successfully")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
    logger.info("Project CypherTrade shut down")