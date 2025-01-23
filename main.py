from fastapi import FastAPI, HTTPException
from playwright.async_api import async_playwright
import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
import logging
import json
import os
from dotenv import load_dotenv
import time
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Get TradingView credentials from environment
TRADINGVIEW_EMAIL = os.getenv('TRADINGVIEW_EMAIL')
TRADINGVIEW_PASSWORD = os.getenv('TRADINGVIEW_PASSWORD')

if not TRADINGVIEW_EMAIL or not TRADINGVIEW_PASSWORD:
    raise ValueError("TradingView credentials not set in environment variables")

app = FastAPI()

def setup_logging():
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(__name__)

logger = setup_logging()

class TradingSignal(BaseModel):
    instrument: str
    timestamp: Optional[str]

async def login_to_tradingview(page):
    """Login to TradingView using environment credentials"""
    try:
        logger.info("Attempting to log in to TradingView")
        
        # First try the main page with header login
        logger.info("Going to main page")
        await page.goto('https://www.tradingview.com/', 
                       wait_until='networkidle',
                       timeout=10000)
        
        # Wait for the page to be fully loaded
        logger.info("Waiting for page to load")
        await page.wait_for_load_state('networkidle')
        await page.wait_for_load_state('domcontentloaded')
        
        # Take a screenshot for debugging
        logger.info("Taking screenshot of page")
        await page.screenshot(path='/tmp/tradingview_page.png', full_page=True)
        
        # Look for the user menu button
        logger.info("Looking for user menu button")
        user_menu = None
        retry_count = 0
        
        while retry_count < 3 and not user_menu:
            try:
                # Try to find the user menu button
                user_menu = await page.wait_for_selector(
                    'button.tv-header__user-menu-button--anonymous',
                    timeout=5000,
                    state='visible'
                )
                
                if user_menu:
                    logger.info("Found user menu button, clicking it")
                    await user_menu.click()
                    
                    # Wait for the menu to be visible
                    logger.info("Waiting for user menu to appear")
                    await page.wait_for_selector(
                        '[data-name="header-user-menu-popup"]',
                        timeout=5000,
                        state='visible'
                    )
                    
                    # Small delay to ensure menu is fully rendered
                    await page.wait_for_timeout(1000)
                    
                    # Wait for the email button and click it
                    logger.info("Looking for email button")
                    email_button = await page.wait_for_selector(
                        'button[name="Email"]',
                        timeout=5000,
                        state='visible'
                    )
                    
                    if email_button:
                        logger.info("Found email button, clicking it")
                        await email_button.click()
                        
                        # Now wait for the email input field
                        logger.info("Waiting for email input")
                        email_input = await page.wait_for_selector(
                            'input[name="username"]',
                            timeout=5000,
                            state='visible'
                        )
                        
                        if email_input:
                            logger.info("Found email input, filling credentials")
                            await email_input.fill(os.getenv('TRADINGVIEW_EMAIL'))
                            
                            # Find and fill password
                            password_input = await page.wait_for_selector(
                                'input[name="password"]',
                                timeout=5000,
                                state='visible'
                            )
                            await password_input.fill(os.getenv('TRADINGVIEW_PASSWORD'))
                            
                            # Click the sign in button
                            sign_in_button = await page.wait_for_selector(
                                'button[type="submit"]',
                                timeout=5000,
                                state='visible'
                            )
                            await sign_in_button.click()
                            
                            # Wait for navigation
                            logger.info("Waiting for login to complete")
                            await page.wait_for_load_state('networkidle')
                            break
            
            except Exception as e:
                retry_count += 1
                logger.warning(f"Retry {retry_count}: Error during login flow: {str(e)}")
                
                # Take a screenshot of the current state
                logger.info("Taking screenshot after failed attempt")
                await page.screenshot(path=f'/tmp/tradingview_login_attempt_{retry_count}.png', full_page=True)
                
                # Log the page content for debugging
                logger.info("Current page content:")
                logger.info(await page.content())
                
                # If we failed to find the email button, try to log the menu content
                if "Email" in str(e):
                    try:
                        menu_content = await page.evaluate('''() => {
                            const menu = document.querySelector('[data-name="header-user-menu-popup"]');
                            return menu ? menu.innerHTML : null;
                        }''')
                        if menu_content:
                            logger.info("Menu content:")
                            logger.info(menu_content)
                    except Exception as menu_error:
                        logger.warning(f"Could not get menu content: {str(menu_error)}")
                
                await page.wait_for_timeout(2000)
        
        if retry_count >= 3:
            raise Exception("Failed to complete login flow after 3 retries")
            
        logger.info("Login flow completed")
        
        # Wait for login to complete with retry
        logger.info("Waiting for login to complete")
        retry_count = 0
        while retry_count < 3:
            try:
                await page.wait_for_selector('.tv-header__user-menu-button', timeout=3000)
                logger.info("Successfully logged in to TradingView")
                return
            except Exception as e:
                retry_count += 1
                if retry_count == 3:
                    raise Exception("Login verification failed after retries")
                logger.warning(f"Retry {retry_count}: Waiting for login completion")
                await page.wait_for_timeout(1000)
        
    except Exception as e:
        logger.error(f"Failed to log in to TradingView: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to log in to TradingView: {str(e)}")

