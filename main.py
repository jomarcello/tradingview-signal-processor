import os
import json
import logging
import traceback
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright
import aiohttp
from python_socks.async_.asyncio import Proxy
import asyncio
from datetime import datetime
import pytz

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

async def login_to_tradingview_with_requests():
    """Login to TradingView using aiohttp"""
    logger.info("Starting login with requests")
    
    # Get proxy configuration
    proxy = await get_rotating_proxy()
    
    # Setup session with proxy if available
    session_kwargs = {
        'timeout': aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
    }
    if proxy:
        session_kwargs['proxy'] = proxy['server']
        session_kwargs['proxy_auth'] = aiohttp.BasicAuth(proxy['username'], proxy['password'])
    
    async with aiohttp.ClientSession(**session_kwargs) as session:
        try:
            # Headers for all requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Origin': 'https://www.tradingview.com',
                'Referer': 'https://www.tradingview.com/',
                'Content-Type': 'application/json',
            }
            
            # First try to get session token
            async with session.post(
                'https://www.tradingview.com/accounts/signin/',
                headers=headers,
                json={
                    "username": os.getenv("TRADINGVIEW_EMAIL"),
                    "password": os.getenv("TRADINGVIEW_PASSWORD"),
                    "remember": True
                },
                timeout=REQUEST_TIMEOUT
            ) as response:
                if response.status == 200:
                    logger.info("Login successful")
                    cookies = response.cookies
                    return {cookie.key: cookie.value for cookie in cookies.values()}
                else:
                    # Try alternative endpoint
                    logger.info("First login attempt failed, trying alternative endpoint")
                    async with session.post(
                        'https://www.tradingview.com/api/v1/auth/signin/',
                        headers=headers,
                        json={
                            "username": os.getenv("TRADINGVIEW_EMAIL"),
                            "password": os.getenv("TRADINGVIEW_PASSWORD"),
                            "remember": True
                        },
                        timeout=REQUEST_TIMEOUT
                    ) as alt_response:
                        if alt_response.status == 200:
                            logger.info("Login successful via alternative endpoint")
                            cookies = alt_response.cookies
                            return {cookie.key: cookie.value for cookie in cookies.values()}
                        else:
                            # Try third endpoint
                            logger.info("Second login attempt failed, trying third endpoint")
                            async with session.post(
                                'https://www.tradingview.com/api/v1/user/signin/',
                                headers=headers,
                                json={
                                    "username": os.getenv("TRADINGVIEW_EMAIL"),
                                    "password": os.getenv("TRADINGVIEW_PASSWORD"),
                                    "remember": True
                                },
                                timeout=REQUEST_TIMEOUT
                            ) as third_response:
                                if third_response.status == 200:
                                    logger.info("Login successful via third endpoint")
                                    cookies = third_response.cookies
                                    return {cookie.key: cookie.value for cookie in cookies.values()}
                                else:
                                    raise Exception(f"Login failed with status {third_response.status}")
                    
        except asyncio.TimeoutError:
            logger.error("Login request timed out")
            raise Exception("Login request timed out")
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise

async def scrape_news(page, symbol):
    """Scrape news for a given symbol with retry logic"""
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Scraping news attempt {attempt + 1}/{MAX_RETRIES}")
            
            # Go to the news page for the symbol
            url = f"https://www.tradingview.com/symbols/{symbol}/news/"
            logger.info(f"Navigating to {url}")
            
            await page.goto(url, timeout=REQUEST_TIMEOUT * 1000)
            await page.wait_for_load_state('networkidle', timeout=REQUEST_TIMEOUT * 1000)
            
            # Wait for news container with increased timeout
            await page.wait_for_selector('.card-HY0D0owe', timeout=REQUEST_TIMEOUT * 1000)
            
            # Get all news items
            news_items = await page.query_selector_all('.card-HY0D0owe')
            
            if not news_items:
                logger.warning("No news items found")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2)  # Wait before retry
                    continue
                return []
            
            # Get first news item
            first_news = news_items[0]
            
            # Get title
            title_el = await first_news.query_selector('[data-name="news-headline-title"]')
            title = await title_el.text_content() if title_el else "No title"
            
            # Get link and navigate to article
            href = await first_news.get_attribute('href')
            article_url = f"https://www.tradingview.com{href}"
            
            await page.goto(article_url, timeout=REQUEST_TIMEOUT * 1000)
            await page.wait_for_load_state('networkidle', timeout=REQUEST_TIMEOUT * 1000)
            
            # Wait for article content
            article = await page.wait_for_selector('article', timeout=REQUEST_TIMEOUT * 1000)
            content = await article.text_content()
            
            return [{
                "title": title.strip(),
                "content": content.strip(),
                "url": article_url
            }]
            
        except Exception as e:
            logger.error(f"Error scraping news (attempt {attempt + 1}): {str(e)}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2)  # Wait before retry
            else:
                raise

@app.post("/trading-signal")
async def process_trading_signal(signal: TradingSignal):
    logger.info("Starting to process trading signal")
    try:
        # First login with requests
        cookies = await login_to_tradingview_with_requests()
        logger.info("Got cookies from login")
        
        # Get proxy configuration
        proxy = await get_rotating_proxy()
        
        async with async_playwright() as p:
            logger.info("Launching browser")
            
            # Configure browser launch options
            browser_kwargs = {
                'headless': True,
                'args': [
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
                ]
            }
            
            # Add proxy if available
            if proxy:
                browser_kwargs['proxy'] = {
                    'server': proxy['server'],
                    'username': proxy['username'],
                    'password': proxy['password']
                }
            
            browser = await p.chromium.launch(**browser_kwargs)
            logger.info("Browser launched successfully")

            logger.info("Creating browser context")
            context = await browser.new_context(
                viewport={'width': 1024, 'height': 768},  # Reduced viewport size
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                bypass_csp=True  # Bypass Content Security Policy
            )
            
            # Add cookies from login
            for name, value in cookies.items():
                await context.add_cookies([{
                    'name': name,
                    'value': value,
                    'domain': '.tradingview.com',
                    'path': '/'
                }])
            
            page = await context.new_page()
            logger.info("Browser context created successfully")
            
            try:
                logger.info("Starting to scrape news")
                news_data = await scrape_news(page, signal.instrument)
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
            finally:
                logger.info("Closing browser")
                await browser.close()
                
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "message": f"Error in main process: {str(e)}",
            "data": None
        }
