"""
Core Configuration Module - AI Trading Platform
Carica variabili d'ambiente e file YAML di configurazione.
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


CONFIG_DIR = Path(__file__).parent.parent.parent / "configs"


class Settings(BaseSettings):
    """Configurazione principale caricata da variabili d'ambiente."""

    # App
    APP_ENV: str = "paper"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "change_me"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql://trading:trading_secret@postgres:5432/trading_db"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Alpaca
    ALPACA_API_KEY: str = ""
    ALPACA_API_SECRET: str = ""
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"
    ALPACA_DATA_URL: str = "https://data.alpaca.markets"

    # LLM
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2000

    # News
    NEWSAPI_KEY: str = ""
    FINNHUB_API_KEY: str = ""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Restituisce l'istanza singleton delle Settings."""
    return Settings()


def load_yaml(filename: str) -> dict:
    """Carica un file YAML dalla cartella configs/."""
    path = CONFIG_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_assets_config() -> dict:
    return load_yaml("assets.yaml")


def get_risk_config() -> dict:
    return load_yaml("risk.yaml")


def get_broker_config() -> dict:
    return load_yaml("broker.yaml")


def get_agents_config() -> dict:
    return load_yaml("agents.yaml")


def get_symbols() -> List[str]:
    """Restituisce la lista dei simboli configurati."""
    assets = get_assets_config()
    return [a["symbol"] for a in assets.get("symbols", [])]


settings = get_settings()
