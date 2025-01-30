import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from pydantic import HttpUrl, Field
from pydantic_settings import BaseSettings

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Service URLs
    SIGNAL_AI_SERVICE_URL: str = Field("https://tradingview-signal-ai-service-production.up.railway.app")
    NEWS_AI_SERVICE_URL: str = Field("https://tradingview-news-ai-service-production.up.railway.app")
    SUBSCRIBER_MATCHER_URL: str = Field("https://sup-abase-subscriber-matcher-production.up.railway.app")
    TELEGRAM_SERVICE_URL: str = Field("https://tradingview-telegram-service-production.up.railway.app")
    CHART_SERVICE_URL: str = Field("https://tradingview-chart-service-production.up.railway.app")
    
    # Supabase Configuration
    SUPABASE_URL: str = Field("https://utigkgjcyqnrhpndzqhs.supabase.co/rest/v1/subscribers")
    SUPABASE_KEY: Optional[str] = Field(None)
    
    # Proxy Configuration
    PROXY_URL: Optional[str] = Field(None)
    PROXY_USERNAME: Optional[str] = Field(None)
    PROXY_PASSWORD: Optional[str] = Field(None)
    
    # Request Configuration
    MAX_RETRIES: int = Field(3)
    REQUEST_TIMEOUT: int = Field(60)
    
    # Monitoring Configuration
    LOG_LEVEL: str = Field("INFO")
    ENABLE_MONITORING: bool = Field(True)
    
    # News Scraping Configuration
    MAX_NEWS_ARTICLES: int = Field(3)
    WANTED_NEWS_PROVIDERS: set = Field(default_factory=lambda: {
        'reuters',
        'forexlive',
        'dow jones newswires',
        'trading economics'
    })
    
    class Config:
        case_sensitive = True
        env_file = ".env"

def get_settings() -> Settings:
    """Get application settings"""
    return Settings()

# Create settings instance
settings = get_settings()

def get_service_headers() -> Dict[str, str]:
    """Get common headers for service requests"""
    return {
        'Content-Type': 'application/json',
        'User-Agent': 'TradingView-Signal-Processor/1.0'
    }

def get_supabase_headers() -> Dict[str, str]:
    """Get headers for Supabase requests"""
    headers = {
        'Content-Type': 'application/json'
    }
    
    if settings.SUPABASE_KEY:
        headers.update({
            'apikey': settings.SUPABASE_KEY,
            'Authorization': f'Bearer {settings.SUPABASE_KEY}'
        })
    
    return headers

def validate_settings() -> None:
    """Log warnings for missing optional settings"""
    missing = []
    
    if not settings.SUPABASE_KEY:
        logger.warning("SUPABASE_KEY is not set. Some features may be limited.")
    
    if not settings.PROXY_URL or not settings.PROXY_USERNAME or not settings.PROXY_PASSWORD:
        logger.warning("Proxy settings are not complete. Running without proxy support.")

# Validate settings on import
validate_settings()