async def scrape_news(page, symbol):
    """Scrape news for a given symbol"""
    try:
        logger.info(f"Navigating to https://www.tradingview.com/symbols/{symbol}/news/")
        await page.goto(f'https://www.tradingview.com/symbols/{symbol}/news/',
                       wait_until='domcontentloaded',
                       timeout=10000)
        
        logger.info("Waiting for news container")
        
        # First check if we're on the right page
        current_url = page.url
        logger.info(f"Current URL: {current_url}")
        
        # Take a screenshot for debugging
        logger.info("Taking screenshot of news page")
        await page.screenshot(path='/tmp/tradingview_news.png', full_page=True)
        
        # Check if we need to click the sign in button on the news page
        try:
            logger.info("Checking for news page sign in button")
            sign_in_button = await page.wait_for_selector(
                'button[data-name="header-sign-in"]',
                timeout=5000,
                state='visible'
            )
            
            if sign_in_button:
                logger.info("Found news page sign in button, clicking it")
                await sign_in_button.click()
                
                # Wait for the login form
                logger.info("Waiting for login form")
                email_input = await page.wait_for_selector(
                    'input[name="username"]',
                    timeout=5000,
                    state='visible'
                )
                
                if email_input:
                    logger.info("Found email input, filling credentials")
                    await email_input.fill(os.getenv('TRADINGVIEW_EMAIL'))
                    
                    # Find and fill password
                    password_input = await page.wait_for_selector(
                        'input[name="password"]',
                        timeout=5000,
                        state='visible'
                    )
                    await password_input.fill(os.getenv('TRADINGVIEW_PASSWORD'))
                    
                    # Click the sign in button
                    submit_button = await page.wait_for_selector(
                        'button[type="submit"]',
                        timeout=5000,
                        state='visible'
                    )
                    await submit_button.click()
                    
                    # Wait for navigation and content to load
                    logger.info("Waiting for login to complete")
                    await page.wait_for_load_state('networkidle')
                    await page.wait_for_timeout(2000)  # Extra wait to ensure content loads
        except Exception as e:
            logger.warning(f"No news page sign in button found or error during sign in: {str(e)}")
        
        # Wait for any news content with retry
        news_items = None
        retry_count = 0
        
        while retry_count < 3 and not news_items:
            try:
                # Try different selectors based on actual HTML structure
                for selector in [
                    'a[href*="/news/"].card-HY0D0owe',  # New selector for news cards
                    '.container-DmjQR0Aa',
                    '.container-HY0D0owe',
                    '[data-name="news-headline-title"]',
                    '.title-DmjQR0Aa'
                ]:
                    try:
                        logger.info(f"Trying selector: {selector}")
                        # Wait for the element to be visible
                        await page.wait_for_selector(selector, timeout=5000, state='visible')
                        news_items = await page.query_selector_all(selector)
                        if news_items and len(news_items) > 0:
                            logger.info(f"Found {len(news_items)} news items with selector: {selector}")
                            
                            # Check if we have non-exclusive news
                            has_real_news = False
                            for item in news_items[:3]:  # Check first 3 items
                                title = await item.evaluate('(el) => el.querySelector("[data-name=news-headline-title]")?.textContent')
                                if title:
                                    logger.info(f"Checking title: {title}")
                                    if not "Sign in to read exclusive news" in title:
                                        has_real_news = True
                                        break
                            
                            if has_real_news:
                                break
                            else:
                                logger.warning("Only found exclusive news, continuing search")
                                news_items = None
                                
                    except Exception as e:
                        logger.warning(f"Failed to find news with selector {selector}: {str(e)}")
                        continue
                
                if news_items and len(news_items) > 0:
                    break
                    
                # If no news found, check page content
                logger.info("Checking page content")
                page_content = await page.content()
                logger.info(f"Page title: {await page.title()}")
                
                # Take another screenshot
                logger.info("Taking screenshot after attempt")
                await page.screenshot(path=f'/tmp/tradingview_news_attempt_{retry_count}.png', full_page=True)
                
                retry_count += 1
                logger.warning(f"Retry {retry_count}: Could not find news items")
                await page.wait_for_timeout(2000)
                
            except Exception as e:
                retry_count += 1
                logger.warning(f"Retry {retry_count}: Error finding news: {str(e)}")
                await page.wait_for_timeout(2000)
        
        if not news_items or len(news_items) == 0:
            raise Exception("Could not find any news items")
            
        # Process the news items
        news_data = []
        for item in news_items[:3]:  # Get latest 3 articles
            try:
                # Get the article data using the exact class names
                article_data = await page.evaluate('''(container) => {
                    const titleEl = container.querySelector('[data-name="news-headline-title"]');
                    const dateEl = container.querySelector('relative-time');
                    const providerEl = container.querySelector('.provider-TUPxzdRV');
                    const articleUrl = container.href || container.closest('a')?.href;
                    
                    const title = titleEl ? titleEl.textContent.trim() : null;
                    
                    // Skip exclusive news
                    if (title && title.includes("Sign in to read exclusive news")) {
                        return null;
                    }
                    
                    return {
                        title: title,
                        date: dateEl ? dateEl.getAttribute('event-time') : null,
                        provider: providerEl ? providerEl.textContent.trim() : null,
                        url: articleUrl,
                        html: container.outerHTML
                    };
                }''', item)
                
                if article_data and article_data['title'] and article_data['url']:
                    # Navigate to the full article
                    logger.info(f"Navigating to article: {article_data['url']}")
                    await page.goto(article_data['url'], wait_until='domcontentloaded')
                    
                    # Log the page content for debugging
                    logger.info("Article page content:")
                    logger.info(await page.content())
                    
                    # Take a screenshot of the article page
                    logger.info("Taking screenshot of article page")
                    await page.screenshot(path='/tmp/tradingview_article.png', full_page=True)
                    
                    # Wait for article content with different selectors
                    article_content = None
                    for selector in [
                        'article',
                        '.content-HY0D0owe',
                        '.content-DmjQR0Aa',
                        '.article-content',
                        '[data-name="news-text"]',
                        '.news-text'
                    ]:
                        try:
                            logger.info(f"Trying article selector: {selector}")
                            article_content = await page.wait_for_selector(selector, timeout=5000)
                            if article_content:
                                logger.info(f"Found article content with selector: {selector}")
                                break
                        except Exception as e:
                            logger.warning(f"Failed to find article content with selector {selector}: {str(e)}")
                    
                    if article_content:
                        article_data['html'] = await article_content.evaluate('el => el.outerHTML')
                        logger.info("Successfully retrieved full article content")
                    else:
                        logger.warning("Could not find article content, using page content")
                        article_data['html'] = await page.evaluate('() => document.body.innerHTML')
                    
                    news_data.append(article_data)
                    logger.info(f"Found article: {article_data['title']}")
                    
                    # Go back to the news list
                    await page.goto(f'https://www.tradingview.com/symbols/{symbol}/news/',
                                  wait_until='domcontentloaded')
            except Exception as e:
                logger.warning(f"Error processing news item: {str(e)}")
                continue
        
        if not news_data:
            raise Exception("Could not find any valid news articles")
            
        return news_data
            
    except Exception as e:
        logger.error(f"Error during news scraping: {str(e)}")
        raise

