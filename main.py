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
                scroll_attempts = 5
                last_count = 0
                for i in range(scroll_attempts):
                    logger.info(f"Scroll attempt {i+1}/{scroll_attempts}")
                    
                    # Get current height
                    current_height = await page.evaluate('document.body.scrollHeight')
                    logger.info(f"Current height: {current_height}")
                    
                    # Scroll to bottom
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(2)  # Wait longer for content to load
                    
                    # Get new height
                    new_height = await page.evaluate('document.body.scrollHeight')
                    logger.info(f"New height after scroll: {new_height}")
                    
                    # Get current number of articles
                    current_items = await page.query_selector_all('.title-HY0D0owe')
                    logger.info(f"Found {len(current_items)} articles after scroll {i+1}")
                    
                    # Check if we're still loading new content
                    if len(current_items) == last_count and current_height == new_height:
                        logger.info("No new content loaded, stopping scroll")
                        break
                    
                    last_count = len(current_items)
                    
                    # Check if we've loaded enough
                    if len(current_items) >= 50:
                        logger.info("Found enough articles, stopping scroll")
                        break
                    
                    # Wait for new content to load
                    await asyncio.sleep(1)
                
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
                wanted_providers = {
                    'forexlive',
                    'trading economics',
                    'dow jones newswires',
                    'reuters'
                }
                logger.info(f"Looking for 3 most recent articles from any of these providers: {wanted_providers}")
                
                for item in news_items:
                    # Stop if we already have 3 articles
                    if len(found_items) >= 3:
                        logger.info("Found 3 articles, stopping search")
                        break
                        
                    try:
                        # Get the href and provider from the parent link
                        parent_info = await item.evaluate('''element => {
                            const parent = element.closest("a");
                            if (!parent) return null;
                            
                            // Try different provider selectors
                            const article = element.closest('article');
                            if (!article) return null;
                            
                            // Try different provider selectors
                            const providerSelectors = [
                                '.provider-HY0D0owe span',
                                '.provider-TUPxzdRV span',
                                '.provider span',
                                '[class*="provider-"] span'
                            ];
                            
                            let providerElement = null;
                            for (const selector of providerSelectors) {
                                providerElement = article.querySelector(selector);
                                if (providerElement) break;
                            }
                            
                            const provider = providerElement ? providerElement.textContent.toLowerCase().trim() : '';
                            
                            return {
                                href: parent.getAttribute("href"),
                                provider: provider,
                                html: parent.outerHTML
                            };
                        }''')
                        
                        if not parent_info or 'provider' not in parent_info or not parent_info['provider']:
                            logger.warning("Could not find provider info in article")
                            continue
                            
                        provider = parent_info['provider'].lower()
                        logger.info(f"Found article from provider: {provider}")
                        
                        # Check if this is one of the providers we want
                        if provider in wanted_providers:
                            title = await item.get_attribute('data-overflow-tooltip-text')
                            if title:  # Only add articles with a valid title
                                logger.info(f"Found article from wanted provider {provider}: {title}")
                                found_items.append((title, item))
                        else:
                            logger.info(f"Skipping article from unwanted provider: {provider}")
                    except Exception as e:
                        logger.warning(f"Error checking article provider: {str(e)}")
                        continue
                
                logger.info(f"Found {len(found_items)} articles in total")
                
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

N8N_WEBHOOK_URL = "YOUR_N8N_WEBHOOK_URL_HERE"  # Dit moet je aanpassen naar je eigen n8n webhook URL

@app.post("/trading-signal")
async def process_trading_signal(signal: TradingSignal) -> dict:
    """Process a trading signal and return relevant news."""
    try:
        logger.info(f"Processing signal for {signal.instrument}")
        
        # Extract relevant signal data
        instrument = signal.instrument
        action = signal.action
        price = signal.price
        timestamp = signal.timestamp
        strategy = signal.strategy
        timeframe = signal.timeframe
        
        # Get news articles
        news_data = await get_news_with_playwright(instrument)
        
        # Prepare data for n8n
        webhook_data = {
            "signal": {
                "instrument": instrument,
                "action": action,
                "price": price,
                "timestamp": timestamp,
                "strategy": strategy,
                "timeframe": timeframe
            },
            "news": news_data,
            "timestamp": timestamp
        }
        
        # Send to n8n webhook
        try:
            response = requests.post(N8N_WEBHOOK_URL, json=webhook_data)
            response.raise_for_status()  # Raise an exception for bad status codes
            logger.info(f"Successfully sent data to n8n webhook. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send data to n8n webhook: {str(e)}")
            # We still return success to the client, but log the webhook error
        
        return {
            "status": "success",
            "message": "Signal processed successfully",
            "data": webhook_data
        }
        
    except Exception as e:
        logger.error(f"Error processing signal: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error traceback: {traceback.format_exc()}")
        
        return {
            "status": "error",
            "message": f"Error processing signal: {str(e)}",
            "data": None
        }
