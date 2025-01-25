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
REQUEST_TIMEOUT = 60  # seconds
PROXY_URL = os.getenv("PROXY_URL", "http://proxy.apify.com:8000")
PROXY_USERNAME = os.getenv("PROXY_USERNAME")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")

# Services URLs
SIGNAL_AI_SERVICE_URL = "https://tradingview-signal-ai-service-production.up.railway.app/format-signal"
SUPABASE_URL = 'https://utigkgjcyqnrhpndzqhs.supabase.co/rest/v1/subscribers'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV0aWdrZ2pjeXFucmhwbmR6cWhzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjMyMzA1NiwiZXhwIjoyMDUxODk5MDU2fQ.8JovzmGQofC4oC2016P7aa6FZQESF3UNSjUTruIYWbg'

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
                await page.goto(url)
                logger.info(f"Navigated to URL: {url}")
                
                # Wait for response
                response = await page.wait_for_load_state("networkidle")
                logger.info(f"Response status: {response}")
                
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
                    
                    # Get parent link
                    parent = await article.evaluate('(element) => { const parent = element.closest("a"); return parent ? { href: parent.getAttribute("href"), html: parent.outerHTML } : null; }')
                    if not parent or not parent.get('href'):
                        continue
                        
                    logger.info(f"Starting to process article: {title}")
                    logger.info(f"Parent info: {parent}")
                    
                    # Navigate to article page
                    article_url = f"https://www.tradingview.com{parent['href']}"
                    logger.info(f"Navigating to: {article_url}")
                    
                    article_page = await browser.new_page()
                    try:
                        await article_page.goto(article_url)
                        logger.info("Waiting for article content")
                        
                        # Try different selectors for content
                        content = None
                        selectors = ['.body-KX2tCBZq', '.article-content']
                        
                        for selector in selectors:
                            logger.info(f"Trying selector: {selector}")
                            content_element = await article_page.wait_for_selector(selector, timeout=5000)
                            if content_element:
                                content = await content_element.text_content()
                                logger.info(f"Found content with selector {selector}: {content[:100]}...")
                                break
                        
                        if content:
                            logger.info(f"Found article content: {content[:100]}...")
                            articles.append({
                                'title': title,
                                'content': content
                            })
                            articles_found += 1
                        
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
        # Return empty list instead of raising
        return []

async def get_subscribers(instrument: str, timeframe: str) -> List[dict]:
    """Haal subscribers op uit Supabase die matchen met het instrument en timeframe."""
    async with httpx.AsyncClient() as client:
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

@app.post("/trading-signal")
async def process_trading_signal(signal: TradingSignal) -> dict:
    """Process a trading signal and return relevant news."""
    try:
        logger.info(f"Processing signal for {signal.instrument}")
        
        # Get matching subscribers from Supabase
        subscribers = await get_subscribers(signal.instrument, signal.timeframe)
        logger.info(f"Found {len(subscribers)} matching subscribers")
        
        # Extract just the chat_ids
        chat_ids = [sub["chat_id"] for sub in subscribers]
        
        # Get news articles
        news_data = await get_news_with_playwright(signal.instrument)
        
        # Prepare data for Signal AI Service
        signal_data = {
            "instrument": signal.instrument,
            "direction": signal.action,
            "entry_price": signal.price,
            "stop_loss": signal.stoploss,
            "take_profit": signal.takeprofit,
            "timeframe": signal.timeframe,
            "strategy": signal.strategy
        }
        
        # Send to Signal AI Service
        try:
            logger.info(f"Sending data to Signal AI Service")
            async with httpx.AsyncClient() as client:
                response = await client.post(SIGNAL_AI_SERVICE_URL, json=signal_data)
                logger.info(f"Signal AI Service response status: {response.status_code}")
                logger.info(f"Signal AI Service response content: {response.text}")
                response.raise_for_status()
                
                # Get formatted message
                formatted_message = response.json()["formatted_message"]
                
                # Send to each subscriber
                for chat_id in chat_ids:
                    # Now send to Telegram Service
                    telegram_data = {
                        "chat_id": chat_id,  # Changed from chat_ids to chat_id
                        "signal_data": signal_data,  # Send original signal data
                        "news_data": {
                            "instrument": signal.instrument,
                            "articles": news_data
                        }
                    }
                    
                    # Send to Telegram Service
                    telegram_response = await client.post(
                        "https://tradingview-telegram-service-production.up.railway.app/send-signal",
                        json=telegram_data
                    )
                    telegram_response.raise_for_status()
                    logger.info(f"Signal sent to chat_id: {chat_id}")
                
            logger.info(f"Successfully processed signal")
            
            return {
                "status": "success",
                "message": "Signal processed successfully",
                "data": {
                    "signal": signal_data,
                    "formatted_message": formatted_message,
                    "chat_ids": chat_ids,
                    "news": news_data
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to process signal: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to process signal: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error processing signal: {str(e)}")
        logger.error(f"Error traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to process signal: {str(e)}")
