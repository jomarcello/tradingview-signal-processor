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
            # Launch browser with debugging options
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            logger.info("Browser launched successfully with debugging options")
            
            try:
                # Create a new page with viewport
                page = await browser.new_page(
                    viewport={'width': 1920, 'height': 1080}
                )
                
                # Set extra HTTP headers
                await page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.9'
                })
                
                # Navigate to TradingView news page for the instrument
                url = f"https://www.tradingview.com/symbols/{instrument}/news/"
                response = await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                logger.info(f"Navigated to URL: {url}")
                logger.info(f"Response status: {response.status}")
                
                # Wait for initial load
                await page.wait_for_timeout(2000)
                
                # Scroll multiple times to load more articles
                scroll_attempts = 5  # Increase number of scroll attempts
                for i in range(scroll_attempts):
                    logger.info(f"Scroll attempt {i+1}/{scroll_attempts}")
                    
                    # Scroll to bottom
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(1)  # Wait for content to load
                    
                    # Get current number of articles
                    current_items = await page.query_selector_all('.title-HY0D0owe')
                    logger.info(f"Found {len(current_items)} articles after scroll {i+1}")
                    
                    # Check if we've loaded enough
                    if len(current_items) >= 50:  # Increase target number
                        logger.info("Found enough articles, stopping scroll")
                        break
                
                await page.screenshot(path="/tmp/tradingview.png")
                logger.info("Screenshot saved")
                
                # Get news items after scrolling
                news_items = await page.query_selector_all('.title-HY0D0owe')
                if not news_items:
                    logger.warning("No news items found with primary selector, trying alternatives...")
                    news_items = await page.query_selector_all('[data-name="news-headline-title"]')
                
                logger.info(f"Found {len(news_items)} news items")
                
                # Log all titles we find
                all_titles = []
                for item in news_items:
                    title = await item.get_attribute('data-overflow-tooltip-text')
                    all_titles.append(title)
                logger.info(f"All titles found on page: {all_titles}")
                
                # First find all the wanted articles
                found_items = []
                wanted_titles = [
                    "EURUSD Technical Analysis – Easing in tariffs risk weakens the USD",
                    "Euro Appreciates, ECB Awaited",
                    "Euro Extends Gains After Eurozone PMI Data — Market Talk"
                ]
                logger.info(f"Looking for these specific titles: {wanted_titles}")
                
                for item in news_items:
                    title = await item.get_attribute('data-overflow-tooltip-text')
                    if title in wanted_titles:
                        found_items.append((title, item))
                        logger.info(f"Found wanted article: {title}")
                    else:
                        logger.info(f"Skipping unwanted article: {title}")
                
                # Sort found items according to wanted_titles order
                found_items.sort(key=lambda x: wanted_titles.index(x[0]))
                logger.info(f"Found {len(found_items)} wanted articles in correct order: {[title for title, _ in found_items]}")
                
                # Create a page for articles
                article_page = await browser.new_page()
                try:
                    # Process found items in order
                    articles = []
                    for title, item in found_items:
                        try:
                            logger.info(f"Starting to process article: {title}")
                            
                            # Find the parent <a> tag and get its properties
                            parent_info = await item.evaluate('''element => {
                                const parent = element.closest("a");
                                if (!parent) return null;
                                return {
                                    href: parent.getAttribute("href"),
                                    html: parent.outerHTML
                                };
                            }''')
                            logger.info(f"Parent info: {parent_info}")
                            
                            if not parent_info or 'href' not in parent_info:
                                logger.warning("Could not find href")
                                continue
                                
                            href = parent_info['href']
                            if not href:
                                logger.warning("Empty href")
                                continue
                                
                            # Skip Mace News articles
                            if 'macenews:' in href:
                                logger.info(f"Skipping Mace News article: {title}")
                                continue
                                
                            # Navigate to article
                            article_url = f"https://www.tradingview.com{href}"
                            logger.info(f"Navigating to: {article_url}")
                            
                            await article_page.goto(article_url, wait_until='domcontentloaded')
                            logger.info("Waiting for article content")
                            
                            # Try different selectors for the article content
                            content = None
                            selectors = [
                                '.body-KX2tCBZq',
                                '.body-pIO_GYwT',
                                '.content-pIO_GYwT'
                            ]
                            
                            for selector in selectors:
                                try:
                                    logger.info(f"Trying selector: {selector}")
                                    element = await article_page.query_selector(selector)
                                    if element:
                                        text = await element.text_content()
                                        logger.info(f"Found content with selector {selector}: {text[:100]}...")
                                        if text and len(text.strip()) > 0:
                                            content = text
                                            break
                                except Exception as e:
                                    logger.warning(f"Error with selector {selector}: {str(e)}")
                            
                            if content:
                                logger.info(f"Found article content: {content[:100]}...")
                                articles.append({
                                    'title': title,
                                    'content': content
                                })
                            
                        except Exception as e:
                            logger.warning(f"Error processing article: {str(e)}")
                            continue
                            
                finally:
                    await article_page.close()
                
                if not articles:
                    raise Exception("No articles with content found")
                
                return articles
        
            finally:
                logger.info("Cleaning up browser resources")
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
