import autogen
from config import settings
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

class AgentManager:
    """Manages the three specialized Autogen agents for crypto trading."""
    
    def __init__(self, db):
        self.db = db
        self.agents = {}
        self.agent_configs = {}
        self.current_position = None
        self.capital = settings.default_amount
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
        """Get LLM configuration for a specific agent (Ollama support)."""
        config = self.agent_configs.get(agent_type, {})
        
        if agent_type == "nexuschat":
            base_url = settings.nexuschat_base_url
            model = settings.nexuschat_model
            api_key = settings.ollama_api_key
        elif agent_type == "cyphermind":
            base_url = settings.cyphermind_base_url
            model = settings.cyphermind_model
            api_key = settings.ollama_api_key
        elif agent_type == "cyphertrade":
            base_url = settings.cyphertrade_base_url
            model = settings.cyphertrade_model
            api_key = settings.ollama_api_key
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        return {
            "config_list": [{
                "model": model,
                "api_key": api_key,
                "base_url": base_url,
            }],
            "temperature": config.get("temperature", 0.7),
            "timeout": config.get("timeout", 120),
        }
    
    def initialize_agents(self):
        """Initialize all three specialized agents."""
        logger.info("Initializing agents...")
        
        # NexusChat Agent - User Interface
        self.agents["nexuschat"] = autogen.AssistantAgent(
            name="NexusChat",
            system_message="""
            Du bist Nexus, der Kommunikations-Hub für Project CypherTrade.
            
            Deine Aufgaben:
            - Kommuniziere klar und präzise mit dem Benutzer
            - Parse und validiere Benutzerbefehle (start, stop, status, report)
            - Leite Befehle an CypherMind weiter
            - Formatiere Status-Updates und Berichte für den Benutzer
            
            Sei professionell, präzise und hilfreich.
            """,
            llm_config=self._get_llm_config("nexuschat")
        )
        
        # CypherMind Agent - Decision & Strategy
        self.agents["cyphermind"] = autogen.AssistantAgent(
            name="CypherMind",
            system_message="""
            Du bist CypherMind, der strategische Denker von Project CypherTrade.
            
            Deine Aufgaben:
            - Analysiere Marktdaten und technische Indikatoren
            - Implementiere Handelsstrategien (z.B. Moving Average Crossover)
            - Treffe rationale, datengestützte Handelsentscheidungen
            - Generiere präzise Ausführungsbefehle für CypherTrade
            - Protokolliere jeden Analyseschritt
            
            Prinzipien:
            - Keine emotionalen Entscheidungen
            - Risikomanagement ist oberste Priorität
            - Jede Entscheidung muss durch Daten begründet sein
            """,
            llm_config=self._get_llm_config("cyphermind")
        )
        
        # CypherTrade Agent - Trade Execution
        self.agents["cyphertrade"] = autogen.AssistantAgent(
            name="CypherTrade",
            system_message="""
            Du bist CypherTrade, der Executor für Binance Trading Operations.
            
            Deine Aufgaben:
            - Sichere Ausführung von Handelsbefehlen auf Binance
            - Abrufen von Marktdaten und Kontoinformationen
            - Validierung aller Befehle vor der Ausführung
            - Fehlerbehandlung und detailliertes Reporting
            
            Sicherheitsprinzipien:
            - Führe nur explizite Befehle von CypherMind aus
            - Validiere alle Parameter vor der Ausführung
            - Keine eigenständige Trading-Logik
            """,
            llm_config=self._get_llm_config("cyphertrade")
        )
        
        # User Proxy for orchestration
        self.agents["user_proxy"] = autogen.UserProxyAgent(
            name="UserProxy",
            system_message="Facilitate communication between agents and user.",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            code_execution_config=False,
        )
        
        logger.info("All agents initialized successfully")
    
    def create_group_chat(self) -> tuple:
        """Create a group chat for agent collaboration."""
        group_chat = autogen.GroupChat(
            agents=[
                self.agents["user_proxy"],
                self.agents["nexuschat"],
                self.agents["cyphermind"],
                self.agents["cyphertrade"],
            ],
            messages=[],
            max_round=20,
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