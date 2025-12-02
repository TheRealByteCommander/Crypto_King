import autogen
from config import settings
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import yaml
from pathlib import Path
from memory_manager import MemoryManager
from agent_tools import AgentTools
from trading_knowledge_loader import TradingKnowledgeLoader

logger = logging.getLogger(__name__)

class AgentManager:
    """Manages the three specialized Autogen agents for crypto trading."""
    
    def __init__(self, db, bot=None, binance_client=None):
        self.db = db
        self.bot = bot
        self.binance_client = binance_client
        self.agents = {}
        self.agent_configs = {}
        self.current_position = None
        self.capital = settings.default_amount
        self.memory_manager = MemoryManager(db)
        # Initialize trading knowledge loader
        self.trading_knowledge_loader = TradingKnowledgeLoader(db)
        self.trading_knowledge = None  # Will be loaded on first access
        # Initialize agent tools
        self.agent_tools = AgentTools(bot=bot, binance_client=binance_client, db=db)
        self.load_agent_configs()
        self.initialize_agents()
    
    def load_agent_configs(self):
        """Load agent configurations from YAML files."""
        config_dir = Path(__file__).parent / "agent_configs"
        
        config_files = {
            "nexuschat": "nexuschat_config.yaml",
            "cyphermind": "cyphermind_config.yaml",
            "cyphertrade": "cyphertrade_config.yaml"
        }
        
        for agent_key, filename in config_files.items():
            config_path = config_dir / filename
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.agent_configs[agent_key] = yaml.safe_load(f)
                logger.info(f"Loaded config for {agent_key} from {filename}")
            except Exception as e:
                logger.error(f"Error loading config for {agent_key}: {e}")
                # Fallback to default config
                self.agent_configs[agent_key] = {
                    "system_message": f"You are {agent_key} agent.",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "timeout": 120
                }
    
    def _get_llm_config(self, agent_type: str) -> Dict[str, Any]:
        """Get LLM configuration for a specific agent with tools (Ollama support)."""
        config = self.agent_configs.get(agent_type, {})
        
        if agent_type == "nexuschat":
            base_url = settings.nexuschat_base_url
            model = settings.nexuschat_model
            api_key = settings.ollama_api_key
            # Get tools for NexusChat
            functions = self.agent_tools.get_nexuschat_tools()
        elif agent_type == "cyphermind":
            base_url = settings.cyphermind_base_url
            model = settings.cyphermind_model
            api_key = settings.ollama_api_key
            # Get tools for CypherMind (market data access)
            functions = self.agent_tools.get_cyphermind_tools()
        elif agent_type == "cyphertrade":
            base_url = settings.cyphertrade_base_url
            model = settings.cyphertrade_model
            api_key = settings.ollama_api_key
            # Get tools for CypherTrade (trade execution)
            functions = self.agent_tools.get_cyphertrade_tools()
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        llm_config = {
            "config_list": [{
                "model": model,
                "api_key": api_key,
                "base_url": base_url,
            }],
            "temperature": config.get("temperature", 0.7),
            "timeout": config.get("timeout", 120),
        }
        
        # Add functions/tools if available (for models that support function calling)
        # Note: Ollama may not support function calling in all models, but we provide it anyway
        if functions:
            llm_config["functions"] = functions
        
        return llm_config
    
    async def _enrich_system_message_with_memory(self, agent_name: str, base_message: str) -> str:
        """Enrich agent system message with memory/learning data."""
        try:
            memory_summary = await self.memory_manager.generate_memory_summary(agent_name)
            return base_message + "\n\n" + memory_summary
        except Exception as e:
            logger.warning(f"Could not load memory for {agent_name}: {e}")
            return base_message
    
    async def _enrich_system_message_with_trading_knowledge(self, agent_name: str, base_message: str) -> str:
        """Enrich agent system message with trading knowledge."""
        try:
            # Load trading knowledge if not already loaded
            if self.trading_knowledge is None:
                self.trading_knowledge = await self.trading_knowledge_loader.load_trading_knowledge()
            
            # Get relevant knowledge for this agent
            knowledge_text = self._format_trading_knowledge_for_agent(agent_name, self.trading_knowledge)
            
            return base_message + "\n\n" + knowledge_text
        except Exception as e:
            logger.warning(f"Could not load trading knowledge for {agent_name}: {e}")
            return base_message
    
    def _format_trading_knowledge_for_agent(self, agent_name: str, knowledge: Dict[str, Any]) -> str:
        """Formatiert Trading-Wissen für einen spezifischen Agent."""
        if not knowledge:
            return ""
        
        knowledge_section = "\n=== TRADING-WISSEN & MARKTPHASEN ===\n\n"
        
        # Market Phases Knowledge
        market_phases = knowledge.get("market_phases", {})
        knowledge_section += "MARKTPHASEN & TRADING-STRATEGIEN:\n"
        knowledge_section += "Du musst IMMER die aktuelle Marktphase erkennen (BULLISH, BEARISH, SIDEWAYS) und die richtige Strategie wählen!\n\n"
        
        for phase, info in market_phases.items():
            knowledge_section += f"📊 {phase}:\n"
            knowledge_section += f"  Charakteristika: {', '.join(info.get('characteristics', []))}\n"
            knowledge_section += f"  Trading-Ansatz: {', '.join(info.get('trading_approach', []))}\n\n"
        
        # Strategy Mapping
        strategy_mapping = knowledge.get("strategy_mapping", {})
        knowledge_section += "STRATEGIE-AUSWAHL BASIEREND AUF MARKTPHASE:\n"
        for phase, mapping in strategy_mapping.items():
            strategies = mapping.get("best_strategies", [])
            knowledge_section += f"  {phase}: {', '.join(strategies)}\n"
            knowledge_section += f"    → {mapping.get('description', '')}\n"
            for rec in mapping.get("recommendations", []):
                knowledge_section += f"    • {rec}\n"
            knowledge_section += "\n"
        
        # Trading Basics (for all agents)
        trading_basics = knowledge.get("trading_basics", {})
        if trading_basics:
            knowledge_section += "GRUNDLEGENDE TRADING-PRINZIPIEN:\n"
            for principle in trading_basics.get("principles", []):
                knowledge_section += f"  ✓ {principle}\n"
            knowledge_section += "\n"
        
        # Agent-specific knowledge
        if agent_name.lower() == "cyphermind":
            indicator_guidelines = knowledge.get("indicator_guidelines", {})
            knowledge_section += "INDIKATOR-RICHTLINIEN:\n"
            for indicator, guidelines in indicator_guidelines.items():
                knowledge_section += f"  {indicator.upper()}: {guidelines.get('description', '')}\n"
                knowledge_section += f"    Best für: {', '.join(guidelines.get('best_for', []))}\n"
                knowledge_section += f"    Verwendung: {guidelines.get('usage', '')}\n\n"
        
        knowledge_section += "=== ENDE TRADING-WISSEN ===\n"
        return knowledge_section
    
    async def update_trading_knowledge(self, force_refresh: bool = False):
        """Lädt und aktualisiert Trading-Wissen für alle Agents."""
        try:
            logger.info("Updating trading knowledge for all agents...")
            self.trading_knowledge = await self.trading_knowledge_loader.load_trading_knowledge(force_refresh=force_refresh)
            
            # Inject into all agents by updating the system_message attribute
            for agent_name in ["nexuschat", "cyphermind", "cyphertrade"]:
                if agent_name in self.agents:
                    config = self.agent_configs.get(agent_name, {})
                    base_message = config.get("system_message", "")
                    enriched_message = await self._enrich_system_message_with_trading_knowledge(agent_name, base_message)
                    # Update system message - Autogen agents store it in _system_message
                    if hasattr(self.agents[agent_name], '_system_message'):
                        self.agents[agent_name]._system_message = enriched_message
                    elif hasattr(self.agents[agent_name], 'system_message'):
                        self.agents[agent_name].system_message = enriched_message
                    logger.info(f"Updated trading knowledge for {agent_name}")
            
            logger.info("Trading knowledge updated for all agents")
            
        except Exception as e:
            logger.error(f"Error updating trading knowledge: {e}", exc_info=True)
    
    def initialize_agents(self):
        """Initialize all three specialized agents with configs from YAML files."""
        logger.info("Initializing agents from configuration files...")
        
        # NexusChat Agent - User Interface
        nexuschat_config = self.agent_configs.get("nexuschat", {})
        base_message = nexuschat_config.get("system_message", "You are NexusChat agent.")
        # Note: Memory enrichment happens async, so we use base message initially
        self.agents["nexuschat"] = autogen.AssistantAgent(
            name=nexuschat_config.get("agent_name", "NexusChat"),
            system_message=base_message,
            llm_config=self._get_llm_config("nexuschat")
        )
        logger.info(f"✓ {nexuschat_config.get('agent_name')} initialized")
        
        # CypherMind Agent - Decision & Strategy
        cyphermind_config = self.agent_configs.get("cyphermind", {})
        base_message = cyphermind_config.get("system_message", "You are CypherMind agent.")
        self.agents["cyphermind"] = autogen.AssistantAgent(
            name=cyphermind_config.get("agent_name", "CypherMind"),
            system_message=base_message,
            llm_config=self._get_llm_config("cyphermind")
        )
        logger.info(f"✓ {cyphermind_config.get('agent_name')} initialized")
        
        # CypherTrade Agent - Trade Execution
        cyphertrade_config = self.agent_configs.get("cyphertrade", {})
        base_message = cyphertrade_config.get("system_message", "You are CypherTrade agent.")
        self.agents["cyphertrade"] = autogen.AssistantAgent(
            name=cyphertrade_config.get("agent_name", "CypherTrade"),
            system_message=base_message,
            llm_config=self._get_llm_config("cyphertrade")
        )
        logger.info(f"✓ {cyphertrade_config.get('agent_name')} initialized")
        
        # User Proxy for orchestration
        self.agents["user_proxy"] = autogen.UserProxyAgent(
            name="UserProxy",
            system_message="Facilitate communication between agents and user.",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            code_execution_config=False,
        )
        logger.info("✓ UserProxy initialized")
        
        logger.info("=" * 60)
        logger.info("All agents initialized successfully from YAML configs")
        logger.info(f"NexusChat: {settings.nexuschat_model} @ {settings.nexuschat_base_url}")
        logger.info(f"CypherMind: {settings.cyphermind_model} @ {settings.cyphermind_base_url}")
        logger.info(f"CypherTrade: {settings.cyphertrade_model} @ {settings.cyphertrade_base_url}")
        logger.info("=" * 60)
    
    def create_group_chat(self) -> tuple:
        """Create a group chat for free agent collaboration."""
        
        # Flexible speaker selection - agents can speak freely
        def custom_speaker_selection(last_speaker, groupchat):
            """Allow agents to speak freely based on context."""
            messages = groupchat.messages
            
            if not messages:
                return self.agents["nexuschat"]
            
            last_message = messages[-1] if messages else None
            
            # If last speaker was user_proxy or nexuschat, let cyphermind analyze
            if last_speaker in [self.agents["user_proxy"], self.agents["nexuschat"]]:
                return self.agents["cyphermind"]
            
            # If cyphermind spoke, let cyphertrade execute or nexuschat respond
            elif last_speaker == self.agents["cyphermind"]:
                # Check if message contains action keywords
                if last_message and any(word in last_message.get("content", "").lower() 
                                       for word in ["execute", "trade", "buy", "sell", "data"]):
                    return self.agents["cyphertrade"]
                else:
                    return self.agents["nexuschat"]
            
            # If cyphertrade spoke, let cyphermind analyze results
            elif last_speaker == self.agents["cyphertrade"]:
                return self.agents["cyphermind"]
            
            # Default: let nexuschat summarize
            return self.agents["nexuschat"]
        
        group_chat = autogen.GroupChat(
            agents=[
                self.agents["user_proxy"],
                self.agents["nexuschat"],
                self.agents["cyphermind"],
                self.agents["cyphertrade"],
            ],
            messages=[],
            max_round=30,  # More rounds for free communication
            speaker_selection_method=custom_speaker_selection,
            allow_repeat_speaker=False,  # Encourage different agents to speak
        )
        
        manager = autogen.GroupChatManager(
            groupchat=group_chat,
            llm_config=self._get_llm_config("cyphermind")
        )
        
        return group_chat, manager
    
    async def log_agent_message(self, agent_name: str, message: str, message_type: str = "info"):
        """Log agent messages to database."""
        try:
            log_entry = {
                "agent_name": agent_name,
                "message": message,
                "message_type": message_type,
                "timestamp": datetime.now().isoformat()
            }
            await self.db.agent_logs.insert_one(log_entry)
        except Exception as e:
            logger.error(f"Error logging agent message: {e}")
    
    def get_agent(self, agent_name: str):
        """Get a specific agent by name (supports both name and key)."""
        # Normalize agent name to lowercase key
        agent_key = agent_name.lower()
        
        # Handle special cases
        if agent_name == "UserProxy":
            agent_key = "user_proxy"
        elif agent_name == "CypherMind":
            agent_key = "cyphermind"
        elif agent_name == "CypherTrade":
            agent_key = "cyphertrade"
        elif agent_name == "NexusChat":
            agent_key = "nexuschat"
        
        # Try direct lookup first
        if agent_name in self.agents:
            return self.agents[agent_name]
        
        # Try normalized key
        if agent_key in self.agents:
            return self.agents[agent_key]
        
        # Try case-insensitive search
        for key in self.agents.keys():
            if key.lower() == agent_name.lower():
                return self.agents[key]
        
        # If still not found, check agent names
        for key, agent in self.agents.items():
            if hasattr(agent, 'name') and agent.name == agent_name:
                return agent
        
        raise ValueError(f"Agent {agent_name} not found. Available agents: {list(self.agents.keys())}")
    
    async def share_news_with_agents(self, articles: List[Dict[str, Any]], 
                                     target_agents: List[str] = None,
                                     priority: str = "medium") -> Dict[str, Any]:
        """
        Teilt wichtige News mit anderen Agents (CypherMind, CypherTrade).
        
        Args:
            articles: Liste von News-Artikeln
            target_agents: Liste von Agent-Namen oder ["both"] für beide
            priority: "high", "medium", "low"
        
        Returns:
            Dict mit Ergebnis der Weiterleitung
        """
        if target_agents is None:
            target_agents = ["both"]
        
        shared_with = []
        
        try:
            # Format news message
            news_messages = []
            for article in articles[:5]:  # Max 5 articles per message
                title = article.get("title", "No title")
                summary = article.get("summary", "")[:200]  # Limit summary
                link = article.get("link", "")
                source = article.get("source", "Unknown")
                symbols = article.get("symbols", [])
                
                symbol_str = f" (Relevant für: {', '.join(symbols)})" if symbols else ""
                
                news_msg = f"📰 {title}{symbol_str}\n{summary}\nQuelle: {source}"
                if link:
                    news_msg += f"\nLink: {link}"
                
                news_messages.append(news_msg)
            
            news_text = "\n\n---\n\n".join(news_messages)
            
            # Determine which agents to notify
            notify_cyphermind = "CypherMind" in target_agents or "both" in target_agents
            notify_cyphertrade = "CypherTrade" in target_agents or "both" in target_agents
            
            # Share with CypherMind (for trading decisions)
            if notify_cyphermind:
                message = f"WICHTIGE MARKT-NEWS ({priority.upper()} PRIORITÄT):\n\n{news_text}\n\nBitte berücksichtige diese News bei deinen Trading-Entscheidungen. Besonders wichtig sind regulatorische Änderungen, Major Events, und signifikante Marktbewegungen."
                await self.log_agent_message("CypherMind", message, "news")
                shared_with.append("CypherMind")
                logger.info(f"Shared {len(articles)} news articles with CypherMind (priority: {priority})")
            
            # Share with CypherTrade (for risk management)
            if notify_cyphertrade:
                message = f"WICHTIGE MARKT-NEWS ({priority.upper()} PRIORITÄT):\n\n{news_text}\n\nBitte berücksichtige diese News bei deinem Risikomanagement. Besonders wichtig sind Security-Breaches, Exchange-Probleme, und regulatorische Änderungen die die Ausführung beeinflussen könnten."
                await self.log_agent_message("CypherTrade", message, "news")
                shared_with.append("CypherTrade")
                logger.info(f"Shared {len(articles)} news articles with CypherTrade (priority: {priority})")
            
            return {
                "success": True,
                "shared_with": shared_with,
                "count": len(articles),
                "message": f"News shared with {', '.join(shared_with)}"
            }
        
        except Exception as e:
            logger.error(f"Error sharing news with agents: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "shared_with": shared_with
            }
    
    async def chat_with_nexuschat(self, user_message: str, bot=None, db=None) -> Dict[str, Any]:
        """Chat directly with NexusChat agent with real bot status context."""
        try:
            logger.info(f"chat_with_nexuschat called with message: {user_message[:100]}...")
            nexuschat = self.agents["nexuschat"]
            user_proxy = self.agents["user_proxy"]
            
            # Handle BotManager - get first running bot or default bot
            actual_bot = None
            if bot is not None:
                # Check if bot is BotManager or TradingBot
                from bot_manager import BotManager
                if isinstance(bot, BotManager):
                    # Get first running bot, or default bot
                    running_bots = [b for b in bot.get_all_bots().values() if b.is_running]
                    if running_bots:
                        actual_bot = running_bots[0]  # Use first running bot
                    else:
                        # Use default bot or create one
                        actual_bot = bot.get_bot()
                else:
                    # It's a TradingBot instance
                    actual_bot = bot
            
            # Check if user is asking for a price and automatically fetch it
            user_lower = user_message.lower()
            price_query = None
            symbol_to_fetch = None
            
            # Common cryptocurrency symbols mapping
            symbol_map = {
                "bitcoin": "BTCUSDT",
                "btc": "BTCUSDT",
                "ethereum": "ETHUSDT",
                "eth": "ETHUSDT",
                "solana": "SOLUSDT",
                "sol": "SOLUSDT",
                "cardano": "ADAUSDT",
                "ada": "ADAUSDT",
                "polkadot": "DOTUSDT",
                "dot": "DOTUSDT",
                "chainlink": "LINKUSDT",
                "link": "LINKUSDT",
            }
            
            # Check if user is asking for a price
            price_keywords = ["preis", "kostet", "kurs", "preis", "wie viel", "what", "price", "cost", "rate"]
            for keyword in price_keywords:
                if keyword in user_lower:
                    # Find cryptocurrency name in message
                    for crypto_name, symbol in symbol_map.items():
                        if crypto_name in user_lower:
                            symbol_to_fetch = symbol
                            price_query = f"Der Benutzer fragt nach dem Preis für {crypto_name.upper()}. Hole den aktuellen Kurs mit get_current_price('{symbol}')."
                            break
                    break
            
            # Check if user is requesting a trade (buy/sell)
            trade_request = None
            trade_side = None
            trade_symbol = None
            trade_quantity = None
            trade_amount = None
            
            logger.info(f"Checking for trade commands in message: {user_message}")
            
            # Trade keywords - IMPORTANT: Check SELL first because "verkaufe" contains "kauf"
            # Use word boundaries to avoid substring matches
            import re
            
            sell_keywords = ["verkauf", "verkaufe", "verkaufen", "sell", "verkauft"]
            buy_keywords = ["kauf", "kaufe", "kaufen", "buy", "kauft"]
            
            # Check for SELL commands FIRST (before BUY, because "verkaufe" contains "kauf")
            # Use word boundaries to match whole words only
            for keyword in sell_keywords:
                # Use word boundary regex to match whole words only
                pattern = rf'\b{re.escape(keyword)}\b'
                if re.search(pattern, user_lower):
                    trade_side = "SELL"
                    logger.info(f"SELL keyword detected: '{keyword}' in message")
                    # Try to find cryptocurrency and quantity
                    # First, try to find exact matches in symbol_map
                    for crypto_name, symbol in symbol_map.items():
                        if crypto_name in user_lower:
                            trade_symbol = symbol
                            # Try to extract quantity from message
                            numbers = re.findall(r'\d+\.?\d*', user_message)
                            if numbers:
                                trade_quantity = float(numbers[0])
                            else:
                                # If no quantity specified, sell all available (will be handled in execute_manual_trade)
                                trade_quantity = None
                            break
                    
                    # If no symbol found yet, try to extract from common patterns
                    if not trade_symbol:
                        # Look for patterns like "den Bitcoin", "die Bitcoin", "Bitcoin", etc.
                        for crypto_name, symbol in symbol_map.items():
                            # Check for "den/die/der [crypto]" or just "[crypto]"
                            pattern = rf'\b(?:den|die|der|das|the)?\s*{crypto_name}\b'
                            if re.search(pattern, user_lower):
                                trade_symbol = symbol
                                # Try to extract quantity
                                numbers = re.findall(r'\d+\.?\d*', user_message)
                                if numbers:
                                    trade_quantity = float(numbers[0])
                                else:
                                    trade_quantity = None
                                break
                    
                    if trade_symbol:
                        trade_request = f"Der Benutzer möchte {trade_symbol} verkaufen."
                    break
            
            # Check for BUY commands (only if no SELL command was detected)
            if not trade_side:
                for keyword in buy_keywords:
                    # Use word boundary regex to match whole words only
                    pattern = rf'\b{re.escape(keyword)}\b'
                    if re.search(pattern, user_lower):
                        trade_side = "BUY"
                        logger.info(f"BUY keyword detected: '{keyword}' in message")
                        # Try to find cryptocurrency and quantity
                        # First, try to find exact matches in symbol_map
                        for crypto_name, symbol in symbol_map.items():
                            if crypto_name in user_lower:
                                trade_symbol = symbol
                                # Try to extract quantity/amount from message
                                # Look for numbers in the message
                                numbers = re.findall(r'\d+\.?\d*', user_message)
                                if numbers:
                                    # If keyword like "für" or "mit" or "$" before number, it's amount in USDT
                                    if any(word in user_lower for word in ["für", "mit", "$", "usdt", "dollar"]):
                                        trade_amount = float(numbers[0])
                                    else:
                                        trade_quantity = float(numbers[0])
                                break
                        
                        # If no symbol found yet, try to extract from common patterns
                        if not trade_symbol:
                            # Look for patterns like "den Bitcoin", "die Bitcoin", "Bitcoin", etc.
                            for crypto_name, symbol in symbol_map.items():
                                # Check for "den/die/der [crypto]" or just "[crypto]"
                                pattern = rf'\b(?:den|die|der|das|the)?\s*{crypto_name}\b'
                                if re.search(pattern, user_lower):
                                    trade_symbol = symbol
                                    # Try to extract quantity/amount
                                    numbers = re.findall(r'\d+\.?\d*', user_message)
                                    if numbers:
                                        if any(word in user_lower for word in ["für", "mit", "$", "usdt", "dollar"]):
                                            trade_amount = float(numbers[0])
                                        else:
                                            trade_quantity = float(numbers[0])
                                    break
                        
                        if trade_symbol:
                            trade_request = f"Der Benutzer möchte {trade_symbol} kaufen."
                        break
            
            # Legacy check (keep for backwards compatibility, but should not be reached if word boundaries work)
            if not trade_side:
                for keyword in sell_keywords:
                    if keyword in user_lower:
                        trade_side = "SELL"
                        # Try to find cryptocurrency and quantity
                        # First, try to find exact matches in symbol_map
                        for crypto_name, symbol in symbol_map.items():
                            if crypto_name in user_lower:
                                trade_symbol = symbol
                                # Try to extract quantity from message
                                import re
                                numbers = re.findall(r'\d+\.?\d*', user_message)
                                if numbers:
                                    trade_quantity = float(numbers[0])
                                else:
                                    # If no quantity specified, sell all available (will be handled in execute_manual_trade)
                                    trade_quantity = None
                                break
                        
                        # If no symbol found yet, try to extract from common patterns
                        if not trade_symbol:
                            import re
                            # Look for patterns like "den Bitcoin", "die Bitcoin", "Bitcoin", etc.
                            for crypto_name, symbol in symbol_map.items():
                                # Check for "den/die/der [crypto]" or just "[crypto]"
                                pattern = rf'\b(?:den|die|der|das|the)?\s*{crypto_name}\b'
                                if re.search(pattern, user_lower):
                                    trade_symbol = symbol
                                    # Try to extract quantity
                                    numbers = re.findall(r'\d+\.?\d*', user_message)
                                    if numbers:
                                        trade_quantity = float(numbers[0])
                                    else:
                                        trade_quantity = None
                                    break
                        
                        if trade_symbol:
                            trade_request = f"Der Benutzer möchte {trade_symbol} verkaufen."
                        break
            
            # Build context message with real bot status and market data
            context_parts = []
            
            # If price query detected, fetch and include the price
            if symbol_to_fetch:
                try:
                    # Try to use bot's binance_client if available, otherwise create temporary one
                    from binance_client import BinanceClientWrapper
                    
                    if actual_bot is not None and actual_bot.binance_client is not None:
                        current_price = actual_bot.binance_client.get_current_price(symbol_to_fetch)
                    elif self.binance_client is not None:
                        current_price = self.binance_client.get_current_price(symbol_to_fetch)
                    else:
                        # Create temporary binance client just to fetch price
                        temp_client = BinanceClientWrapper()
                        current_price = temp_client.get_current_price(symbol_to_fetch)
                    
                    context_parts.append(f"\n[AKTUELLER KURS - {symbol_to_fetch}]")
                    context_parts.append(f"- {symbol_to_fetch}: {current_price} USDT")
                    context_parts.append(f"- Format: 1 {symbol_to_fetch.replace('USDT', '')} = {current_price} USDT")
                    logger.info(f"Auto-fetched price for {symbol_to_fetch}: {current_price}")
                except Exception as e:
                    logger.warning(f"Could not auto-fetch price for {symbol_to_fetch}: {e}")
                    context_parts.append(f"\n[WARNUNG]")
                    context_parts.append(f"- Konnte Preis für {symbol_to_fetch} nicht abrufen: {str(e)}")
                    context_parts.append(f"- Fehler: {str(e)}")
            
            # Add bot status if available
            # Use explicit None check - database objects cannot be used as boolean
            if actual_bot is not None:
                try:
                    bot_status = await actual_bot.get_status()
                    if bot_status.get("is_running"):
                        config = bot_status.get("config", {})
                        symbol = config.get("symbol", "N/A")
                        strategy = config.get("strategy", "N/A")
                        amount = config.get("amount", 0)
                        
                        context_parts.append(f"\n[AKTUELLER BOT-STATUS]")
                        context_parts.append(f"- Bot läuft: Ja")
                        context_parts.append(f"- Symbol: {symbol}")
                        context_parts.append(f"- Strategie: {strategy}")
                        context_parts.append(f"- Betrag: ${amount}")
                        
                        # Get current price if bot is running and has binance_client
                        if actual_bot.binance_client is not None and symbol and symbol != "N/A":
                            try:
                                current_price = actual_bot.binance_client.get_current_price(symbol)
                                context_parts.append(f"- Aktueller Kurs für {symbol}: {current_price} USDT")
                            except Exception as e:
                                logger.warning(f"Could not get current price for {symbol}: {e}")
                        
                        # Get balances
                        balances = bot_status.get("balances", {})
                        if balances:
                            balance_info = ", ".join([f"{asset}: {bal}" for asset, bal in balances.items()])
                            context_parts.append(f"- Balances: {balance_info}")
                    else:
                        context_parts.append(f"\n[AKTUELLER BOT-STATUS]")
                        context_parts.append(f"- Bot läuft: Nein")
                except Exception as e:
                    logger.warning(f"Could not get bot status for context: {e}")
            
            # If trade request detected, execute it first
            trade_result = None
            logger.info(f"Trade detection result: trade_side={trade_side}, trade_symbol={trade_symbol}, bot={actual_bot is not None}")
            if trade_side and trade_symbol and actual_bot is not None:
                logger.info(f"Trade command detected! Side: {trade_side}, Symbol: {trade_symbol}, Quantity: {trade_quantity}, Amount: {trade_amount}")
                try:
                    # Ensure binance_client is available
                    # If bot is running, binance_client should exist, but check anyway
                    if actual_bot.binance_client is None:
                        from binance_client import BinanceClientWrapper
                        logger.warning(f"Bot binance_client is None, creating new client (bot.is_running={actual_bot.is_running})")
                        actual_bot.binance_client = BinanceClientWrapper()
                    
                    if actual_bot.binance_client is not None:
                        logger.info(f"Executing manual trade: {trade_side} {trade_quantity or trade_amount or 'all'} {trade_symbol}")
                        # Execute the trade
                        trade_result = await actual_bot.execute_manual_trade(
                            symbol=trade_symbol,
                            side=trade_side,
                            quantity=trade_quantity,
                            amount_usdt=trade_amount
                        )
                        
                        logger.info(f"Trade result: success={trade_result.get('success')}, message={trade_result.get('message')}")
                        
                        if trade_result.get("success"):
                            order = trade_result.get("order", {})
                            order_id = order.get("orderId") if order else None
                            executed_quantity = trade_result.get('quantity', trade_quantity or 'all')
                            price = trade_result.get('price', 'N/A')
                            
                            context_parts.append(f"\n[TRADE AUSGEFÜHRT]")
                            context_parts.append(f"- Order: {trade_side} {executed_quantity} {trade_symbol}")
                            context_parts.append(f"- Preis: {price} USDT")
                            if order_id:
                                context_parts.append(f"- Order ID: {order_id}")
                            else:
                                context_parts.append(f"- Order ID: Nicht verfügbar")
                            context_parts.append(f"- Status: Erfolgreich ausgeführt")
                            
                            await self.log_agent_message(
                                "CypherTrade",
                                f"Manual trade executed via NexusChat: {trade_side} {executed_quantity} {trade_symbol} at {price} USDT (Order ID: {order_id or 'N/A'})",
                                "trade"
                            )
                            
                            logger.info(f"Trade executed successfully: {trade_side} {executed_quantity} {trade_symbol} (Order ID: {order_id})")
                        else:
                            error_message = trade_result.get('message', 'Unbekannter Fehler')
                            context_parts.append(f"\n[TRADE FEHLGESCHLAGEN]")
                            context_parts.append(f"- Fehler: {error_message}")
                            context_parts.append(f"- Der Trade konnte nicht ausgeführt werden.")
                            context_parts.append(f"- Bitte versuche es erneut oder kontaktiere den Support.")
                            
                            await self.log_agent_message(
                                "CypherTrade",
                                f"Manual trade failed: {error_message}",
                                "error"
                            )
                            logger.error(f"Trade execution failed: {error_message}")
                    else:
                        error_msg = "Binance Client nicht verfügbar. Bitte starte den Bot zuerst."
                        context_parts.append(f"\n[TRADE FEHLER]")
                        context_parts.append(f"- {error_msg}")
                        logger.error(error_msg)
                except Exception as e:
                    error_str = str(e)
                    logger.error(f"Error executing trade from chat: {e}", exc_info=True)
                    context_parts.append(f"\n[TRADE FEHLER]")
                    context_parts.append(f"- Fehler beim Ausführen des Trades: {error_str}")
                    context_parts.append(f"- Der Trade konnte nicht ausgeführt werden.")
                    
                    await self.log_agent_message(
                        "CypherTrade",
                        f"Error executing manual trade: {error_str}",
                        "error"
                    )
            
            # Add recent trade history if available
            # Use explicit None check - database objects cannot be used as boolean
            if db is not None:
                try:
                    recent_trades = await db.trades.find({}, {"_id": 0}).sort("timestamp", -1).limit(5).to_list(5)
                    if recent_trades:
                        context_parts.append(f"\n[LETZTE TRADES]")
                        for trade in recent_trades[:3]:  # Show only last 3
                            side = trade.get('side', 'N/A')
                            symbol = trade.get('symbol', 'N/A')
                            quantity = trade.get('quantity', 0)
                            
                            # Get USDT value - prefer quote_qty, fallback to execution_price * quantity
                            quote_qty = trade.get('quote_qty', 0)
                            execution_price = trade.get('execution_price') or trade.get('entry_price')
                            
                            if quote_qty and quote_qty > 0:
                                usdt_value = quote_qty
                            elif execution_price and execution_price > 0 and quantity > 0:
                                usdt_value = execution_price * quantity
                            else:
                                usdt_value = 0
                            
                            # Format trade info with proper USDT value
                            trade_info = f"- {side} {symbol}: {quantity} @ {usdt_value:.2f} USDT"
                            if execution_price:
                                trade_info += f" (Preis: {execution_price:.6f})"
                            context_parts.append(trade_info)
                except Exception as e:
                    logger.warning(f"Could not get recent trades for context: {e}")
            
            # Combine context with user message
            if context_parts:
                context_message = "\n".join(context_parts)
                
                # Add instruction for trade requests
                if trade_side and trade_symbol:
                    if trade_result and trade_result.get("success"):
                        # Trade was successful - use ONLY real data from context
                        enhanced_message = f"{user_message}\n\n{context_message}\n\nKRITISCH WICHTIG - NUR ECHTE DATEN VERWENDEN:\n- Der Trade wurde von CypherTrade ausgeführt.\n- Verwende NUR die Informationen aus dem [TRADE AUSGEFÜHRT] Abschnitt im Kontext.\n- Wenn keine Order ID im Kontext steht, sage klar, dass die Order ID nicht verfügbar ist.\n- Erfinde KEINE Order IDs, Preise oder andere Details!\n- Wenn etwas nicht im Kontext steht, sage klar, dass diese Information nicht verfügbar ist."
                    elif trade_result and not trade_result.get("success"):
                        # Trade failed - inform user about the error
                        enhanced_message = f"{user_message}\n\n{context_message}\n\nKRITISCH WICHTIG:\n- Der Trade konnte NICHT ausgeführt werden.\n- Verwende NUR die Fehlermeldung aus dem [TRADE FEHLGESCHLAGEN] Abschnitt im Kontext.\n- Sage klar und direkt, dass der Trade fehlgeschlagen ist und warum.\n- Erfinde KEINE Details über einen erfolgreichen Trade!\n- Wenn der Fehler im Kontext steht, erkläre ihn dem Benutzer."
                    else:
                        # Trade execution was attempted but no result
                        enhanced_message = f"{user_message}\n\n{context_message}\n\nKRITISCH WICHTIG:\n- Der Trade konnte NICHT ausgeführt werden.\n- Es gibt KEINE [TRADE AUSGEFÜHRT] Information im Kontext.\n- Sage klar, dass der Trade nicht ausgeführt werden konnte.\n- Erfinde KEINE Order IDs, Preise oder Erfolgsmeldungen!\n- Informiere den Benutzer, dass ein Fehler aufgetreten ist."
                else:
                    enhanced_message = f"{user_message}\n\n{context_message}\n\nBitte verwende NUR diese echten Daten und erfinde keine Informationen!"
            else:
                enhanced_message = f"{user_message}\n\nWICHTIG: Wenn du keine echten Daten hast, sage das klar. Erfinde keine Kurse, Positionen oder andere Informationen!"
            
            # Create a simple chat between user_proxy and nexuschat
            # Use initiate_chat for direct communication (synchronous method)
            # Run in executor to avoid blocking
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Execute synchronous initiate_chat in thread pool
            response = await loop.run_in_executor(
                None,
                lambda: user_proxy.initiate_chat(
                    recipient=nexuschat,
                    message=enhanced_message,
                    max_turns=1,  # Single turn for direct chat
                    clear_history=False,  # Keep context
                    silent=False  # Allow logging
                )
            )
            
            # Extract the response from NexusChat
            # initiate_chat returns a ChatResult object
            # Get the last message from the chat history
            nexuschat_response = "No response received"
            sender = "NexusChat"
            
            if hasattr(response, 'chat_history') and response.chat_history:
                # Find the last message from NexusChat
                for msg in reversed(response.chat_history):
                    if hasattr(msg, 'name') and msg.name == nexuschat.name:
                        nexuschat_response = msg.content if hasattr(msg, 'content') else str(msg)
                        sender = msg.name if hasattr(msg, 'name') else "NexusChat"
                        break
                    elif isinstance(msg, dict) and msg.get("name") == nexuschat.name:
                        nexuschat_response = msg.get("content", str(msg))
                        sender = msg.get("name", "NexusChat")
                        break
            elif hasattr(response, 'summary') and response.summary:
                nexuschat_response = response.summary
            
            # Log the conversation
            await self.log_agent_message("NexusChat", f"User: {user_message}", "info")
            await self.log_agent_message("NexusChat", f"NexusChat: {nexuschat_response}", "info")
            
            return {
                "success": True,
                "response": nexuschat_response,
                "agent": sender,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error chatting with NexusChat: {e}", exc_info=True)
            await self.log_agent_message("NexusChat", f"Error: {str(e)}", "error")
            return {
                "success": False,
                "response": f"Error: {str(e)}",
                "agent": "NexusChat",
                "timestamp": datetime.now().isoformat()
            }