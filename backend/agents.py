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
        """Get a specific agent by name."""
        if agent_name not in self.agents:
            raise ValueError(f"Agent {agent_name} not found")
        return self.agents[agent_name]
    
    async def chat_with_nexuschat(self, user_message: str, bot=None, db=None) -> Dict[str, Any]:
        """Chat directly with NexusChat agent with real bot status context."""
        try:
            nexuschat = self.agents["nexuschat"]
            user_proxy = self.agents["user_proxy"]
            
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
            
            # Build context message with real bot status and market data
            context_parts = []
            
            # If price query detected, fetch and include the price
            if symbol_to_fetch:
                try:
                    # Try to use bot's binance_client if available, otherwise create temporary one
                    from binance_client import BinanceClientWrapper
                    
                    if bot is not None and bot.binance_client is not None:
                        current_price = bot.binance_client.get_current_price(symbol_to_fetch)
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
            if bot is not None:
                try:
                    bot_status = await bot.get_status()
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
                        if bot.binance_client is not None and symbol and symbol != "N/A":
                            try:
                                current_price = bot.binance_client.get_current_price(symbol)
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
            
            # Add recent trade history if available
            # Use explicit None check - database objects cannot be used as boolean
            if db is not None:
                try:
                    recent_trades = await db.trades.find({}, {"_id": 0}).sort("timestamp", -1).limit(5).to_list(5)
                    if recent_trades:
                        context_parts.append(f"\n[LETZTE TRADES]")
                        for trade in recent_trades[:3]:  # Show only last 3
                            trade_info = f"- {trade.get('side', 'N/A')} {trade.get('symbol', 'N/A')}: {trade.get('quantity', 0)} @ {trade.get('price', 0)} USDT"
                            context_parts.append(trade_info)
                except Exception as e:
                    logger.warning(f"Could not get recent trades for context: {e}")
            
            # Combine context with user message
            if context_parts:
                context_message = "\n".join(context_parts)
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