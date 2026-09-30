import os
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # Telegram
    TELEGRAM_BOT_TOKEN: str = Field(..., description="Telegram Bot Token")
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/travel_bot",
        description="PostgreSQL connection URL"
    )
    
    # OpenRouter
    OPENROUTER_API_KEY: str = Field(..., description="OpenRouter API Key")
    OPENROUTER_BASE_URL: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL"
    )
    OPENROUTER_MODEL: str = Field(
        default="meta-llama/llama-3.1-8b-instruct:free",
        description="OpenRouter model to use (free optimal model)"
    )
    
    # Travel APIs (optional - can use free APIs)
    AVIASALES_API_KEY: Optional[str] = Field(default=None, description="Aviasales API key for flights")
    AMADEUS_API_KEY: Optional[str] = Field(default=None, description="Amadeus API key")
    AMADEUS_API_SECRET: Optional[str] = Field(default=None, description="Amadeus API secret")
    BOOKING_COM_API_KEY: Optional[str] = Field(default=None, description="Booking.com API key")
    
    # App
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()