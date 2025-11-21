"""
Memory Manager for Agent Learning
Enables agents to learn from past trades and decisions.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from constants import (
    MAX_SHORT_TERM_MEMORY,
    DEFAULT_MEMORY_RETRIEVAL_LIMIT,
    DEFAULT_MEMORY_DAYS_BACK,
    DEFAULT_MEMORY_CLEANUP_DAYS
)
import json

logger = logging.getLogger(__name__)

class AgentMemory:
    """Memory system for individual agents."""
    
    def __init__(self, db: AsyncIOMotorDatabase, agent_name: str):
        self.db = db
        self.agent_name = agent_name
        self.collection = db[f"memory_{agent_name.lower()}"]
        self.short_term_memory = []  # In-memory for current session
        self.max_short_term = MAX_SHORT_TERM_MEMORY
    
    async def store_memory(self, memory_type: str, content: Dict[str, Any], metadata: Dict[str, Any] = None):
        """Store a memory entry."""
        try:
            memory_entry = {
                "agent": self.agent_name,
                "type": memory_type,
                "content": content,
                "metadata": metadata or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": metadata.get("session_id") if metadata else None
            }
            
            # Store in database
            result = await self.collection.insert_one(memory_entry)
            
            # Add to short-term memory
            self.short_term_memory.append(memory_entry)
            if len(self.short_term_memory) > self.max_short_term:
                self.short_term_memory.pop(0)
            
            logger.info(f"{self.agent_name} stored memory: {memory_type}")
            return str(result.inserted_id)
        
        except Exception as e:
            logger.error(f"Error storing memory for {self.agent_name}: {e}")
            return None
    
    async def retrieve_memories(self, memory_type: Optional[str] = None, 
                                limit: int = DEFAULT_MEMORY_RETRIEVAL_LIMIT, 
                                days_back: int = DEFAULT_MEMORY_DAYS_BACK) -> List[Dict[str, Any]]:
        """Retrieve past memories."""
        try:
            query = {"agent": self.agent_name}
            
            if memory_type:
                query["type"] = memory_type
            
            # Only get recent memories
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            query["timestamp"] = {"$gte": cutoff_date.isoformat()}
            
            memories = await self.collection.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
            
            logger.info(f"{self.agent_name} retrieved {len(memories)} memories")
            return memories
        
        except Exception as e:
            logger.error(f"Error retrieving memories for {self.agent_name}: {e}")
            return []
    
    async def learn_from_trade(self, trade: Dict[str, Any], outcome: str, profit_loss: float):
        """Learn from a completed trade."""
        try:
            learning_entry = {
                "trade_id": trade.get("order_id"),
                "symbol": trade.get("symbol"),
                "side": trade.get("side"),
                "strategy": trade.get("strategy"),
                "entry_price": trade.get("entry_price"),
                "exit_price": trade.get("exit_price"),
                "outcome": outcome,  # "success", "failure", "neutral"
                "profit_loss": profit_loss,
                "indicators_at_entry": trade.get("indicators", {}),
                "signal_confidence": trade.get("confidence", 0.0),
                "lessons": self._extract_lessons(trade, outcome, profit_loss)
            }
            
            await self.store_memory(
                memory_type="trade_learning",
                content=learning_entry,
                metadata={"outcome": outcome, "profit_loss": profit_loss}
            )
            
            logger.info(f"{self.agent_name} learned from trade: {outcome}")
        
        except Exception as e:
            logger.error(f"Error learning from trade: {e}")
    
    def _extract_lessons(self, trade: Dict[str, Any], outcome: str, profit_loss: float) -> List[str]:
        """Extract lessons from trade outcome."""
        lessons = []
        
        strategy = trade.get("strategy", "unknown")
        confidence = trade.get("confidence", 0.0)
        
        if outcome == "success":
            lessons.append(f"Strategy '{strategy}' worked well with confidence {confidence:.2f}")
            if profit_loss > 5:
                lessons.append(f"High profit trade - similar conditions may be favorable")
        elif outcome == "failure":
            lessons.append(f"Strategy '{strategy}' failed with confidence {confidence:.2f}")
            if confidence < 0.6:
                lessons.append(f"Low confidence signals are risky - require higher threshold")
            lessons.append(f"Review market conditions at entry time")
        
        return lessons
    
    async def get_pattern_insights(self, symbol: str, strategy: str) -> Dict[str, Any]:
        """Get insights about patterns for specific symbol and strategy."""
        try:
            # Get past trades with same symbol and strategy
            query = {
                "agent": self.agent_name,
                "type": "trade_learning",
                "content.symbol": symbol,
                "content.strategy": strategy
            }
            
            trades = await self.collection.find(query, {"_id": 0}).to_list(100)
            
            if not trades:
                return {
                    "total_trades": 0,
                    "insights": ["No historical data for this symbol/strategy combination"]
                }
            
            # Analyze outcomes
            successes = [t for t in trades if t["content"]["outcome"] == "success"]
            failures = [t for t in trades if t["content"]["outcome"] == "failure"]
            
            total_profit = sum(t["content"]["profit_loss"] for t in trades)
            avg_profit = total_profit / len(trades) if trades else 0
            
            success_rate = len(successes) / len(trades) * 100 if trades else 0
            
            # Find common patterns in successful trades
            successful_conditions = []
            if successes:
                avg_success_confidence = sum(t["content"]["signal_confidence"] for t in successes) / len(successes)
                successful_conditions.append(f"Successful trades had avg confidence: {avg_success_confidence:.2f}")
            
            insights = {
                "total_trades": len(trades),
                "success_rate": round(success_rate, 2),
                "total_profit_loss": round(total_profit, 2),
                "avg_profit_per_trade": round(avg_profit, 2),
                "successful_trades": len(successes),
                "failed_trades": len(failures),
                "insights": successful_conditions,
                "recommendation": self._generate_recommendation(success_rate, avg_profit, trades)
            }
            
            return insights
        
        except Exception as e:
            logger.error(f"Error getting pattern insights: {e}")
            return {"total_trades": 0, "insights": [f"Error: {str(e)}"]}
    
    def _generate_recommendation(self, success_rate: float, avg_profit: float, trades: List) -> str:
        """Generate trading recommendation based on historical performance."""
        if len(trades) < 5:
            return "Insufficient data - continue gathering experience"
        
        if success_rate > 60 and avg_profit > 0:
            return "POSITIVE - Strategy shows good performance"
        elif success_rate > 50 and avg_profit > 0:
            return "NEUTRAL - Strategy is profitable but inconsistent"
        elif success_rate < 40 or avg_profit < 0:
            return "NEGATIVE - Consider adjusting strategy or parameters"
        else:
            return "MIXED - Requires more data or parameter tuning"
    
    async def get_recent_lessons(self, limit: int = 10) -> List[str]:
        """Get recent lessons learned."""
        try:
            memories = await self.retrieve_memories(memory_type="trade_learning", limit=limit)
            
            all_lessons = []
            for memory in memories:
                lessons = memory.get("content", {}).get("lessons", [])
                all_lessons.extend(lessons)
            
            # Return unique lessons
            return list(set(all_lessons))[-limit:]
        
        except Exception as e:
            logger.error(f"Error getting recent lessons: {e}")
            return []
    
    async def clear_old_memories(self, days_to_keep: int = DEFAULT_MEMORY_CLEANUP_DAYS):
        """Clear memories older than specified days."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            result = await self.collection.delete_many({
                "timestamp": {"$lt": cutoff_date.isoformat()}
            })
            
            logger.info(f"{self.agent_name} cleared {result.deleted_count} old memories")
            return result.deleted_count
        
        except Exception as e:
            logger.error(f"Error clearing old memories: {e}")
            return 0


