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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app with increased timeout
app = FastAPI()

# Constants
MAX_RETRIES = 3
REQUEST_TIMEOUT = 60  # seconds
PROXY_URL = os.getenv("PROXY_URL", "http://proxy.apify.com:8000")
PROXY_USERNAME = os.getenv("PROXY_USERNAME")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")

class TradingSignal(BaseModel):
    action: str
    price: float
    strategy: Optional[str]
    timeframe: Optional[str]
    instrument: str
    timestamp: Optional[str]

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
        browser = await get_browser()
        context = await browser.new_context(
            viewport={'width': 1024, 'height': 768},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        
        page = await context.new_page()
        
        # First login
        logger.info("Logging in")
        await page.goto('https://www.tradingview.com/#signin', wait_until='networkidle', timeout=60000)
        await page.fill('input[name="username"]', os.getenv("TRADINGVIEW_EMAIL"), timeout=60000)
        await page.fill('input[name="password"]', os.getenv("TRADINGVIEW_PASSWORD"), timeout=60000)
        await page.click('button[type="submit"]', timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=60000)
        
        # Go to news page
        logger.info("Going to news page")
        url = f'https://www.tradingview.com/news/?symbol={instrument}'
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=60000)
        
        # Wait for news feed
        logger.info("Waiting for news feed")
        await page.wait_for_selector('.news-feed article', timeout=60000)
        
        # Get news content
        articles = []
        news_items = await page.query_selector_all('.news-feed article')
        
        for item in news_items:
            title_el = await item.query_selector('.news-feed__title')
            content_el = await item.query_selector('.news-feed__content')
            
            if title_el and content_el:
                title = await title_el.text_content()
                content = await content_el.text_content()
                articles.append({
                    'title': title.strip(),
                    'content': content.strip()
                })
        
        logger.info(f"Found {len(articles)} articles")
        
        await context.close()
        await browser.close()
        
        return articles
        
    except Exception as e:
        logger.error(f"Failed to get news: {str(e)}")
        logger.error(f"Error traceback: {traceback.format_exc()}")
        if 'context' in locals():
            await context.close()
        if 'browser' in locals():
            await browser.close()
        raise

@app.post("/trading-signal")
async def process_trading_signal(signal: TradingSignal):
    """Process a trading signal and retrieve relevant news"""
    try:
        news_data = await get_news_with_playwright(signal.instrument)
        logger.info(f"News data scraped successfully: {news_data}")
        
        return {
            "status": "success",
            "message": "Signal processed successfully",
            "data": {
                "signal": {
                    "instrument": signal.instrument,
                    "timestamp": signal.timestamp
                },
                "news": news_data[0] if news_data else {"title": "No news found", "content": "No content found"},
                "timestamp": signal.timestamp
            }
        }
        
    except Exception as e:
        logger.error(f"Error in processing: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "message": f"Error processing signal: {str(e)}",
            "data": None
        }
