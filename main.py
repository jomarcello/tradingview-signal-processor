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

async def login_to_tradingview(page):
    """Login to TradingView using environment credentials"""
    try:
        logger.info("Attempting to log in to TradingView")
        
        # Set extra headers
        await page.set_extra_http_headers({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Go directly to the email sign in page
        logger.info("Going to email sign in page")
        await page.goto('https://www.tradingview.com/accounts/signin/', wait_until='networkidle')
        
        # Wait for the page to load and stabilize
        logger.info("Waiting for page to stabilize")
        await page.wait_for_load_state('domcontentloaded')
        await page.wait_for_load_state('networkidle')
        
        # Wait for CSS bundles to load in parallel with a short timeout
        css_bundles = [
            'https://static.tradingview.com/static/bundles/44524.822aea2118d5fb32382f.css',
            'https://static.tradingview.com/static/bundles/62093.5d0098bab0d2d4ea02e5.css',
            'https://static.tradingview.com/static/bundles/4752.aac2f2a838ddc6c166c7.css'
        ]
        
        async def wait_for_css(css):
            try:
                await page.wait_for_selector(f'link[href="{css}"]', timeout=3000)
                logger.info(f"CSS bundle loaded: {css}")
                return True
            except Exception as e:
                logger.warning(f"Failed to wait for CSS bundle {css}: {str(e)}")
                return False
        
        # Wait for all CSS bundles in parallel
        css_results = await asyncio.gather(*[wait_for_css(css) for css in css_bundles], return_exceptions=True)
        loaded_css = sum(1 for r in css_results if r is True)
        logger.info(f"Loaded {loaded_css} out of {len(css_bundles)} CSS bundles")
        
        # Extra wait for JavaScript initialization (shorter)
        await page.wait_for_timeout(3000)
        
        # Take screenshot before any frame switching
        await page.screenshot(path="/tmp/signin-page.png")
        
        # Log the current URL and content
        current_url = page.url
        content = await page.content()
        logger.info(f"Current URL: {current_url}")
        logger.info(f"Page content: {content[:1000]}...")
        
        # Check for and switch to login iframe if present
        iframes = page.frames
        logger.info(f"Found {len(iframes)} frames")
        main_frame = page
        
        for frame in iframes:
            logger.info(f"Frame URL: {frame.url}")
            if 'signin' in frame.url.lower():
                logger.info(f"Found signin frame: {frame.url}")
                main_frame = frame
                break
        
        # Try different selectors for email/password fields
        selectors = [
            ('input[name="username"]', 'input[name="password"]'),
            ('input[type="email"]', 'input[type="password"]'),
            ('#email-signin__user-name-input', '#email-signin__password-input'),
            ('form input[type="text"]', 'form input[type="password"]'),
            ('[name="username"]', '[name="password"]'),
            ('.tv-control-material-textbox__input', '.tv-control-material-textbox__input[type="password"]')
        ]
        
        logged_in = False
        for email_selector, password_selector in selectors:
            try:
                logger.info(f"Trying selectors: {email_selector}, {password_selector}")
                
                # First check if elements exist using proper JavaScript syntax
                email_exists = await main_frame.evaluate(f'''() => !!document.querySelector('{email_selector.replace("'", "\\'")}')''')
                password_exists = await main_frame.evaluate(f'''() => !!document.querySelector('{password_selector.replace("'", "\\'")}')''')
                
                if not email_exists or not password_exists:
                    logger.warning(f"Elements not found in DOM: email={email_exists}, password={password_exists}")
                    continue
                
                # Wait for and fill in email field
                email_elem = await main_frame.wait_for_selector(email_selector, timeout=3000, state='visible')
                if not email_elem:
                    logger.warning(f"Email field {email_selector} not visible")
                    continue
                    
                await email_elem.fill(TRADINGVIEW_EMAIL)
                logger.info("Filled email field")
                
                # Wait for and fill in password field
                password_elem = await main_frame.wait_for_selector(password_selector, timeout=3000, state='visible')
                if not password_elem:
                    logger.warning(f"Password field {password_selector} not visible")
                    continue
                    
                await password_elem.fill(TRADINGVIEW_PASSWORD)
                logger.info("Filled password field")
                
                # Find and click sign in button
                submit_buttons = [
                    'button[type="submit"]',
                    'button:has-text("Sign in")',
                    '[data-name="submit"]',
                    'button.tv-button__loader',
                    '.tv-button--primary',
                    '.tv-button'
                ]
                
                for submit_selector in submit_buttons:
                    try:
                        logger.info(f"Trying to click submit button: {submit_selector}")
                        # First check if button exists using proper JavaScript syntax
                        button_exists = await main_frame.evaluate(f'''() => !!document.querySelector('{submit_selector.replace("'", "\\'")}')''')
                        if not button_exists:
                            logger.warning(f"Submit button {submit_selector} not found in DOM")
                            continue
                            
                        submit_elem = await main_frame.wait_for_selector(submit_selector, timeout=3000, state='visible')
                        if submit_elem:
                            # Take screenshot before clicking
                            await page.screenshot(path="/tmp/before-submit.png")
                            await submit_elem.click()
                            logger.info("Clicked submit button")
                            break
                    except Exception as e:
                        logger.warning(f"Failed to click {submit_selector}: {str(e)}")
                        continue
                
                # Wait for login to complete
                await page.wait_for_selector('.tv-header__user-menu-button', timeout=5000)
                logger.info("Successfully logged in to TradingView")
                logged_in = True
                break
            except Exception as e:
                logger.warning(f"Failed with selectors {email_selector}, {password_selector}: {str(e)}")
                continue
        
        if not logged_in:
            raise Exception("Could not find login form with any known selectors")
        
    except Exception as e:
        logger.error(f"Failed to log in to TradingView: {str(e)}")
        # Only take screenshot if we're on the main page
        await page.screenshot(path="/tmp/login-error.png")
        raise HTTPException(status_code=500, detail=f"Failed to log in to TradingView: {str(e)}")

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
            
            # Now navigate to news page
            url = f"https://www.tradingview.com/symbols/{symbol}/news/"
            logger.info(f"Navigating to {url}")
            await page.goto(url)
            
            logger.info("Waiting for news table")
            await page.wait_for_selector('.news-table', timeout=10000)
            
            logger.info("Finding first news article")
            first_news = page.locator('.news-table tr:first-child td.desc a')
            news_title = await first_news.text_content()
            news_link = await first_news.get_attribute('href')
            
            full_news_url = f"https://www.tradingview.com{news_link}"
            logger.info(f"Navigating to news article: {full_news_url}")
            await page.goto(full_news_url)
            
            logger.info("Waiting for article content")
            article = await page.wait_for_selector('article')
            article_content = await article.text_content()
            
            logger.info("Successfully scraped news")
            return {
                "title": news_title.strip(),
                "content": article_content.strip(),
                "url": full_news_url
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
async def receive_trading_signal(signal: Dict):
    try:
        # Log incoming signal
        logger.info(f"Received trading signal: {json.dumps(signal, indent=2)}")
        
        # Get the trading pair
        pair = signal.get('instrument')
        if not pair:
            raise HTTPException(status_code=400, detail="No trading pair provided")
        
        # Get news for the pair
        news = await get_news(pair)
        
        # Analyze sentiment
        sentiment = await analyze_sentiment(news['content'])
        
        # Combine all data
        combined_data = {
            "signal": signal,
            "news": news,
            "sentiment": sentiment,
            "timestamp": signal.get('timestamp', None)
        }
        
        return {
            "status": "success",
            "message": "Signal processed successfully",
            "data": combined_data
        }
    except Exception as e:
        logger.error(f"Error processing signal: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
