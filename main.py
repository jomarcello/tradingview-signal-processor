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
                await page.goto(url, wait_until='load', timeout=30000)  # Reduced timeout, only wait for load
                logger.info("News page loaded")
                
                # Take screenshot for debugging
                logger.info("Taking screenshot")
                await page.screenshot(path='/tmp/debug.png')
                
                # Wait for news feed with retry
                logger.info("Waiting for news feed")
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await page.wait_for_selector('.title-HY0D0owe', timeout=10000)  # Reduced timeout
                        break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise
                        logger.warning(f"Retry {attempt + 1}/{max_retries} waiting for news feed")
                        await page.reload(wait_until='load', timeout=30000)  # Also reduced timeout here
                
                # Get first 3 news articles
                articles = []
                news_items = await page.query_selector_all('.title-HY0D0owe')
                logger.info(f"Found {len(news_items)} news items")
                
                for item in news_items[:3]:  # Only get first 3 articles
                    try:
                        # Get parent element that contains the link
                        parent = await item.evaluate('element => element.closest("a")')
                        if not parent:
                            logger.warning("Could not find parent link element")
                            continue
                            
                        # Get href attribute
                        href = await parent.get_attribute('href')
                        if not href:
                            logger.warning("Could not find href attribute")
                            continue
                            
                        # Get title
                        title = await item.get_attribute('data-overflow-tooltip-text')
                        if not title:
                            logger.warning("Could not find title")
                            continue
                            
                        logger.info(f"Opening article: {title}")
                        
                        # Open article in new page
                        article_page = await context.new_page()
                        try:
                            full_url = f"https://www.tradingview.com{href}"
                            await article_page.goto(full_url, wait_until='load', timeout=30000)
                            
                            # Wait for article content
                            await article_page.wait_for_selector('.body-bETdSLzM', timeout=10000)
                            
                            # Get full article content
                            content = await article_page.evaluate('() => document.querySelector(".body-bETdSLzM").innerText')
                            
                            logger.info(f"Found article content: {content[:100]}...")
                            articles.append({
                                'title': title.strip(),
                                'content': content.strip(),
                                'url': full_url
                            })
                        except Exception as e:
                            logger.warning(f"Error getting article content: {str(e)}")
                            articles.append({
                                'title': title.strip(),
                                'content': title.strip(),  # Fallback to title if we can't get content
                                'url': full_url
                            })
                        finally:
                            await article_page.close()
                            
                    except Exception as e:
                        logger.warning(f"Error processing news item: {str(e)}")
                        continue
                
                # Return all articles found
                if articles:
                    logger.info(f"Successfully found {len(articles)} articles")
                    return articles
                else:
                    raise Exception("No articles found")
        
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
                "news": news_data,  # Return all 3 articles
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
