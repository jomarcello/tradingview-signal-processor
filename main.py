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
        await page.goto('https://www.tradingview.com/accounts/signin/', wait_until='networkidle', timeout=10000)
        
        # Wait for the page to load and stabilize
        logger.info("Waiting for page to stabilize")
        await page.wait_for_load_state('domcontentloaded')
        await page.wait_for_load_state('networkidle')
        
        # Take screenshot of initial state
        logger.info("Taking screenshot of initial state")
        await page.screenshot(path="/tmp/initial-state.png")
        
        # Log the current URL and content
        current_url = page.url
        content = await page.content()
        logger.info(f"Current URL: {current_url}")
        logger.info(f"Page content length: {len(content)} characters")
        logger.info(f"Page content preview: {content[:500]}...")
        
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
        
        # Log all available elements for debugging, including shadow DOM
        logger.info("Checking available elements in DOM:")
        elements = await main_frame.evaluate('''() => {
            function getAllElements(root) {
                const elements = Array.from(root.querySelectorAll('*'));
                const shadowElements = [];
                
                elements.forEach(el => {
                    if (el.shadowRoot) {
                        shadowElements.push(...getAllElements(el.shadowRoot));
                    }
                });
                
                return [...elements, ...shadowElements].filter(el => 
                    el.tagName === 'INPUT' || el.tagName === 'BUTTON'
                ).map(el => ({
                    tag: el.tagName,
                    type: el.type,
                    id: el.id,
                    name: el.name,
                    class: el.className,
                    shadowRoot: !!el.shadowRoot,
                    hidden: el.hidden,
                    display: window.getComputedStyle(el).display,
                    visibility: window.getComputedStyle(el).visibility
                }));
            }
            return getAllElements(document);
        }''')
        logger.info(f"Found elements: {json.dumps(elements, indent=2)}")
        
        # Wait for any dynamic content to load
        logger.info("Waiting for dynamic content")
        await page.wait_for_timeout(2000)
        
        # Try different selectors for email/password fields
        selectors = [
            ('input[name="username"]', 'input[name="password"]'),
            ('input[type="email"]', 'input[type="password"]'),
            ('#email-signin__user-name-input', '#email-signin__password-input'),
            ('form input[type="text"]', 'form input[type="password"]'),
            ('[name="username"]', '[name="password"]'),
            ('.tv-control-material-textbox__input', '.tv-control-material-textbox__input[type="password"]'),
            # Add more specific TradingView selectors
            ('input.tv-control-material-textbox__input[name="username"]', 'input.tv-control-material-textbox__input[name="password"]'),
            ('input[autocomplete="username"]', 'input[autocomplete="current-password"]')
        ]
        
        logged_in = False
        for email_selector, password_selector in selectors:
            try:
                logger.info(f"Trying selectors: {email_selector}, {password_selector}")
                
                # First check if elements exist using proper JavaScript syntax
                js_email_selector = email_selector.replace("'", "\\'")
                js_password_selector = password_selector.replace("'", "\\'")
                
                # Check in both regular DOM and shadow DOM
                email_check = f'''
                    () => {{
                        const el = document.querySelector('{js_email_selector}');
                        if (el) return true;
                        const shadowEls = Array.from(document.querySelectorAll('*'))
                            .filter(el => el.shadowRoot)
                            .map(el => el.shadowRoot.querySelector('{js_email_selector}'));
                        return shadowEls.some(el => el !== null);
                    }}
                '''
                password_check = f'''
                    () => {{
                        const el = document.querySelector('{js_password_selector}');
                        if (el) return true;
                        const shadowEls = Array.from(document.querySelectorAll('*'))
                            .filter(el => el.shadowRoot)
                            .map(el => el.shadowRoot.querySelector('{js_password_selector}'));
                        return shadowEls.some(el => el !== null);
                    }}
                '''
                
                email_exists = await main_frame.evaluate(email_check)
                password_exists = await main_frame.evaluate(password_check)
                
                if not email_exists or not password_exists:
                    logger.warning(f"Elements not found in DOM: email={email_exists}, password={password_exists}")
                    continue
                
                # Wait for and fill in email field
                email_elem = await main_frame.wait_for_selector(email_selector, timeout=2000, state='visible')
                if not email_elem:
                    logger.warning(f"Email field {email_selector} not visible")
                    continue
                    
                await email_elem.fill(TRADINGVIEW_EMAIL)
                logger.info("Filled email field")
                
                # Wait for and fill in password field
                password_elem = await main_frame.wait_for_selector(password_selector, timeout=2000, state='visible')
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
                    '.tv-button',
                    # Add more specific TradingView button selectors
                    'button.tv-button--primary[type="submit"]',
                    '[data-name="submit-button"]'
                ]
                
                for submit_selector in submit_buttons:
                    try:
                        logger.info(f"Trying to click submit button: {submit_selector}")
                        # First check if button exists using proper JavaScript syntax
                        js_submit_selector = submit_selector.replace("'", "\\'")
                        button_check = f'''
                            () => {{
                                const el = document.querySelector('{js_submit_selector}');
                                if (el) return true;
                                const shadowEls = Array.from(document.querySelectorAll('*'))
                                    .filter(el => el.shadowRoot)
                                    .map(el => el.shadowRoot.querySelector('{js_submit_selector}'));
                                return shadowEls.some(el => el !== null);
                            }}
                        '''
                        button_exists = await main_frame.evaluate(button_check)
                        if not button_exists:
                            logger.warning(f"Submit button {submit_selector} not found in DOM")
                            continue
                            
                        submit_elem = await main_frame.wait_for_selector(submit_selector, timeout=2000, state='visible')
                        if submit_elem:
                            # Take screenshot before clicking
                            logger.info("Taking screenshot before submit")
                            await page.screenshot(path="/tmp/before-submit.png")
                            await submit_elem.click()
                            logger.info("Clicked submit button")
                            break
                    except Exception as e:
                        logger.warning(f"Failed to click {submit_selector}: {str(e)}")
                        continue
                
                # Wait for login to complete
                logger.info("Waiting for login to complete")
                await page.wait_for_selector('.tv-header__user-menu-button', timeout=3000)
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
        logger.info("Taking error screenshot")
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