async def get_news(pair: str) -> Dict:
    logger.info(f"Starting news scraping for {pair}")
    special_symbols = {
        'XAUUSD': 'GOLD'
    }
    
    symbol = special_symbols.get(pair, pair)
    logger.info(f"Using symbol: {symbol}")
    
    async with async_playwright() as p:
        logger.info("Launching browser")
        browser = await p.chromium.launch(headless=True)
        try:
            logger.info("Creating new page")
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            # First login to TradingView
            await login_to_tradingview(page)
            
            # Now scrape news
            news_data = await scrape_news(page, symbol)
            
            logger.info("Successfully scraped news")
            return {
                "title": news_data[0]['title'],
                "content": news_data[0]['html'],
                "url": f"https://www.tradingview.com/symbols/{symbol}/news/"
            }
        except Exception as e:
            logger.error(f"Error scraping news: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            logger.info("Closing browser")
            await browser.close()

async def analyze_sentiment(content: str) -> Dict:
    # Simple sentiment analysis based on keywords
    bullish_words = ['bullish', 'surge', 'gain', 'rise', 'higher', 'positive']
    bearish_words = ['bearish', 'drop', 'fall', 'lower', 'negative', 'decline']
    
    content_lower = content.lower()
    bullish_count = sum(1 for word in bullish_words if word in content_lower)
    bearish_count = sum(1 for word in bearish_words if word in content_lower)
    
    total = bullish_count + bearish_count
    if total == 0:
        score = 0.5
        label = "neutral"
    else:
        score = bullish_count / total
        if score > 0.6:
            label = "bullish"
        elif score < 0.4:
            label = "bearish"
        else:
            label = "neutral"
    
    return {
        "score": score,
        "label": label,
        "bullish_words": bullish_count,
        "bearish_words": bearish_count
    }

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "TradingView Signal Processor API",
        "endpoints": {
            "POST /trading-signal": "Process trading signals and news",
            "GET /health": "Health check"
        }
    }

