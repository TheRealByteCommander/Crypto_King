from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """Application configuration with environment variable support."""
    
    # MongoDB Configuration
    mongo_url: str
    db_name: str
    cors_origins: str = "*"
    
    # Binance Configuration
    binance_api_key: str
    binance_api_secret: str
    binance_testnet: bool = True
    
    # NexusChat Agent LLM Configuration
    nexuschat_llm_provider: str = "openai"
    nexuschat_api_key: str
    nexuschat_model: str = "gpt-4"
    
    # CypherMind Agent LLM Configuration
    cyphermind_llm_provider: str = "openai"
    cyphermind_api_key: str
    cyphermind_model: str = "gpt-4"
    
    # CypherTrade Agent LLM Configuration
    cyphertrade_llm_provider: str = "openai"
    cyphertrade_api_key: str
    cyphertrade_model: str = "gpt-4"
    
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