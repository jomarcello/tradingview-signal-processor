import os
import json
import logging
import traceback
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright
import aiohttp
from python_socks.async_.asyncio import Proxy
import asyncio
from datetime import datetime
import pytz
from bs4 import BeautifulSoup
import requests
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app with increased timeout
app = FastAPI()

# Constants
MAX_RETRIES = 3
REQUEST_TIMEOUT = 60  # seconds for all requests
PROXY_URL = os.getenv("PROXY_URL", "http://proxy.apify.com:8000")
PROXY_USERNAME = os.getenv("PROXY_USERNAME")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")

# Services URLs
SIGNAL_AI_SERVICE_URL = "https://tradingview-signal-ai-service-production.up.railway.app"  # AI service for analysis and formatting
NEWS_AI_SERVICE_URL = "https://tradingview-news-ai-service-production.up.railway.app"  # AI service for news analysis
SUBSCRIBER_MATCHER_URL = "https://sup-abase-subscriber-matcher-production.up.railway.app"  # Subscriber matcher service
SUPABASE_URL = 'https://utigkgjcyqnrhpndzqhs.supabase.co/rest/v1/subscribers'  # Supabase database for subscribers
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV0aWdrZ2pjeXFucmhwbmR6cWhzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjMyMzA1NiwiZXhwIjoyMDUxODk5MDU2fQ.8JovzmGQofC4oC2016P7aa6FZQESF3UNSjUTruIYWbg'
TELEGRAM_SERVICE = "https://tradingview-telegram-service-production.up.railway.app"  # Telegram service for sending signals
CHART_SERVICE_URL = "https://tradingview-chart-service-production.up.railway.app"  # Chart service for technical analysis

class TradingSignal(BaseModel):
    instrument: str
    action: str
    price: float
    timestamp: Optional[str]
    strategy: Optional[str]
    timeframe: Optional[str]
    stoploss: float
    takeprofit: float

async def get_rotating_proxy():
    """Get a rotating proxy from a proxy service"""
    if not PROXY_URL or not PROXY_USERNAME or not PROXY_PASSWORD:
        return None
        
    return {
        'server': PROXY_URL,
        'username': PROXY_USERNAME,
        'password': PROXY_PASSWORD
    }

async def get_browser():
    async with async_playwright() as p:
        return await p.chromium.launch(headless=True, args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--single-process',
            '--disable-gpu',
            '--disable-extensions',
            '--disable-software-rasterizer',
            '--disable-features=site-per-process',
            '--js-flags=--max-old-space-size=500'  # Limit JS heap size
        ])

async def get_news_with_playwright(instrument: str) -> List[dict]:
    """Get news for a specific instrument using Playwright"""
    logger.info(f"Getting news for {instrument}")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            logger.info("Browser launched successfully with debugging options")
            
            try:
                page = await browser.new_page(
                    viewport={'width': 1920, 'height': 1080}
                )
                
                await page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.9'
                })
                
                url = f"https://www.tradingview.com/symbols/{instrument}/news/"
                await page.goto(url, timeout=60000)  # Increased timeout to 60 seconds
                logger.info(f"Navigated to URL: {url}")
                
                # Wait for content with increased timeout
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=60000)
                    await page.wait_for_selector("article", timeout=60000)
                except Exception as e:
                    logger.warning(f"Timeout waiting for page load: {str(e)}")
                    # Continue anyway as we might have some content
                
                articles = []
                scroll_attempts = 0
                max_scroll_attempts = 5
                
                while scroll_attempts < max_scroll_attempts:
                    scroll_attempts += 1
                    logger.info(f"Scroll attempt {scroll_attempts}/{max_scroll_attempts}")
                    
                    # Get current height
                    current_height = await page.evaluate("document.body.scrollHeight")
                    logger.info(f"Current height: {current_height}")
                    
                    # Scroll to bottom
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2000)  # Wait for content to load
                    
                    # Get new height
                    new_height = await page.evaluate("document.body.scrollHeight")
                    logger.info(f"New height after scroll: {new_height}")
                    
                    # Get all articles after scroll
                    article_elements = await page.query_selector_all("article")
                    logger.info(f"Found {len(article_elements)} articles after scroll {scroll_attempts}")
                    
                    if new_height == current_height:
                        logger.info("No new content loaded, stopping scroll")
                        break
                
                # Take screenshot for debugging
                await page.screenshot(path="debug_screenshot.png")
                logger.info("Screenshot saved")
                
                # Get all article elements
                article_elements = await page.query_selector_all("article")
                if not article_elements:
                    logger.warning("No articles found, returning empty list")
                    return []
                    
                logger.info(f"Found {len(article_elements)} news items")
                
                # Get all titles first
                titles = []
                for article in article_elements:
                    title_element = await article.query_selector('[data-name="news-headline-title"]')
                    if title_element:
                        title = await title_element.text_content()
                        titles.append(title)
                    else:
                        titles.append(None)
                
                logger.info(f"All titles found on page: {titles}")
                
                # Define wanted providers
                wanted_providers = {'reuters', 'forexlive', 'dow jones newswires', 'trading economics'}
                logger.info(f"Looking for 3 most recent articles from any of these providers: {wanted_providers}")
                
                articles_found = 0
                for article in article_elements:
                    if articles_found >= 3:
                        logger.info("Found 3 articles, stopping search")
                        break
                        
                    try:
                        # Get provider
                        provider_element = await article.query_selector('.provider-TUPxzdRV')
                        if not provider_element:
                            continue
                            
                        provider = await provider_element.text_content()
                        provider = provider.lower().strip()
                        logger.info(f"Found article from provider: {provider}")
                        
                        if provider not in wanted_providers:
                            continue
                            
                        # Get title
                        title_element = await article.query_selector('[data-name="news-headline-title"]')
                        if not title_element:
                            continue
                            
                        title = await title_element.text_content()
                        logger.info(f"Found article from wanted provider {provider}: {title}")
                        
                        # Add article even without content if we can't get it
                        articles.append({
                            'title': title,
                            'content': title  # Use title as content if we can't get full content
                        })
                        articles_found += 1
                        
                    except Exception as e:
                        logger.warning(f"Error processing article: {str(e)}")
                        continue
                
                return articles
                
            finally:
                logger.info("Cleaning up browser resources")
                await browser.close()
        
    except Exception as e:
        logger.error(f"Failed to get news: {str(e)}")
        logger.error(f"Error traceback: {traceback.format_exc()}")
        return []

