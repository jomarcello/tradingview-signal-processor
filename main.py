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
            
            # Launch browser with custom user agent
            browser = await p.chromium.launch(
                headless=True
            )
            
            # Create context with user agent
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            logger.info("Creating context")
            page = await context.new_page()
            logger.info("Created new page")
            
            try:
                # Go directly to news page
                logger.info("Going to news page")
                url = f'https://www.tradingview.com/symbols/{instrument}/news/'
                await page.goto(url, wait_until='load', timeout=60000)  # Increased timeout
                
                # Wait a bit and scroll
                logger.info("Waiting for page to settle")
                await page.wait_for_timeout(5000)  # Wait 5 seconds
                
                # Scroll down to load dynamic content
                logger.info("Scrolling page")
                await page.evaluate('window.scrollBy(0, 500)')
                await page.wait_for_timeout(2000)  # Wait after scroll
                
                # Take screenshot for debugging
                logger.info("Taking screenshot")
                await page.screenshot(path='/tmp/debug.png', full_page=True)
                
                # Get page content for debugging
                logger.info("Getting page content")
                page_content = await page.content()
                logger.info(f"Page content: {page_content[:1000]}...")
                
                # Wait for news feed with retry
                logger.info("Waiting for news feed")
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # Try different selectors
                        selectors = [
                            '.title-HY0D0owe',
                            '[data-name="news-headline-title"]',
                            '.title-DmjQR0Aa',
                            'a[href*="/news/"]'  # Any link containing /news/
                        ]
                        
                        for selector in selectors:
                            try:
                                logger.info(f"Trying selector: {selector}")
                                await page.wait_for_selector(selector, timeout=10000)
                                logger.info(f"Found selector: {selector}")
                                break
                            except Exception:
                                continue
                        break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise
                        logger.warning(f"Retry {attempt + 1}/{max_retries} waiting for news feed")
                        await page.reload(wait_until='load', timeout=60000)
                        await page.wait_for_timeout(5000)
                        await page.evaluate('window.scrollBy(0, 500)')
                        await page.wait_for_timeout(2000)
                
                # Get news articles with content
                articles = []
                news_items = await page.query_selector_all('.title-HY0D0owe')
                logger.info(f"Found {len(news_items)} news items")
                
                # Keep track of which items we've processed
                processed = 0
                
                while len(articles) < 3 and processed < len(news_items):
                    try:
                        item = news_items[processed]
                        processed += 1
                        
                        # Get title and parent link
                        title = await item.get_attribute('data-overflow-tooltip-text')
                        parent = await item.evaluate('element => element.closest("a")')
                        href = await parent.get_attribute('href')
                        
                        if not title or not href:
                            logger.warning("Could not find title or href")
                            continue
                            
                        # Skip Mace News articles
                        if 'macenews:' in href:
                            logger.info(f"Skipping Mace News article: {title}")
                            continue
                            
                        logger.info(f"Opening article: {title}")
                        
                        # Navigate to article
                        full_url = f"https://www.tradingview.com{href}"
                        logger.info(f"Navigating to: {full_url}")
                        await page.goto(full_url, wait_until='load', timeout=30000)
                        
                        try:
                            # Wait for article content to load
                            logger.info("Waiting for article content")
                            
                            # Try different selectors for the content
                            content = None
                            selectors = [
                                '.body-KX2tCBZq',  # New main selector
                                '.body-pIO_GYwT',  # Alternative class
                                '.content-pIO_GYwT',  # Alternative class
                                'div[class*="body-"] p'  # Fallback: any div with class containing "body-" and its paragraphs
                            ]
                            
                            for selector in selectors:
                                try:
                                    await page.wait_for_selector(selector, timeout=5000)
                                    content = await page.evaluate(f'() => document.querySelector("{selector}").innerText')
                                    if content and len(content.strip()) > 0:
                                        break
                                except Exception:
                                    continue
                            
                            if content and len(content.strip()) > 0:
                                logger.info(f"Found article content: {content[:100]}...")
                                articles.append({
                                    'title': title.strip(),
                                    'content': content.strip()
                                })
                            else:
                                logger.info("Article has no content, skipping")
                        except Exception as e:
                            logger.warning(f"Could not get content, skipping: {str(e)}")
                            continue
                        
                        # Go back to news page
                        news_url = f'https://www.tradingview.com/symbols/{instrument}/news/'
                        logger.info(f"Going back to: {news_url}")
                        await page.goto(news_url, wait_until='load', timeout=30000)
                        await page.wait_for_selector('.title-HY0D0owe', timeout=10000)
                            
                    except Exception as e:
                        logger.warning(f"Error processing news item: {str(e)}")
                        continue
                
                if not articles:
                    raise Exception("No articles with content found")
                
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
async def process_trading_signal(signal: TradingSignal) -> dict:
    """Process a trading signal and return relevant news."""
    try:
        logger.info(f"Processing signal for {signal.instrument}")
        
        # Get news for the instrument
        news_data = await get_news_with_playwright(signal.instrument)
        
        # Return all news articles
        return {
            "status": "success",
            "message": "Signal processed successfully",
            "data": {
                "signal": {
                    "instrument": signal.instrument,
                    "timestamp": signal.timestamp
                },
                "news": news_data,  # Return all articles
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
