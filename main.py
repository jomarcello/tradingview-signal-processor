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
        async with async_playwright() as p:
            # Install browsers first
            logger.info("Installing browsers")
            import subprocess
            subprocess.run(['playwright', 'install', 'chromium'])
            
            # Launch browser with more conservative options
            logger.info("Launching browser")
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            
            # Create context with minimal options
            logger.info("Creating context")
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            try:
                page = await context.new_page()
                logger.info("Created new page")
                
                # First go to main page
                logger.info("Going to main page")
                await page.goto('https://www.tradingview.com/', wait_until='networkidle', timeout=120000)
                await page.wait_for_load_state('domcontentloaded', timeout=120000)
                await page.wait_for_load_state('load', timeout=120000)
                logger.info("Main page loaded")
                
                # Take screenshot for debugging
                logger.info("Taking screenshot")
                await page.screenshot(path='/tmp/debug.png')
                
                # Get page content for debugging
                content = await page.content()
                logger.info(f"Page content length: {len(content)}")
                logger.info(f"First 500 chars: {content[:500]}")
                
                # Wait for page to be fully loaded
                await page.wait_for_timeout(5000)
                
                # Click user icon to open login modal
                logger.info("Looking for user menu button")
                await page.wait_for_selector('button[aria-label="Open user menu"]', timeout=60000)
                await page.click('button[aria-label="Open user menu"]', timeout=60000)
                logger.info("Clicked user menu button")
                
                # Wait a bit for the menu to open
                await page.wait_for_timeout(2000)
                
                # Click "Sign in" button
                logger.info("Looking for sign in button")
                await page.wait_for_selector('button[data-overflow-tooltip-text="Sign in"]', timeout=60000)
                await page.click('button[data-overflow-tooltip-text="Sign in"]', timeout=60000)
                logger.info("Clicked sign in button")
                
                # Wait a bit for the dialog to open
                await page.wait_for_timeout(2000)
                
                # Click email button
                logger.info("Looking for email button")
                await page.wait_for_selector('button[name="Email"]', timeout=60000)
                await page.click('button[name="Email"]', timeout=60000)
                logger.info("Clicked email button")
                
                # Wait a bit for the form to load
                await page.wait_for_timeout(2000)
                
                # Fill in credentials
                logger.info("Looking for username field")
                await page.wait_for_selector('#id_username', timeout=60000)
                await page.fill('#id_username', os.getenv("TRADINGVIEW_EMAIL"), timeout=60000)
                logger.info("Filled username")
                
                logger.info("Looking for password field")
                await page.wait_for_selector('#id_password', timeout=60000)
                await page.fill('#id_password', os.getenv("TRADINGVIEW_PASSWORD"), timeout=60000)
                logger.info("Filled password")
                
                # Submit form
                logger.info("Looking for submit button")
                await page.wait_for_selector('button[type="submit"]', timeout=60000)
                await page.click('button[type="submit"]', timeout=60000)
                logger.info("Clicked submit button")
                
                await page.wait_for_load_state('load', timeout=120000)
                
                # Go to news page
                logger.info("Going to news page")
                url = f'https://www.tradingview.com/news/?symbol={instrument}'
                response = await page.goto(url, wait_until='load', timeout=120000)
                logger.info(f"News page status: {response.status if response else 'No response'}")
                
                # Wait for news feed with retry
                logger.info("Waiting for news feed")
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await page.wait_for_selector('.news-feed article', timeout=60000)
                        break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise
                        logger.warning(f"Retry {attempt + 1}/{max_retries} waiting for news feed")
                        await page.reload()
                
                # Get first 3 news articles
                articles = []
                news_items = await page.query_selector_all('.news-feed article')
                logger.info(f"Found {len(news_items)} news items")
                
                for item in news_items[:3]:  # Only get first 3 articles
                    title_el = await item.query_selector('.news-feed__title')
                    content_el = await item.query_selector('.news-feed__content')
                    
                    if title_el and content_el:
                        title = await title_el.text_content()
                        content = await content_el.text_content()
                        articles.append({
                            'title': title.strip(),
                            'content': content.strip()
                        })
                
                logger.info(f"Processed {len(articles)} articles")
                return articles
                
            finally:
                logger.info("Cleaning up browser resources")
                await context.close()
                await browser.close()
        
    except Exception as e:
        logger.error(f"Failed to get news: {str(e)}")
        logger.error(f"Error traceback: {traceback.format_exc()}")
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
