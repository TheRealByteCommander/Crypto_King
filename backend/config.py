from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """Application configuration with environment variable support."""
    
    # MongoDB Configuration
    mongo_url: str
    db_name: str
    cors_origins: str = "*"
    
    # MCP Server Configuration
    mcp_enabled: bool = False
    mcp_port: int = 8002
    
    # Binance Configuration
    binance_api_key: str
    binance_api_secret: str
    binance_testnet: bool = True
    
    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_api_key: str = "ollama"
    
    # NexusChat Agent LLM Configuration
    nexuschat_llm_provider: str = "ollama"
    nexuschat_model: str = "llama3.2"
    nexuschat_base_url: str = "http://localhost:11434/v1"
    
    # CypherMind Agent LLM Configuration
    cyphermind_llm_provider: str = "ollama"
    cyphermind_model: str = "llama3.2"
    cyphermind_base_url: str = "http://localhost:11434/v1"
    
    # CypherTrade Agent LLM Configuration
    cyphertrade_llm_provider: str = "ollama"
    cyphertrade_model: str = "llama3.2"
    cyphertrade_base_url: str = "http://localhost:11434/v1"
    
    # Trading Configuration
    default_strategy: str = "ma_crossover"
    default_symbol: str = "BTCUSDT"
    default_amount: float = 100
    max_position_size: float = 1000
    risk_per_trade: float = 0.02
    
    # Notification Configuration
    email_enabled: bool = False
    email_host: str = ""
    email_port: int = 587
    email_user: str = ""
    email_password: str = ""
    email_to: str = ""
    
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

settings = Settings()