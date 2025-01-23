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

async def login_to_tradingview():
    """Login to TradingView using Playwright's built-in authentication"""
    logger.info("Starting login with Playwright")
    
    try:
        browser = await get_browser()
        context = await browser.new_context(
            viewport={'width': 1024, 'height': 768},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        
        page = await context.new_page()
        
        # Go to login page with increased timeout
        logger.info("Navigating to login page")
        await page.goto('https://www.tradingview.com/#signin', wait_until='networkidle', timeout=60000)
        
        # Fill in credentials with increased timeout
        logger.info("Filling in credentials")
        await page.fill('input[name="username"]', os.getenv("TRADINGVIEW_EMAIL"), timeout=60000)
        await page.fill('input[name="password"]', os.getenv("TRADINGVIEW_PASSWORD"), timeout=60000)
        
        # Click sign in button and wait for navigation
        logger.info("Clicking sign in button")
        await page.click('button[type="submit"]', timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=60000)
        
        # Get cookies after successful login
        logger.info("Getting cookies")
        cookies = await context.cookies()
        cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
        
        await context.close()
        await browser.close()
        
        logger.info("Login successful")
        return cookie_dict
        
    except Exception as e:
        logger.error(f"Login failed with error: {str(e)}")
        logger.error(f"Error traceback: {traceback.format_exc()}")
        raise

async def get_news_for_instrument(instrument: str) -> List[dict]:
    """Get news for a specific instrument"""
    logger.info(f"Getting news for {instrument}")
    
    try:
        # Get cookies from successful login
        cookies = await login_to_tradingview()
        logger.info("Got cookies from login")
        
        # Use cookies for subsequent requests
        timeout = aiohttp.ClientTimeout(total=60)  # 60 seconds timeout
        async with aiohttp.ClientSession(cookies=cookies, timeout=timeout) as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            url = f'https://www.tradingview.com/news/?symbol={instrument}'
            logger.info(f"Fetching news from {url}")
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    logger.info("Got HTML response")
                    
                    # Extract news articles using BeautifulSoup
                    soup = BeautifulSoup(html, 'html.parser')
                    articles = []
                    
                    for article in soup.select('.news-feed article'):
                        title = article.select_one('.news-feed__title')
                        content = article.select_one('.news-feed__content')
                        if title and content:
                            articles.append({
                                'title': title.text.strip(),
                                'content': content.text.strip()
                            })
                    
                    logger.info(f"Found {len(articles)} articles")
                    return articles
                else:
                    raise Exception(f"Failed to get news: HTTP {response.status}")
                    
    except Exception as e:
        logger.error(f"Failed to get news: {str(e)}")
        logger.error(f"Error traceback: {traceback.format_exc()}")
        raise

@app.post("/trading-signal")
async def process_trading_signal(signal: TradingSignal):
    logger.info("Starting to process trading signal")
    try:
        news_data = await get_news_for_instrument(signal.instrument)
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
