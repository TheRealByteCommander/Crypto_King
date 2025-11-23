"""
MCP (Model Context Protocol) Server Integration
Provides trading tools as MCP tools for AI agents.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter
from config import settings
from bot_manager import get_bot_instance
from agents import AgentManager
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server for exposing trading tools to AI agents."""
    
    def __init__(self, db: AsyncIOMotorDatabase, agent_manager: AgentManager, bot):
        self.db = db
        self.agent_manager = agent_manager
        self.bot = bot
        self.router = APIRouter(prefix="/mcp")
        self._register_routes()
    
    def _register_routes(self):
        """Register MCP routes."""
        
        @self.router.get("/tools")
        async def list_tools():
            """List all available MCP tools."""
            return {
                "tools": [
                    {
                        "name": "get_bot_status",
                        "description": "Get current trading bot status and configuration",
                        "parameters": {}
                    },
                    {
                        "name": "get_trade_history",
                        "description": "Get recent trade history",
                        "parameters": {
                            "limit": {"type": "integer", "default": 10, "description": "Number of trades to return"}
                        }
                    },
                    {
                        "name": "get_market_analysis",
                        "description": "Get recent market analysis",
                        "parameters": {
                            "limit": {"type": "integer", "default": 5, "description": "Number of analyses to return"}
                        }
                    },
                    {
                        "name": "get_performance_stats",
                        "description": "Get trading performance statistics",
                        "parameters": {}
                    },
                    {
                        "name": "get_agent_memory",
                        "description": "Get memory/learning data for a specific agent",
                        "parameters": {
                            "agent_name": {"type": "string", "required": True, "description": "Agent name (NexusChat, CypherMind, CypherTrade)"},
                            "limit": {"type": "integer", "default": 10, "description": "Number of memories to return"}
                        }
                    },
                    {
                        "name": "get_learning_insights",
                        "description": "Get collective learning insights from all agents",
                        "parameters": {}
                    }
                ]
            }
        
        @self.router.post("/tools/{tool_name}")
        async def execute_tool(tool_name: str, parameters: Dict[str, Any] = None):
            """Execute an MCP tool."""
            if parameters is None:
                parameters = {}
            
            try:
                if tool_name == "get_bot_status":
                    # Handle BotManager - get all bots status
                    from bot_manager import BotManager
                    if isinstance(self.bot, BotManager):
                        status = await self.bot.get_all_bots_status()
                    else:
                        status = await self.bot.get_status()
                    return {
                        "success": True,
                        "result": status
                    }
                
                elif tool_name == "get_trade_history":
                    limit = parameters.get("limit", 10)
                    trades = await self.db.trades.find({}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
                    return {
                        "success": True,
                        "result": {
                            "trades": trades,
                            "count": len(trades)
                        }
                    }
                
                elif tool_name == "get_market_analysis":
                    limit = parameters.get("limit", 5)
                    analyses = await self.db.analyses.find({}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
                    return {
                        "success": True,
                        "result": {
                            "analyses": analyses,
                            "count": len(analyses)
                        }
                    }
                
                elif tool_name == "get_performance_stats":
                    total_trades = await self.db.trades.count_documents({})
                    buy_trades = await self.db.trades.find({"side": "BUY"}, {"_id": 0}).to_list(1000)
                    sell_trades = await self.db.trades.find({"side": "SELL"}, {"_id": 0}).to_list(1000)
                    
                    total_bought = sum(float(t.get("quote_qty", 0)) for t in buy_trades)
                    total_sold = sum(float(t.get("quote_qty", 0)) for t in sell_trades)
                    profit_loss = total_sold - total_bought
                    
                    return {
                        "success": True,
                        "result": {
                            "total_trades": total_trades,
                            "buy_trades": len(buy_trades),
                            "sell_trades": len(sell_trades),
                            "total_bought_usdt": round(total_bought, 2),
                            "total_sold_usdt": round(total_sold, 2),
                            "profit_loss_usdt": round(profit_loss, 2)
                        }
                    }
                
                elif tool_name == "get_agent_memory":
                    agent_name = parameters.get("agent_name")
                    if not agent_name:
                        return {
                            "success": False,
                            "error": "agent_name parameter is required"
                        }
                    
                    limit = parameters.get("limit", 10)
                    memory = self.agent_manager.memory_manager.get_agent_memory(agent_name)
                    memories = await memory.retrieve_memories(limit=limit)
                    
                    return {
                        "success": True,
                        "result": {
                            "agent": agent_name,
                            "memories": memories,
                            "count": len(memories)
                        }
                    }
                
                elif tool_name == "get_learning_insights":
                    insights = await self.agent_manager.memory_manager.get_collective_insights()
                    return {
                        "success": True,
                        "result": insights
                    }
                
                else:
                    return {
                        "success": False,
                        "error": f"Unknown tool: {tool_name}"
                    }
            
            except Exception as e:
                logger.error(f"Error executing MCP tool {tool_name}: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        @self.router.get("/health")
        async def mcp_health():
            """MCP server health check."""
            return {
                "status": "healthy",
                "enabled": settings.mcp_enabled,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


def create_mcp_server(db: AsyncIOMotorDatabase, agent_manager: AgentManager, bot) -> Optional[MCPServer]:
    """Create and return MCP server if enabled."""
    if not settings.mcp_enabled:
        logger.info("MCP Server is disabled in configuration")
        return None
    
    logger.info(f"MCP Server enabled on port {settings.mcp_port}")
    return MCPServer(db, agent_manager, bot)

