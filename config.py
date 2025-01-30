import os
from typing import Dict, Any
from dotenv import load_dotenv
from pydantic import BaseSettings, HttpUrl

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    # Service URLs
    SIGNAL_AI_SERVICE_URL: HttpUrl = os.getenv("SIGNAL_AI_SERVICE_URL", "https://tradingview-signal-ai-service-production.up.railway.app")
    NEWS_AI_SERVICE_URL: HttpUrl = os.getenv("NEWS_AI_SERVICE_URL", "https://tradingview-news-ai-service-production.up.railway.app")
    SUBSCRIBER_MATCHER_URL: HttpUrl = os.getenv("SUBSCRIBER_MATCHER_URL", "https://sup-abase-subscriber-matcher-production.up.railway.app")
    TELEGRAM_SERVICE_URL: HttpUrl = os.getenv("TELEGRAM_SERVICE_URL", "https://tradingview-telegram-service-production.up.railway.app")
    CHART_SERVICE_URL: HttpUrl = os.getenv("CHART_SERVICE_URL", "https://tradingview-chart-service-production.up.railway.app")
    
    # Supabase Configuration
    SUPABASE_URL: HttpUrl = os.getenv("SUPABASE_URL", "https://utigkgjcyqnrhpndzqhs.supabase.co/rest/v1/subscribers")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # Proxy Configuration
    PROXY_URL: str = os.getenv("PROXY_URL", "http://proxy.apify.com:8000")
    PROXY_USERNAME: str = os.getenv("PROXY_USERNAME", "")
    PROXY_PASSWORD: str = os.getenv("PROXY_PASSWORD", "")
    
    # Request Configuration
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "60"))
    
    # Monitoring Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_MONITORING: bool = os.getenv("ENABLE_MONITORING", "true").lower() == "true"
    
    # News Scraping Configuration
    MAX_NEWS_ARTICLES: int = int(os.getenv("MAX_NEWS_ARTICLES", "3"))
    WANTED_NEWS_PROVIDERS: set = {
        'reuters',
        'forexlive',
        'dow jones newswires',
        'trading economics'
    }
    
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
    return {
        'apikey': settings.SUPABASE_KEY,
        'Authorization': f'Bearer {settings.SUPABASE_KEY}',
        'Content-Type': 'application/json'
    }

def validate_settings() -> None:
    """Validate required settings"""
    missing = []
    
    if not settings.SUPABASE_KEY:
        missing.append("SUPABASE_KEY")
        
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

# Validate settings on import
validate_settings()