"""
Validation utilities for external service connections.
"""

import logging
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from binance.client import Client
from binance.exceptions import BinanceAPIException
from config import settings
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


async def validate_mongodb_connection() -> Tuple[bool, Optional[str]]:
    """
    Validate MongoDB connection.
    Returns: (is_valid, error_message)
    """
    try:
        client = AsyncIOMotorClient(settings.mongo_url, serverSelectionTimeoutMS=5000)
        # Try to ping the server
        await client.admin.command('ping')
        client.close()
        logger.info("MongoDB connection validated successfully")
        return True, None
    except Exception as e:
        error_msg = f"MongoDB connection failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def validate_binance_connection() -> Tuple[bool, Optional[str]]:
    """
    Validate Binance API connection.
    Returns: (is_valid, error_message)
    """
    try:
        client = Client(
            settings.binance_api_key,
            settings.binance_api_secret,
            testnet=settings.binance_testnet
        )
        # Try to get account info
        client.get_account()
        logger.info("Binance API connection validated successfully")
        return True, None
    except BinanceAPIException as e:
        error_msg = f"Binance API error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Binance connection failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


async def validate_ollama_connection() -> Tuple[bool, Optional[str]]:
    """
    Validate Ollama server connection.
    Returns: (is_valid, error_message)
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Try to access Ollama health endpoint or list models
            response = await client.get(f"{settings.ollama_base_url.replace('/v1', '')}/api/tags")
            if response.status_code == 200:
                logger.info("Ollama connection validated successfully")
                return True, None
            else:
                error_msg = f"Ollama server returned status {response.status_code}"
                logger.error(error_msg)
                return False, error_msg
    except httpx.TimeoutException:
        error_msg = "Ollama server connection timeout"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Ollama connection failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


async def validate_all_services() -> dict:
    """
    Validate all external services.
    Returns: dict with validation results for each service
    """
    results = {
        "mongodb": {"valid": False, "error": None},
        "binance": {"valid": False, "error": None},
        "ollama": {"valid": False, "error": None}
    }
    
    # Validate MongoDB
    mongodb_valid, mongodb_error = await validate_mongodb_connection()
    results["mongodb"] = {"valid": mongodb_valid, "error": mongodb_error}
    
    # Validate Binance
    binance_valid, binance_error = validate_binance_connection()
    results["binance"] = {"valid": binance_valid, "error": binance_error}
    
    # Validate Ollama
    ollama_valid, ollama_error = await validate_ollama_connection()
    results["ollama"] = {"valid": ollama_valid, "error": ollama_error}
    
    return results