@app.post("/trading-signal")
async def process_trading_signal(signal: TradingSignal):
    try:
        logger.info(f"Received trading signal: {json.dumps(signal.dict(), indent=2)}")
        
        # Initialize Playwright
        logger.info("Starting news scraping for EURUSD")
        logger.info(f"Using symbol: {signal.instrument}")
        async with async_playwright() as p:
            # Launch browser with optimized settings
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-gpu',
                    '--disable-dev-shm-usage',
                    '--disable-setuid-sandbox',
                    '--no-sandbox',
                    '--disable-extensions',
                    '--disable-notifications',
                    '--disable-geolocation'
                ]
            )
            
            # Create a new context with specific settings
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                java_script_enabled=True,
                bypass_csp=True,
                ignore_https_errors=True
            )

            # Add route to block unnecessary resources
            await context.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,otf,eot}", lambda route: route.abort())
            await context.route("**/{analytics,tracking,advertisement}**", lambda route: route.abort())
            
            # Create new page
            logger.info("Creating new page")
            page = await context.new_page()
            
            try:
                # Login to TradingView
                await login_to_tradingview(page)
                
                # Now scrape news
                news_data = await scrape_news(page, signal.instrument)
                
                # Analyze sentiment
                sentiment = await analyze_sentiment(news_data[0]['html'])
                
                # Combine all data
                combined_data = {
                    "signal": signal.dict(),
                    "news": {
                        "title": news_data[0]['title'],
                        "content": news_data[0]['html'],
                        "url": f"https://www.tradingview.com/symbols/{signal.instrument}/news/"
                    },
                    "sentiment": sentiment,
                    "timestamp": signal.timestamp
                }
                
                return {
                    "status": "success",
                    "message": "Signal processed successfully",
                    "data": combined_data
                }
            except Exception as e:
                logger.error(f"Error during processing: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
            finally:
                await browser.close()
    except Exception as e:
        logger.error(f"Error processing signal: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