async def get_subscribers(instrument: str, timeframe: str) -> List[dict]:
    """Haal subscribers op uit Supabase die matchen met het instrument en timeframe."""
    async with httpx.AsyncClient(timeout=60.0) as client:  # Increased timeout to 60 seconds
        response = await client.get(
            f"{SUPABASE_URL}?select=*&instrument=eq.{instrument}&timeframe=eq.{timeframe}",
            headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json'
            }
        )
        response.raise_for_status()
        return response.json()

async def get_subscribers() -> List[dict]:
    """Haal subscribers op uit Supabase."""
    async with httpx.AsyncClient(timeout=60.0) as client:  # Increased timeout to 60 seconds
        response = await client.get(
            f"{SUPABASE_URL}?select=*",
            headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json'
            }
        )
        response.raise_for_status()
        return response.json()

@app.post("/trading-signal")
async def process_trading_signal(signal: TradingSignal) -> dict:
    """Process a trading signal and send it to subscribers"""
    try:
        logger.info(f"Processing signal for {signal.instrument}")
        
        # Format signal data
        signal_data = {
            "instrument": signal.instrument,
            "direction": signal.action,
            "entry_price": str(signal.price),
            "stop_loss": str(signal.stoploss),
            "take_profit": str(signal.takeprofit),
            "timeframe": signal.timeframe,
            "strategy": signal.strategy,
            "timestamp": signal.timestamp
        }
        
        # Step 1: Get news articles
        try:
            articles = await get_news_with_playwright(signal.instrument)
            logger.info(f"Got {len(articles)} news articles")
            
            # Send articles to news AI service
            if articles:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    response = await client.post(
                        f"{NEWS_AI_SERVICE_URL}/analyze-news",
                        json={"instrument": signal.instrument, "articles": articles}
                    )
                    response.raise_for_status()
                    logger.info("Sent articles to news AI service")
                    
        except Exception as e:
            logger.error(f"Error processing news: {str(e)}")
            # Continue even if news processing fails
        
        # Step 2: Send to subscriber matcher
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(
                    f"{SUBSCRIBER_MATCHER_URL}/match-subscribers",
                    json=signal_data
                )
                response.raise_for_status()
                subscriber_result = response.json()
                logger.info("Got subscriber matches")
                
                # Add chat IDs to signal data
                signal_data["chat_ids"] = subscriber_result["chat_ids"]
                
        except Exception as e:
            logger.error(f"Error sending to subscriber matcher: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error getting subscribers: {str(e)}")
            
        # Step 3: Send to chart service
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(
                    f"{CHART_SERVICE_URL}/capture-chart",
                    json=signal_data
                )
                response.raise_for_status()
                logger.info("Signal sent to chart service")
                
        except Exception as e:
            logger.error(f"Error sending to chart service: {str(e)}")
            # Continue even if chart service fails
            
        # Step 4: Get AI analysis
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(
                    f"{SIGNAL_AI_SERVICE_URL}/analyze-signal",
                    json=signal_data
                )
                response.raise_for_status()
                analysis_result = response.json()
                logger.info(f"Got AI analysis: {analysis_result}")
                
                # Add AI verdict to signal data
                signal_data["ai_verdict"] = analysis_result["verdict"]
                signal_data["risk_reward_ratio"] = analysis_result["risk_reward_ratio"]
                
        except Exception as e:
            logger.error(f"Error getting AI analysis: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error getting AI analysis: {str(e)}")
            
        # Step 5: Get formatted message
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(
                    f"{SIGNAL_AI_SERVICE_URL}/format-signal",
                    json=signal_data
                )
                response.raise_for_status()
                format_result = response.json()
                logger.info("Got formatted message from AI service")
                
                # Add formatted message to signal data
                signal_data["formatted_message"] = format_result["formatted_message"]
                
        except Exception as e:
            logger.error(f"Error formatting signal: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error formatting signal: {str(e)}")
            
        # Step 6: Send to Telegram service
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(
                    f"{TELEGRAM_SERVICE}/send-signal",
                    json={"signal_data": signal_data, "chat_ids": signal_data["chat_ids"]}
                )
                response.raise_for_status()
                logger.info("Signal sent to Telegram service")
                
        except Exception as e:
            logger.error(f"Error sending to Telegram: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error sending to Telegram: {str(e)}")
            
        return {"status": "success", "message": "Signal processed and sent successfully"}
        
    except Exception as e:
        logger.error(f"Error processing signal: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing signal: {str(e)}")

@app.get("/get-news")
async def get_news(instrument: str):
    """Get news articles for a specific instrument from TradingView"""
    try:
        logger.info(f"Getting news for {instrument}")
        articles = await get_news_with_playwright(instrument)
        
        if not articles:
            logger.warning(f"No news found for {instrument}")
            return {"status": "error", "message": "No news found"}
            
        return {
            "status": "success",
            "articles": articles
        }
            
    except Exception as e:
        logger.error(f"Error getting news: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
