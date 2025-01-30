import logging
import traceback
import asyncio
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import httpx
from datetime import datetime

from config import settings, get_service_headers, get_supabase_headers
from news_scraper import get_news_articles
from monitoring import monitor
from proxy_manager import proxy_manager

# Initialize FastAPI app
app = FastAPI(title="TradingView Signal Processor")

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

class TradingSignal(BaseModel):
    instrument: str
    action: str
    price: float
    timestamp: str | None = None
    strategy: str | None = None
    timeframe: str | None = None
    stoploss: float
    takeprofit: float

async def get_http_client():
    """Get HTTP client with default configuration"""
    async with httpx.AsyncClient(
        timeout=settings.REQUEST_TIMEOUT,
        verify=True,  # Enable SSL verification
        headers=get_service_headers()
    ) as client:
        yield client

async def process_news(instrument: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    """Process news articles for an instrument"""
    try:
        articles = await get_news_articles(instrument)
        monitor.log_news_scrape(len(articles))
        
        if not articles:
            return {}
            
        response = await client.post(
            f"{settings.NEWS_AI_SERVICE_URL}/analyze-news",
            json={"instrument": instrument, "articles": articles}
        )
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        logger.error(f"Error processing news: {str(e)}")
        return {}

async def match_subscribers(
    instrument: str,
    timeframe: str,
    client: httpx.AsyncClient
) -> List[str]:
    """Match signal with subscribers"""
    try:
        # If Supabase key is not set, return empty list
        if not settings.SUPABASE_KEY:
            logger.warning("Supabase key not set. Skipping subscriber matching.")
            return []

        response = await client.post(
            f"{settings.SUBSCRIBER_MATCHER_URL}/match-subscribers",
            json={"instrument": instrument, "timeframe": timeframe}
        )
        response.raise_for_status()
        result = response.json()
        return result.get("chat_ids", [])
        
    except Exception as e:
        logger.error(f"Error matching subscribers: {str(e)}")
        return []  # Return empty list instead of raising error

async def get_chart_data(
    instrument: str,
    timeframe: str,
    client: httpx.AsyncClient
) -> bytes | None:
    """Get chart data from chart service"""
    try:
        response = await client.get(
            f"{settings.CHART_SERVICE_URL}/chart",
            params={
                "symbol": instrument,
                "interval": timeframe,
                "theme": "dark"
            }
        )
        response.raise_for_status()
        return response.content
        
    except Exception as e:
        logger.error(f"Error getting chart: {str(e)}")
        return None

async def get_ai_analysis(
    signal_data: Dict[str, Any],
    client: httpx.AsyncClient
) -> Dict[str, Any]:
    """Get AI analysis of the signal"""
    try:
        response = await client.post(
            f"{settings.SIGNAL_AI_SERVICE_URL}/analyze-signal",
            json=signal_data
        )
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        logger.error(f"Error getting AI analysis: {str(e)}")
        return {
            "verdict": "Analysis unavailable",
            "risk_reward_ratio": 0.0
        }

async def format_signal_message(
    signal_data: Dict[str, Any],
    client: httpx.AsyncClient
) -> str:
    """Get formatted signal message"""
    try:
        response = await client.post(
            f"{settings.SIGNAL_AI_SERVICE_URL}/format-signal",
            json=signal_data
        )
        response.raise_for_status()
        result = response.json()
        return result["formatted_message"]
        
    except Exception as e:
        logger.error(f"Error formatting signal: {str(e)}")
        # Provide basic formatting if AI service fails
        return f"""
Signal Alert

Instrument: {signal_data['instrument']}
Action: {signal_data['direction']}
Entry Price: {signal_data['entry_price']}
Stop Loss: {signal_data['stop_loss']}
Take Profit: {signal_data['take_profit']}
Timeframe: {signal_data.get('timeframe', 'Not specified')}
Strategy: {signal_data.get('strategy', 'Not specified')}
        """.strip()

async def send_telegram_message(
    signal_data: Dict[str, Any],
    chat_ids: List[str],
    client: httpx.AsyncClient
) -> None:
    """Send signal to Telegram service"""
    if not chat_ids:
        logger.warning("No chat IDs provided. Skipping Telegram message.")
        return

    try:
        response = await client.post(
            f"{settings.TELEGRAM_SERVICE_URL}/send-signal",
            json={"signal_data": signal_data, "chat_ids": chat_ids}
        )
        response.raise_for_status()
        
    except Exception as e:
        logger.error(f"Error sending to Telegram: {str(e)}")
        # Don't raise exception, just log the error

@app.post("/trading-signal")
async def process_trading_signal(
    signal: TradingSignal,
    client: httpx.AsyncClient = Depends(get_http_client)
) -> Dict[str, str]:
    """Process a trading signal and send it to subscribers"""
    try:
        monitor.log_request()
        logger.info(f"Processing signal for {signal.instrument}")
        
        # Format initial signal data
        signal_data = {
            "instrument": signal.instrument,
            "direction": signal.action,
            "entry_price": str(signal.price),
            "stop_loss": str(signal.stoploss),
            "take_profit": str(signal.takeprofit),
            "timeframe": signal.timeframe,
            "strategy": signal.strategy,
            "timestamp": signal.timestamp or datetime.now().isoformat()
        }
        
        # Step 1: Process news (non-blocking)
        news_result = await process_news(signal.instrument, client)
        if news_result:
            signal_data["news_analysis"] = news_result.get("sentiment")
        
        # Step 2: Match subscribers (continues even if no subscribers found)
        chat_ids = await match_subscribers(signal.instrument, signal.timeframe, client)
        signal_data["chat_ids"] = chat_ids
        
        # Step 3: Get chart (non-blocking)
        chart_data = await get_chart_data(signal.instrument, signal.timeframe, client)
        if chart_data:
            signal_data["chart_data"] = chart_data
        
        # Step 4: Get AI analysis (continues with default if fails)
        analysis_result = await get_ai_analysis(signal_data, client)
        signal_data["ai_verdict"] = analysis_result.get("verdict", "Analysis unavailable")
        signal_data["risk_reward_ratio"] = analysis_result.get("risk_reward_ratio", 0.0)
        
        # Step 5: Format message (uses basic format if AI fails)
        signal_data["formatted_message"] = await format_signal_message(signal_data, client)
        
        # Step 6: Send to Telegram (skips if no chat IDs)
        if chat_ids:
            await send_telegram_message(signal_data, chat_ids, client)
        
        monitor.log_signal_processed()
        return {"status": "success", "message": "Signal processed successfully"}
        
    except Exception as e:
        monitor.log_error(str(e))
        logger.error(f"Error processing signal: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing signal: {str(e)}"
        )

@app.get("/get-news")
async def get_news(
    instrument: str,
    client: httpx.AsyncClient = Depends(get_http_client)
) -> Dict[str, Any]:
    """Get news articles for a specific instrument"""
    try:
        monitor.log_request()
        logger.info(f"Getting news for {instrument}")
        
        articles = await get_news_articles(instrument)
        monitor.log_news_scrape(len(articles))
        
        if not articles:
            return {
                "status": "error",
                "message": "No news found"
            }
            
        return {
            "status": "success",
            "articles": articles
        }
        
    except Exception as e:
        monitor.log_error(str(e))
        logger.error(f"Error getting news: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return monitor.get_health()

@app.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get service metrics"""
    return monitor.get_metrics()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        # Initialize proxy manager
        await proxy_manager.initialize()
        logger.info("Proxy manager initialized")
        
        # Start system monitoring if enabled
        if settings.ENABLE_MONITORING:
            asyncio.create_task(monitor.monitor_system_resources())
            logger.info("System monitoring started")
            
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        # Don't raise the error, allow service to start with limited functionality

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        await proxy_manager.cleanup()
        logger.info("Service shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