class MemoryManager:
    """Central memory manager for all agents."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.agent_memories = {
            "NexusChat": AgentMemory(db, "NexusChat"),
            "CypherMind": AgentMemory(db, "CypherMind"),
            "CypherTrade": AgentMemory(db, "CypherTrade")
        }
    
    def get_agent_memory(self, agent_name: str) -> AgentMemory:
        """Get memory for specific agent."""
        if agent_name not in self.agent_memories:
            self.agent_memories[agent_name] = AgentMemory(self.db, agent_name)
        return self.agent_memories[agent_name]
    
    async def store_collective_memory(self, memory_type: str, content: Dict[str, Any]):
        """Store a memory accessible to all agents."""
        try:
            collective_entry = {
                "type": "collective",
                "memory_type": memory_type,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self.db.collective_memory.insert_one(collective_entry)
            logger.info(f"Stored collective memory: {memory_type}")
        
        except Exception as e:
            logger.error(f"Error storing collective memory: {e}")
    
    async def get_collective_insights(self) -> Dict[str, Any]:
        """Get insights from all agents combined."""
        try:
            insights = {}
            
            for agent_name, memory in self.agent_memories.items():
                agent_insights = {
                    "total_memories": await self.db[f"memory_{agent_name.lower()}"].count_documents({}),
                    "recent_lessons": await memory.get_recent_lessons(limit=5)
                }
                insights[agent_name] = agent_insights
            
            return insights
        
        except Exception as e:
            logger.error(f"Error getting collective insights: {e}")
            return {}
    
    async def generate_memory_summary(self, agent_name: str) -> str:
        """Generate a text summary of agent's memory for injection into prompts."""
        try:
            memory = self.get_agent_memory(agent_name)
            
            # Get recent lessons
            lessons = await memory.get_recent_lessons(limit=5)
            
            # Get recent trade learnings
            recent_trades = await memory.retrieve_memories(memory_type="trade_learning", limit=5)
            
            summary = f"\n=== Memory Summary for {agent_name} ===\n"
            
            if lessons:
                summary += "\nRecent Lessons Learned:\n"
                for i, lesson in enumerate(lessons, 1):
                    summary += f"{i}. {lesson}\n"
            
            if recent_trades:
                summary += "\nRecent Trade Outcomes:\n"
                for trade in recent_trades[:3]:
                    content = trade.get("content", {})
                    outcome = content.get("outcome", "unknown")
                    profit = content.get("profit_loss", 0)
                    strategy = content.get("strategy", "unknown")
                    summary += f"- {strategy}: {outcome} (P&L: ${profit:.2f})\n"
            
            if not lessons and not recent_trades:
                summary += "No prior learning data available yet.\n"
            
            summary += "=== End Memory Summary ===\n"
            
            return summary
        
        except Exception as e:
            logger.error(f"Error generating memory summary: {e}")
            return f"\n=== No memory available for {agent_name} ===\n"
